#include <SPI.h>
#include <MFRC522.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <EEPROM.h>
#include <HTTPClient.h>
#include <Update.h>
#include <ArduinoJson.h>

// RFID Pins
#define SS_PIN  10
#define RST_PIN 9

// Feedback pins
#define GREEN_LED_PIN  4   // Green LED
#define RED_LED_PIN    8   // Red LED 
#define BUZZER_PIN    18   // Buzzer

// Buzzer tones (HZ)
#define TONE_SUCCESS 2000
#define TONE_ERROR   4000
#define TONE_ADD     1500
#define TONE_REMOVE  700

// EEPROM settings
#define MAX_CARDS 10
#define CARD_SIZE 4
#define EEPROM_SIZE 512




// WiFi credentials
const char* ssid = "SSID HERE";
const char* password = "SSID PASSWORD HERE";

// MQTT och API settings
const char* mqttServer = "YOUR-IP";
const int mqttPort = 8883;
const char* mqtt_topic = "rfid/readings";
const char* API_URL = "http://YOUR-IP:8000";

// Timer intervals
const unsigned long MAX_OFFLINE_TIME = 18000000; // 5 h
unsigned long lastSync = 0;
const unsigned long SYNC_INTERVAL = 300000; // 5 min
unsigned long lastUpdateCheck = 0;
const unsigned long UPDATE_CHECK_INTERVAL = 86400000; // 24 h

const unsigned long MODE_TIMEOUT = 30000;        // 30 sekunder timeout for admin-mode
unsigned long modeStartTime = 0;            // for timeout-managment

/*

possible future implentation for battery check if battery level is low

const unsigned long BATTERY_CHECK_INTERVAL = 0; 
unsigned long lastBatteryCheck = 0; 
*/

// OTA settings
String currentVersion = "1.0.0";  // Current firmware version
String lastResponse = "";         // Store MQTT response


// Dina befintliga certifikat
const char* ca_cert = R"(-----BEGIN CERTIFICATE-----
MIIDBTCCAe2gAwIBAgIUGARqcboLTXROE53oIWo/VEnbyhgwDQYJKoZIhvcNAQEL
BQAwEjEQMA4GA1UEAwwHTVFUVCBDQTAeFw0yNDEwMjYwNjM3MjVaFw0yNTEwMjYw
NjM3MjVaMBIxEDAOBgNVBAMMB01RVFQgQ0EwggEiMA0GCSqGSIb3DQEBAQUAA4IB
DwAwggEKAoIBAQCe7QXYscFuluZxNmsnFnop8Dy+XsX0tAsuN5ibSFkPNpWmjbVd
gNR5atgtt6PKAnDvOA+gPkvtyTTNVaCalyr5fAYtfRPJ5EdIZ9fLlrW2JKponURs
S7iFTx07At/dK3yZ2K/wgCR3qBo70rxxoT3UxxQHuQI4oE0HKEcqbPI9adyKRAYN
mfSItbmQSvJhUDDB3YS+jwmjZ6QOdSofczBsWROrP2JwMMwNPVLBXbY2DZZIBALX
95ikmlmNZd4/yIbcnnFsp3wrItLbHhb0ofI7Oadw8nrBud018TJ1F2qD1J2V1t7C
Vsqg5y9EoP4+KTgQaCDJh0V5hnddWVB6BHxbAgMBAAGjUzBRMB0GA1UdDgQWBBTa
C/e1tjfaB2vhYq2NAVLjGhFaAjAfBgNVHSMEGDAWgBTaC/e1tjfaB2vhYq2NAVLj
GhFaAjAPBgNVHRMBAf8EBTADAQH/MA0GCSqGSIb3DQEBCwUAA4IBAQByai4DxI0o
IaV5LGUsgOdPMvn+Jx7oBWFyFEhUjOOH/2QiL8BSlvAkQDrcV3WXJMTeGylfxNWn
5XhjTCq2EpbWR7Ua78sBRkr6QFcqIGcM4fXg3uawwa0/pZJmaYiKjQELOar7m6R/
LjamGDTswGc67fzydpb4hXjKR2GuRPsHUq6F8ZeT0PIR5Q+/NpAPmXbwpF+4Mc+U
pKNtquf3ijsBYui8ms0i41dbdD6aKOL1UOjtjnBGdnCaDmPK213GfU8i+mMKFssP
6sdvBatAOU4jUQQRZcy/7n3P/8DNOcgO3BfxWYXZRQGVUVIlkZVfJHutiRqblsLf
85MeZPbM/8f2
-----END CERTIFICATE-----)";

