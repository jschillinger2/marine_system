EXPERIMENTAL VERSION 

# 🛰️ OpenPlotter Signal K System Monitor + Shutdown Server

This project is a combined Python service for Raspberry Pi running **OpenPlotter** and **Signal K**. It monitors key system metrics and sends them to Signal K, while also exposing a **shutdown button endpoint** for integration into the Signal K KIP dashboard.

---

## 📦 Features

- ✅ Send **CPU temperature**, **CPU usage**, and **system uptime** to Signal K
- ✅ Report **LTE signal strength** (via `mmcli`) to Signal K
- ✅ Run a local **Flask server** with a `/shutdown` endpoint
- ✅ Configure Signal K credentials in an external `config.properties` file
- ✅ Designed for marine environments with OpenPlotter + Signal K
- ✅ Easily integratable with **KIP**
