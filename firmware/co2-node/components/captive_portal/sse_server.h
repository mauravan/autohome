#pragma once
#include "esphome/core/defines.h"
#ifdef USE_CAPTIVE_PORTAL

#include "esphome/core/helpers.h"
#include "esphome/core/string_ref.h"
#include "esphome/components/json/json_util.h"
#include "esphome/components/web_server_base/web_server_base.h"

#include <atomic>
#include <cstddef>
#include <cstdint>
#include <memory>
#include <vector>

struct iovec;  // NOLINT(readability-identifier-naming) - forward decl of lwip's gather list entry

namespace esphome::captive_portal {

class CaptivePortal;

// ============================================================================
// sse_chunk — wire framing of one Server-Sent-Events event inside the chunked
// /events response. Copied from esphome/components/web_server_idf/sse_chunk.*.
// ============================================================================

// Wire framing of one Server-Sent-Events event inside the chunked /events response:
//   "%08x\r\n" + fields + "data: " line ["\r\ndata: " line]... "\r\n" + "\r\n" + "\r\n"
// The chunk header and the final CRLF (the chunk terminator) do not count toward the
// chunk length; everything between them does.

// HTTP chunk header "%08x\r\n"
constexpr size_t CHUNK_HDR_LEN = 10;
// Chunk terminator, also the only piece of a null message (no data line, no blank line)
constexpr char CHUNK_END[] = "\r\n";
constexpr size_t CHUNK_END_LEN = sizeof(CHUNK_END) - 1;
// Between two data lines: the end of one and the prefix of the next
constexpr char SSE_SEP[] = "\r\ndata: ";
constexpr size_t SSE_SEP_LEN = sizeof(SSE_SEP) - 1;
// End of the last data line, the blank line ending the event, and the chunk terminator
constexpr char SSE_SUFFIX[] = "\r\n\r\n\r\n";
constexpr size_t SSE_SUFFIX_LEN = sizeof(SSE_SUFFIX) - 1;

// Receives one piece of the chunk; ctx is whatever the caller passed to for_each_chunk_piece()
using ChunkPieceSink = void (*)(void *ctx, const char *piece, size_t len);

// Calls sink for each piece after the prefix: data lines split on \n, \r or \r\n with SSE_SEP
// between them and SSE_SUFFIX after the last (as ESPAsyncWebServer: a trailing break adds no
// empty line, an inner one is kept). A null message yields only the chunk terminator.
void for_each_chunk_piece(const char *message, size_t message_len, ChunkPieceSink sink, void *ctx);

// Writes the chunk header placeholder, the retry/id/event lines and, with_data, the first
// "data: " into buf. Returns the prefix length; size - 1 or more means the event name did not fit.
size_t build_chunk_prefix(char *buf, size_t size, const char *event, uint32_t id, uint32_t reconnect, bool with_data);

// Fills the header placeholder at the start of buf once the chunk length is known
void write_chunk_header(char *buf, size_t chunk_len);

// ============================================================================
// SSE transport — forked from esphome/components/web_server_idf/web_server_idf.{h,cpp}.
// The only behavioural change: owner is esphome::captive_portal::CaptivePortal (was
// esphome::web_server::WebServer), and the greeting is sent by the portal itself
// (send_initial_states_) instead of walking a ListEntitiesIterator.
// ============================================================================

class AsyncEventSource;
class AsyncEventSourceResponse;

// A log line is capped by the portal before it reaches the wire.
constexpr size_t LOG_EVENT_MAX_LEN = 512;

using message_generator_t = void(esphome::captive_portal::CaptivePortal *, void *, json::JsonBuilder &);

/*
  This class holds a pointer to the source component that wants to publish a state event, and a pointer to a function
  that will lazily generate that event.  The two pointers allow dedup in the deferred queue if multiple publishes for
  the same component are backed up, and take up only two pointers of memory.  The entry in the deferred queue (a
  std::vector) is the DeferredEvent instance itself (not a pointer to one elsewhere in heap) so still only two
  pointers per entry (and no heap fragmentation).  Even 100 backed up events (you'd have to have at least 100 sensors
  publishing because of dedup) would take up only 0.8 kB.
*/
struct DeferredEvent {
  friend class AsyncEventSourceResponse;