const char* client_cert = R"(-----BEGIN CERTIFICATE-----
MIIC+jCCAeKgAwIBAgIUK6ULIgHT+1Zis1IVf2uGCVUhJX4wDQYJKoZIhvcNAQEL
BQAwEjEQMA4GA1UEAwwHTVFUVCBDQTAeFw0yNDEwMjYwNjM3NDRaFw0yNTEwMjYw
NjM3NDRaMBgxFjAUBgNVBAMMDUFyZHVpbm9DbGllbnQwggEiMA0GCSqGSIb3DQEB
AQUAA4IBDwAwggEKAoIBAQChCuvvJag9gZ/BcKcizESMTwOHKmbXiTWV6BkxVCUZ
IkL3xULw8E0Ug4juUnLKTrGbxoz0Thg2VVz3JPFFdzaP/Tp7l33LuXZ7ihBO1Prb
cy2KihjiShjWvY9zTJ+AMNAbz8pL/hfL0fiwZbLxQ29R2XHb7EwHgqHPRjyWfr8j
gJ4vRjPXMYAmI2kozJnnj4riPLYqVPOGFj9/4nZzokT8E0/SANhEiXB6Qu+aUiD1
tNwOO//dFsejCSbp2Z5oassXQpiXj2to6qliURZxexYrFbpM4riWOB3Q3qnioFet
u35MhwXWtxgy30tkHeKwUHZyvPAVjq8isCzI2lE8motDAgMBAAGjQjBAMB0GA1Ud
DgQWBBTTL8utSNk++fByNCjwHKl26jVh0jAfBgNVHSMEGDAWgBTaC/e1tjfaB2vh
Yq2NAVLjGhFaAjANBgkqhkiG9w0BAQsFAAOCAQEAgPr4GviU4BV8cofcvFi0FVf3
PG1cXkNzTGTVaHe6Vvqojuf+UDtS7o5AZBorC44ilq5gZDGGEacPXvuAQlK4Zy0n
Y6H0G44N2jdfK40vSi2Oi6573/HQLqRMrA7zJvOuZcirYGUaawEdDVBJHDbp3Noo
Sn73j8Gvf7w5E7WcmAtucF5izeeSPLbf1IDt7+hAVU6/kVqetuV73lpZ7VRej3XU
SaVc4zeHivfGc35U7NEPHoXEonD0VKQhsxXlzj3l0GbVKnUziijrM5sXNkCT0YlJ
FHn8OYc4KCvssKsiXAuPMwYfdcx+62nJcEzl3uBznp0GzNIIXFsGgQJwMVZnRQ==
-----END CERTIFICATE-----)";

