from datetime import datetime
import logging
import asyncio
import threading
from pymongo import MongoClient
from config import *

logger = logging.getLogger(__name__)

class CardManager:
    def __init__(self, backup_manager=None):
        """
        Initialize the Card Manager
        
        Args:
            backup_manager: Optional backup manager instance
        """
        logger.info(f"Initializing CardManager with backup_manager: {backup_manager}")
        self.backup_manager = backup_manager
        self.client = MongoClient(MONGO_URI)
        self.db = self.client[MONGO_DB]
        self.cards = self.db[MONGO_COLLECTIONS['cards']]
        self.logs = self.db[MONGO_COLLECTIONS['logs']]
        self._thread_local = threading.local()
    
    def get_or_create_eventloop(self):
        """Get or create an event loop for the current thread"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop

    def run_coroutine(self, coroutine):
        """
        Run a coroutine in the current thread's event loop
        
        Args:
            coroutine: The coroutine to run
        """
        loop = self.get_or_create_eventloop()
        if loop.is_running():
            # If loop is running, schedule the coroutine
            future = asyncio.run_coroutine_threadsafe(coroutine, loop)
            try:
                future.result(timeout=5)  # Wait max 5 seconds
            except Exception as e:
                logger.error(f"Error running coroutine: {e}")
        else:
            # If loop is not running, run the coroutine directly
            loop.run_until_complete(coroutine)
    
    def save_access_log(self, payload):
        """
        Save access log to MongoDB
        
        Args:
            payload: The access log data to save
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.logs.insert_one(payload)
            logger.info(f"Saved access log: {payload}")
            return True
        except Exception as e:
            logger.error(f"Error saving access log: {e}")
            return False

    def check_if_card_exists(self, card_id):
        """
        Check if a card exists in the database
        
        Args:
            card_id: The card ID to check
            
        Returns:
            bool: True if card exists, False otherwise
        """
        try:
            return bool(self.cards.find_one({"card_id": card_id}))
        except Exception as e:
            logger.error(f"Error checking card existence: {e}")
            return False
    
    async def create_backup_for_card(self, operation, card_id):
        """
        Create backup for card operation
        
        Args:
            operation: The operation being performed (add/remove)
            card_id: The card ID being operated on
        """
        if self.backup_manager:
            try:
                await self.backup_manager.handle_card_change(operation, card_id)
                logger.info(f"Backup created for {operation} operation on card: {card_id}")
            except Exception as e:
                logger.error(f"Failed to create backup for {operation} operation on card {card_id}: {e}")
    
    def add_card(self, card_id, description=""):
        """
        Add a new card if it doesn't already exist
        
        Args:
            card_id: The card ID to add
            description: Optional description for the card
            
        Returns:
            bool: True if card was added successfully, False otherwise
        """
        try:
            logger.info(f"Attempting to add card: {card_id}")
            
            # Check if card already exists
            existing_card = self.cards.find_one({"card_id": card_id})
            if existing_card:
                logger.warning(f"Card {card_id} already exists in the database")
                return False
                
            card_data = {
                "card_id": card_id,
                "description": description,
                "added_at": datetime.now(),
                "status": "active",
                "last_used": None,
                "access_count": 0
            }
            
            # Add to database
            self.cards.insert_one(card_data)
            logger.info(f"Successfully added new card: {card_id}")
            
            # Create backup after adding card
            if self.backup_manager:
                self.run_coroutine(self.create_backup_for_card("add", card_id))
                
            return True
            
        except Exception as e:
            logger.error(f"Error adding card {card_id}: {e}", exc_info=True)
            return False
    
    def remove_card(self, card_id):
        """
        Remove a card from the database
        
        Args:
            card_id: The card ID to remove
            
        Returns:
            bool: True if card was removed successfully, False otherwise
        """
        try:
            logger.info(f"Attempting to remove card: {card_id}")
            result = self.cards.delete_one({"card_id": card_id})
            
            if result.deleted_count > 0:
                logger.info(f"Successfully removed card: {card_id}")
                
                # Create backup after removing card
                if self.backup_manager:
                    self.run_coroutine(self.create_backup_for_card("remove", card_id))
                
                return True
            else:
                logger.warning(f"Card {card_id} not found for removal")
                return False
                
        except Exception as e:
            logger.error(f"Error removing card {card_id}: {e}", exc_info=True)
            return False
    
    def sync_cards_to_device(self, device_id):
        """
        Get all active cards for a device
        
        Args:
            device_id: The device ID requesting synchronization
            
        Returns:
            list: List of card IDs
        """
        try:
            cards = list(self.cards.find({"status": "active"}))
            return [card["card_id"] for card in cards]
        except Exception as e:
            logger.error(f"Error syncing cards for device {device_id}: {e}")
            return []
    
    def get_security_logs(self, since):
        """
        Get security logs since a specific date
        
        Args:
            since: Datetime to get logs from
            
        Returns:
            list: List of security log entries
        """
        try:
            return list(self.logs.find(
                {"server_timestamp": {"$gte": since}},
                {'_id': 0}
            ))
        except Exception as e:
            logger.error(f"Error getting security logs: {e}")
            return []

    def update_card_usage(self, card_id):
        """
        Update the usage statistics for a card
        
        Args:
            card_id: The card ID to update
            
        Returns:
            bool: True if update was successful, False otherwise
        """
        try:
            update_result = self.cards.update_one(
                {"card_id": card_id},
                {
                    "$set": {"last_used": datetime.now()},
                    "$inc": {"access_count": 1}
                }
            )
            return update_result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating card usage: {e}")
            return False

    def get_all_cards(self):
        """
        Get all cards in the database
        
        Returns:
            list: List of all cards
        """
        try:
            return list(self.cards.find({}, {'_id': 0}))
        except Exception as e:
            logger.error(f"Error getting all cards: {e}")
            return []

    def get_card_details(self, card_id):
        """
        Get detailed information about a specific card
        
        Args:
            card_id: The card ID to get details for
            
        Returns:
            dict: Card details or None if not found
        """
        try:
            card = self.cards.find_one({"card_id": card_id}, {'_id': 0})
            if card:
                # Get recent access logs for this card
                recent_logs = list(self.logs.find(
                    {"uid": card_id},
                    {'_id': 0}
                ).sort("server_timestamp", -1).limit(10))
                card["recent_access"] = recent_logs
                return card
            return None
        except Exception as e:
            logger.error(f"Error getting card details: {e}")
            return None

    def get_active_cards(self):
        """
        Get all active cards
        
        Returns:
            list: List of active cards
        """
        try:
            return list(self.cards.find({"status": "active"}, {'_id': 0}))
        except Exception as e:
            logger.error(f"Error getting active cards: {e}")
            return []