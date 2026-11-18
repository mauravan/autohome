#pragma once
#include "esphome/core/defines.h"
#ifdef USE_CAPTIVE_PORTAL
#include <memory>
#if defined(USE_ESP32)
#include "dns_server_esp32_idf.h"
#elif defined(USE_ARDUINO)
#include <DNSServer.h>
#endif
#include "esphome/core/component.h"
#include "esphome/core/helpers.h"
#include "esphome/core/preferences.h"
#include "esphome/components/json/json_util.h"
#include "esphome/components/web_server_base/web_server_base.h"
#include "sse_server.h"

namespace esphome::captive_portal {

class CaptivePortal final : public AsyncWebHandler, public Component {
 public:
  CaptivePortal(web_server_base::WebServerBase *base);
  void setup() override;
  void dump_config() override;
  void loop() override {
#if defined(USE_ESP32)
    if (this->dns_server_ != nullptr) {
      this->dns_server_->process_next_request();
    }
#elif defined(USE_ARDUINO)
    if (this->dns_server_ != nullptr) {
      this->dns_server_->processNextRequest();
    }
#endif
    if (!this->events_.loop() && !this->active_)
      this->disable_loop();
  }
  float get_setup_priority() const override;
  void start();
  bool is_active() const { return this->active_; }
  /// Serve the readings/setup view on the setup AP too (BLE nodes are configured there).
  void set_config_on_ap(bool config_on_ap) { this->config_on_ap_ = config_on_ap; }
  void end() {
    this->active_ = false;
    // The HTTP server stays up for the process lifetime so the config page keeps
    // working over STA after the AP tears down. Only loop() shuts itself off once
    // no SSE clients remain.
    if (this->dns_server_ != nullptr) {
      this->dns_server_->stop();
      this->dns_server_ = nullptr;
    }
  }

  bool canHandle(AsyncWebServerRequest *request) const override;
  void handleRequest(AsyncWebServerRequest *req) override;

  void handle_config(AsyncWebServerRequest *request);
  void handle_wifisave(AsyncWebServerRequest *request);

  /// Return the portal configuration as JSON (served as the SSE `ping`).
  json::SerializationBuffer<> get_config_json();
  /// Send the per-entity greeting snapshot to one newly connected SSE client.
  /// Called from the SSE session start on the main loop.
  void send_initial_states_(AsyncEventSourceResponse *es);

  using Component::defer;  // entity_routes defers actions to the main loop

 protected:
  web_server_base::WebServerBase *base_;
  bool initialized_{false};
  bool active_{false};
  bool config_on_ap_{false};
  AsyncEventSource events_{StringRef("/events"), this};
#if defined(USE_ARDUINO) || defined(USE_ESP32)
  std::unique_ptr<DNSServer> dns_server_{nullptr};
#endif
};

extern CaptivePortal *global_captive_portal;  // NOLINT(cppcoreguidelines-avoid-non-const-global-variables)

}  // namespace esphome::captive_portal

#endif