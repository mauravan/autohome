#pragma once

#include "esphome/components/esp32_ble/ble.h"
#include "esphome/components/sensor/sensor.h"
#include "esphome/core/component.h"

#ifdef USE_ESP32

#include <esp_bt.h>
#include <esp_gap_ble_api.h>
#include <string>

namespace esphome::bthome_adv {

using esp32_ble::ESP32BLE;
class BTHomeAdv : public Component {
 public:
  void set_parent(ESP32BLE *parent) { this->parent_ = parent; }
  void set_name(const std::string &name) { this->name_ = name; }
  void set_co2_sensor(sensor::Sensor *s) { this->co2_ = s; }
  void set_temperature_sensor(sensor::Sensor *s) { this->temperature_ = s; }
  void set_humidity_sensor(sensor::Sensor *s) { this->humidity_ = s; }
  void set_battery_sensor(sensor::Sensor *s) { this->battery_ = s; }
  void set_duration_ms(uint32_t ms) { this->duration_ms_ = ms; }
  void set_interval_ms(uint32_t ms) { this->interval_ms_ = ms; }
#ifndef CONFIG_BT_CONTROLLER_DISABLED
  void set_tx_power(int level) { this->tx_power_ = (esp_power_level_t) level; }
#endif

  void setup() override;
  void loop() override;
  void dump_config() override;
  float get_setup_priority() const override;

  /// Start (or queue, if the BLE stack is not up yet) a duration-bounded BTHome burst.
  void publish();
  /// Abort an in-flight burst.
  void stop();
  /// True once the current burst finished (or was skipped: no reading this wake).
  bool is_done() const { return this->done_; }
  bool is_advertising() const { return this->advertising_; }

  void gap_event_handler(esp_gap_ble_cb_event_t event, esp_ble_gap_cb_param_t *param);

 protected:
  /// Build the advertisement into adv_ and hand it to the stack.
  void start_now_();
  void stop_();

  ESP32BLE *parent_{nullptr};
  std::string name_;
  sensor::Sensor *co2_{nullptr};
  sensor::Sensor *temperature_{nullptr};
  sensor::Sensor *humidity_{nullptr};
  sensor::Sensor *battery_{nullptr};
  uint32_t duration_ms_{4000};
  uint32_t interval_ms_{100};
#ifndef CONFIG_BT_CONTROLLER_DISABLED
  esp_power_level_t tx_power_{ESP_PWR_LVL_N0};
#endif

  esp_ble_adv_params_t ble_adv_params_{};
  uint8_t adv_[31]{};
  uint8_t adv_len_{0};
  bool advertising_{false};
  bool pending_{false};
  bool done_{false};
  uint32_t started_ms_{0};
};

}  // namespace esphome::bthome_adv

#endif
