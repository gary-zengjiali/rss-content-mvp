from pathlib import Path
from typing import Dict, List
import yaml

from .models import Source


BASE_DIR = Path(__file__).resolve().parents[2]
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
DB_PATH = DATA_DIR / "rss_mvp.db"


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "daily").mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "topics").mkdir(parents=True, exist_ok=True)


def load_sources() -> List[Source]:
    path = CONFIG_DIR / "sources.yaml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    items = raw.get("sources", [])
    sources = [Source(**item) for item in items if item.get("enabled", True)]
    return sources


def load_topic_config() -> Dict:
    path = CONFIG_DIR / "topics.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_yaml_config(name: str) -> Dict:
    path = CONFIG_DIR / name
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
