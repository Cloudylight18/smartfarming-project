#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClient.h>
#include <DHT.h>
#include <ArduinoJson.h>

const char* WIFI_SSID     = "Numpang Mulu!!!";
const char* WIFI_PASSWORD = "Gua miskin";
const char* SERVER_HOST   = "http://10.112.209.131:5000";

#define DHTPIN      D2        
#define DHTTYPE     DHT11  
DHT dht(DHTPIN, DHTTYPE);

// KONFIGURASI SENSOR TANAH
#define SOIL_PIN    A0        


const int SOIL_RAW_KERING = 1023;  
const int SOIL_RAW_BASAH  = 300;   

#define RELAY_PIN   D1    
const bool RELAY_ACTIVE_LOW = false;

// KONFIGURASI LAMPU INDIKATOR
#define LED_MERAH   D5   
#define LED_HIJAU   D6   
#define LED_KUNING  D7   

float suhu = 0.0;
float kelembapanUdara = 0.0;
float kelembapanTanah = 0.0;
bool statusRelay = true;

const unsigned long INTERVAL_MS = 1000;
unsigned long lastSend = 0;

WiFiClient wifiClient;

void setRelay(bool on) {
  statusRelay = on;
  digitalWrite(RELAY_PIN, RELAY_ACTIVE_LOW ? !on : on);
}

void connectWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Konek WiFi");
  
  unsigned long startAttemptTime = millis();
  while (WiFi.status() != WL_CONNECTED) {
    delay(500); 
    Serial.print(".");
    if (millis() - startAttemptTime > 15000) {
      Serial.println("\nGagal terhubung. Restart otomatis...");
      ESP.restart();
    }
  }
  Serial.println("\nWiFi OK!");
}

// FUNGSI KONDISI LAMPU 
void kondisiKering() {
  digitalWrite(LED_MERAH, HIGH);
  digitalWrite(LED_HIJAU, LOW);
  digitalWrite(LED_KUNING, LOW);
  Serial.print(" [Status: KERING] ");
}

void kondisiLembab() {
  digitalWrite(LED_MERAH, LOW);
  digitalWrite(LED_HIJAU, HIGH);
  digitalWrite(LED_KUNING, LOW);
  Serial.print(" [Status: LEMBAB] ");
}

void kondisiBasah() {
  digitalWrite(LED_MERAH, LOW);
  digitalWrite(LED_HIJAU, LOW);
  digitalWrite(LED_KUNING, HIGH);
  Serial.print(" [Status: BASAH] ");
}


void evaluasiKondisiTanah() {
  if (kelembapanTanah < 30.0) {
    kondisiKering();
  } else if (kelembapanTanah >= 30.0 && kelembapanTanah <= 70.0) {
    kondisiLembab();
  } else {
    kondisiBasah();
  }
}

void bacaSensor() {
  float t = dht.readTemperature();
  float h = dht.readHumidity();

  if (!isnan(t)) suhu = t;
  if (!isnan(h)) kelembapanUdara = h;
  int raw = analogRead(SOIL_PIN);
  float persen = (float)(SOIL_RAW_KERING - raw) * 100.0 / (float)(SOIL_RAW_KERING - SOIL_RAW_BASAH);

  if (persen < 0) persen = 0;
  if (persen > 100) persen = 100;
  
  kelembapanTanah = persen;
}

void kirimData() {
  if (WiFi.status() != WL_CONNECTED) return;
  HTTPClient http;

  http.begin(wifiClient, String(SERVER_HOST) + "/api/sensors");
  http.addHeader("Content-Type", "application/json");

  StaticJsonDocument<128> doc;
  doc["suhu"] = suhu;
  doc["lembap"] = kelembapanUdara;
  doc["tanah"] = kelembapanTanah;

  String payload;
  serializeJson(doc, payload);

  int code = http.POST(payload);
  if (code == 200) {
    String resBody = http.getString();
    StaticJsonDocument<128> resDoc;
    if (!deserializeJson(resDoc, resBody)) {
      bool commandRelay = resDoc["actuator_on"];
      setRelay(commandRelay);
    }
  } else {
    Serial.printf("Gagal HTTP, Kode: %d\n", code);
  }
  http.end();
}

void setup() {
  Serial.begin(115200);
  pinMode(RELAY_PIN, OUTPUT);
  setRelay(false);
  pinMode(LED_MERAH, OUTPUT);
  pinMode(LED_HIJAU, OUTPUT);
  pinMode(LED_KUNING, OUTPUT);
  
  dht.begin();
  connectWiFi();
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    connectWiFi();
  }

  if (millis() - lastSend >= INTERVAL_MS) {
    lastSend = millis();
    
    bacaSensor();          
    evaluasiKondisiTanah(); 
    kirimData();          
    
    Serial.printf("| Analog: %d -> Persen: %.1f%% | Suhu: %.1f°C | Pompa: %s\n",
                  analogRead(SOIL_PIN), kelembapanTanah, suhu, statusRelay ? "ON" : "OFF");
  }
}