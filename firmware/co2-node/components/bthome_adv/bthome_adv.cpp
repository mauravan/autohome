#include "bthome_adv.h"
#include "esphome/core/log.h"

#ifdef USE_ESP32

#include <esp_bt.h>
#include <cstring>

#include "esphome/core/hal.h"

namespace esphome::bthome_adv {

static const char *const TAG = "bthome_adv";

// BTHome v2, unencrypted. Device info 0x44: bit 2 (trigger/normal state, set so
// HA does not mark the sparse entities unavailable between advertisements),
// bit 6 (BTHome version 2). Object IDs in ascending order; no packet-id.
static constexpr uint16_t BTHOME_UUID16 = 0xFCD2;
static constexpr uint8_t BTHOME_DEVICE_INFO = 0x44;
static constexpr uint8_t OBJ_BATTERY = 0x01;      // u8, %
static constexpr uint8_t OBJ_TEMPERATURE = 0x02;  // s16 LE, x0.01 C
static constexpr uint8_t OBJ_HUMIDITY = 0x03;    // u16 LE, x0.01 %
static constexpr uint8_t OBJ_CO2 = 0x12;         // u16 LE, ppm

void BTHomeAdv::setup() {
  uint16_t adv_int = (uint16_t) (this->interval_ms_ / 0.625f);
  if (adv_int < 0x0020)
    adv_int = 0x0020;
  if (adv_int > 0x4000)
    adv_int = 0x4000;
  this->ble_adv_params_ = {
      .adv_int_min = adv_int,
      .adv_int_max = adv_int,
      .adv_type = ADV_TYPE_NONCONN_IND,
      .own_addr_type = BLE_ADDR_TYPE_PUBLIC,
      .peer_addr = {0x00, 0x00, 0x00, 0x00, 0x00, 0x00},
      .peer_addr_type = BLE_ADDR_TYPE_PUBLIC,
      .channel_map = ADV_CHNL_ALL,
      .adv_filter_policy = ADV_FILTER_ALLOW_SCAN_ANY_CON_ANY,
  };
  ESP_LOGCONFIG(TAG, "name '%s' duration %ums interval %ums", this->name_.c_str(), this->duration_ms_,
                this->interval_ms_);
}

void BTHomeAdv::dump_config() {
  ESP_LOGCONFIG(TAG, "BTHome advertiser '%s':", this->name_.c_str());
  LOG_SENSOR("  ", "CO2", this->co2_);
  LOG_SENSOR("  ", "Temperature", this->temperature_);
  LOG_SENSOR("  ", "Humidity", this->humidity_);
  LOG_SENSOR("  ", "Battery", this->battery_);
}

float BTHomeAdv::get_setup_priority() const { return setup_priority::AFTER_BLUETOOTH; }

static bool valid_float(float v) { return !std::isnan(v); }

void BTHomeAdv::publish() {
  this->done_ = false;
  this->cancel_timeout("bthome");
  if (this->advertising_)
    this->stop_();
  if (this->parent_ == nullptr || !this->parent_->is_active()) {
    // BLE stack not up yet: the loop retries once it is.
    this->pending_ = true;
    this->enable_loop();
    return;
  }
  this->start_now_();
}

void BTHomeAdv::stop() {
  this->cancel_timeout("bthome");
  this->pending_ = false;
  this->stop_();
}

void BTHomeAdv::start_now_() {
  this->pending_ = false;
  this->adv_len_ = 0;

  float co2 = this->co2_ != nullptr ? this->co2_->state : NAN;
  float temp = this->temperature_ != nullptr ? this->temperature_->state : NAN;
  float hum = this->humidity_ != nullptr ? this->humidity_->state : NAN;
  float batt = this->battery_ != nullptr ? this->battery_->state : NAN;

  if (!valid_float(co2)) {
    // No SCD41 reading this wake: nothing to advertise. Mark done so the
    // sleep gate still opens and the node sleeps on time.
    ESP_LOGW(TAG, "no SCD41 reading this wake; skipping advertisement");
    this->done_ = true;
    return;
  }

  uint8_t svc[1 + 2 + 3 + 4 + 3]{};  // device info + battery + temp + humidity + co2
  uint8_t slen = 0;
  svc[slen++] = BTHOME_DEVICE_INFO;
  if (valid_float(batt)) {
    float b = batt < 0 ? 0 : (batt > 100 ? 100 : batt);
    svc[slen++] = OBJ_BATTERY;
    svc[slen++] = (uint8_t) (b + 0.5f);
  }
  bool temp_ok = valid_float(temp);
  bool hum_ok = valid_float(hum);
  if (temp_ok) {
    float t = temp < -127.99f ? -127.99f : (temp > 127.99f ? 127.99f : temp);
    int16_t v = (int16_t) (t * 100.0f + (t >= 0 ? 0.5f : -0.5f));
    svc[slen++] = OBJ_TEMPERATURE;
    svc[slen++] = (uint8_t) (v & 0xFF);
    svc[slen++] = (uint8_t) ((v >> 8) & 0xFF);
  }
  if (hum_ok) {
    float h = hum < 0 ? 0 : (hum > 100 ? 100 : hum);
    uint16_t v = (uint16_t) (h * 100.0f + 0.5f);
    svc[slen++] = OBJ_HUMIDITY;
    svc[slen++] = (uint8_t) (v & 0xFF);
    svc[slen++] = (uint8_t) ((v >> 8) & 0xFF);
  }
  {
    float c = co2 < 0 ? 0 : (co2 > 65535 ? 65535 : co2);
    uint16_t v = (uint16_t) (c + 0.5f);
    svc[slen++] = OBJ_CO2;
    svc[slen++] = (uint8_t) (v & 0xFF);
    svc[slen++] = (uint8_t) ((v >> 8) & 0xFF);
  }

  uint8_t *p = this->adv_;
  // Flags: LE general discoverable, BR/EDR not supported.
  *p++ = 2;
  *p++ = 0x01;
  *p++ = 0x06;
  // Service Data, UUID 0xFCD2.
  uint8_t *svc_len = p++;
  *p++ = 0x16;
  *p++ = (uint8_t) (BTHOME_UUID16 & 0xFF);
  *p++ = (uint8_t) ((BTHOME_UUID16 >> 8) & 0xFF);
  memcpy(p, svc, slen);
  p += slen;
  *svc_len = (uint8_t) (p - svc_len - 1);

  // Complete (0x09) or shortened (0x08) local name, if it fits.
  size_t nlen = this->name_.size();
  size_t room = sizeof(this->adv_) - (size_t) (p - this->adv_);
  if (nlen > 0 && room >= 2) {
    size_t fit = nlen;
    uint8_t ad_type = 0x09;
    if (fit + 2 > room) {
      fit = room - 2;
      ad_type = 0x08;
    }
    if (fit > 0) {
      *p++ = (uint8_t) (fit + 1);
      *p++ = ad_type;
      memcpy(p, this->name_.data(), fit);
      p += fit;
    }
  }
  this->adv_len_ = (uint8_t) (p - this->adv_);

  ESP_LOGD(TAG, "advertising %uB (name '%s', co2=%.0f temp=%s hum=%s batt=%s)", this->adv_len_,
           this->name_.c_str(), co2, temp_ok ? "ok" : "nan", hum_ok ? "ok" : "nan",
           valid_float(batt) ? "ok" : "nan");

#ifndef CONFIG_BT_CONTROLLER_DISABLED
  {
    esp_err_t tx_err = esp_ble_tx_power_set(ESP_BLE_PWR_TYPE_ADV, this->tx_power_);
    if (tx_err != ESP_OK) {
      ESP_LOGW(TAG, "esp_ble_tx_power_set failed: %s", esp_err_to_name(tx_err));
    }
  }
#endif

  // The hub arbitrates the ADV start via advertising_start(); the raw payload
  // completes in gap_event_handler -> ADC_DATA_RAW_SET_COMPLETE_EVT.
  this->parent_->advertising_start();
  esp_err_t err = esp_ble_gap_config_adv_data_raw(this->adv_, this->adv_len_);
  if (err != ESP_OK) {
    ESP_LOGE(TAG, "esp_ble_gap_config_adv_data_raw failed: %s", esp_err_to_name(err));
    this->parent_->advertising_stop();
    this->done_ = true;
    return;
  }
  this->started_ms_ = millis();
  this->advertising_ = true;
  this->set_timeout("bthome", this->duration_ms_, [this]() {
    this->stop_();
    this->done_ = true;
  });
}

void BTHomeAdv::stop_() {
  if (this->advertising_) {
    esp_err_t err = esp_ble_gap_stop_advertising();
    if (err != ESP_OK) {
      ESP_LOGW(TAG, "esp_ble_gap_stop_advertising failed: %s", esp_err_to_name(err));
    }
  }
  if (this->parent_ != nullptr)
    this->parent_->advertising_stop();
  this->advertising_ = false;
}

void BTHomeAdv::loop() {
  if (this->pending_ && this->parent_ != nullptr && this->parent_->is_active()) {
    this->pending_ = false;
    this->start_now_();
  }
  if (!this->pending_ && !this->advertising_)
    this->disable_loop();
}

void BTHomeAdv::gap_event_handler(esp_gap_ble_cb_event_t event, esp_ble_gap_cb_param_t *param) {
  switch (event) {
    case ESP_GAP_BLE_ADV_DATA_RAW_SET_COMPLETE_EVT: {
      if (param->adv_data_raw_cmpl.status != ESP_BT_STATUS_SUCCESS) {
        ESP_LOGE(TAG, "raw data set failed: %d", param->adv_data_raw_cmpl.status);
        this->stop_();
        this->done_ = true;
        break;
      }
      esp_err_t err = esp_ble_gap_start_advertising(&this->ble_adv_params_);
      if (err != ESP_OK) {
        ESP_LOGE(TAG, "esp_ble_gap_start_advertising failed: %s", esp_err_to_name(err));
        this->stop_();
        this->done_ = true;
      }
      break;
    }
    case ESP_GAP_BLE_ADV_START_COMPLETE_EVT: {
      if (param->adv_start_cmpl.status != ESP_BT_STATUS_SUCCESS) {
        ESP_LOGE(TAG, "BLE adv start failed: %d", param->adv_start_cmpl.status);
        this->advertising_ = false;
        this->done_ = true;
      }
      break;
    }
    case ESP_GAP_BLE_ADV_STOP_COMPLETE_EVT: {
      if (param->adv_stop_cmpl.status != ESP_BT_STATUS_SUCCESS) {
        ESP_LOGW(TAG, "BLE adv stop failed: %d", param->adv_stop_cmpl.status);
      }
      this->advertising_ = false;
      break;
    }
    default:
      break;
  }
}

}  // namespace esphome::bthome_adv

#endif
