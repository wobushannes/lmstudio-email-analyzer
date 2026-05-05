import logging
import os
from datetime import datetime
from pathlib import Path

def setup_logging():
    """Professionelles Logging einrichten"""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / f"email_analyzer_{datetime.now().strftime('%Y%m%d')}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def ensure_directories():
    """Benötigte Verzeichnisse erstellen"""
    Path("exports").mkdir(exist_ok=True)
    Path("logs").mkdir(exist_ok=True)

def safe_str(text, max_length=1000):
    """Text sicher für LLM kürzen"""
    if not text:
        return ""
    text = str(text).strip()
    if len(text) > max_length:
        text = text[:max_length] + "..."
    return text