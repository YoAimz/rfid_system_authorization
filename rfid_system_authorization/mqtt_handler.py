import paho.mqtt.client as mqtt
import json
import datetime
import logging
import ssl
from config import *

logger = logging.getLogger(__name__)

class MQTTHandler:
    def __init__(self, card_manager, security_monitor):
        """
        Initialize MQTT Handler
        
        Args:
            card_manager: Instance of CardManager for card operations
            security_monitor: Instance of SecurityMonitor for security checks
        """
        logger.info("Initializing MQTT Handler")
        self.card_manager = card_manager
        self.security_monitor = security_monitor
        self.client = mqtt.Client(
            client_id=MQTT_CLIENT_ID,
            protocol=mqtt.MQTTv5,
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2
        )
        self.setup_client()

    def setup_client(self):
        """Configure MQTT client with callbacks and TLS"""
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        
        # Configure TLS
        try:
            self.client.tls_set(
                ca_certs=CA_CERT,
                certfile=CLIENT_CERT,
                keyfile=CLIENT_KEY,
                cert_reqs=ssl.CERT_REQUIRED,
                tls_version=ssl.PROTOCOL_TLS,
            )
            logger.info("TLS configuration successful")
        except Exception as e:
            logger.error(f"Failed to configure TLS: {e}")
            raise

    def start(self):
        """Start the MQTT client and connect to broker"""
        try:
            self.client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE)
            self.client.loop_start()
            logger.info("MQTT client started successfully")
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            raise

    def stop(self):
        """Stop the MQTT client properly"""
        try:
            self.client.loop_stop()
            self.client.disconnect()
            logger.info("MQTT client stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping MQTT client: {e}")

    def on_connect(self, client, userdata, flags, rc, properties=None):
        """
        Callback for when the client connects to the broker
        
        Args:
            client: MQTT client instance
            userdata: Private user data
            flags: Response flags from broker
            rc: Connection result code
            properties: MQTT v5.0 properties (optional)
        """
        logger.info(f"Connected to MQTT Broker with result code {rc}")
        try:
            client.subscribe(MQTT_TOPIC)
            logger.info(f"Subscribed to topic: {MQTT_TOPIC}")
            
            # Subscribe to additional control topics
            client.subscribe(f"{MQTT_TOPIC}/control")
            logger.info(f"Subscribed to control topic: {MQTT_TOPIC}/control")
        except Exception as e:
            logger.error(f"Error in subscribe: {e}")

    def on_disconnect(self, client, userdata, rc, properties=None, reason_code=None, reasonstr=None):
        """
        Callback when client disconnects
        
        Args:
            client: MQTT client instance
            userdata: Private user data
            rc: Disconnect result code
            properties: MQTT v5.0 properties (optional)
            reason_code: Disconnect reason code (optional)
            reasonstr: Reason string (optional)
        """
        if rc != 0:
            logger.warning(f"Unexpected disconnection. RC: {rc}")
        else:
            logger.info("Disconnected from broker")

    def send_response(self, topic, response_data):
        """
        Send a response message back to the device
        
        Args:
            topic: Topic to publish response to
            response_data: Data to send in the response
        """
        try:
            response_json = json.dumps(response_data)
            self.client.publish(f"{topic}/response", response_json)
            logger.debug(f"Sent response: {response_data}")
        except Exception as e:
            logger.error(f"Error sending response: {e}")

    def handle_card_command(self, command, payload):
        """
        Handle card-related commands
        
        Args:
            command: Command to execute
            payload: Command payload data
        
        Returns:
            dict: Response data
        """
        try:
            card_id = payload.get("uid")
            if not card_id:
                return {
                    "type": "response",
                    "command": command,
                    "status": "error",
                    "reason": "No card ID provided"
                }

            if command == "add_card":
                success = self.card_manager.add_card(card_id)
                if success:
                    response = {
                        "type": "response",
                        "command": command,
                        "status": "success",
                        "card_id": card_id
                    }
                else:
                    response = {
                        "type": "response",
                        "command": command,
                        "status": "error",
                        "reason": "Card already exists or error occurred",
                        "card_id": card_id
                    }

            elif command == "remove_card":
                success = self.card_manager.remove_card(card_id)
                if success:
                    response = {
                        "type": "response",
                        "command": command,
                        "status": "success",
                        "card_id": card_id
                    }
                else:
                    response = {
                        "type": "response",
                        "command": command,
                        "status": "error",
                        "reason": "Card not found or error occurred",
                        "card_id": card_id
                    }

            return response

        except Exception as e:
            logger.error(f"Error handling card command: {e}")
            return {
                "type": "response",
                "command": command,
                "status": "error",
                "reason": "Internal server error"
            }

    def on_message(self, client, userdata, msg):
        """
        Callback for when a message is received from the broker
        
        Args:
            client: MQTT client instance
            userdata: Private user data
            msg: Received message
        """
        try:
            logger.info(f"Received MQTT message on topic: {msg.topic}")
            payload = json.loads(msg.payload.decode())
            logger.info(f"Decoded payload: {payload}")
            
            payload["server_timestamp"] = datetime.datetime.now()
            
            # Check if it's a command
            if "command" in payload:
                logger.info(f"Processing command: {payload['command']}")
                
                if payload["command"] in ["add_card", "remove_card"]:
                    response = self.handle_card_command(payload["command"], payload)
                    self.send_response(msg.topic, response)
                
                elif payload["command"] == "sync_request":
                    # Handle sync request
                    device_id = payload.get("device_id")
                    if device_id:
                        cards = self.card_manager.sync_cards_to_device(device_id)
                        self.send_response(msg.topic, {
                            "type": "response",
                            "command": "sync",
                            "status": "success",
                            "cards": cards
                        })
            
            else:
                # Regular card reading
                card_id = payload.get("uid")
                device_id = payload.get("device_id")
                
                if card_id and device_id:
                    # Check if card is authorized
                    is_authorized = self.card_manager.check_if_card_exists(card_id)
                    payload["authorized"] = is_authorized
                    
                    # Save access log
                    self.card_manager.save_access_log(payload)
                    logger.info(f"Processed and saved RFID reading: {payload}")
                    
                    # Update card usage if authorized
                    if is_authorized:
                        self.card_manager.update_card_usage(card_id)
                    
                    # Security check
                    self.security_monitor.check_for_intrusion_sync(card_id, device_id)
                    
                    # Send response to device
                    self.send_response(msg.topic, {
                        "type": "access_response",
                        "status": "success",
                        "authorized": is_authorized,
                        "card_id": card_id
                    })
                else:
                    logger.warning("Received message missing card_id or device_id")
                    
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON message: {e}")
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)

    def publish_message(self, topic, message):
        """
        Publish a message to a specific topic
        
        Args:
            topic: Topic to publish to
            message: Message to publish
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            result = self.client.publish(topic, json.dumps(message))
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"Successfully published message to {topic}")
                return True
            else:
                logger.error(f"Failed to publish message. Result code: {result.rc}")
                return False
        except Exception as e:
            logger.error(f"Error publishing message: {e}")
            return False