 protected:
  void *source_;
  message_generator_t *message_generator_;

 public:
  DeferredEvent(void *source, message_generator_t *message_generator)
      : source_(source), message_generator_(message_generator) {}
  bool operator==(const DeferredEvent &test) const {
    return (source_ == test.source_ && message_generator_ == test.message_generator_);
  }
};
static_assert(sizeof(DeferredEvent) == sizeof(void *) + sizeof(message_generator_t *),
              "DeferredEvent should have no padding");

class AsyncEventSourceResponse {
  friend class AsyncEventSource;

 public:
  bool try_send_nodefer(const char *message, size_t message_len, const char *event = nullptr, uint32_t id = 0,
                        uint32_t reconnect = 0);
  void deferrable_send_state(void *source, const char *event_type, message_generator_t *message_generator);
  void loop();

 protected:
  AsyncEventSourceResponse(const AsyncWebServerRequest *request, esphome::captive_portal::AsyncEventSource *server,
                           esphome::captive_portal::CaptivePortal *portal);

  // Main-loop only: sends initial ping/config, starts entity iterator.
  void start_session_main_loop_();

  void deq_push_back_with_dedup_(void *source, message_generator_t *message_generator);
  void process_deferred_queue_();
  // A new chunk may go out: not re-entered from a log line, session alive, tail empty
  bool ready_to_send_();
  // Non-blocking gather write. Returns bytes written, 0 on would-block or a socket that is not
  // ours, -1 after requesting the close on any other error.
  ssize_t send_(struct iovec *iov, int iovcnt);
  // Push what is left of the chunk in tail_ to the socket; owns the stall timer.
  void drain_tail_();
  // Grow tail_ to hold len bytes, kept at its high-water mark. False on OOM.
  bool reserve_tail_(size_t len);
  // Keep the whole chunk in tail_ and continue from sent; false when the tail cannot be allocated.
  bool stash_chunk_(const char *prefix, size_t prefix_len, const char *message, size_t message_len, size_t total,
                    size_t sent);
  // Send a state event; JSON too large for the stack buffer is serialized into tail_ instead
  bool send_json_(void *source, message_generator_t *generator);
  enum class JsonPrepareResult : uint8_t {
    JSON_PREPARE_RESULT_BUFFER,
    JSON_PREPARE_RESULT_TAIL,
    JSON_PREPARE_RESULT_NO_MEMORY,
    JSON_PREPARE_RESULT_TOO_LARGE,
  };
  // Keep the arena out of the caller's frame so it is gone before the state send.
  // size_out: BUFFER = JSON length, NO_MEMORY = requested tail capacity, TOO_LARGE = available JSON room;
  // unused for TAIL.
  JsonPrepareResult __attribute__((noinline))
  prepare_json_(void *source, message_generator_t *generator, char *buffer, size_t *size_out);
  // Warn once, and close the session once the stall timeout passes with no memory for the tail
  void tail_alloc_failed_(size_t cap);
  void request_close_();

  // A log line emitted inside a send re-enters try_send_nodefer on this session; refuse it
  struct SendGuard {
    AsyncEventSourceResponse &owner;
    explicit SendGuard(AsyncEventSourceResponse &owner) : owner(owner) { owner.sending_ = true; }
    ~SendGuard() { this->owner.sending_ = false; }
  };
  void process_close_();
  static void close_session_work(void *arg);
  void refresh_lru_();
  static void refresh_lru_work(void *arg);
  // httpd frees a session before closing its socket, so the fd may already belong to a new client
  bool owns_session_(int fd) const { return fd != 0 && httpd_sess_get_ctx(this->hd_, fd) == this; }

  // Deletable only after destroy() zeroed fd_ and no queued HTTPD work still references this object.
  bool safe_to_delete_() const {
    return this->fd_.load() == 0 && !this->close_work_queued_.load(std::memory_order_acquire) &&
           !this->lru_work_queued_.load(std::memory_order_acquire);
  }

