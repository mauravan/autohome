#pragma once

#include "esphome/components/display/display.h"
#include "esphome/components/epaper_spi/epaper_spi_ssd1683.h"
#include "esphome/components/spi/spi.h"

namespace esphome::runtime_epaper {

class RuntimeEPaper : public display::Display,
                      public spi::SPIDevice<spi::BIT_ORDER_MSB_FIRST,
                                            spi::CLOCK_POLARITY_LOW,
                                            spi::CLOCK_PHASE_LEADING,
                                            spi::DATA_RATE_2MHZ> {
 public:
  void set_dc_pin(GPIOPin *pin) { this->dc_pin_ = pin; }
  void set_reset_pin(GPIOPin *pin) { this->reset_pin_ = pin; }
  void set_busy_pin(GPIOPin *pin) { this->busy_pin_ = pin; }

  void set_panel_requested(bool is_42) {
    this->requested_panel_ = is_42 ? PANEL_42 : PANEL_154;
  }
  bool is_panel_change_pending() const {
    return this->active_ != nullptr && this->requested_panel_ != this->panel_;
  }
  void apply_panel_change();

  void set_rotation(display::DisplayRotation rotation) override;
  void setup() override;
  void update() override;
  void dump_config() override;

  int get_width() override;
  int get_height() override;
  void draw_pixel_at(int x, int y, Color color) override;
  void fill(Color color) override;
  void clear() override;
  display::DisplayType get_display_type() override;

  float get_setup_priority() const override { return setup_priority::PROCESSOR; }

 protected:
  int get_width_internal() override;
  int get_height_internal() override;
  void apply_rotations_();
  static display::DisplayRotation add_90_(display::DisplayRotation r);

  enum Panel : uint8_t { PANEL_154 = 0, PANEL_42 = 1 };

  // Flattened init sequences: cmd, arg-count, args...
  // SSD1681 200x200: driver output 199, temp sensor, data entry.
  static constexpr uint8_t INIT_154[] = {
      0x01, 0x03, 0xC7, 0x00, 0x00,
      0x18, 0x01, 0x80,
      0x11, 0x01, 0x03,
  };
  // SSD1683 400x300: driver output 299 (0x012B), temp sensor, data entry.
  static constexpr uint8_t INIT_42[] = {
      0x01, 0x03, 0x2B, 0x01, 0x00,
      0x18, 0x01, 0x80,
      0x11, 0x01, 0x03,
  };

  epaper_spi::EPaperSSD1683 small_{"WeAct-1.54", 200, 200, INIT_154, sizeof(INIT_154)};
  epaper_spi::EPaperSSD1683 large_{"WeAct-4.2", 400, 300, INIT_42, sizeof(INIT_42)};

  epaper_spi::EPaperBase *active_{nullptr};
  GPIOPin *dc_pin_{nullptr};
  GPIOPin *reset_pin_{nullptr};
  GPIOPin *busy_pin_{nullptr};
  Panel requested_panel_{PANEL_154};
  Panel panel_{PANEL_154};
  bool setup_154_{false};
  bool setup_42_{false};
};

}  // namespace esphome::runtime_epaper
