#pragma once
#include "esphome/core/defines.h"
#ifdef USE_CAPTIVE_PORTAL

#include <cstddef>
#include <string>

#include "esphome/components/json/json_util.h"
#include "esphome/core/entity_base.h"
#include "esphome/core/string_ref.h"
#include "esphome/components/web_server_base/web_server_base.h"

namespace esphome::captive_portal {

class CaptivePortal;  // fwd

enum class JsonDetail : uint8_t { DETAIL_ALL, DETAIL_STATE };

namespace entity_routes {

/// Result of matching a URL against an entity
struct EntityMatchResult {
  bool matched;          ///< True if entity matched the URL
  bool action_is_empty;  ///< True if no action/method segment in URL
};

/// Internal helper struct that is used to parse incoming URLs
struct UrlMatch {
  StringRef domain;  ///< Domain within URL, for example "sensor"
  StringRef id;      ///< Entity name/id within URL, for example "Temperature"
  StringRef method;  ///< Method within URL, for example "turn_on"
  bool valid{false}; ///< Whether this match is valid

  // Helper methods for string comparisons
  bool domain_equals(const char *str) const { return this->domain == str; }
  bool method_equals(const char *str) const { return this->method == str; }

  /// Match entity by name.
  EntityMatchResult match_entity(EntityBase *entity) const;
};

/// Parse a URL. `only_domain` stops after the first segment (used by canHandle).
UrlMatch match_url(const char *url_ptr, size_t url_len, bool only_domain, bool is_post = false);

/// Serve one request that canHandle() already accepted. Returns true if it wrote a response.
bool handle(CaptivePortal *portal, AsyncWebServerRequest *request);

// ---- state generators (used as message_generator_t) ------------------------
// Each ignores the CaptivePortal* and serializes DETAIL_ALL for the greeting or
// DETAIL_STATE for live updates.
#ifdef USE_SENSOR
void sensor_state_json_generator(CaptivePortal *portal, void *source, json::JsonBuilder &builder);
void sensor_all_json_generator(CaptivePortal *portal, void *source, json::JsonBuilder &builder);
#endif
#ifdef USE_TEXT_SENSOR
void text_sensor_state_json_generator(CaptivePortal *portal, void *source, json::JsonBuilder &builder);
void text_sensor_all_json_generator(CaptivePortal *portal, void *source, json::JsonBuilder &builder);
#endif
#ifdef USE_SWITCH
void switch_state_json_generator(CaptivePortal *portal, void *source, json::JsonBuilder &builder);
void switch_all_json_generator(CaptivePortal *portal, void *source, json::JsonBuilder &builder);
#endif
#ifdef USE_NUMBER
void number_state_json_generator(CaptivePortal *portal, void *source, json::JsonBuilder &builder);
void number_all_json_generator(CaptivePortal *portal, void *source, json::JsonBuilder &builder);
#endif
#ifdef USE_TEXT
void text_state_json_generator(CaptivePortal *portal, void *source, json::JsonBuilder &builder);
void text_all_json_generator(CaptivePortal *portal, void *source, json::JsonBuilder &builder);
#endif

}  // namespace entity_routes
}  // namespace esphome::captive_portal

#endif