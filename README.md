# Secure RFID Access System - Proof of Concept (PoC)



https://github.com/user-attachments/assets/fd297c8e-743e-4573-a3ef-4ac2900b6549


*Demo showing access denied (white RFID card) and access granted (blue RFID tag)*


## Executive Summary
This Proof of Concept (PoC) demonstrates a secure IoT solution for RFID access control, designed in compliance with the Cyber Resilience Act (CRA). The system incorporates industry-standard security practices, secure communication protocols, and robust system architecture.

## 1. System Overview

### 1.1 Purpose
The system provides a secure RFID-based access control solution with:
- Centralized management of access cards
- Real-time monitoring and logging
- Secure over-the-air updates
- Comprehensive backup system
- Security vulnerability monitoring

### 1.2 Core Features
- RFID card registration and verification
- Secure MQTT communication over TLS
- Automated firmware updates
- Security event monitoring
- Data backup and recovery
- Access logging and analytics

## 2. Technical Architecture

### 2.1 Hardware Components
- ESP32 Microcontroller
- MFRC522 RFID Reader
- Status LEDs and Buzzer
- EEPROM for local storage

### 2.2 Software Components
- ESP32 Firmware (C++)
- FastAPI Backend Server (Python)
- MongoDB Database
- MQTT Broker with TLS
- Management Services:
  - Card Management
  - Security Monitoring
  - Backup System
  - Update Management
  - Vulnerability Scanner

