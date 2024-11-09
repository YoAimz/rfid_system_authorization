# MQTT Configuration
MQTT_BROKER = "192.168.0.6"
MQTT_PORT = 8883
MQTT_TOPIC = "rfid/readings"
MQTT_CLIENT_ID = "python-rfid-client"
MQTT_KEEPALIVE = 60

# Certificate paths
CERT_PATH = "certs/"
CA_CERT = CERT_PATH + "ca.crt"
CLIENT_CERT = CERT_PATH + "client.crt"
CLIENT_KEY = CERT_PATH + "client.key"

# MongoDB Configuration
MONGO_URI = "mongodb://127.0.0.1:27017/"
MONGO_DB = "rfid_system"

MONGO_COLLECTIONS = {
    'cards': 'authorized_cards',
    'logs': 'access_logs',
    'backup': 'system_backup',
    'security': 'security_events'
}

# API Configuration
API_HOST = "0.0.0.0"
API_PORT = 8000