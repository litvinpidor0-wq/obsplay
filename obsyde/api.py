"""SoundCloud API client + background QThread workers.

client_id is scraped from public sndcdn JS bundles and cached on disk.
Auto-refreshes when the cached id expires (401/403 from the API).
"""
import re, random, time, traceback
from typing import Optional, List

import requests
from PyQt6.QtCore import QThread, pyqtSignal

from .constants import _API, _HOST, CONFIG_DIR
from .models import Track

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

_CID_RE = re.compile(r'client_id\s*[:=]\s*["\']([A-Za-z0-9_-]{20,})["\']')
_SCRIPT_RE = re.compile(r'<script[^>]+src="(https?://[^"]+\.js)"', re.IGNORECASE)


class MusicAPI:
    def __init__(self):
        self.client_id: Optional[str] = None
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": _UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })
        self._load_cached_cid()

    # ---- on-disk cache ----
    def _cid_path(self):
        return CONFIG_DIR / "client_id"

    def _load_cached_cid(self):
        try:
            p = self._cid_path()
            if p.exists():
                v = p.read_text(encoding="utf-8").strip()
                if 20 <= len(v) <= 64 and re.match(r"^[A-Za-z0-9_-]+$", v):
                    self.client_id = v
        except Exception:
            pass

    def _save_cached_cid(self, cid: str):
        try:
            self._cid_path().write_text(cid, encoding="utf-8")
        except Exception:
            pass

    # ---- scraping ----
    def _fetch_cid(self) -> Optional[str]:
        try:
            r = self.session.get(_HOST, timeout=15)
            if r.status_code >= 400:
                return None
            urls = _SCRIPT_RE.findall(r.text)
            # Prefer JS bundles served from SoundCloud's CDN (they reliably contain client_id).
            cdn = [u for u in urls if "sndcdn.com" in u or "soundcloud.com" in u]
            others = [u for u in urls if u not in cdn]
            # Main bundle is usually the last script tag; iterate in reverse.
            for u in list(reversed(cdn)) + list(reversed(others)):
                try:
                    js = self.session.get(u, timeout=15).text
                except Exception:
                    continue
                m = _CID_RE.search(js)
                if m:
                    return m.group(1)
        except Exception:
            return None
        return None

    def cid(self, force_refresh: bool = False) -> Optional[str]:
        if force_refresh or not self.client_id:
            new = self._fetch_cid()
            if new:
                self.client_id = new
                self._save_cached_cid(new)
            elif force_refresh:
                # Don't blow away a cached id we have just because one refresh attempt failed.
                pass
        return self.client_id

    # ---- helpers ----
    def _get(self, path: str, params: dict, timeout: int = 15) -> Optional[requests.Response]:
        """GET with one retry on 401/403 using a freshly scraped client_id."""
        for attempt in range(2):
            c = self.cid(force_refresh=(attempt == 1))
            if not c:
                return None
            p = dict(params); p["client_id"] = c
            try:
                r = self.session.get(f"{_API}{path}", params=p, timeout=timeout)
            except Exception:
                if attempt == 0:
                    continue
                return None
            if r.status_code in (401, 403) and attempt == 0:
                # Cached client_id likely rotated server-side; refresh and retry once.
                continue
            return r
        return None

    # ---- public API ----
    def search_tracks(self, q: str, limit: int = 30) -> List[Track]:
        r = self._get("/search/tracks", {"q": q, "limit": limit})
        if r is None or r.status_code >= 400:
            return []
        try:
            data = r.json()
        except Exception:
            return []
        return [
            Track.from_api(it)
            for it in data.get("collection", [])
            if it.get("kind") == "track"
        ]

    def resolve(self, url: str) -> Optional[Track]:
        r = self._get("/resolve", {"url": url})
        if r is None or r.status_code >= 400:
            return None
        try:
            j = r.json()
        except Exception:
            return None
        if j.get("kind") == "track":
            return Track.from_api(j)
        return None

    def stream_url(self, tid) -> Optional[str]:
        r = self._get(f"/tracks/{tid}", {})
        if r is None or r.status_code >= 400:
            return None
        try:
            data = r.json()
        except Exception:
            return None
        c = self.client_id
        for t in (data.get("media") or {}).get("transcodings", []):
            fmt = (t.get("format") or {})
            if fmt.get("protocol") == "progressive":
                u = t.get("url")
                if not u:
                    continue
                try:
                    rr = self.session.get(u, params={"client_id": c}, timeout=15)
                except Exception:
                    continue
                if rr.status_code < 400:
                    try:
                        return rr.json().get("url")
                    except Exception:
                        continue
        return None

    def related(self, tid, limit: int = 20) -> list:
        r = self._get(f"/tracks/{tid}/related", {"limit": limit})
        if r is None or r.status_code >= 400:
            return []
        try:
            return r.json().get("collection", [])
        except Exception:
            return []

    def ensure_id(self, tr):
        if tr.id:
            return tr.id
        if not tr.permalink_url:
            return 0
        r = self.resolve(tr.permalink_url)
        if r:
            tr.id = r.id
        return tr.id


# ---- module singleton ----
API = MusicAPI()


class SearchWorker(QThread):
    done = pyqtSignal(list)
    failed = pyqtSignal(str)

    def __init__(self, q):
        super().__init__()
        self.q = q

    def run(self):
        try:
            q = self.q.strip()
            if not q:
                self.done.emit([])
                return
            if q.startswith("http"):
                t = API.resolve(q)
                self.done.emit([t] if t else [])
                return
            # Ensure we have a client_id; if not, surface a connectivity error
            # so the UI doesn't silently show “nothing found”.
            if not API.cid():
                self.failed.emit(
                    "Не удалось подключиться к SoundCloud. "
                    "Проверь интернет / VPN и попробуй ещё раз."
                )
                return
            self.done.emit(API.search_tracks(q))
        except Exception as e:
            traceback.print_exc()
            self.failed.emit(str(e))


class StreamWorker(QThread):
    got = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, tr):
        super().__init__()
        self.tr = tr

    def run(self):
        try:
            tid = API.ensure_id(self.tr)
            if not tid:
                self.failed.emit("no id")
                return
            u = API.stream_url(tid)
            if u:
                self.got.emit(u)
            else:
                self.failed.emit("no stream")
        except Exception as e:
            traceback.print_exc()
            self.failed.emit(str(e))


class MixWorker(QThread):
    done = pyqtSignal(list)
    failed = pyqtSignal(str)

    def __init__(self, seeds, target=25, exclude=None):
        super().__init__()
        self.seeds = list(seeds)
        self.target = target
        self.exclude = set(exclude or set())

    def run(self):
        try:
            if not self.seeds:
                self.done.emit([])
                return
            random.shuffle(self.seeds)
            picks = self.seeds[:max(5, min(8, len(self.seeds)))]
            seen = set(self.exclude)
            for s in self.seeds:
                seen.add(s.permalink_url)
            res = []
            for s in picks:
                tid = API.ensure_id(s)
                if not tid:
                    continue
                try:
                    items = API.related(tid, limit=20)
                except Exception:
                    continue
                for it in items:
                    if it.get("kind") != "track":
                        continue
                    tr = Track.from_api(it)
                    if not tr.permalink_url or tr.permalink_url in seen:
                        continue
                    seen.add(tr.permalink_url)
                    res.append(tr)
                if len(res) >= self.target * 2:
                    break
            random.shuffle(res)
            self.done.emit(res[:self.target])
        except Exception as e:
            traceback.print_exc()
            self.failed.emit(str(e))