### 2.3 System Architecture Diagram
![architecture](https://github.com/user-attachments/assets/a747830a-630e-4a59-98a3-a10dd7ed6a6c)


## 3. Security Implementation

### 3.1 Communication Security
- **Protocol**: MQTT over TLS (Port 8883)
- **Authentication**: Mutual TLS (mTLS)
- **Certificates**:
  - CA Certificate
  - Client Certificates
  - Client Keys
- **TLS Version**: 1.2 minimum

### 3.2 Device Security
- Secure boot process
- Local EEPROM encryption
- Access attempt monitoring
- Offline fallback capability
- Rate limiting for card reads

### 3.3 Backend Security
- API authentication
- Database encryption
- Access logging
- Intrusion detection
- Regular backups
- Security event monitoring

## 4. CRA Compliance

### 4.1 Security by Design
- Encrypted communication
- Secure storage
- Authentication systems
- Access monitoring
- Event logging

### 4.2 Update Management
- OTA update system
- Version control
- Update verification
- Automatic update checks

### 4.3 Vulnerability Management
- Security monitoring
- Event logging
- Basic vulnerability scanning

## 5. Data Flow

### 5.1 Card Access Flow
1. Card presented to RFID reader
2. ESP32 reads card data
3. Data sent via MQTT over TLS
4. Backend verifies authorization
5. Response returned to device
6. Access granted/denied feedback via LED/Buzzer

### 5.2 Management Flow
1. Admin initiates command
2. Command sent via secure API
3. Backend processes request
4. Changes synchronized to devices
5. Action logged and verified

## 6. Backup and Recovery

### 6.1 Backup System
- Daily automated backups
- Weekly consolidation
- Monthly archives
- Critical event backups

### 6.2 Recovery Procedures
- Point-in-time recovery
- System state restoration
- Data verification
- Integrity checks

## 7. System Monitoring

### 7.1 Security Monitoring
- Access attempts logging
- Unauthorized access detection
- System health monitoring
- Connection status tracking
- Error logging and alerts

### 7.2 Performance Monitoring
- Response time tracking
- System resource usage
- Network connectivity status
- Database performance metrics

## 8. Risk Assessment

### 8.1 Identified Risks
1. Network connectivity failures
2. Physical tampering attempts
3. Unauthorized access attempts
4. Data breach possibilities
5. System malfunction

### 8.2 Mitigation Strategies
1. Offline operation capability
2. Tamper detection
3. Access monitoring
4. Encryption and security protocols
5. Regular maintenance and updates

## 9. Implementation Status

### 9.1 Completed Features
✅ RFID card reading and verification

✅ Secure MQTT communication

✅ Basic access control

✅ Backup system

✅ Update mechanism

✅ Security monitoring

✅ LED and buzzer feedback

### 9.2 Pending for Production
🔄 Door Lock Integration
* Electronic door strike/magnetic lock integration
* Fail-secure/fail-safe mechanism selection
* Lock timing configuration
* Door position sensor
* Emergency override system
* Power backup for lock mechanism
* Lock state monitoring and logging

🔄 Camera Integration
* ESP32-CAM module integration
* Photo capture on access attempts
* Secure image storage
* Image transfer over MQTT
* Motion-triggered captures
* Low-light performance optimization
* Event-based photo logging

## 10. Conclusion
This PoC demonstrates a viable secure IoT solution that meets the basic requirements of the Cyber Resilience Act. The implementation provides a solid foundation for secure RFID access control with comprehensive monitoring, backup, and update capabilities.

## Appendix A: MQTT Configuration
```plaintext
listener 8883
allow_anonymous false

cafile ../certs/ca.crt
certfile ../certs/server.crt
keyfile ../certs/server.key

require_certificate true
use_identity_as_username true
tls_version tlsv1.2

log_type debug
connection_messages true
```

## Appendix B: System Requirements
- Python 3.8 or higher
- MongoDB 4.4 or higher
- MQTT Broker with TLS support
- ESP32 development board
- MFRC522 RFID reader module
- Basic electronic components (LEDs, buzzer)

***

# RFID System Installation and Setup Guide

## 1. Hardware Setup
### Components
- Freenove ESP32-S3
- RFID-RC522 module
- LEDs (Green and Red)
- Buzzer
- Jumper wires & Breadboard

### Connections
```
ESP32-S3 -> RFID-RC522
- 3.3V -> 3.3V
- GND -> GND
- GPIO 10 -> SDA
- GPIO 11 -> SCK
- GPIO 12 -> MOSI
- GPIO 13 -> MISO
- GPIO 14 -> RST

ESP32-S3 -> Other
- GPIO 4 -> Green LED
- GPIO 8 -> Red LED
- GPIO 18 -> Buzzer
```

## 2. Arduino Setup
1. Install Arduino IDE
2. Add ESP32 board support URL in Preferences:
   ```
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
3. Install board: Tools -> Board Manager -> Search "ESP32"
4. Select: Tools -> Board -> ESP32S3 Dev Module
5. Install Libraries:
   - MFRC522
   - PubSubClient
   - ArduinoJson
6. Configure Network Settings in esp32-s3.ino:
   ```cpp
   // WiFi credentials
   const char* ssid = "Your_WiFi_Name";         // Replace with your WiFi network name
   const char* password = "Your_WiFi_Password";  // Replace with your WiFi password

   // MQTT and API settings
   const char* mqttServer = "YOUR_IP";          // Replace with your MQTT broker IP (local network)
   const int mqttPort = 8883;                   // Default MQTT TLS port - do not change
   const char* mqtt_topic = "rfid/readings";     // Default MQTT topic - do not change
   const char* API_URL = "http://YOUR_IP:8000"; // Replace with same IP as mqttServer
   ```
7. Upload esp32-s3.ino code from espUploadCode folder

## 3. Backend Setup
1. Install Python 3.8+ and MongoDB
2. Open terminal in project folder
3. Create and activate virtual environment:
   ```bash
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # Linux/Mac:
   source venv/bin/activate
   ```
4. Install requirements:
   ```bash
   pip install -r requirements.txt
   ```
5. Start MongoDB service
6. Start the system:
   ```bash
   python -m uvicorn app:app --host 0.0.0.0 --port 8000
   ```

## 4. Testing
1. Open Arduino Serial Monitor (115200 baud)
2. Available commands:
   ```
   help   - Show commands
   add    - Add card
   remove - Remove card
   list   - List cards
   ```
3. Test card reading
4. Check system status:
   ```
   http://localhost:8000/system/health
   ```

## Troubleshooting
- **Upload fails**: Hold BOOT button while uploading
- **Can't detect board**: Check USB cable and COM port
- **RFID not working**: Verify connections
- **Backend errors**: Check MongoDB is running