const char* client_key = R"(-----BEGIN PRIVATE KEY-----
MIIEvwIBADANBgkqhkiG9w0BAQEFAASCBKkwggSlAgEAAoIBAQChCuvvJag9gZ/B
cKcizESMTwOHKmbXiTWV6BkxVCUZIkL3xULw8E0Ug4juUnLKTrGbxoz0Thg2VVz3
JPFFdzaP/Tp7l33LuXZ7ihBO1Prbcy2KihjiShjWvY9zTJ+AMNAbz8pL/hfL0fiw
ZbLxQ29R2XHb7EwHgqHPRjyWfr8jgJ4vRjPXMYAmI2kozJnnj4riPLYqVPOGFj9/
4nZzokT8E0/SANhEiXB6Qu+aUiD1tNwOO//dFsejCSbp2Z5oassXQpiXj2to6qli
URZxexYrFbpM4riWOB3Q3qnioFetu35MhwXWtxgy30tkHeKwUHZyvPAVjq8isCzI
2lE8motDAgMBAAECggEAA9Hg/8aqY28YLXvxEvO6aoOTR1j7oIAqK7iaJF/lE2AL
K5pbuKBSi7qE/HYrL95G+zVt8XuKunsy3c/cAzRNMIQmp3jT7ImlJFAFjAEkRCFK
wr780R1F0o4jgW4fWGiP/yDiIQRRZy2/UtvOr0dUtCHOwBMuSH1SPjrhxAYUnZBt
StqyiHBWAgxTerSkXfnKNT9oTIZXTdQxSCggTmKwtxL2VIyO9HyWYglY073SJFAP
HnqNPiyssuDtIisk4dthr7/i6Vz1PTocGDHnt+mzvvreEXF0OSJe0UUhOcRW9Pg+
5ndMB2HSaD765KwH+9DjCUIboh1R80HfKfZHKzRJFQKBgQDV9fwtjYZN6nbbtrvP
5i1TC00Oq7X6kolfE1Pcw5TB/b99N2uBjaI2S/XSK9uTa9jMsU246ZFW9EXBh/sr
EzM9IrRICU+UZ1U+XITN8mp9s4Shm6U7Qtoys0Wkx917kgEKtBJn0xlx+wfrQV62
8we7zJvRce1bXHe3E8nNYmQK/QKBgQDArzQ4/N2ZGMnckhOTo/uCBe8nDYr93Sdp
4IJWaaa7mddrl7hAOlA7+NLcM8+/f3OUa7lgmsVGmOwSHozXdcfkZHI1q9Tcfhvp
SNL3laO2vSBx+1gO+S/60donIO0QbTaPzcfIeQ87qCx+aZKuRqa0iCIgKsKqOGAU
PgIVb2xjPwKBgQCR2vJiC0w26VLFTLiTbRIQvm91RND1U9eZnI9au2k5JUXYkmMT
Gf4ujXGyKHuy754HTAbzuyV85WB4Ib6zCo+vaW0EfnRlclvF+0P9MPgvYKVVlcj5
sQUV8ufTAPyXNFzJcx/o7xs1fC9VzGZIyTvIZh8ClGt+EHb7st2qyRvx8QKBgQC5
3QdB5WEYWdn2Iw4xP1/PV0wOXrjxEo//SGpRUo5brhUnGu3HPrjAcM9tS6kc7qMd
yx/BOOoMpFwrSj7PYzSTcfTdIsgsfJUN3Ypq+nQ2RI70g9+4adRHXH/TeKZUTxTv
eC87iNMR17I7qjisVUhfImXQo46tRb4gKIQ4CwgBXwKBgQCEk/kOMCA/Tke44+9w
yW9xPE0EZDsG7Bo/AGJCD7FuT/GX5oAWHarXRPA5frblWo6CDlmtADyOCJf3ec+E
5P+z7a5le7ywjzfA4B2UCbNY3aJT0gJbx3EFakERgQKBcnB5kPMf/jyQcKb+Vh/D
Hrby4RPCE7KS8Dj+pscQQaFUrw==
-----END PRIVATE KEY-----)";


enum Mode {
    DOOR_MODE,
    ADMIN_MODE
};

// Global variables
MFRC522 rfid(SS_PIN, RST_PIN);
WiFiClientSecure wifiClient;
PubSubClient client(wifiClient);
Mode currentMode = DOOR_MODE;
byte storedCards[MAX_CARDS][CARD_SIZE];
int numCards = 0;
String pendingCommand = "";
String deviceId;

// Function declarations
void loadCards();
void saveCards();
void handleCommands();
void checkForUpdates();
bool performUpdate(String version, String expectedChecksum, int firmware_size);
void syncWithServer();
String cardIdToString(byte* uid);
void reconnectMQTT();
void handleAccessResult(bool granted, const char* operation = "access");



