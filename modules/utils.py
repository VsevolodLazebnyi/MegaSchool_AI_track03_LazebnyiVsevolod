import json
import os
from typing import List, Dict

LOG_FILE = "interview_log.json"

def save_log(participant_name: str, turns: List[Dict], final_feedback: str = ""):
    """Сохраняет данные сессии в JSON."""
    data = {
        "participant_name": participant_name,
        "turns": turns,
        "final_feedback": final_feedback
    }
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_log():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}