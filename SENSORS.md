# Sensors

| Sensor / Module | Function | Description |
|---|---|---|
| Sensirion SCD41 | CO2 + temperature + humidity | I2C, single-package NDIR CO2 sensor, 400–5000 ppm ±(50 ppm + 5%). 3 units bought for floor nodes |
| DHT11 | Temperature + humidity | 1-Wire, bench spare only, ±2 °C / ±5 %RH, not deployed |
| LSM6DSOX (STEVAL-MKI197V1) | 6-axis IMU (accel + gyro) | I2C/SPI, ±2/4/8/16 g accel, ±125–2000 dps gyro, vibration + tilt R&D for blinds/windows |
| ADXL335 BBoard v2 | 3-axis analog accelerometer | ±3 g, 3 analog voltage outputs, tilt/vibration on blind/window motor or door; needs ADC |
| ADXL335 (on Joy-Pi breadboard) | 3-axis analog accelerometer | Same sensor on Joy-Pi breakout, bench prototyping |
| H3LIS331DL (on Joy-Pi breadboard) | 3-axis high-g accelerometer | ±100/200/400 g, shock/impact detection, bench prototyping |
| MPU6050 (on Joy-Pi breadboard) | 6-axis IMU (accel + gyro) | I2C, ±2/4/8/16 g, ±250–2000 dps, bench IMU prototyping |
| BMP280 (on Joy-Pi breadboard) | Barometric pressure + temperature | I2C, 300–1100 hPa, ±1 hPa, bench altimeter/weather prototyping |
| BMP180 (on Joy-Pi breadboard) | Barometric pressure + temperature | I2C, legacy predecessor to BMP280, bench prototyping |
| BME280 (on Joy-Pi breadboard) | Temp + humidity + pressure | I2C, ±1 °C / ±3 %RH / ±1 hPa, bench env prototyping |
| DHT22 / AM2302 (on Joy-Pi breadboard) | Temperature + humidity | 1-Wire, ±0.5 °C / ±2 %RH, bench env prototyping |
| DS18B20 (on Joy-Pi breadboard) | 1-Wire temperature | ±0.5 °C, waterproof probe variant available, bench 1-Wire prototyping |
| TSL2561 (on Joy-Pi breadboard) | Ambient light | I2C, 0.1–40000 lux, bench lux prototyping |
| BH1750 (on Joy-Pi breadboard) | Ambient light | I2C, 1–65535 lux, bench lux prototyping |
| VEML6075 (on Joy-Pi breadboard) | UV index (UVA + UVB) | I2C, UV index 0–15+, bench UV prototyping |
| MQ-2 (on Joy-Pi breadboard) | LPG / propane / smoke | Analog, heater + analog out, bench gas prototyping |
| MQ-7 (on Joy-Pi breadboard) | Carbon monoxide | Analog, cyclic heater, bench CO prototyping |
| MQ-135 (on Joy-Pi breadboard) | Air quality (CO2, NH3, benzene, smoke) | Analog, broad VOC/CO2 proxy, bench AQ prototyping |
| MQ-9 (on Joy-Pi breadboard) | LPG / CO / CH4 | Analog, cyclic heater, bench gas prototyping |
| MICS-5524 (on Joy-Pi breadboard) | CO / VOC / reducing gases | I2C, MEMS metal-oxide, bench gas prototyping |
| SGP30 (on Joy-Pi breadboard) | TVOC + eCO2 | I2C, Sensirion MOX, bench TVOC/eCO2 prototyping |
| CCS811 (on Joy-Pi breadboard) | TVOC + eCO2 | I2C, AMS MOX, bench TVOC/eCO2 prototyping |
| PMS5003 (on Joy-Pi breadboard) | PM1.0 / PM2.5 / PM10 | UART, laser scattering, bench particulate prototyping |
| SPS30 (on Joy-Pi breadboard) | PM1.0 / PM2.5 / PM4 / PM10 | I2C/UART, Sensirion laser, bench particulate prototyping |
| MH-Z19B (on Joy-Pi breadboard) | NDIR CO2 | UART/PWM, 0–5000 ppm, bench CO2 prototyping |
| Winsen ZE08-CH2O (on Joy-Pi breadboard) | Formaldehyde | UART, electrochemical, bench CH2O prototyping |
| Reed switch (on Joy-Pi breadboard) | Door/window open/close | Digital dry contact, magnetic, bench contact prototyping |
| Hall effect sensor (on Joy-Pi breadboard) | Magnetic field / position | Digital or analog, bench position prototyping |
| Tilt sensor / ball switch (on Joy-Pi breadboard) | Orientation / tilt | Digital, bench tilt prototyping |
| HC-SR04 (on Joy-Pi breadboard) | Ultrasonic distance | 2–400 cm, GPIO trig/echo, bench distance prototyping |
| VL53L0X (on Joy-Pi breadboard) | Time-of-flight distance | I2C, up to 2 m, bench ToF prototyping |
| TCRT5000 (on Joy-Pi breadboard) | IR reflective / line / proximity | Analog/digital, bench IR prox prototyping |
| KY-008 (on Joy-Pi breadboard) | Laser dot | 650 nm, digital on/off, bench laser prototyping |
| KY-022 / VS1838B (on Joy-Pi breadboard) | IR receiver | 38 kHz, NEC/RC5/etc, IR remote prototyping |
| KY-005 (on Joy-Pi breadboard) | IR transmitter | 38 kHz, IR remote prototyping |
| KY-012 / KY-006 (on Joy-Pi breadboard) | Active / passive buzzer | GPIO tone, audible alert prototyping |
| KY-009 / KY-016 (on Joy-Pi breadboard) | RGB LED (common anode/cathode) | PWM color mixing, status light prototyping |
| Rotary encoder + push (on Joy-Pi breadboard) | Rotary input + select | Quadrature + push, UI input prototyping |
| Joystick module (on Joy-Pi breadboard) | 2-axis analog + push | 2× analog + digital, UI input prototyping |
| 4×4 matrix keypad (on Joy-Pi breadboard) | 16-key input | 8 GPIO, keypad prototyping |
| Servo (SG90 / MG996R on Joy-Pi breadboard) | Positional actuator | PWM, bench actuator prototyping |
| Stepper 28BYJ-48 + ULN2003 (on Joy-Pi breadboard) | Stepper motor | 4-phase, driver board, bench stepper prototyping |
| DC motor + L298N (on Joy-Pi breadboard) | Brushed DC motor | H-bridge, PWM speed + direction, bench DC prototyping |
| Relay module 1/2/4/8-ch (on Joy-Pi breadboard) | Mains/load switching | Opto-isolated, GPIO trigger, bench switching prototyping |
| Solenoid (on Joy-Pi breadboard) | Linear actuator | 5/12 V, driver needed, bench linear prototyping |
| KY-040 | Rotary encoder | Quadrature encoder with push button, direction + speed + select, UI input prototyping |
| YL-69 | Soil moisture sensor | Two-probe conductive sensor, analog output, garden/plant moisture monitoring |