// MQTT callback
void callback(char* topic, byte* payload, unsigned int length) {
    String message = String((char*)payload, length);
    
    // Handle responses from server
    if (strstr(topic, "/response")) {
        lastResponse = message;
        DynamicJsonDocument response(256);
        deserializeJson(response, message);
        
        if (response.containsKey("authorized")) {
            handleAccessResult(response["authorized"]);
            if (Serial) {
                Serial.print("Access ");
                Serial.println(response["authorized"] ? "Granted" : "Denied");
            }
        }
        return;
    }
    
    // Process incoming message
    DynamicJsonDocument doc(256);
    deserializeJson(doc, message);
    
    if (doc.containsKey("command")) {
        String command = doc["command"].as<String>();
        
        if (command == "add_mode") {
            currentMode = ADMIN_MODE;
            pendingCommand = "add";
            modeStartTime = millis();
            digitalWrite(GREEN_LED_PIN, HIGH);
            tone(BUZZER_PIN, TONE_ADD, 500);
            if (Serial) Serial.println("Add mode activated via MQTT");
        }
        else if (command == "remove_mode") {
            currentMode = ADMIN_MODE;
            pendingCommand = "remove";
            modeStartTime = millis();
            digitalWrite(RED_LED_PIN, HIGH);
            tone(BUZZER_PIN, TONE_REMOVE, 500);
            if (Serial) Serial.println("Remove mode activated via MQTT");
        }
        else if (command == "cancel") {
            currentMode = DOOR_MODE;
            pendingCommand = "";
            digitalWrite(GREEN_LED_PIN, LOW);
            digitalWrite(RED_LED_PIN, LOW);
            if (Serial) Serial.println("Admin mode cancelled via MQTT");
        }
        else if (command == "sync_request") {
            //if (Serial) Serial.println("Sync request received");
            syncWithServer();
        }
        else if (command == "update") {
            if (Serial) Serial.println("Checking for updates...");
            checkForUpdates();
        }
        else if (command == "status") {
            // Report device status back via MQTT
            DynamicJsonDocument statusDoc(256);
            statusDoc["device_id"] = deviceId;
            statusDoc["mode"] = currentMode == ADMIN_MODE ? "ADMIN" : "DOOR";
            statusDoc["version"] = currentVersion;
            statusDoc["uptime"] = millis();
            
            String statusMessage;
            serializeJson(statusDoc, statusMessage);
            client.publish(String(mqtt_topic + String("/status")).c_str(), statusMessage.c_str());
            
            if (Serial) Serial.println("Status report sent");
        }
    }
}

// Card operation handler
void handleCardOperation(const char* operation, byte* uid) {
    // Check memory limits first
    if (strcmp(operation, "add_card") == 0 && numCards >= MAX_CARDS) {
        Serial.println("Memory full - cannot add more cards");
        handleAccessResult(false, operation);
        return;
    }

    DynamicJsonDocument doc(256);
    doc["uid"] = cardIdToString(uid);
    doc["command"] = operation;
    doc["timestamp"] = millis();
    doc["device_id"] = deviceId;
    
    String message;
    serializeJson(doc, message);
    
    // Publish message
    if (client.publish(mqtt_topic, message.c_str())) {
        Serial.println("Command sent successfully");
        
        // Wait for response (timeout after 5 seconds)
        unsigned long startTime = millis();
        bool responseReceived = false;
        
        while (millis() - startTime < 5000 && !responseReceived) {
            client.loop();
            if (lastResponse.length() > 0) {
                DynamicJsonDocument response(256);
                deserializeJson(response, lastResponse);
                
                if (response["type"] == "response" && 
                    response["command"] == operation) {
                    
                    if (response["status"] == "success") {
                        handleAccessResult(true, operation);
                    } else {
                        handleAccessResult(false, operation);
                        Serial.print("Operation failed: ");
                        Serial.println(response["reason"].as<String>());
                    }
                    responseReceived = true;
                }
                lastResponse = "";
            }
            delay(10);
        }
        
        if (!responseReceived) {
            Serial.println("Timeout waiting for response");
            handleAccessResult(false, operation);
        }
    } else {
        Serial.println("Failed to send command");
        handleAccessResult(false, operation);
    }
}

