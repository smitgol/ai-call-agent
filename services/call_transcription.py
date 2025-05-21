from pathlib import Path
import aiofiles
import time
from typing import List, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class TranscriptionLogger:
    def __init__(self, call_sid: str):
        self.call_sid = call_sid
        self.base_dir = Path("call_transcriptions")
        self.entries: List[Tuple[float, str, str]] = []
        self._saved = False

    def add_entry(self, source: str, text: str):
        """Store transcript in memory with timestamp"""
        timestamp = time.time()
        self.entries.append((timestamp, source, text))

    async def save_to_file(self):
        """Save all entries to file at once"""
        if self._saved or not self.entries:
            return

        self.base_dir.mkdir(parents=True, exist_ok=True)
        transcript_file = self.base_dir / f"{self.call_sid}.txt"

        try:
            # Format all entries first
            formatted = []
            for ts, source, text in self.entries:
                timestamp = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S.%f")
                formatted.append(f"[{timestamp}] [{source}]: {text}\n")
            # Write all at once
            
            async with aiofiles.open(str(transcript_file), "w", encoding="utf-8") as f:
                await f.writelines(" ".join(formatted) + "\n")
            print("Transcription saved successfully.", transcript_file)
            
            self._saved = True
        except Exception as e:
            print(f"Error saving transcription: {e}")
            logger.error(f"Error saving transcription: {e}")