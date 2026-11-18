#include "entity_routes.h"
#include "captive_portal.h"
#ifdef USE_CAPTIVE_PORTAL

#include <cmath>
#include <cstdlib>
#include <cstring>

#include "esphome/core/application.h"
#include "esphome/core/helpers.h"
#include "esphome/core/log.h"
#include "esphome/core/progmem.h"

#ifdef USE_SENSOR
#include "esphome/components/sensor/sensor.h"
#endif
#ifdef USE_TEXT_SENSOR
#include "esphome/components/text_sensor/text_sensor.h"
#endif
#ifdef USE_SWITCH
#include "esphome/components/switch/switch.h"
#endif
#ifdef USE_BUTTON
#include "esphome/components/button/button.h"
#endif
#ifdef USE_NUMBER
#include "esphome/components/number/number.h"
#endif
#ifdef USE_TEXT
#include "esphome/components/text/text.h"
#endif

namespace esphome::captive_portal {
namespace entity_routes {

static const char *const TAG = "captive_portal";

// ---------------------------------------------------------------------------
// helpers (ported from esphome/components/web_server/web_server.cpp)
// ---------------------------------------------------------------------------

static const char *web_ui_name(const StringRef &name, size_t &out_len) {
  const std::string &friendly = App.get_friendly_name();  // empty if unset
  out_len = name.size();
  if (!friendly.empty()) {
    const size_t flen = friendly.size();
    if (out_len > flen + 1 && name[flen] == ' ' && memcmp(name.c_str(), friendly.c_str(), flen) == 0) {
      out_len -= flen + 1;
      return name.c_str() + flen + 1;
    }
  }
  return name.c_str();
}

static void send_json(AsyncWebServerRequest *request, json::JsonBuilder &builder) {
  auto data = builder.serialize();
  request->send(200, ESPHOME_F("application/json"), data.c_str());
}

static JsonDetail get_request_detail(AsyncWebServerRequest *request) {
  return request->arg(ESPHOME_F("detail")) == "all" ? JsonDetail::DETAIL_ALL : JsonDetail::DETAIL_STATE;
}

// Build unique id as: {domain}/{entity_name}. Uses names (not object_id) to avoid
// UTF-8 collision issues.
static void set_json_id(JsonObject root, EntityBase *obj, const char *prefix, JsonDetail start_config) {
  const StringRef &name = obj->get_name();
  size_t name_len = name.size();

  static constexpr size_t ID_BUF_SIZE = ESPHOME_DOMAIN_MAX_LEN + 1 + ESPHOME_FRIENDLY_NAME_MAX_LEN + 1;
  char id_buf[ID_BUF_SIZE];
  const size_t prefix_len = strlen(prefix);
  memcpy(id_buf, prefix, prefix_len);  // NOLINT(bugprone-not-null-terminated-result)

  char *p = id_buf + prefix_len;
  *p++ = '/';
  memcpy(p, name.c_str(), name_len);
  p[name_len] = '\0';
  root[ESPHOME_F("id")] = static_cast<const char *>(id_buf);

  if (start_config == JsonDetail::DETAIL_ALL) {
    root[ESPHOME_F("domain")] = prefix;
    // Strip the friendly-name prefix for the web UI; MQTT discovery still uses the full name.
    size_t ui_name_len;
    const char *ui_name = web_ui_name(name, ui_name_len);
    char ui_name_buf[ESPHOME_FRIENDLY_NAME_MAX_LEN + 1];
    memcpy(ui_name_buf, ui_name, ui_name_len);
    ui_name_buf[ui_name_len] = '\0';
    root[ESPHOME_F("name")] = static_cast<const char *>(ui_name_buf);
#ifdef USE_ENTITY_ICON
    char icon_buf[MAX_ICON_LENGTH];
    root[ESPHOME_F("icon")] = obj->get_icon_to(icon_buf);
#endif
    root[ESPHOME_F("entity_category")] = obj->get_entity_category();
    bool is_disabled = obj->is_disabled_by_default();
    if (is_disabled)
      root[ESPHOME_F("is_disabled_by_default")] = is_disabled;
  }
}

template<typename T>
static void set_json_value(JsonObject root, EntityBase *obj, const char *prefix, T value, JsonDetail start_config) {
  set_json_id(root, obj, prefix, start_config);
  root[ESPHOME_F("value")] = value;
}

template<typename S, typename T>
static void set_json_icon_state_value(JsonObject root, EntityBase *obj, const char *prefix, S state, T value,
                                      JsonDetail start_config) {
  set_json_value(root, obj, prefix, value, start_config);
  root[ESPHOME_F("state")] = state;
}

// Generic helper to parse and apply a numeric parameter
template<typename NumT, typename T, typename Ret>
static void parse_num_param_(AsyncWebServerRequest *request, const char *param_name, T &call, Ret (T::*setter)(NumT)) {
  auto value = parse_number<NumT>(request->arg(param_name).c_str());
  if (value.has_value()) {
    (call.*setter)(*value);
  }
}

// Generic helper to parse and apply a string parameter using const char* setter
template<typename T, typename Ret>
static void parse_cstr_param_(AsyncWebServerRequest *request, const char *param_name, T &call,
                              Ret (T::*setter)(const char *, size_t)) {
  if (request->hasArg(param_name)) {
    const auto &value = request->arg(param_name);
    (call.*setter)(value.c_str(), value.length());
  }
}

#define DEFER_ACTION(portal, capture, action) (portal)->defer([capture]() mutable { action; })

// ---------------------------------------------------------------------------
// URL matching (ported from the ESPHome web_server component)
// ---------------------------------------------------------------------------

UrlMatch match_url(const char *url_ptr, size_t url_len, bool only_domain, bool is_post) {
  // Every path returns this one object so it is built in place; fields are only set once the URL is known valid
  UrlMatch match{};

  // URL must start with '/' and have content after it
  if (url_len < 2 || url_ptr[0] != '/')
    return match;

  const char *p = url_ptr + 1;
  const char *end = url_ptr + url_len;

  auto next_segment = [&end](const char *start) -> const char * {
    const char *slash = (const char *) memchr(start, '/', end - start);
    return slash ? slash + 1 : nullptr;
  };

  auto make_ref = [&end](const char *start, const char *next_start) -> StringRef {
    return StringRef(start, (next_start ? next_start - 1 : end) - start);
  };

  const char *s1 = p;
  const char *s2 = next_segment(s1);

  // Must have domain with trailing slash
  if (!s2)
    return match;

  if (only_domain || s2 >= end) {
    match.domain = make_ref(s1, s2);
    match.valid = true;
    return match;
  }

  const char *s3 = next_segment(s2);

  StringRef seg2 = make_ref(s2, s3);
  StringRef seg3 = s3 ? make_ref(s3, nullptr) : StringRef();

  // Reject empty segments
  if (seg2.empty() || (s3 && seg3.empty()))
    return match;

  if (!s3) {
    // 1 segment after domain: /{domain}/{entity}
    match.id = seg2;
  } else {
    // 2 segments after domain: /{domain}/{X}/{Y}
    // HTTP method disambiguates: GET = entity state, POST = entity/action
    if (is_post) {
      match.id = seg2;
      match.method = seg3;
    } else {
      return match;  // 3-segment GET not supported
    }
  }

  match.domain = make_ref(s1, s2);
  match.valid = true;
  return match;
}

EntityMatchResult UrlMatch::match_entity(EntityBase *entity) const {
  EntityMatchResult result{false, this->method.empty()};

  // Match by entity name (full name first, then stripped web-UI name)
  if (this->id == entity->get_name()) {
    result.matched = true;
  } else {
    size_t ui_len;
    const char *ui = web_ui_name(entity->get_name(), ui_len);
    result.matched = (this->id.size() == ui_len && memcmp(this->id.c_str(), ui, ui_len) == 0);
  }

  return result;
}

// ---------------------------------------------------------------------------
// sensor
// ---------------------------------------------------------------------------
#ifdef USE_SENSOR
static void sensor_json_(sensor::Sensor *obj, float value, JsonDetail start_config, json::JsonBuilder &builder) {
  JsonObject root = builder.root();

  const auto uom_ref = obj->get_unit_of_measurement_ref();
  char buf[VALUE_ACCURACY_MAX_LEN];
  const char *state = std::isnan(value)
                          ? "NA"
                          : (value_accuracy_with_uom_to_buf(buf, value, obj->get_accuracy_decimals(), uom_ref), buf);
  set_json_icon_state_value(root, obj, "sensor", state, value, start_config);
  if (start_config == JsonDetail::DETAIL_ALL) {
    if (!uom_ref.empty())
      root[ESPHOME_F("uom")] = uom_ref.c_str();
  }
}

void sensor_state_json_generator(CaptivePortal *, void *source, json::JsonBuilder &builder) {
  sensor_json_((sensor::Sensor *) (source), ((sensor::Sensor *) (source))->state, JsonDetail::DETAIL_STATE, builder);
}
void sensor_all_json_generator(CaptivePortal *, void *source, json::JsonBuilder &builder) {
  sensor_json_((sensor::Sensor *) (source), ((sensor::Sensor *) (source))->state, JsonDetail::DETAIL_ALL, builder);
}
#endif

// ---------------------------------------------------------------------------
// text_sensor
// ---------------------------------------------------------------------------
#ifdef USE_TEXT_SENSOR
static void text_sensor_json_(text_sensor::TextSensor *obj, const std::string &value, JsonDetail start_config,
                              json::JsonBuilder &builder) {
  JsonObject root = builder.root();
  set_json_icon_state_value(root, obj, "text_sensor", value.c_str(), value.c_str(), start_config);
}
void text_sensor_state_json_generator(CaptivePortal *, void *source, json::JsonBuilder &builder) {
  text_sensor_json_((text_sensor::TextSensor *) (source), ((text_sensor::TextSensor *) (source))->state,
                    JsonDetail::DETAIL_STATE, builder);
}
void text_sensor_all_json_generator(CaptivePortal *, void *source, json::JsonBuilder &builder) {
  text_sensor_json_((text_sensor::TextSensor *) (source), ((text_sensor::TextSensor *) (source))->state,
                    JsonDetail::DETAIL_ALL, builder);
}
#endif

// ---------------------------------------------------------------------------
// switch
// ---------------------------------------------------------------------------
#ifdef USE_SWITCH
enum SwitchAction : uint8_t { SWITCH_ACTION_NONE, SWITCH_ACTION_TOGGLE, SWITCH_ACTION_TURN_ON, SWITCH_ACTION_TURN_OFF };

static void execute_switch_action(switch_::Switch *obj, SwitchAction action) {
  switch (action) {
    case SWITCH_ACTION_TOGGLE:
      obj->toggle();
      break;
    case SWITCH_ACTION_TURN_ON:
      obj->turn_on();
      break;
    case SWITCH_ACTION_TURN_OFF:
      obj->turn_off();
      break;
    default:
      break;
  }
}

static void switch_json_(switch_::Switch *obj, bool value, JsonDetail start_config, json::JsonBuilder &builder) {
  JsonObject root = builder.root();
  set_json_icon_state_value(root, obj, "switch", value ? "ON" : "OFF", value, start_config);
  if (start_config == JsonDetail::DETAIL_ALL) {
    root[ESPHOME_F("assumed_state")] = obj->assumed_state();
  }
}
void switch_state_json_generator(CaptivePortal *, void *source, json::JsonBuilder &builder) {
  switch_json_((switch_::Switch *) (source), ((switch_::Switch *) (source))->state, JsonDetail::DETAIL_STATE, builder);
}
void switch_all_json_generator(CaptivePortal *, void *source, json::JsonBuilder &builder) {
  switch_json_((switch_::Switch *) (source), ((switch_::Switch *) (source))->state, JsonDetail::DETAIL_ALL, builder);
}
#endif

// ---------------------------------------------------------------------------
// number
// ---------------------------------------------------------------------------
#ifdef USE_NUMBER
static void number_json_(number::Number *obj, float value, JsonDetail start_config, json::JsonBuilder &builder) {
  JsonObject root = builder.root();

  const auto uom_ref = obj->get_unit_of_measurement_ref();
  const int8_t accuracy = step_to_accuracy_decimals(obj->traits.get_step());

  char val_buf[VALUE_ACCURACY_MAX_LEN];
  char state_buf[VALUE_ACCURACY_MAX_LEN];
  const char *val_str = std::isnan(value) ? "\"NaN\"" : (value_accuracy_to_buf(val_buf, value, accuracy), val_buf);
  const char *state_str =
      std::isnan(value) ? "NA" : (value_accuracy_with_uom_to_buf(state_buf, value, accuracy, uom_ref), state_buf);
  set_json_icon_state_value(root, obj, "number", state_str, val_str, start_config);
  if (start_config == JsonDetail::DETAIL_ALL) {
    // ArduinoJson copies the string immediately, so we can reuse val_buf
    root[ESPHOME_F("min_value")] = (value_accuracy_to_buf(val_buf, obj->traits.get_min_value(), accuracy), val_buf);
    root[ESPHOME_F("max_value")] = (value_accuracy_to_buf(val_buf, obj->traits.get_max_value(), accuracy), val_buf);
    root[ESPHOME_F("step")] = (value_accuracy_to_buf(val_buf, obj->traits.get_step(), accuracy), val_buf);
    root[ESPHOME_F("mode")] = (int) obj->traits.get_mode();
    if (!uom_ref.empty())
      root[ESPHOME_F("uom")] = uom_ref.c_str();
  }
}
void number_state_json_generator(CaptivePortal *, void *source, json::JsonBuilder &builder) {
  number_json_((number::Number *) (source), ((number::Number *) (source))->state, JsonDetail::DETAIL_STATE, builder);
}
void number_all_json_generator(CaptivePortal *, void *source, json::JsonBuilder &builder) {
  number_json_((number::Number *) (source), ((number::Number *) (source))->state, JsonDetail::DETAIL_ALL, builder);
}
#endif

// ---------------------------------------------------------------------------
// text
// ---------------------------------------------------------------------------
#ifdef USE_TEXT
static void text_json_(text::Text *obj, const std::string &value, JsonDetail start_config, json::JsonBuilder &builder) {
  JsonObject root = builder.root();

  // A password entity shows the mask and prefills the input with nothing, so the secret never
  // reaches the JSON and the mask cannot be written back as the value
  const bool password = obj->traits.get_mode() == text::TextMode::TEXT_MODE_PASSWORD;
  set_json_icon_state_value(root, obj, "text", password ? "********" : value.c_str(), password ? "" : value.c_str(),
                            start_config);
  root[ESPHOME_F("min_length")] = obj->traits.get_min_length();
  root[ESPHOME_F("max_length")] = obj->traits.get_max_length();
  root[ESPHOME_F("pattern")] = obj->traits.get_pattern_c_str();
  if (start_config == JsonDetail::DETAIL_ALL) {
    root[ESPHOME_F("mode")] = (int) obj->traits.get_mode();
  }
}
void text_state_json_generator(CaptivePortal *, void *source, json::JsonBuilder &builder) {
  text_json_((text::Text *) (source), ((text::Text *) (source))->state, JsonDetail::DETAIL_STATE, builder);
}
void text_all_json_generator(CaptivePortal *, void *source, json::JsonBuilder &builder) {
  text_json_((text::Text *) (source), ((text::Text *) (source))->state, JsonDetail::DETAIL_ALL, builder);
}
#endif

// ---------------------------------------------------------------------------
// dispatch (ported from WebServer::handleRequest for our six domains)
// ---------------------------------------------------------------------------
bool handle(CaptivePortal *portal, AsyncWebServerRequest *request) {
  char url_buf[AsyncWebServerRequest::URL_BUF_SIZE];
  StringRef url = request->url_to(url_buf);
  UrlMatch match = match_url(url.c_str(), url.length(), false, request->method() == HTTP_POST);

  if (!match.valid)
    return false;

#ifdef USE_SENSOR
  if (match.domain_equals(ESPHOME_F("sensor"))) {
    for (sensor::Sensor *obj : App.get_sensors()) {
      auto entity_match = match.match_entity(obj);
      if (!entity_match.matched)
        continue;
      if (request->method() == HTTP_GET && entity_match.action_is_empty) {
        auto detail = get_request_detail(request);
        json::JsonBuilder builder;
        sensor_json_(obj, obj->state, detail, builder);
        send_json(request, builder);
        return true;
      }
      request->send(404);
      return true;
    }
    request->send(404);
    return true;
  }
#endif
#ifdef USE_TEXT_SENSOR
  if (match.domain_equals(ESPHOME_F("text_sensor"))) {
    for (text_sensor::TextSensor *obj : App.get_text_sensors()) {
      auto entity_match = match.match_entity(obj);
      if (!entity_match.matched)
        continue;
      if (request->method() == HTTP_GET && entity_match.action_is_empty) {
        auto detail = get_request_detail(request);
        json::JsonBuilder builder;
        text_sensor_json_(obj, obj->state, detail, builder);
        send_json(request, builder);
        return true;
      }
      request->send(404);
      return true;
    }
    request->send(404);
    return true;
  }
#endif
#ifdef USE_SWITCH
  if (match.domain_equals(ESPHOME_F("switch"))) {
    for (switch_::Switch *obj : App.get_switches()) {
      auto entity_match = match.match_entity(obj);
      if (!entity_match.matched)
        continue;

      if (request->method() == HTTP_GET && entity_match.action_is_empty) {
        auto detail = get_request_detail(request);
        json::JsonBuilder builder;
        switch_json_(obj, obj->state, detail, builder);
        send_json(request, builder);
        return true;
      }

      SwitchAction action = SWITCH_ACTION_NONE;
      if (match.method_equals(ESPHOME_F("toggle")))
        action = SWITCH_ACTION_TOGGLE;
      else if (match.method_equals(ESPHOME_F("turn_on")))
        action = SWITCH_ACTION_TURN_ON;
      else if (match.method_equals(ESPHOME_F("turn_off")))
        action = SWITCH_ACTION_TURN_OFF;

      if (action != SWITCH_ACTION_NONE) {
        portal->defer([obj, action]() { execute_switch_action(obj, action); });
        request->send(200);
      } else {
        request->send(404);
      }
      return true;
    }
    request->send(404);
    return true;
  }
#endif
#ifdef USE_BUTTON
  if (match.domain_equals(ESPHOME_F("button"))) {
    for (button::Button *obj : App.get_buttons()) {
      auto entity_match = match.match_entity(obj);
      if (!entity_match.matched)
        continue;
      if (match.method_equals(ESPHOME_F("press"))) {
        DEFER_ACTION(portal, obj, obj->press());
        request->send(200);
      } else {
        request->send(404);
      }
      return true;
    }
    request->send(404);
    return true;
  }
#endif
#ifdef USE_NUMBER
  if (match.domain_equals(ESPHOME_F("number"))) {
    for (auto *obj : App.get_numbers()) {
      auto entity_match = match.match_entity(obj);
      if (!entity_match.matched)
        continue;

      if (request->method() == HTTP_GET && entity_match.action_is_empty) {
        auto detail = get_request_detail(request);
        json::JsonBuilder builder;
        number_json_(obj, obj->state, detail, builder);
        send_json(request, builder);
        return true;
      }
      if (!match.method_equals(ESPHOME_F("set"))) {
        request->send(404);
        return true;
      }

      auto call = obj->make_call();
      parse_num_param_(request, ESPHOME_F("value"), call, &decltype(call)::set_value);

      DEFER_ACTION(portal, call, call.perform());
      request->send(200);
      return true;
    }
    request->send(404);
    return true;
  }
#endif
#ifdef USE_TEXT
  if (match.domain_equals(ESPHOME_F("text"))) {
    for (auto *obj : App.get_texts()) {
      auto entity_match = match.match_entity(obj);
      if (!entity_match.matched)
        continue;

      if (request->method() == HTTP_GET && entity_match.action_is_empty) {
        auto detail = get_request_detail(request);
        json::JsonBuilder builder;
        text_json_(obj, obj->state, detail, builder);
        send_json(request, builder);
        return true;
      }
      if (!match.method_equals(ESPHOME_F("set"))) {
        request->send(404);
        return true;
      }

      auto call = obj->make_call();
      parse_cstr_param_(
          request, ESPHOME_F("value"), call,
          static_cast<text::TextCall &(text::TextCall::*) (const char *, size_t)>(&decltype(call)::set_value));

      DEFER_ACTION(portal, call, call.perform());
      request->send(200);
      return true;
    }
    request->send(404);
    return true;
  }
#endif

  return false;
}

}  // namespace entity_routes
}  // namespace esphome::captive_portal

#endif