// OTA Functions
void checkForUpdates() {
    HTTPClient http;
    String url = String(API_URL) + "/system/updates/available?device_id=" + deviceId + "&current_version=" + currentVersion;
    
    http.begin(wifiClient, url);
    int httpCode = http.GET();
    
    if (httpCode == HTTP_CODE_OK) {
        String payload = http.getString();
        DynamicJsonDocument doc(1024);
        deserializeJson(doc, payload);
        
        if (doc.containsKey("updates") && doc["updates"].size() > 0) {
            JsonObject update = doc["updates"][0];  // Get first available update
            String newVersion = update["version"].as<String>();
            String checksum = update["checksum"].as<String>();
            int firmware_size = update["size"].as<int>();
            
            Serial.printf("New firmware version %s available\n", newVersion.c_str());
            
            if (performUpdate(newVersion, checksum, firmware_size)) {
                currentVersion = newVersion;
                Serial.println("Update successful!");
                ESP.restart();
            }
        }
    }
    http.end();
}

bool performUpdate(String version, String expectedChecksum, int firmware_size) {
    HTTPClient http;
    String url = String(API_URL) + "/firmware/" + version;
    
    http.begin(wifiClient, url);
    int httpCode = http.GET();
    
    if (httpCode == HTTP_CODE_OK) {
        if (!Update.begin(firmware_size)) {
            Serial.println("Not enough space for update");
            return false;
        }
        
        const int bufferSize = 1024;
        uint8_t buffer[bufferSize];
        WiFiClient* stream = http.getStreamPtr();
        
        while (http.connected() && (firmware_size > 0)) {
            size_t available = stream->available();
            if (available) {
                int c = stream->readBytes(buffer, ((firmware_size > bufferSize) ? bufferSize : firmware_size));
                Update.write(buffer, c);
                firmware_size -= c;
            }
            delay(1);
        }
        
        if (Update.end()) {
            if (Update.md5String() != expectedChecksum) {
                Serial.println("Checksum verification failed!");
                return false;
            }
            Serial.println("Update successfully completed");
            return true;
        }
    }
    
    http.end();
    return false;
}

// EEPROM Functions
void loadCards() {
    numCards = EEPROM.read(0);
    if (numCards > MAX_CARDS) numCards = 0;
    
    for (int i = 0; i < numCards; i++) {
        for (int j = 0; j < CARD_SIZE; j++) {
            storedCards[i][j] = EEPROM.read(1 + (i * CARD_SIZE) + j);
        }
    }
    Serial.println("Loaded " + String(numCards) + " cards from memory");
}

void saveCards() {
    EEPROM.write(0, numCards);
    for (int i = 0; i < numCards; i++) {
        for (int j = 0; j < CARD_SIZE; j++) {
            EEPROM.write(1 + (i * CARD_SIZE) + j, storedCards[i][j]);
        }
    }
    EEPROM.commit();
    Serial.println("Cards saved to EEPROM");
}

// Server Sync
void syncWithServer() {
    DynamicJsonDocument doc(256);
    doc["command"] = "sync_request";
    doc["device_id"] = deviceId;
    
    String message;
    serializeJson(doc, message);
    client.publish(mqtt_topic, message.c_str());
}

// Helper Functions
void reconnectMQTT() {
    while (!client.connected()) {
        Serial.print("Attempting MQTT connection...");
        String clientId = "ESP32Client-" + String(random(0xffff), HEX);
        
        if (client.connect(clientId.c_str())) {
            Serial.println("connected");
            client.subscribe(mqtt_topic);
            client.subscribe(String(mqtt_topic + String("/response")).c_str());
        } else {
            Serial.print("failed, rc=");
            Serial.print(client.state());
            Serial.println(" retrying in 5 seconds");
            delay(5000);
        }
    }
}

String cardIdToString(byte* uid) {
    String cardId = "";
    for (byte i = 0; i < 4; i++) {
        cardId += (uid[i] < 0x10 ? "0" : "");
        cardId += String(uid[i], HEX);
    }
    return cardId;
}

