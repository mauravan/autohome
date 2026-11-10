#include "runtime_epaper.h"

#include <esp_attr.h>

#include "esphome/core/application.h"
#include "esphome/core/hal.h"
#include "esphome/core/log.h"

namespace esphome::runtime_epaper {
static const char *const TAG = "runtime_epaper";

namespace {
struct RenderState {
  uint32_t magic;              // signature gate below is valid
  uint32_t signature;
  uint32_t panel_magic;        // the panel is showing an image this firmware wrote
  uint32_t values_magic;       // that image was drawn from real sensor readings
  uint16_t partial_refreshes;  // Mode 2 refreshes since the last Mode 1 cleanup
};
RTC_NOINIT_ATTR RenderState render_state;
constexpr uint32_t RENDER_MAGIC = 0x434F3246u;  // bumped: RenderState layout changed, stale RTC state must not be trusted
}  // namespace

bool RuntimeEPaper::needs_render(uint32_t signature) const {
  return render_state.magic != RENDER_MAGIC || render_state.signature != signature;
}

bool RuntimeEPaper::panel_has_values() const {
  return render_state.panel_magic == RENDER_MAGIC && render_state.values_magic == RENDER_MAGIC;
}

void RuntimeEPaper::commit_render(uint32_t signature, bool has_values) {
  render_state.magic = RENDER_MAGIC;
  render_state.signature = signature;
  render_state.values_magic = has_values ? RENDER_MAGIC : 0;
}

void RuntimeEPaper::force_render() {
  render_state.magic = 0;
  render_state.values_magic = 0;   // the glass content is not trusted after a cold boot
  render_state.panel_magic = 0;    // ...including for take_full_refresh_'s decision
}

void WaveformEPaperSSD1683::refresh_screen(bool /*partial*/) {
  const bool full = this->full_;
  this->full_ = true;  // one-shot: anything not explicitly marked partial refreshes fully
  ESP_LOGD(TAG, "Refresh: %s", full ? "Mode 1 (full)" : "Mode 2 (no flash)");
  epaper_spi::EPaperSSD1683::refresh_screen(!full);
}

bool RuntimeEPaper::take_full_refresh_() {
  if (this->force_full_ || render_state.panel_magic != RENDER_MAGIC) {
    this->force_full_ = false;
    render_state.partial_refreshes = 0;
    return true;
  }
  if (++render_state.partial_refreshes >= this->partial_refresh_limit_) {
    render_state.partial_refreshes = 0;
    return true;
  }
  return false;
}

display::DisplayRotation RuntimeEPaper::add_90_(display::DisplayRotation r) {
  return static_cast<display::DisplayRotation>((static_cast<int>(r) + 90) % 360);
}

void RuntimeEPaper::set_rotation(display::DisplayRotation rotation) {
  display::Display::set_rotation(rotation);
  this->apply_rotations_();
}

void RuntimeEPaper::apply_rotations_() {
  // 1.54" is mounted 90 degrees relative to the 4.2" landscape panel.
  this->small_.set_rotation(add_90_(this->rotation_));
  this->large_.set_rotation(this->rotation_);
}

void RuntimeEPaper::setup() {
  for (auto *panel : {&this->small_, &this->large_}) {
    panel->set_dc_pin(this->dc_pin_);
    panel->set_reset_pin(this->reset_pin_);
    panel->set_busy_pin(this->busy_pin_);
    panel->set_spi_parent(this->parent_);
    panel->set_cs_pin(this->cs_);
    panel->set_data_rate(this->data_rate_);
    panel->set_mode(this->mode_);
    panel->set_auto_clear(false);       // the outer forwards the page drawing
    panel->set_full_update_every(1);   // keep upstream on a full-window transfer: this firmware redraws the
                                       // whole page, so every refresh rewrites all panel RAM and the waveform
                                       // is chosen in refresh_screen() instead
  }
  this->small_.set_reset_duration(2);
  this->large_.set_reset_duration(10);
  this->apply_rotations_();

  this->panel_ = this->requested_panel_;
  this->active_ = this->panel_ == PANEL_42 ? &this->large_ : &this->small_;
  this->active_panel_ = this->panel_ == PANEL_42 ? &this->large_ : &this->small_;
  this->active_->setup();               // buffer + pins + SPI, no panel init yet
  if (this->panel_ == PANEL_42) {
    this->setup_42_ = true;
  } else {
    this->setup_154_ = true;
  }
}

void RuntimeEPaper::update() {
  if (this->active_ == nullptr || this->active_panel_ == nullptr)
    return;

  this->active_panel_->set_full_refresh(this->take_full_refresh_());
  this->do_update_();                   // clears white, runs the current page lambda
  this->active_->update();              // starts the epaper_spi state machine
  uint32_t start = millis();
  while (this->active_->is_updating()) {
    this->active_->loop();              // pump the non-blocking state machine
    App.feed_wdt();
    delay(1);                           // BUSY poll; the CPU must stay awake for the whole frame
    if (millis() - start > 15000) {
      ESP_LOGW(TAG, "e-paper update did not finish within 15s");
      break;
    }
  }
  if (!this->active_->is_updating())
    render_state.panel_magic = RENDER_MAGIC;  // the panel now shows this image
}

void RuntimeEPaper::apply_panel_change() {
  if (this->active_ == nullptr || this->requested_panel_ == this->panel_)
    return;

  this->panel_ = this->requested_panel_;
  this->active_ = this->panel_ == PANEL_42 ? &this->large_ : &this->small_;
  this->active_panel_ = this->panel_ == PANEL_42 ? &this->large_ : &this->small_;
  this->apply_rotations_();

  bool &done = this->panel_ == PANEL_42 ? this->setup_42_ : this->setup_154_;
  if (!done) {
    this->active_->setup();
    done = true;
  }
  this->active_->request_full_update();
  this->force_full_ = true;   // the newly selected panel may never have been written
  this->update();
}

int RuntimeEPaper::get_width() {
  return this->active_ != nullptr ? this->active_->get_width() : 200;
}
int RuntimeEPaper::get_height() {
  return this->active_ != nullptr ? this->active_->get_height() : 200;
}
int RuntimeEPaper::get_width_internal() {
  return this->active_ != nullptr ? this->active_->get_native_width() : 200;
}
int RuntimeEPaper::get_height_internal() {
  return this->active_ != nullptr ? this->active_->get_native_height() : 200;
}

void RuntimeEPaper::draw_pixel_at(int x, int y, Color color) {
  if (this->active_ == nullptr || this->is_point_clipped(x, y))
    return;
  // Preserve the old waveshare_epaper convention for this codebase:
  // COLOR_ON is ink (black), COLOR_OFF is paper (white). epaper_spi uses
  // luminance, so invert at the boundary.
  this->active_->draw_pixel_at(x, y, ~color);
}

void RuntimeEPaper::fill(Color color) {
  if (this->active_ != nullptr)
    this->active_->fill(~color);
}

void RuntimeEPaper::clear() {
  if (this->active_ != nullptr)
    this->active_->clear();             // epaper_spi clear = white paper
}

display::DisplayType RuntimeEPaper::get_display_type() {
  return this->active_ != nullptr ? this->active_->get_display_type()
                                  : display::DISPLAY_TYPE_BINARY;
}

void RuntimeEPaper::dump_config() {
  ESP_LOGCONFIG(TAG, "Runtime E-Paper:");
  ESP_LOGCONFIG(TAG, "  Active panel: %s",
                this->panel_ == PANEL_42 ? "4.2in 400x300" : "1.54in 200x200");
  ESP_LOGCONFIG(TAG, "  Full refresh every: %u partial refreshes", this->partial_refresh_limit_);
  LOG_PIN("  DC Pin: ", this->dc_pin_);
  LOG_PIN("  Reset Pin: ", this->reset_pin_);
  LOG_PIN("  Busy Pin: ", this->busy_pin_);
  LOG_PIN("  CS Pin: ", this->cs_);
}

}  // namespace esphome::runtime_epaper
