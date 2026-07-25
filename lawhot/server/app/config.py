from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
REPO_LAWHOT = BASE_DIR.parent  # .../lawhot
SOURCES_YAML = Path(
    os.environ.get("LAWHOT_SOURCES_YAML", REPO_LAWHOT / "references" / "sources.v1.yaml")
)
DATA_DIR = Path(os.environ.get("LAWHOT_DATA_DIR", BASE_DIR / "data"))
DB_PATH = Path(os.environ.get("LAWHOT_DB_PATH", DATA_DIR / "lawhot.sqlite3"))

PUBLIC_BASE_URL = os.environ.get("LAWHOT_PUBLIC_BASE_URL", "https://hot.fachuiai.com").rstrip(
    "/"
)
FETCH_INTERVAL_SECONDS = int(os.environ.get("LAWHOT_FETCH_INTERVAL_SECONDS", "1800"))
USER_AGENT = os.environ.get(
    "LAWHOT_USER_AGENT",
    "lawhot-fetcher/0.1 (+https://hot.fachuiai.com/; news aggregation)",
)

# Optional: when set, future versions may call LLM for better summaries.
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "").strip()
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini").strip()