void handleCommands() {
    if (Serial.available()) {
        String command = Serial.readStringUntil('\n');
        command.trim();
        
        if (command == "help") {
            Serial.println("\nAvailable commands:");
            Serial.println("------------------");
            Serial.println("add    - Add new card");
            Serial.println("remove - Remove a card");
            Serial.println("list   - List all stored cards");
            Serial.println("mode   - Switch between admin/door mode");
            Serial.println("update - Check and install firmware updates");
            Serial.println("help   - Show this help message");
            Serial.println("\nCurrent mode: " + String(currentMode == ADMIN_MODE ? "ADMIN" : "DOOR"));
        }
        else if (command == "add") {
            Serial.println("Place card to add...");
            currentMode = ADMIN_MODE;
            pendingCommand = "add";
            modeStartTime = millis();
        }
        else if (command == "remove") {
            Serial.println("Place card to remove...");
            currentMode = ADMIN_MODE;
            pendingCommand = "remove";
            modeStartTime = millis();
        }
        else if (command == "list") {
            listCards();
        }
        else if (command == "mode") {
            currentMode = (currentMode == ADMIN_MODE) ? DOOR_MODE : ADMIN_MODE;
            pendingCommand = "";
            Serial.println("Switched to " + String(currentMode == ADMIN_MODE ? "ADMIN" : "DOOR") + " mode");
        }
        else if (command == "update") {
            Serial.println("Checking for updates...");
            checkForUpdates();
        }
        else {
            Serial.println("Unknown command. Type 'help' for available commands.");
        }
    }
}

void listCards() {
    Serial.println("\nStored cards:");
    for (int i = 0; i < numCards; i++) {
        Serial.print(i + 1);
        Serial.print(": ");
        for (int j = 0; j < CARD_SIZE; j++) {
            Serial.print(storedCards[i][j] < 0x10 ? " 0" : " ");
            Serial.print(storedCards[i][j], HEX);
        }
        Serial.println();
    }
    Serial.println("Total cards: " + String(numCards));
}

void handleAccessResult(bool granted, const char* operation) {
    if (operation == "access") {
        if (granted) {
            // Access granted
            Serial.println("Access Granted - Door Opened");
            digitalWrite(GREEN_LED_PIN, HIGH);
            tone(BUZZER_PIN, TONE_SUCCESS, 500);
            delay(1000);
            digitalWrite(GREEN_LED_PIN, LOW);
        } else {
            // Access denied
            Serial.println("Access Denied - Unauthorized Card");
            for(int i = 0; i < 3; i++) {
                digitalWrite(RED_LED_PIN, HIGH);
                tone(BUZZER_PIN, TONE_ERROR, 100);
                delay(100);
                digitalWrite(RED_LED_PIN, LOW);
                noTone(BUZZER_PIN);
                delay(100);
            }
        }
    } 
    else if (operation == "add_card") {
        if (granted) {
            Serial.println("Card Added Successfully");
            digitalWrite(GREEN_LED_PIN, HIGH);
            tone(BUZZER_PIN, TONE_ADD, 1000);
            delay(1000);
            digitalWrite(GREEN_LED_PIN, LOW);
        } else {
            Serial.println("Failed to Add Card");
            for(int i = 0; i < 2; i++) {
                digitalWrite(RED_LED_PIN, HIGH);
                tone(BUZZER_PIN, TONE_ERROR, 200);
                delay(200);
                digitalWrite(RED_LED_PIN, LOW);
                noTone(BUZZER_PIN);
                delay(200);
            }
        }
    }
    else if (operation == "remove_card") {
        if (granted) {
            Serial.println("Card Removed Successfully");
            digitalWrite(RED_LED_PIN, HIGH);
            tone(BUZZER_PIN, TONE_REMOVE, 800);
            delay(800);
            digitalWrite(RED_LED_PIN, LOW);
        } else {
            Serial.println("Failed to Remove Card");
            for(int i = 0; i < 2; i++) {
                digitalWrite(RED_LED_PIN, HIGH);
                tone(BUZZER_PIN, TONE_ERROR, 200);
                delay(200);
                digitalWrite(RED_LED_PIN, LOW);
                noTone(BUZZER_PIN);
                delay(200);
            }
        }
    }
}

