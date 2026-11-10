import esphome.codegen as cg
from esphome.components import esp32_ble, sensor
from esphome.components.esp32 import add_idf_sdkconfig_option, request_bluetooth
from esphome.components.esp32_ble import CONF_BLE_ID
import esphome.config_validation as cv
from esphome.const import (
    CONF_CO2,
    CONF_DURATION,
    CONF_HUMIDITY,
    CONF_ID,
    CONF_INTERVAL,
    CONF_NAME,
    CONF_TEMPERATURE,
    CONF_TX_POWER,
)
CONF_BATTERY = "battery"
DEPENDENCIES = ["esp32", "esp32_ble"]

bthome_adv_ns = cg.esphome_ns.namespace("bthome_adv")
BTHomeAdv = bthome_adv_ns.class_("BTHomeAdv", cg.Component)



CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(): cv.declare_id(BTHomeAdv),
        cv.GenerateID(CONF_BLE_ID): cv.use_id(esp32_ble.ESP32BLE),
        cv.Required(CONF_NAME): cv.All(cv.string, cv.Length(max=10)),
        cv.Required(CONF_CO2): cv.use_id(sensor.Sensor),
        cv.Required(CONF_TEMPERATURE): cv.use_id(sensor.Sensor),
        cv.Required(CONF_HUMIDITY): cv.use_id(sensor.Sensor),
        cv.Optional(CONF_BATTERY): cv.use_id(sensor.Sensor),
        cv.Optional(CONF_DURATION, default="4s"): cv.positive_time_period_milliseconds,
        cv.Optional(CONF_INTERVAL, default="100ms"): cv.All(
            cv.positive_time_period_milliseconds,
            cv.Range(min=cv.TimePeriod(milliseconds=20), max=cv.TimePeriod(milliseconds=10240)),
        ),
        cv.OnlyWithout(CONF_TX_POWER, "esp32_hosted", default="0dBm"): cv.All(
            cv.conflicts_with_component("esp32_hosted"),
            cv.decibel,
            cv.enum(esp32_ble.TX_POWER_LEVELS, int=True),
        ),
    }
).extend(cv.COMPONENT_SCHEMA)

FINAL_VALIDATE_SCHEMA = esp32_ble.validate_variant


async def to_code(config):
    cg.add_define("USE_ESP32_BLE_UUID")
    cg.add_define("USE_ESP32_BLE_ADVERTISING")

    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)

    parent = await cg.get_variable(config[CONF_BLE_ID])
    esp32_ble.register_gap_event_handler(parent, var)
    cg.add(var.set_parent(parent))

    cg.add(var.set_name(config[CONF_NAME]))
    for key, setter in (
        (CONF_CO2, "set_co2_sensor"),
        (CONF_TEMPERATURE, "set_temperature_sensor"),
        (CONF_HUMIDITY, "set_humidity_sensor"),
    ):
        sens = await cg.get_variable(config[key])
        cg.add(getattr(var, setter)(sens))
    if CONF_BATTERY in config:
        sens = await cg.get_variable(config[CONF_BATTERY])
        cg.add(var.set_battery_sensor(sens))

    cg.add(var.set_duration_ms(config[CONF_DURATION]))
    cg.add(var.set_interval_ms(config[CONF_INTERVAL]))
    if CONF_TX_POWER in config:
        cg.add(var.set_tx_power(config[CONF_TX_POWER]))

    add_idf_sdkconfig_option("CONFIG_BT_ENABLED", True)
    add_idf_sdkconfig_option("CONFIG_BT_BLUEDROID_ENABLED", True)
    add_idf_sdkconfig_option("CONFIG_BT_BLE_42_FEATURES_SUPPORTED", True)
    request_bluetooth()
