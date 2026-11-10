#pragma once
// ESP-IDF's lwIP SNTP module polls once at init (before the station associates) and then
// retries on a 15 s+backoff timer, so the first sync can land ~24 s after WiFi even when
// the LAN NTP server answers instantly. sntp_restart() re-inits the module, which sends a
// request immediately. Declared here (C linkage, exported by lwip) instead of including
// <esp_sntp.h>, whose lwip include path is not guaranteed for the generated main.cpp.
extern "C" bool sntp_restart(void);
inline void sntp_poll_now() { sntp_restart(); }
