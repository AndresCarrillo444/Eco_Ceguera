import json
import threading
import urllib.request
import urllib.error
import time

FIREBASE_URL = "https://eco-ceguera-default-rtdb.firebaseio.com/"

TOP_N           = 10        # entries shown per level
_TIMEOUT        = 6         # seconds per HTTP call

# Runtime state (all modified only from background threads)
_cache          = {}        # {level_idx: [sorted entry dicts]}
_status         = "syncing" if FIREBASE_URL else "unconfigured"
_last_fetch_t   = {}        # {level_idx: timestamp}
_CACHE_TTL      = 30        # seconds before re-fetching


# helpers

def _configured():
    return bool(FIREBASE_URL and FIREBASE_URL.startswith("https://"))


def _node_url(level_idx):
    return FIREBASE_URL.rstrip("/") + f"/leaderboard/level_{level_idx}.json"


def _player_url(level_idx, key):
    return FIREBASE_URL.rstrip("/") + f"/leaderboard/level_{level_idx}/{key}.json"


def _safe_key(name: str) -> str:
    bad = '.#$[]/'
    k = "".join(c if c not in bad else '_' for c in name.strip() or "anon")
    return k[:32] or "anon"


# background workers

def _bg_fetch(level_idx: int):
    global _status
    _status = "syncing"
    try:
        req = urllib.request.urlopen(_node_url(level_idx), timeout=_TIMEOUT)
        raw  = req.read().decode("utf-8")
        data = json.loads(raw)
        if isinstance(data, dict):
            raw_entries = [e for e in data.values() if isinstance(e, dict) and "ticks" in e]
            
            # Deduplicate by player name (keep the lowest ticks)
            best_by_name = {}
            for e in raw_entries:
                n = str(e.get("name", "anon")).strip().lower()
                if n not in best_by_name or e["ticks"] < best_by_name[n]["ticks"]:
                    best_by_name[n] = e
                    
            entries = list(best_by_name.values())
            entries.sort(key=lambda e: e.get("ticks", 9_999_999))
            _cache[level_idx] = entries[:TOP_N]
        else:
            _cache[level_idx] = []
        _last_fetch_t[level_idx] = time.monotonic()
        _status = "online"
    except Exception:
        _status = "error"


def _bg_submit(level_idx: int, name: str, ticks: int, score: int):
    global _status
    if not _configured():
        return
    try:
        key      = _safe_key(name)
        node_url = _player_url(level_idx, key)

        # Read current entry for this player
        try:
            r        = urllib.request.urlopen(node_url, timeout=_TIMEOUT)
            existing = json.loads(r.read().decode("utf-8"))
        except Exception:
            existing = None

        if existing is None or ticks < existing.get("ticks", 9_999_999):
            payload = json.dumps({
                "name":  name[:16],
                "ticks": ticks,
                "score": score,
            }).encode("utf-8")
            put = urllib.request.Request(node_url, data=payload, method="PUT")
            put.add_header("Content-Type", "application/json")
            urllib.request.urlopen(put, timeout=_TIMEOUT)

        # Refresh cache for this level
        _bg_fetch(level_idx)

    except Exception:
        _status = "error"

#  public API (non-blocking) 

def ol_submit(level_idx: int, name: str, ticks: int, score: int):
    """Submit a score.  Runs in a daemon thread — never blocks the game loop."""
    if not _configured():
        return
    t = threading.Thread(
        target=_bg_submit, args=(level_idx, name, ticks, score), daemon=True
    )
    t.start()


def ol_fetch(level_idx: int, force: bool = False):
    """
    Trigger a background fetch for level_idx.
    Respects _CACHE_TTL unless force=True.
    """
    if not _configured():
        return
    age = time.monotonic() - _last_fetch_t.get(level_idx, 0)
    if force or age > _CACHE_TTL:
        t = threading.Thread(target=_bg_fetch, args=(level_idx,), daemon=True)
        t.start()


def ol_fetch_all(n_levels: int, force: bool = False):
    """Fetch scores for all levels in parallel background threads."""
    for i in range(n_levels):
        ol_fetch(i, force=force)


def ol_get(level_idx: int):
    """Return cached list of entry dicts for level_idx (may be [])."""
    return list(_cache.get(level_idx, []))


def ol_status() -> str:
    """
    Returns a short status string:
      'unconfigured' | 'syncing' | 'online' | 'error'
    """
    if not _configured():
        return "unconfigured"
    return _status


def ol_is_ready() -> bool:
    return _configured() and _status == "online"


def ol_is_configured() -> bool:
    """Returns True if FIREBASE_URL is set (regardless of connectivity)."""
    return _configured()
