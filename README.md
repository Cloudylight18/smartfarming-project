# Web Monitoring 2 Sensor + Kontrol 1 Aktuator (Python/Flask)

Aplikasi web sederhana untuk memantau 2 sensor (Suhu & Kelembapan) dan
mengontrol 1 aktuator (Kipas). Semua logika — simulasi sensor, histori,
mode otomatis, kontrol aktuator — berjalan di **Python (Flask)**, bukan
JavaScript. Halaman HTML hanya menampilkan hasil render dari server dan
mengirim form biasa, lalu me-refresh otomatis tiap 3 detik.

## Isi folder

```
monitoring-py/
├── app.py              # aplikasi Flask + logika sensor & aktuator
├── requirements.txt    # dependensi Python
├── templates/
│   └── index.html      # halaman utama (Jinja2)
└── static/
    └── style.css        # tampilan
```

## Cara menjalankan

1. (Opsional) buat virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate      # Windows: venv\Scripts\activate
   ```

2. Install dependensi:
   ```
   pip install -r requirements.txt
   ```

3. Jalankan server:
   ```
   python app.py
   ```

4. Buka browser ke:
   ```
   http://localhost:5000
   ```

## Fitur

- **Sensor Suhu (°C)** dan **Sensor Kelembapan (%)** — nilai disimulasikan
  di server dengan random walk tiap kali halaman dimuat, lengkap dengan
  grafik mini (SVG, digambar dari data histori Python) dan status
  Normal / Tinggi / Panas.
- **Kontrol Kipas (aktuator)**:
  - Mode **Manual** — tombol ON/OFF.
  - Mode **Otomatis** — kipas menyala sendiri jika suhu melewati ambang
    batas yang bisa diatur (default 30°C).
- **Log aktivitas** — mencatat setiap perubahan status aktuator dan mode.

## Menghubungkan ke ESP32 / ESP8266 (sensor & aktuator sungguhan)

Ada dua pilihan firmware, tinggal pakai sesuai board yang Anda punya:

- `esp32-firmware/esp32_monitoring.ino` -> untuk board **ESP32**
- `esp8266-firmware/esp8266_monitoring.ino` -> untuk board **ESP8266 / NodeMCU**

Keduanya membaca sensor **DHT22** (suhu & kelembapan) dan mengontrol
**relay/kipas**, lalu berkomunikasi dengan server Flask ini lewat HTTP.
Logikanya identik, hanya library WiFi/HTTP dan penomoran pin yang beda
menyesuaikan chip masing-masing.

### Alur komunikasi

```
ESP32/ESP8266 --POST JSON--> Flask /api/sensors    (kirim suhu & kelembapan)
ESP32/ESP8266 --GET-------->  Flask /api/actuator  (ambil status ON/OFF terbaru)
```

Begitu server menerima data dari `/api/sensors`, dashboard otomatis
berpindah ke mode **"Perangkat IoT (data nyata)"** (terlihat di pojok kanan
atas), dan simulasi acak berhenti. Jika perangkat berhenti mengirim data
selama 15 detik, dashboard otomatis kembali ke mode simulasi.

### Langkah setup - ESP32

1. Install **Arduino IDE**, lalu tambahkan board **ESP32**
   (Boards Manager -> cari "esp32" by Espressif).
2. Install library (Library Manager):
   - `DHT sensor library` (by Adafruit)
   - `Adafruit Unified Sensor`
   - `ArduinoJson` (versi 6.x)
3. Wiring: **DHT22** VCC->3V3, GND->GND, DATA->**GPIO4**.
   **Relay** VCC->5V, GND->GND, IN->**GPIO26**.
4. Buka `esp32-firmware/esp32_monitoring.ino`, ganti `WIFI_SSID`,
   `WIFI_PASSWORD`, dan `SERVER_HOST` (IP komputer server Flask).
5. Upload ke board, buka Serial Monitor (baud 115200) untuk memastikan
   koneksi WiFi & pengiriman data berhasil.

### Langkah setup - ESP8266 / NodeMCU

1. Install **Arduino IDE**, lalu tambahkan board **ESP8266**
   (Boards Manager -> cari "esp8266" by ESP8266 Community), pilih board
   "NodeMCU 1.0 (ESP-12E Module)" (atau sesuai modul Anda).
2. Install library yang sama seperti di atas (DHT sensor library,
   Adafruit Unified Sensor, ArduinoJson).
3. Wiring: **DHT22** VCC->3V3, GND->GND, DATA->**D4**.
   **Relay** VCC->5V (pin VU/VIN), GND->GND, IN->**D1**.
4. Buka `esp8266-firmware/esp8266_monitoring.ino`, ganti `WIFI_SSID`,
   `WIFI_PASSWORD`, dan `SERVER_HOST` (IP komputer server Flask).
5. Upload ke board, buka Serial Monitor (baud 115200) untuk memastikan
   koneksi WiFi & pengiriman data berhasil.

> Cek IP komputer server dengan `ipconfig` (Windows) atau
> `ifconfig` / `ip addr` (Mac/Linux). Pastikan board dan komputer server
> berada di **jaringan WiFi yang sama**.

Setelah board menyala dan terkoneksi, jalankan `python app.py` di komputer,
lalu buka `http://<IP-komputer>:5000` dari browser mana pun di jaringan
yang sama.


### Kalau tidak pakai DHT22 / sensor lain

Ganti bagian pembacaan sensor di `loop()` pada file `.ino` sesuai sensor Anda
(misalnya sensor cahaya LDR, soil moisture, dsb.), selama nilainya tetap
dikirim sebagai dua angka `suhu` dan `lembap` ke endpoint `/api/sensors`
(nama field boleh disesuaikan asal konsisten dengan `app.py`).

### Kalau pakai Raspberry Pi (bukan ESP32)

Ubah `set_actuator_hardware(on)` di `app.py`, contoh untuk GPIO Raspberry Pi:

```python
import RPi.GPIO as GPIO
RELAY_PIN = 17
GPIO.setmode(GPIO.BCM)
GPIO.setup(RELAY_PIN, GPIO.OUT)

def set_actuator_hardware(on: bool):
    GPIO.output(RELAY_PIN, GPIO.HIGH if on else GPIO.LOW)
```