void setup() {
    Serial.begin(115200);
    while(!Serial) { ; }
    delay(1000);
    
    Serial.println("Starting secure RFID system...");
    pinMode(GREEN_LED_PIN, OUTPUT);
    pinMode(RED_LED_PIN, OUTPUT);
    pinMode(BUZZER_PIN, OUTPUT);

    // Test LED och Buzzer
    digitalWrite(GREEN_LED_PIN, HIGH);
    digitalWrite(RED_LED_PIN, HIGH);
    tone(BUZZER_PIN, TONE_SUCCESS, 200);
    delay(500);
    digitalWrite(GREEN_LED_PIN, LOW);
    digitalWrite(RED_LED_PIN, LOW);
    
    // Generate unique device ID
    deviceId = "ESP32_" + String((uint32_t)ESP.getEfuseMac(), HEX);
    Serial.println("Device ID: " + deviceId);
    
    // Initialize EEPROM
    EEPROM.begin(EEPROM_SIZE);
    loadCards();
    
    // Initialize RFID
    SPI.begin();
    rfid.PCD_Init();
    
    // Test RFID
    byte v = rfid.PCD_ReadRegister(MFRC522::VersionReg);
    Serial.print("RFID Version: 0x");
    Serial.println(v, HEX);
    
    // Connect to WiFi with visual feedback
    WiFi.begin(ssid, password);
    Serial.print("Connecting to WiFi");
    while (WiFi.status() != WL_CONNECTED) {
        digitalWrite(RED_LED_PIN, HIGH);
        delay(250);
        digitalWrite(RED_LED_PIN, LOW);
        delay(250);
        Serial.print(".");
    }
    // WiFi connected indication
    digitalWrite(GREEN_LED_PIN, HIGH);
    tone(BUZZER_PIN, TONE_SUCCESS, 200);
    delay(500);
    digitalWrite(GREEN_LED_PIN, LOW);
    
    Serial.println("\nWiFi connected");
    Serial.print("IP Address: ");
    Serial.println(WiFi.localIP());
    
    // Configure TLS/SSL
    wifiClient.setCACert(ca_cert);
    wifiClient.setCertificate(client_cert);
    wifiClient.setPrivateKey(client_key);
    
    // Configure MQTT
    client.setServer(mqttServer, mqttPort);
    client.setCallback(callback);
    
    // Connect to MQTT
    String clientId = "ESP32Client-" + String(random(0xffff), HEX);
    Serial.print("Connecting to MQTT as: ");
    Serial.println(clientId);
    
    if (client.connect(clientId.c_str())) {
        Serial.println("Connected to MQTT");
        // Subscribe to topics
        if (client.subscribe(mqtt_topic)) {
            Serial.println("Subscribed to main topic");
        }
        if (client.subscribe(String(mqtt_topic + String("/response")).c_str())) {
            Serial.println("Subscribed to response topic");
        }
        // MQTT connected indication
        digitalWrite(GREEN_LED_PIN, HIGH);
        tone(BUZZER_PIN, TONE_SUCCESS, 200);
        delay(500);
        digitalWrite(GREEN_LED_PIN, LOW);
    } else {
        Serial.print("MQTT connection failed, rc=");
        Serial.println(client.state());
        // Error indication
        for(int i = 0; i < 3; i++) {
            digitalWrite(RED_LED_PIN, HIGH);
            tone(BUZZER_PIN, TONE_ERROR, 200);
            delay(200);
            digitalWrite(RED_LED_PIN, LOW);
            delay(200);
        }
    }
    
    // Initial sync with server
    syncWithServer();
    
    Serial.println("Setup complete!");
    // Setup complete indication
    digitalWrite(GREEN_LED_PIN, HIGH);
    tone(BUZZER_PIN, TONE_SUCCESS, 500);
    delay(1000);
    digitalWrite(GREEN_LED_PIN, LOW);
}

