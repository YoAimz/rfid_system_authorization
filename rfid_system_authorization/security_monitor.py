import logging
from datetime import datetime, timedelta
from config import *
from pymongo import MongoClient

logger = logging.getLogger(__name__)

class SecurityMonitor:
    def __init__(self, card_manager):
        self.card_manager = card_manager
        self.client = MongoClient(MONGO_URI)
        self.db = self.client[MONGO_DB]
        self.security_logs = self.db[MONGO_COLLECTIONS['security']]
    
    def check_for_intrusion_sync(self, card_id, device_id):
        """Synchronous version of intrusion detection"""
        try:
            # Check recent access attempts for this card (excluding admin operations)
            recent_attempts = list(self.card_manager.logs.find({
                'uid': card_id,
                'server_timestamp': {
                    '$gte': datetime.now() - timedelta(minutes=5)
                },
                # Only count normal access attempts, not admin operations
                'command': {'$exists': False}
            }))
            
            # Check for suspicious activity (more than 5 attempts in 5 minutes)
            if len(recent_attempts) > 5:
                self.log_security_event({
                    'type': 'suspicious_activity',
                    'card_id': card_id,
                    'device_id': device_id,
                    'attempts': len(recent_attempts),
                    'timestamp': datetime.now()
                })
                logger.warning(f"Suspicious activity detected for card {card_id}: {len(recent_attempts)} attempts in 5 minutes")
            
            # Check for unauthorized attempts
            if not self.card_manager.check_if_card_exists(card_id):
                self.log_security_event({
                    'type': 'unauthorized_attempt',
                    'card_id': card_id,
                    'device_id': device_id,
                    'timestamp': datetime.now()
                })
                logger.warning(f"Unauthorized access attempt with card {card_id}")
                
        except Exception as e:
            logger.error(f"Error in intrusion check: {e}")
    
    def log_security_event(self, event_data):
        """Log security events"""
        try:
            self.security_logs.insert_one(event_data)
            logger.info(f"Security event logged: {event_data}")
        except Exception as e:
            logger.error(f"Error logging security event: {e}")

    def get_recent_security_events(self, minutes=60):
        """Get recent security events"""
        try:
            return list(self.security_logs.find({
                'timestamp': {
                    '$gte': datetime.now() - timedelta(minutes=minutes)
                }
            }).sort('timestamp', -1))
        except Exception as e:
            logger.error(f"Error getting recent security events: {e}")
            return []