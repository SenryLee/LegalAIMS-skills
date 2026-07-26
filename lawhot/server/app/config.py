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

# Overseas fetch proxy (scheme A). Domestic sources bypass via source_needs_proxy().
# Prefer LAWHOT_HTTPS_PROXY; fall back to LAWHOT_HTTP_PROXY / standard HTTPS_PROXY.
LAWHOT_HTTP_PROXY = (
    os.environ.get("LAWHOT_HTTPS_PROXY")
    or os.environ.get("LAWHOT_HTTP_PROXY")
    or os.environ.get("HTTPS_PROXY")
    or os.environ.get("HTTP_PROXY")
    or ""
).strip()
LAWHOT_NO_PROXY = os.environ.get(
    "LAWHOT_NO_PROXY",
    "localhost,127.0.0.1,.cn,cac.gov.cn,court.gov.cn,gov.cn,miit.gov.cn,npc.gov.cn,moj.gov.cn,legaldaily.com.cn",
).strip()

# Optional: when set, future versions may call LLM for better summaries.
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "").strip()
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini").strip()


def source_needs_proxy(source: dict) -> bool:
    """Domestic CN sources go direct; everything else uses overseas proxy when configured."""
    if source.get("egress") == "domestic":
        return False
    if source.get("egress") == "overseas":
        return True
    if source.get("channel") == "wechat":
        return False
    regions = source.get("region") or []
    if regions == ["cn"] or (len(regions) == 1 and regions[0] == "cn"):
        return False
    if source.get("lang") == "zh" and "cn" in regions and "us" not in regions and "eu" not in regions:
        return False
    return True
