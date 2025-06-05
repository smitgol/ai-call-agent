import time
from typing import List, Tuple
from datetime import datetime
import logging
from utils import getDb

logger = logging.getLogger(__name__)

class TranscriptionLogger:
    def __init__(self, call_sid: str):
        self.call_sid = call_sid
        self.entries: List[Tuple[float, str, str]] = []
        self._saved = False
        self.db = getDb()

    def add_entry(self, source: str, text: str):
        """Store transcript in memory with timestamp"""
        timestamp = time.time()
        self.entries.append((timestamp, source, text))

    async def save_to_mongodb(self):
        """Save all entries to MongoDB"""
        if self._saved or not self.entries:
            return

        try:
            # Format entries for MongoDB
            formatted_entries = []
            for ts, source, text in self.entries:
                timestamp = datetime.fromtimestamp(ts)
                formatted_entries.append({
                    "timestamp": timestamp,
                    "source": source,
                    "text": text
                })
            
            # Save to MongoDB
            document = {
                "call_sid": self.call_sid,
                "created_at": datetime.now(),
                "entries": formatted_entries
            }
            
            await self.db.call_transcriptions.insert_one(document)
            print(f"Transcription saved successfully to MongoDB for call_sid: {self.call_sid}")
            
            self._saved = True
        except Exception as e:
            print(f"Error saving transcription to MongoDB: {e}")
            logger.error(f"Error saving transcription to MongoDB: {e}")