void loop() {
    // Check MQTT connection
    if (!client.connected()) {
        reconnectMQTT();
    }
    client.loop();
    
    unsigned long currentMillis = millis();
    
    // Handle periodic tasks
    if (currentMillis - lastSync >= SYNC_INTERVAL) {
        syncWithServer();
        lastSync = currentMillis;
        lastServerSync = currentMillis;  // Uppdate offline timer when we sync
    }
    
    if (currentMillis - lastUpdateCheck >= UPDATE_CHECK_INTERVAL) {
        checkForUpdates();
        lastUpdateCheck = currentMillis;
    }
    
    // Handle serial commands if available
    if (Serial) {
        handleCommands();
    }
    
    // Check for new cards
    if (rfid.PICC_IsNewCardPresent() && rfid.PICC_ReadCardSerial()) {
        if (currentMode == ADMIN_MODE && pendingCommand != "") {
            if (pendingCommand == "add") {
                handleCardOperation("add_card", rfid.uid.uidByte);
                pendingCommand = "";
                currentMode = DOOR_MODE;
                digitalWrite(GREEN_LED_PIN, LOW);
            } 
            else if (pendingCommand == "remove") {
                handleCardOperation("remove_card", rfid.uid.uidByte);
                pendingCommand = "";
                currentMode = DOOR_MODE;
                digitalWrite(RED_LED_PIN, LOW);
            }
        } 
        else {
            // Normal card reading in door mode
            bool locallyVerified = false;
            
            // Check locally stored cards first
            for (int i = 0; i < numCards; i++) {
                bool match = true;
                for (byte j = 0; j < CARD_SIZE; j++) {
                    if (rfid.uid.uidByte[j] != storedCards[i][j]) {
                        match = false;
                        break;
                    }
                }
                if (match) {
                    locallyVerified = true;
                    break;
                }
            }

            // If MQTT is connected, proceed with server verification
            if (client.connected()) {
                String cardId = cardIdToString(rfid.uid.uidByte);
                DynamicJsonDocument doc(256);
                doc["uid"] = cardId;
                doc["timestamp"] = millis();
                doc["device_id"] = deviceId;
                
                String message;
                serializeJson(doc, message);
                
                if (client.publish(mqtt_topic, message.c_str())) {
                    unsigned long startTime = millis();
                    bool responseReceived = false;
                    
                    while (millis() - startTime < 2000 && !responseReceived) {
                        client.loop();
                        if (lastResponse.length() > 0) {
                            DynamicJsonDocument response(256);
                            deserializeJson(response, lastResponse);
                            
                            if (response.containsKey("authorized")) {
                                handleAccessResult(response["authorized"]);
                                if (Serial) {
                                    Serial.print("Access ");
                                    Serial.println(response["authorized"] ? "Granted" : "Denied");
                                }
                                responseReceived = true;
                            }
                            lastResponse = "";
                        }
                        delay(10);
                    }
                    
                    if (!responseReceived) {
                        if (Serial) Serial.println("No response from server - Using local verification");
                        if (currentMillis - lastServerSync < MAX_OFFLINE_TIME) {
                            handleAccessResult(locallyVerified);
                        } else {
                            handleAccessResult(false);
                        }
                    }
                } else {
                    if (Serial) Serial.println("Failed to send card reading - Using local verification");
                    if (currentMillis - lastServerSync < MAX_OFFLINE_TIME) {
                        handleAccessResult(locallyVerified);
                    } else {
                        handleAccessResult(false);
                    }
                }
            } else {
                // Offline mode with time limit
                if (currentMillis - lastServerSync < MAX_OFFLINE_TIME) {
                    handleAccessResult(locallyVerified);
                } else {
                    handleAccessResult(false);
                }
            }
        }
        
        rfid.PICC_HaltA();
        rfid.PCD_StopCrypto1();
    }

    // Handle mode timeout
    if (currentMode == ADMIN_MODE && (currentMillis - modeStartTime > MODE_TIMEOUT)) {
        currentMode = DOOR_MODE;
        pendingCommand = "";
        digitalWrite(GREEN_LED_PIN, LOW);
        digitalWrite(RED_LED_PIN, LOW);
        if (Serial) Serial.println("Admin mode timeout");
    }
    
    delay(100);
}
