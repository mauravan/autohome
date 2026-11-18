#include "sse_server.h"
#include "captive_portal.h"
#ifdef USE_CAPTIVE_PORTAL

#define CRLF_STR "\r\n"
#define CRLF_LEN (sizeof(CRLF_STR) - 1)

#include "esphome/core/application.h"
#include "esphome/core/log.h"
#include "esphome/components/json/json_util.h"

#include <atomic>
#include <cinttypes>
#include <cstring>
#include <memory>
#include <vector>
#include <cerrno>
#include <esp_http_server.h>
#include <esp_err.h>
#include <sys/socket.h>

namespace esphome::captive_portal {

static const char *const TAG = "captive_portal";

// ---------------------------------------------------------------------------
// sse_chunk (copied from esphome/components/web_server_idf/sse_chunk.cpp)
// ---------------------------------------------------------------------------

void for_each_chunk_piece(const char *message, size_t message_len, ChunkPieceSink sink, void *ctx) {
  if (message == nullptr) {
    sink(ctx, CHUNK_END, CHUNK_END_LEN);
    return;
  }
  const char *pos = message;
  const char *end = message + message_len;
  for (;;) {
    const size_t remaining = end - pos;
    const auto *n = static_cast<const char *>(memchr(pos, '\n', remaining));
    // Only a \r before the next \n can end this line, so the search stops there instead of
    // rescanning the rest of the message for every line
    const auto *r = static_cast<const char *>(memchr(pos, '\r', n != nullptr ? n - pos : remaining));
    if (n == nullptr && r == nullptr) {
      sink(ctx, pos, remaining);
      break;
    }
    const char *brk = (r != nullptr && (n == nullptr || r < n)) ? r : n;
    sink(ctx, pos, brk - pos);
    pos = brk + ((brk == r && brk + 1 == n) ? 2 : 1);
    if (pos >= end) {
      break;
    }
    sink(ctx, SSE_SEP, SSE_SEP_LEN);
  }
  sink(ctx, SSE_SUFFIX, SSE_SUFFIX_LEN);
}

size_t build_chunk_prefix(char *buf, size_t size, const char *event, uint32_t id, uint32_t reconnect, bool with_data) {
  size_t len = CHUNK_HDR_LEN;
  if (reconnect) {
    len = buf_append_printf(buf, size, len, "retry: %" PRIu32 "\r\n", reconnect);
  }
  if (id) {
    len = buf_append_printf(buf, size, len, "id: %" PRIu32 "\r\n", id);
  }
  if (event && *event) {
    len = buf_append_str(buf, size, len, "event: ");
    len = buf_append_str(buf, size, len, event);
    len = buf_append_str(buf, size, len, "\r\n");
  }
  if (with_data) {
    len = buf_append_str(buf, size, len, "data: ");
  }
  return len;
}

void write_chunk_header(char *buf, size_t chunk_len) {
  // Eight lowercase hex digits; the temp keeps the terminator format_hex_to writes out of buf
  char digits[9];
  format_hex_to(digits, static_cast<uint32_t>(chunk_len));
  std::memcpy(buf, digits, 8);
  buf[8] = '\r';
  buf[9] = '\n';
}

// ---------------------------------------------------------------------------
// send override copied from esphome/components/web_server_idf/web_server_idf.cpp
// ---------------------------------------------------------------------------
namespace {
// Non-blocking send function to prevent watchdog timeouts when TCP buffers are full
int nonblocking_send(httpd_handle_t hd, int sockfd, const char *buf, size_t buf_len, int flags) {
  if (buf == nullptr) {
    return HTTPD_SOCK_ERR_INVALID;
  }
  int ret = send(sockfd, buf, buf_len, flags | MSG_DONTWAIT);
  if (ret < 0) {
    const int err = errno;
    if (err == EAGAIN || err == EWOULDBLOCK) {
      return HTTPD_SOCK_ERR_TIMEOUT;
    }
    ESP_LOGD(TAG, "send error: errno %d", err);
    return HTTPD_SOCK_ERR_FAIL;
  }
  return ret;
}
}  // namespace

// ---------------------------------------------------------------------------
// AsyncEventSource / AsyncEventSourceResponse
// ---------------------------------------------------------------------------
AsyncEventSource::~AsyncEventSource() {
  LockGuard guard{this->pending_mutex_};
  for (auto *vec : {&this->sessions_, &this->pending_sessions_}) {
    for (auto *ses : *vec) {
      delete ses;  // NOLINT(cppcoreguidelines-owning-memory)
    }
  }
}

void AsyncEventSource::handleRequest(AsyncWebServerRequest *request) {
  // Httpd task: set up the live httpd_req_t and park the session; main loop does the rest.
  // NOLINTNEXTLINE(cppcoreguidelines-owning-memory,clang-analyzer-cplusplus.NewDeleteLeaks)
  auto *rsp = new AsyncEventSourceResponse(request, this, this->portal_);
  {
    LockGuard guard{this->pending_mutex_};
    this->pending_sessions_.push_back(rsp);
    this->has_pending_sessions_.store(true, std::memory_order_release);
  }
  this->portal_->enable_loop_soon_any_context();
}

// clang-analyzer traces a false-positive leak path from loop() through
// adopt_pending_sessions_main_loop_() into start_session_main_loop_() and
// finally ArduinoJson. Suppress along the entire in-our-code call chain.
// NOLINTBEGIN(clang-analyzer-cplusplus.NewDeleteLeaks)
bool AsyncEventSource::loop() {
  // Fast path: one atomic load per tick. Slow path is out-of-line on connect.
  if (this->has_pending_sessions_.load(std::memory_order_acquire)) {
    this->adopt_pending_sessions_main_loop_();
  }

  // Clean up dead sessions safely
  // This follows the ESP-IDF pattern where free_ctx marks resources as dead
  // and the main loop handles the actual cleanup to avoid race conditions
  for (size_t i = 0; i < this->sessions_.size();) {
    auto *ses = this->sessions_[i];
    // If the session has a dead socket (marked by destroy callback)
    if (ses->safe_to_delete_()) {
      // destroy() already logged the close with the fd; don't double-log here.
      delete ses;  // NOLINT(cppcoreguidelines-owning-memory)
      // Remove by swapping with last element (O(1) removal, order doesn't matter for sessions)
      this->sessions_[i] = this->sessions_.back();
      this->sessions_.pop_back();
    } else {
      ses->loop();
      ++i;
    }
  }
  // A session still waiting for httpd to commit its context keeps the loop alive too
  return !this->sessions_.empty() || this->has_pending_sessions_.load(std::memory_order_acquire);
}

void AsyncEventSource::adopt_pending_sessions_main_loop_() {
  std::vector<AsyncEventSourceResponse *> incoming;
  {
    LockGuard guard{this->pending_mutex_};
    incoming.swap(this->pending_sessions_);
    this->has_pending_sessions_.store(false, std::memory_order_relaxed);
  }
  for (auto *rsp : incoming) {
    // Already disconnected? Drop it; skip session start on a dead session.
    if (rsp->safe_to_delete_()) {
      delete rsp;  // NOLINT(cppcoreguidelines-owning-memory)
      continue;
    }
    // httpd commits the session context only after the creating handler returns, so stay
    // pending until then; httpd_req_cleanup() always commits it or calls destroy()
    if (httpd_sess_get_ctx(rsp->hd_, rsp->fd_.load()) != rsp) {
      LockGuard guard{this->pending_mutex_};
      this->pending_sessions_.push_back(rsp);
      this->has_pending_sessions_.store(true, std::memory_order_release);
      continue;
    }
    this->sessions_.push_back(rsp);
    rsp->start_session_main_loop_();
  }
}
// NOLINTEND(clang-analyzer-cplusplus.NewDeleteLeaks)

void AsyncEventSource::try_send_nodefer(const char *message, size_t message_len, const char *event, uint32_t id,
                                        uint32_t reconnect) {
  for (auto *ses : this->sessions_) {
    if (ses->fd_.load() != 0) {  // Skip dead sessions
      ses->try_send_nodefer(message, message_len, event, id, reconnect);
    }
  }
}

void AsyncEventSource::deferrable_send_state(void *source, const char *event_type,
                                             message_generator_t *message_generator) {
  // Skip if no connected clients to avoid unnecessary processing
  if (this->empty())
    return;
  for (auto *ses : this->sessions_) {
    if (ses->fd_.load() != 0) {  // Skip dead sessions
      ses->deferrable_send_state(source, event_type, message_generator);
    }
  }
}

AsyncEventSourceResponse::AsyncEventSourceResponse(const AsyncWebServerRequest *request,
                                                   esphome::captive_portal::AsyncEventSource *server,
                                                   esphome::captive_portal::CaptivePortal *portal)
    : server_(server), portal_(portal) {
  // Httpd task only. start_session_main_loop_() sends the greeting and starts the iterator.
  httpd_req_t *req = *request;

  httpd_resp_set_status(req, HTTPD_200);
  httpd_resp_set_type(req, "text/event-stream");
  httpd_resp_set_hdr(req, "Cache-Control", "no-cache");
  httpd_resp_set_hdr(req, "Connection", "keep-alive");

  httpd_resp_send_chunk(req, CRLF_STR, CRLF_LEN);

  req->sess_ctx = this;
  req->free_ctx = AsyncEventSourceResponse::destroy;

  this->hd_ = req->handle;
  this->fd_.store(httpd_req_to_sockfd(req));

  // Use non-blocking send to prevent watchdog timeouts when TCP buffers are full
  httpd_sess_set_send_override(this->hd_, this->fd_.load(), nonblocking_send);
}

// NOLINTBEGIN(clang-analyzer-cplusplus.NewDeleteLeaks) false positive with ArduinoJson
void AsyncEventSourceResponse::start_session_main_loop_() {
  auto *portal = this->portal_;

  // The tcp send buffer is empty on connect. A refusal is a closing session or a failed tail
  // allocation; nothing retries the greeting, so close and let the client reconnect.
  auto message = portal->get_config_json();
  if (!this->try_send_nodefer(message.c_str(), message.size(), "ping", millis(), 30000)) {
    ESP_LOGW(TAG, "Config not sent to fd %d", this->fd_.load());
    this->request_close_();
    return;
  }

  portal->send_initial_states_(this);
}
// NOLINTEND(clang-analyzer-cplusplus.NewDeleteLeaks)

void AsyncEventSourceResponse::destroy(void *ptr) {
  auto *rsp = static_cast<AsyncEventSourceResponse *>(ptr);
  int fd = rsp->fd_.exchange(0);  // Atomically get and clear fd
  ESP_LOGD(TAG, "Event source connection closed (fd: %d)", fd);
  // Mark as dead - will be cleaned up in the main loop
  // Note: We don't delete or remove from set here to avoid race conditions
  // httpd will call our custom close_fn (safe_close_with_shutdown) which handles
  // shutdown() before close() to prevent lwIP race conditions
}

// helper for allowing only unique entries in the queue
void AsyncEventSourceResponse::deq_push_back_with_dedup_(void *source, message_generator_t *message_generator) {
  DeferredEvent item(source, message_generator);

  // Use range-based for loop instead of std::find_if to reduce template instantiation overhead and binary size
  for (auto &event : this->deferred_queue_) {
    if (event == item) {
      return;  // Already in queue, no need to update since items are equal
    }
  }
  this->deferred_queue_.push_back(item);
}

void AsyncEventSourceResponse::process_deferred_queue_() {
  if (this->close_requested_) {
    return;
  }
  while (!deferred_queue_.empty()) {
    DeferredEvent &de = deferred_queue_.front();
    if (this->send_json_(de.source_, de.message_generator_)) {
      if (this->close_requested_ || deferred_queue_.empty()) {
        return;
      }
      // O(n) but memory efficiency is more important than speed here which is why std::vector was chosen
      deferred_queue_.erase(deferred_queue_.begin());
    } else {
      break;
    }
  }
}

void AsyncEventSourceResponse::request_close_() {
  if (!this->close_requested_) {
    this->close_requested_ = true;
    this->deferred_queue_.clear();
    this->tail_.reset();
    this->tail_cap_ = 0;
    this->tail_len_ = 0;
    this->tail_sent_ = 0;
    this->next_close_attempt_ms_ = App.get_loop_component_start_time();
  }

  this->process_close_();
}

void AsyncEventSourceResponse::process_close_() {
  if (!this->close_requested_ || this->close_work_queued_.load(std::memory_order_acquire)) {
    return;
  }
  const int fd = this->fd_.load();
  if (fd == 0) {
    return;
  }

  const uint32_t now = App.get_loop_component_start_time();
  if (static_cast<int32_t>(now - this->next_close_attempt_ms_) < 0) {
    return;
  }

  // Queue an identity-checked shutdown on the HTTPD task. The public
  // httpd_sess_trigger_close() queues only a reusable fd/session slot and can
  // therefore close a new client if the original peer disconnects meanwhile.
  this->close_work_queued_.store(true, std::memory_order_release);
  const esp_err_t err = httpd_queue_work(this->hd_, &AsyncEventSourceResponse::close_session_work, this);
  this->next_close_attempt_ms_ = now + (err == ESP_OK ? CLOSE_CONFIRM_INTERVAL_MS : CLOSE_RETRY_INTERVAL_MS);
  if (err == ESP_OK) {
    return;
  }

  this->close_work_queued_.store(false, std::memory_order_release);
  if (!this->close_retry_warning_logged_) {
    ESP_LOGW(TAG, "Failed to queue EventSource close (%s); retrying", esp_err_to_name(err));
    this->close_retry_warning_logged_ = true;
  }
}

void AsyncEventSourceResponse::refresh_lru_() {
  // httpd only advances a session's LRU counter when a request arrives, and an event stream receives one
  // request ever, so the purge that frees a socket for a new client would evict the live streams first.
  // The HTTPD task owns the session table, so the refresh runs there.
  // A stalled stream is the socket the purge should take, and a zeroed fd has no session left to refresh.
  if (this->send_failure_started_ms_ != 0 || this->fd_.load() == 0)
    return;
  const uint32_t now = App.get_loop_component_start_time();
  if (now - this->last_lru_refresh_ms_ < LRU_REFRESH_INTERVAL_MS ||
      this->lru_work_queued_.load(std::memory_order_acquire)) {
    return;
  }
  this->last_lru_refresh_ms_ = now;  // a full queue also waits for the next interval
  this->lru_work_queued_.store(true, std::memory_order_release);
  if (httpd_queue_work(this->hd_, &AsyncEventSourceResponse::refresh_lru_work, this) != ESP_OK) {
    this->lru_work_queued_.store(false, std::memory_order_release);
  }
}

void AsyncEventSourceResponse::refresh_lru_work(void *arg) {
  auto *response = static_cast<AsyncEventSourceResponse *>(arg);
  const int fd = response->fd_.load();
  if (response->owns_session_(fd)) {
    httpd_sess_update_lru_counter(response->hd_, fd);
  }
  // Release self only after the HTTPD-task callback has finished every access.
  response->lru_work_queued_.store(false, std::memory_order_release);
}

void AsyncEventSourceResponse::close_session_work(void *arg) {
  auto *response = static_cast<AsyncEventSourceResponse *>(arg);
  const int fd = response->fd_.load();
  if (response->owns_session_(fd)) {
    // The HTTPD task remains the session owner. Shutting the socket down makes
    // its next select/recv path delete the session and invoke destroy().
    shutdown(fd, SHUT_RDWR);
  }

  // Release self only after the HTTPD-task callback has finished every access.
  response->close_work_queued_.store(false, std::memory_order_release);
}

ssize_t AsyncEventSourceResponse::send_(struct iovec *iov, int iovcnt) {
  // httpd frees a session before closing its socket, so the fd may already be a new client's.
  // Treated as would-block; the stall timer ends a session that never becomes ours again.
  const int fd = this->fd_.load();
  if (!this->owns_session_(fd)) {
    return 0;
  }
  struct msghdr msg {};
  msg.msg_iov = iov;
  msg.msg_iovlen = iovcnt;
  const ssize_t sent = sendmsg(fd, &msg, MSG_DONTWAIT);
  if (sent >= 0) {
    return sent;
  }
  const int err = errno;
  if (err == EAGAIN || err == EWOULDBLOCK) {
    return 0;
  }
  ESP_LOGD(TAG, "send error: errno %d", err);
  this->request_close_();
  return -1;
}

void AsyncEventSourceResponse::drain_tail_() {
  if (this->sending_ || this->close_requested_ || this->tail_len_ == 0) {
    return;
  }
  SendGuard guard{*this};

  const size_t remaining = this->tail_len_ - this->tail_sent_;
  struct iovec iov = {this->tail_.get() + this->tail_sent_, remaining};
  const ssize_t sent = this->send_(&iov, 1);
  if (sent < 0) {
    return;
  }
  if (sent == 0) {
    // Socket buffer full, try again later
    // NOTE: Similar logic exists in the ESPHome web_server component.
    // The IDF path is intentionally time-based and closes through HTTPD to preserve session ownership.
    const uint32_t now = App.get_loop_component_start_time();
    if (this->send_failure_started_ms_ == 0) {
      this->send_failure_started_ms_ = now != 0 ? now : 1;  // Reserve zero for no stall.
    }
    if (static_cast<int32_t>(now - (this->send_failure_started_ms_ + SEND_STALL_TIMEOUT_MS)) >= 0) {
      ESP_LOGW(TAG, "Closing stuck EventSource connection after %" PRIu32 " ms without send progress",
               now - this->send_failure_started_ms_);
      this->request_close_();
    }
    return;
  }

  this->send_failure_started_ms_ = 0;
  this->tail_sent_ += sent;
  if (this->tail_sent_ < this->tail_len_) {
    ESP_LOGV(TAG, "Partial send: %zd/%zu bytes (total: %u/%u)", sent, remaining, this->tail_sent_, this->tail_len_);
    return;
  }
  // Fully sent; the storage stays for the next stall
  this->tail_len_ = 0;
}

bool AsyncEventSourceResponse::reserve_tail_(size_t len) {
  if (this->tail_cap_ >= len) {
    return true;
  }
  if (len > TAIL_MAX_SIZE) {
    return false;
  }
  // Nothing is pending while the tail grows, so free the old block first. PREFER_INTERNAL keeps
  // the tail where plain new put it.
  this->tail_.reset();
  this->tail_ = RAMAllocator<uint8_t>(RAMAllocator<uint8_t>::PREFER_INTERNAL).make_unique_array_for_overwrite(len);
  this->tail_cap_ = this->tail_ ? len : 0;
  return this->tail_cap_ != 0;
}

bool AsyncEventSourceResponse::stash_chunk_(const char *prefix, size_t prefix_len, const char *message,
                                            size_t message_len, size_t total, size_t sent) {
  // A log event of nothing but line breaks is the largest chunk; reserve_tail_() must never
  // refuse it for size, only for memory
  static_assert(SSE_SEP_LEN * LOG_EVENT_MAX_LEN + PREFIX_BUF_SIZE + SSE_SUFFIX_LEN <= TAIL_MAX_SIZE,
                "the log cut in sse_server.h must keep a worst case log event inside the tail ceiling");
  if (!this->reserve_tail_(total)) {
    if (sent != 0) {
      // Part of the chunk is on the wire, so the stream is broken and the client has to go
      ESP_LOGW(TAG, "Cannot buffer a %zu byte chunk, closing", total);
      this->request_close_();
    } else {
      this->tail_alloc_failed_(total);  // nothing on the wire, the caller retries on the stall clock
    }
    return false;
  }
  uint8_t *dst = this->tail_.get();
  std::memcpy(dst, prefix, prefix_len);
  dst += prefix_len;
  for_each_chunk_piece(
      message, message_len,
      [](void *ctx, const char *piece, size_t len) {
        auto &out = *static_cast<uint8_t **>(ctx);
        std::memcpy(out, piece, len);
        out += len;
      },
      &dst);
  this->tail_len_ = total;
  this->tail_sent_ = sent;
  return true;
}

void AsyncEventSourceResponse::loop() {
  if (this->close_requested_) {
    this->process_close_();
    return;
  }
  this->refresh_lru_();
  drain_tail_();
  process_deferred_queue_();
  if (this->close_requested_)
    return;
}

#if defined(__GNUC__) && !defined(__clang__) && __GNUC__ >= 14 && defined(__OPTIMIZE_SIZE__)
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wstack-usage="  // the one frame that holds the JSON arena
#endif
AsyncEventSourceResponse::JsonPrepareResult AsyncEventSourceResponse::prepare_json_(void *source,
                                                                                    message_generator_t *generator,
                                                                                    char *buffer, size_t *size_out) {
  // Log lines emitted while the generator runs are dropped for this session: on the large path they would fill
  // tail_ before it is overwritten, and on the small path they would go out ahead of the event being built.
  SendGuard guard{*this};
  json::JsonArena<json::JSON_ARENA_SIZE> arena;  // NOLINT
  json::JsonBuilder builder(&arena);
  generator(this->portal_, source, builder);
  *size_out = builder.serialize_to(buffer, JSON_BUF_SIZE);
  if (*size_out < JSON_BUF_SIZE) {
    return JsonPrepareResult::JSON_PREPARE_RESULT_BUFFER;
  }

  char prefix[PREFIX_BUF_SIZE];
  const size_t prefix_len = build_chunk_prefix(prefix, sizeof(prefix), "state", 0, 0, true);

  // Nothing reaches the wire until the complete document and its framing are owned by the caller.
  size_t json_len = 0;
  size_t cap = std::max<size_t>(JSON_BUF_SIZE * 2, this->tail_cap_);
  for (;;) {
    if (!this->reserve_tail_(cap)) {
      *size_out = cap;
      return JsonPrepareResult::JSON_PREPARE_RESULT_NO_MEMORY;
    }
    const size_t room = cap - prefix_len - SSE_SUFFIX_LEN;
    json_len = builder.serialize_to(reinterpret_cast<char *>(this->tail_.get()) + prefix_len, room);
    if (json_len < room) {
      break;
    }
    if (cap >= TAIL_MAX_SIZE) {
      *size_out = room;
      return JsonPrepareResult::JSON_PREPARE_RESULT_TOO_LARGE;
    }
    cap = std::min<size_t>(cap * 2, TAIL_MAX_SIZE);
  }

  const size_t total = prefix_len + json_len + SSE_SUFFIX_LEN;
  write_chunk_header(prefix, total - CHUNK_HDR_LEN - CHUNK_END_LEN);
  uint8_t *dst = this->tail_.get();
  std::memcpy(dst, prefix, prefix_len);
  std::memcpy(dst + prefix_len + json_len, SSE_SUFFIX, SSE_SUFFIX_LEN);
  this->tail_len_ = total;
  this->tail_sent_ = 0;
  return JsonPrepareResult::JSON_PREPARE_RESULT_TAIL;
}
#if defined(__GNUC__) && !defined(__clang__) && __GNUC__ >= 14 && defined(__OPTIMIZE_SIZE__)
#pragma GCC diagnostic pop
#endif

bool AsyncEventSourceResponse::send_json_(void *source, message_generator_t *generator) {
  if (!this->ready_to_send_()) {
    return false;
  }
  char buffer[JSON_BUF_SIZE];
  size_t size;
  const auto result = this->prepare_json_(source, generator, buffer, &size);
  switch (result) {
    case JsonPrepareResult::JSON_PREPARE_RESULT_BUFFER:
      return this->try_send_nodefer(buffer, size, "state");
    case JsonPrepareResult::JSON_PREPARE_RESULT_TAIL:
      this->drain_tail_();
      return true;
    case JsonPrepareResult::JSON_PREPARE_RESULT_NO_MEMORY: {
      SendGuard guard{*this};
      this->tail_alloc_failed_(size);
      return false;
    }
    case JsonPrepareResult::JSON_PREPARE_RESULT_TOO_LARGE: {
      SendGuard guard{*this};
      ESP_LOGW(TAG, "State event does not fit %zu bytes, dropped", size);
      this->tail_.reset();
      this->tail_cap_ = 0;
      this->send_failure_started_ms_ = 0;
      return true;
    }
  }
  return false;
}

void AsyncEventSourceResponse::tail_alloc_failed_(size_t cap) {
  // Same stall clock as a socket that stops draining, so a session cannot retry forever
  const uint32_t now = App.get_loop_component_start_time();
  if (this->send_failure_started_ms_ == 0) {
    this->send_failure_started_ms_ = now != 0 ? now : 1;  // Reserve zero for no stall.
    ESP_LOGW(TAG, "No memory for a %zu byte chunk", cap);
    return;
  }
  if (static_cast<int32_t>(now - (this->send_failure_started_ms_ + SEND_STALL_TIMEOUT_MS)) >= 0) {
    ESP_LOGW(TAG, "Closing EventSource after %" PRIu32 " ms without memory", now - this->send_failure_started_ms_);
    this->request_close_();
  }
}

bool AsyncEventSourceResponse::ready_to_send_() {
  if (this->sending_ || this->fd_.load() == 0 || this->close_requested_) {
    return false;
  }
  drain_tail_();
  return !this->close_requested_ && this->tail_len_ == 0;
}

bool AsyncEventSourceResponse::try_send_nodefer(const char *message, size_t message_len, const char *event, uint32_t id,
                                                uint32_t reconnect) {
  if (!this->ready_to_send_()) {
    return false;
  }
  SendGuard guard{*this};

  // Everything after the prefix goes out straight from the caller's buffer
  char prefix[PREFIX_BUF_SIZE];
  const size_t prefix_len = build_chunk_prefix(prefix, sizeof(prefix), event, id, reconnect, message != nullptr);
  if (message == nullptr && prefix_len == CHUNK_HDR_LEN) {
    return true;  // Match ESPAsyncWebServer: nothing to send
  }
  if (prefix_len >= PREFIX_BUF_SIZE - 1) {
    // The appenders truncate silently, which would put a malformed event on the wire
    ESP_LOGW(TAG, "Event name too long, dropped");
    return true;
  }

  // Gather list: the prefix, then the data lines and their separators from the message
  struct Gather {
    struct iovec iov[MAX_SEND_IOV];  // left uninitialized on purpose
    int iovcnt{1};
    size_t total{0};
    bool fits{true};
  } g;
  g.total = prefix_len;
  for_each_chunk_piece(
      message, message_len,
      [](void *ctx, const char *piece, size_t len) {
        auto &g = *static_cast<Gather *>(ctx);
        g.total += len;
        if (len == 0) {
          return;
        }
        if (g.iovcnt == MAX_SEND_IOV) {
          g.fits = false;
          return;
        }
        g.iov[g.iovcnt++] = {const_cast<char *>(piece), len};
      },
      &g);
  // The header and the terminator are not part of the chunk length
  write_chunk_header(prefix, g.total - CHUNK_HDR_LEN - CHUNK_END_LEN);
  g.iov[0] = {prefix, prefix_len};

  // A message with more lines than the list holds skips straight to the tail
  const ssize_t sent = g.fits ? this->send_(g.iov, g.iovcnt) : 0;
  if (sent < 0) {
    return false;
  }
  if (static_cast<size_t>(sent) == g.total) {
    this->send_failure_started_ms_ = 0;  // progress, whichever stall clock was running
    return true;
  }
  // The caller's buffers do not outlive this call, so keep the chunk and continue from loop()
  return this->stash_chunk_(prefix, prefix_len, message, message_len, g.total, sent);
}

void AsyncEventSourceResponse::deferrable_send_state(void *source, const char *event_type,
                                                     message_generator_t *message_generator) {
  if (source == nullptr)
    return;
  if (event_type == nullptr)
    return;
  if (message_generator == nullptr)
    return;

  if (0 != strcmp(event_type, "state_detail_all") && 0 != strcmp(event_type, "state")) {
    ESP_LOGE(TAG, "Can't defer non-state event");
  }

  drain_tail_();
  process_deferred_queue_();

  if (this->close_requested_) {
    return;
  }

  if (this->tail_len_ != 0 || !deferred_queue_.empty()) {
    // outgoing event buffer or deferred queue still not empty which means downstream tcp send buffer full, no point
    // trying to send first
    deq_push_back_with_dedup_(source, message_generator);
  } else {
    // A send error closes the session and clears the queue; nothing is queued after that
    if (!this->send_json_(source, message_generator) && !this->close_requested_) {
      deq_push_back_with_dedup_(source, message_generator);
    }
  }
}

}  // namespace esphome::captive_portal

#endif