  static void destroy(void *p);
  AsyncEventSource *server_;
  httpd_handle_t hd_{};
  std::atomic<int> fd_{};
  std::vector<DeferredEvent> deferred_queue_;
  esphome::captive_portal::CaptivePortal *portal_;
  // One chunk the socket did not take whole, allocated on the first stall; the only heap use
  // on the send path
  RAMUniquePtr<uint8_t[]> tail_;
  uint32_t send_failure_started_ms_{0};  // Zero means no send stall in progress.
  uint32_t next_close_attempt_ms_{0};
  uint32_t last_lru_refresh_ms_{0};
  uint16_t tail_cap_{0};
  uint16_t tail_len_{0};  // Zero means nothing pending
  uint16_t tail_sent_{0};
  // Set on the main loop before queueing close work, cleared by the HTTPD-task callback when done.
  std::atomic<bool> close_work_queued_{false};
  std::atomic<bool> lru_work_queued_{false};
  // Main-loop only; the HTTPD task never reads or writes these flags.
  bool close_requested_{false};
  bool close_retry_warning_logged_{false};
  bool sending_{false};
  // The longest multi line log message in the tree (a climate dump_config) has 22 lines; a
  // longer one goes through the tail
  static constexpr size_t MAX_SEND_LINES = 22;
  static constexpr size_t MAX_SEND_IOV = 1 + 2 * MAX_SEND_LINES;
  // Chunk header, retry/id/event lines and the first "data: "
  static constexpr size_t PREFIX_BUF_SIZE = 128;

  // Stack buffer for a state event's JSON; a larger document is serialized into the tail
  static constexpr size_t JSON_BUF_SIZE = 1024;
  // Same ceiling JsonBuilder::serialize() applies (max_heap_size in json_util.cpp); a larger
  // document is dropped before anything is on the wire
  static constexpr size_t JSON_MAX_SIZE = 5120;
  // Most RAM a stalled session keeps: the largest state document plus any accepted framing
  static constexpr size_t TAIL_MAX_SIZE = JSON_MAX_SIZE + PREFIX_BUF_SIZE + SSE_SUFFIX_LEN;
  static constexpr uint32_t SEND_STALL_TIMEOUT_MS = 20000;
  static constexpr uint32_t CLOSE_RETRY_INTERVAL_MS = 250;
  static constexpr uint32_t CLOSE_CONFIRM_INTERVAL_MS = 1000;
  static constexpr uint32_t LRU_REFRESH_INTERVAL_MS = 1000;
};

using AsyncEventSourceClient = AsyncEventSourceResponse;

class AsyncEventSource : public AsyncWebHandler {
  friend class AsyncEventSourceResponse;

 public:
  AsyncEventSource(StringRef url, esphome::captive_portal::CaptivePortal *portal) : url_(url), portal_(portal) {}
  ~AsyncEventSource() override;

  // NOLINTNEXTLINE(readability-identifier-naming)
  bool canHandle(AsyncWebServerRequest *request) const override {
    if (request->method() != HTTP_GET)
      return false;
    char url_buf[AsyncWebServerRequest::URL_BUF_SIZE];
    return request->url_to(url_buf) == this->url_;
  }
  // NOLINTNEXTLINE(readability-identifier-naming)
  void handleRequest(AsyncWebServerRequest *request) override;
  void try_send_nodefer(const char *message, size_t message_len, const char *event = nullptr, uint32_t id = 0,
                        uint32_t reconnect = 0);
  void deferrable_send_state(void *source, const char *event_type, message_generator_t *message_generator);
  /// Returns true if there are sessions remaining (including pending cleanup).
  bool loop();
  bool empty() { return this->count() == 0; }

  size_t count() const { return this->sessions_.size(); }

 protected:
  // Cold path: move sessions from pending_sessions_ into sessions_ and greet each one.
  void __attribute__((noinline, cold)) adopt_pending_sessions_main_loop_();

  StringRef url_;  // Must outlive this object (string literal)
  // Main-loop only. Vector: SSE sessions are 1-5 connections, linear search beats set.
  std::vector<AsyncEventSourceResponse *> sessions_;
  // Httpd-task intake; guarded by pending_mutex_, gated by has_pending_sessions_.
  std::vector<AsyncEventSourceResponse *> pending_sessions_;
  Mutex pending_mutex_;
  esphome::captive_portal::CaptivePortal *portal_;
  std::atomic<bool> has_pending_sessions_{false};
};

}  // namespace esphome::captive_portal

#endif