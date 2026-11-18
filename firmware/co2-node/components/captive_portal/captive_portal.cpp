#include "captive_portal.h"
#ifdef USE_CAPTIVE_PORTAL
#include "esphome/core/log.h"
#include "esphome/core/application.h"
#include "esphome/core/helpers.h"
#include "esphome/core/string_ref.h"
#include "esphome/components/json/json_util.h"
#include "esphome/components/wifi/scan_list.h"
#include "esphome/components/wifi/wifi_component.h"
#ifdef USE_PROVISIONING
#include "esphome/components/provisioning/provisioning.h"
#endif
#include "config_index.h"
#include "entity_routes.h"
#include "portal_logo.h"

namespace esphome::captive_portal {

static const char *const TAG = "captive_portal";

// Out of line: every GET handler ends with this
static void send_json(AsyncWebServerRequest *request, json::JsonBuilder &builder) {
  auto data = builder.serialize();
  request->send(200, ESPHOME_F("application/json"), data.c_str());
}

void CaptivePortal::handle_config(AsyncWebServerRequest *request) {
  AsyncResponseStream *stream = request->beginResponseStream(ESPHOME_F("application/json"));
  stream->addHeader(ESPHOME_F("cache-control"), ESPHOME_F("public, max-age=0, must-revalidate"));
  char mac_s[MAC_ADDRESS_PRETTY_BUFFER_SIZE];
  const char *mac_str = get_mac_address_pretty_into_buffer(mac_s);
#ifdef USE_ESP8266
  stream->print(ESPHOME_F("{\"mac\":\""));
  stream->print(mac_str);
  stream->print(ESPHOME_F("\",\"name\":\""));
  stream->print(App.get_name().c_str());
  stream->print(ESPHOME_F("\",\"aps\":[{}"));
#else
  stream->printf(R"({"mac":"%s","name":"%s","aps":[{})", mac_str, App.get_name().c_str());
#endif

  // An SSID can contain a " or \ that would break the JSON, so escape it before writing it out. An SSID is at most
  // 32 bytes (IEEE 802.11), so this is large enough that nothing is ever dropped. Reused for every scan result.
  char escaped_ssid[32 * JSON_ESCAPE_MAX_EXPANSION + 1];
  {
    // Invariant: only bounded in-memory work under the lock; the network send
    // happens later in request->send()
    wifi::ScanResultsLock lock(wifi::global_wifi_component);
    const auto &results = wifi::global_wifi_component->get_scan_result();
    for (const auto &scan : results) {
      bool with_auth = false;
      if (!wifi::should_show_scan_entry(results, scan, with_auth))
        continue;

      json_escape_into_buffer(escaped_ssid, scan.get_ssid());
#ifdef USE_ESP8266
      stream->print(ESPHOME_F(",{\"ssid\":\""));
      stream->print(escaped_ssid);
      stream->print(ESPHOME_F("\",\"rssi\":"));
      stream->print(scan.get_rssi());
      stream->print(ESPHOME_F(",\"lock\":"));
      stream->print(with_auth);
      stream->print(ESPHOME_F("}"));
#else
      stream->printf(R"(,{"ssid":"%s","rssi":%d,"lock":%d})", escaped_ssid, scan.get_rssi(), with_auth);
#endif
    }
  }
  stream->print(ESPHOME_F("]}"));
  request->send(stream);
}
void CaptivePortal::handle_wifisave(AsyncWebServerRequest *request) {
  const auto &ssid = request->arg("ssid");
  const auto &psk = request->arg("psk");
  ESP_LOGI(TAG,
           "Requested WiFi Settings Change:\n"
           "  SSID='%s'\n"
           "  Password=" LOG_SECRET("'%s'"),
           ssid.c_str(), psk.c_str());
#ifdef USE_ESP8266
  // ESP8266 is single-threaded, call directly
  wifi::global_wifi_component->save_wifi_sta(ssid.c_str(), psk.c_str());
#else
  // Defer save to main loop thread to avoid NVS operations from HTTP thread
  this->defer([ssid, psk]() { wifi::global_wifi_component->save_wifi_sta(ssid.c_str(), psk.c_str()); });
#endif
  request->send(200, ESPHOME_F("text/plain"), ESPHOME_F("Saved. Connecting..."));
}

// Kept out of the callers so the 64 bit division is emitted once
__attribute__((noinline)) static uint32_t uptime_seconds() { return static_cast<uint32_t>(millis_64() / 1000); }

json::SerializationBuffer<> CaptivePortal::get_config_json() {
  json::JsonBuilder builder;
  JsonObject root = builder.root();

  root[ESPHOME_F("title")] = App.get_friendly_name().empty() ? App.get_name().c_str() : App.get_friendly_name().c_str();
  char comment_buffer[Application::ESPHOME_COMMENT_SIZE_MAX];
  App.get_comment_string(comment_buffer);
  root[ESPHOME_F("comment")] = static_cast<const char *>(comment_buffer);
  root[ESPHOME_F("ota")] = false;
  root[ESPHOME_F("log")] = false;
  root[ESPHOME_F("lang")] = "en";
  root[ESPHOME_F("uptime")] = uptime_seconds();
  root[ESPHOME_F("portal_active")] = this->active_;
  root[ESPHOME_F("config_on_ap")] = this->config_on_ap_;

  return builder.serialize();
}

void CaptivePortal::send_initial_states_(AsyncEventSourceResponse *es) {
  // Full-detail snapshot, one `state` event per entity of the six domains. The page
  // merges them by `id`. Live updates use the same event name.
#ifdef USE_SENSOR
  for (sensor::Sensor *obj : App.get_sensors())
    es->deferrable_send_state(obj, "state", entity_routes::sensor_all_json_generator);
#endif
#ifdef USE_TEXT_SENSOR
  for (text_sensor::TextSensor *obj : App.get_text_sensors())
    es->deferrable_send_state(obj, "state", entity_routes::text_sensor_all_json_generator);
#endif
#ifdef USE_SWITCH
  for (switch_::Switch *obj : App.get_switches())
    es->deferrable_send_state(obj, "state", entity_routes::switch_all_json_generator);
#endif
#ifdef USE_NUMBER
  for (number::Number *obj : App.get_numbers())
    es->deferrable_send_state(obj, "state", entity_routes::number_all_json_generator);
#endif
#ifdef USE_TEXT
  for (text::Text *obj : App.get_texts())
    es->deferrable_send_state(obj, "state", entity_routes::text_all_json_generator);
#endif
  // buttons have no state; they reach the page only as the greeting's buttons are
  // static markup in portal.html (Finish setup, Save MQTT, etc.)
}

void CaptivePortal::setup() {
  // The shared HTTP server lives for the process lifetime: the config page keeps
  // working over STA after the AP tears down, so init once here (not in start()).
  this->base_->init();

  if (!this->initialized_) {
    // /events first so the SSE greeting wins over the entity handlers.
    this->base_->add_handler_without_auth(&this->events_);
    this->base_->add_handler_without_auth(this);

    // Subscribe once per stateful domain; internal entities are always sent.
#ifdef USE_SENSOR
    for (sensor::Sensor *obj : App.get_sensors())
      obj->add_on_state_callback([this, obj](auto &&value) {
        this->events_.deferrable_send_state(obj, "state", entity_routes::sensor_state_json_generator);
      });
#endif
#ifdef USE_TEXT_SENSOR
    for (text_sensor::TextSensor *obj : App.get_text_sensors())
      obj->add_on_state_callback([this, obj](auto &&value) {
        this->events_.deferrable_send_state(obj, "state", entity_routes::text_sensor_state_json_generator);
      });
#endif
#ifdef USE_SWITCH
    for (switch_::Switch *obj : App.get_switches())
      obj->add_on_state_callback([this, obj](auto &&value) {
        this->events_.deferrable_send_state(obj, "state", entity_routes::switch_state_json_generator);
      });
#endif
#ifdef USE_NUMBER
    for (number::Number *obj : App.get_numbers())
      obj->add_on_state_callback([this, obj](auto &&value) {
        this->events_.deferrable_send_state(obj, "state", entity_routes::number_state_json_generator);
      });
#endif
#ifdef USE_TEXT
    for (text::Text *obj : App.get_texts())
      obj->add_on_state_callback([this, obj](auto &&value) {
        this->events_.deferrable_send_state(obj, "state", entity_routes::text_state_json_generator);
      });
#endif

    // Keepalive: send `ping` only while SSE clients exist.
    this->set_interval(10000, [this]() {
      if (this->events_.empty())
        return;
      char buf[32];
      auto uptime = uptime_seconds();
      size_t len = buf_append_printf(buf, sizeof(buf), 0, "{\"uptime\":%" PRIu32 "}", uptime);
      this->events_.try_send_nodefer(buf, len, "ping", millis(), 30000);
    });
  }
  this->initialized_ = true;

  // Disable loop by default - enabled when the captive portal starts (or an SSE client connects).
  this->disable_loop();

#ifdef USE_PROVISIONING
  // The captive portal is a provisioning surface: once the provisioning window
  // has closed, stop serving it. WiFi's own closed-callback shuts down the
  // access point the portal runs on, and the gated fallback in WiFiComponent's
  // loop() ensures neither is started again afterwards.
  if (provisioning::global_provisioning_manager != nullptr) {
    provisioning::global_provisioning_manager->add_on_closed_callback([this]() {
      if (this->active_) {
        ESP_LOGD(TAG, "Provisioning window closed; stopping captive portal");
        this->end();
      }
    });
  }
#endif
}
void CaptivePortal::start() {
  network::IPAddress ip = wifi::global_wifi_component->wifi_soft_ap_ip();

#if defined(USE_ESP32)
  // Create DNS server instance for ESP-IDF
  this->dns_server_ = make_unique<DNSServer>();
  this->dns_server_->start(ip);
#elif defined(USE_ARDUINO)
  this->dns_server_ = make_unique<DNSServer>();
  this->dns_server_->setErrorReplyCode(DNSReplyCode::NoError);
  this->dns_server_->start(53, ESPHOME_F("*"), ip);
#endif

  this->active_ = true;

  // Enable loop() now that captive portal is active
  this->enable_loop();

  ESP_LOGV(TAG, "Captive portal started");
}

bool CaptivePortal::canHandle(AsyncWebServerRequest *request) const {
#ifdef USE_ESP32
  char url_buf[AsyncWebServerRequest::URL_BUF_SIZE];
  StringRef url = request->url_to(url_buf);
#else
  const auto &url = request->url();
#endif
  const auto method = request->method();

  // Static routes
  if (url == ESPHOME_F("/config.json"))
    return true;
  if (url == ESPHOME_F("/wifisave"))
    return true;
  if (url == ESPHOME_F("/logo.png"))
    return true;

  const bool is_get = method == HTTP_GET;
  const bool is_post = method == HTTP_POST;
  if (!is_get && !is_post)
    return false;

  // Entity routes: /{domain}/{name} (GET) or /{domain}/{name}/{method} (POST)
  entity_routes::UrlMatch match = entity_routes::match_url(url.c_str(), url.length(), true);
  if (match.valid) {
    if (is_get && match.domain_equals(ESPHOME_F("sensor")))
      return true;
    if (is_get && match.domain_equals(ESPHOME_F("text_sensor")))
      return true;
    if (is_get && match.domain_equals(ESPHOME_F("number")))
      return true;
    if (is_get && match.domain_equals(ESPHOME_F("text")))
      return true;
    if (is_get && match.domain_equals(ESPHOME_F("switch")))
      return true;
    if (is_post && match.domain_equals(ESPHOME_F("switch")))
      return true;
    if (is_post && match.domain_equals(ESPHOME_F("button")))
      return true;
    if (is_post && match.domain_equals(ESPHOME_F("number")))
      return true;
    if (is_post && match.domain_equals(ESPHOME_F("text")))
      return true;
  }

  // Root and OS captive-probe catch-all: serve the config page while active.
  if (url == ESPHOME_F("/"))
    return true;
  if (is_get && this->active_)
    return true;

  return false;
}

void CaptivePortal::handleRequest(AsyncWebServerRequest *req) {
#ifdef USE_ESP32
  char url_buf[AsyncWebServerRequest::URL_BUF_SIZE];
  StringRef url = req->url_to(url_buf);
#else
  const auto &url = req->url();
#endif
  if (url == ESPHOME_F("/config.json")) {
    this->handle_config(req);
    return;
  } else if (url == ESPHOME_F("/wifisave")) {
    this->handle_wifisave(req);
    return;
  } else if (url == ESPHOME_F("/logo.png")) {
    auto *response = req->beginResponse(200, ESPHOME_F("image/png"), LOGO_PNG, sizeof(LOGO_PNG));
    response->addHeader(ESPHOME_F("Cache-Control"), ESPHOME_F("public, max-age=86400"));
    req->send(response);
    return;
  }

  if (url == ESPHOME_F("/") || (req->method() == HTTP_GET && this->active_)) {
    // Serve the config page. It carries the WiFi-join UI too, so the same page
    // answers OS captive probes while the setup AP is up.
    auto *response = req->beginResponse(200, ESPHOME_F("text/html"), CONFIG_GZ, CONFIG_GZ_SIZE);
    response->addHeader(ESPHOME_F("Content-Encoding"), ESPHOME_F("gzip"));
    req->send(response);
    return;
  }

  if (entity_routes::handle(this, req))
    return;

  req->send(404);
}

CaptivePortal::CaptivePortal(web_server_base::WebServerBase *base) : base_(base) { global_captive_portal = this; }
float CaptivePortal::get_setup_priority() const {
  // Before WiFi
  return setup_priority::WIFI + 1.0f;
}
void CaptivePortal::dump_config() {
  ESP_LOGCONFIG(TAG, "Captive Portal: config UI on port %u (setup AP serves config: %s)",
                this->base_->get_port(), this->config_on_ap_ ? "yes" : "no");
}

CaptivePortal *global_captive_portal = nullptr;  // NOLINT(cppcoreguidelines-avoid-non-const-global-variables)

}  // namespace esphome::captive_portal

#endif