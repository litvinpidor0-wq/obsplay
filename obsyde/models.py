import json, time
from dataclasses import dataclass, field, asdict
from typing import Optional, List

from .constants import CONFIG_DIR, PL_DIR

class Settings:
    DEFAULTS = {
        "default_volume": 25,
        "mix_size": 25,
        "minimize_to_tray": True,
        "autoplay_next": True,
        "resolution": "1080x680",
        "bg_effect": "none",
        "window_opacity": 100,
    }
    FILE = CONFIG_DIR / "settings.json"

    def __init__(self):
        self.data = dict(self.DEFAULTS)
        if self.FILE.exists():
            try:
                self.data.update(json.loads(self.FILE.read_text("utf-8")))
            except Exception:
                pass

    def get(self, k):
        return self.data.get(k, self.DEFAULTS.get(k))

    def set(self, k, v):
        self.data[k] = v
        try:
            self.FILE.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), "utf-8")
        except Exception:
            pass


@dataclass
class Track:
    title: str = ""
    artist: str = ""
    permalink_url: str = ""
    duration_ms: int = 0
    artwork_url: str = ""
    id: int = 0

    @classmethod
    def from_api(cls, d):
        user = d.get("user") or {}
        return cls(
            title=str(d.get("title") or "").strip(),
            artist=str(user.get("username") or "").strip(),
            permalink_url=str(d.get("permalink_url") or "").strip(),
            duration_ms=int(d.get("duration") or 0),
            artwork_url=str(d.get("artwork_url") or "").strip(),
            id=int(d.get("id") or 0),
        )


class Library:
    def __init__(self):
        self.liked: list[Track] = []
        self.playlists: dict[str, list[Track]] = {}
        self._load()

    def _load(self):
        f = CONFIG_DIR / "liked.json"
        if f.exists():
            try:
                self.liked = [Track(**d) for d in json.loads(f.read_text("utf-8"))]
            except Exception:
                pass
        for p in PL_DIR.glob("*.json"):
            try:
                self.playlists[p.stem] = [Track(**d) for d in json.loads(p.read_text("utf-8"))]
            except Exception:
                pass

    def save_liked(self):
        try:
            (CONFIG_DIR/"liked.json").write_text(json.dumps([asdict(t) for t in self.liked], ensure_ascii=False), "utf-8")
        except Exception:
            pass

    def save_playlist(self, name):
        try:
            (PL_DIR/f"{name}.json").write_text(json.dumps([asdict(t) for t in self.playlists.get(name, [])], ensure_ascii=False), "utf-8")
        except Exception:
            pass

    def is_liked(self, tr):
        return any(t.permalink_url == tr.permalink_url for t in self.liked)

    def toggle_like(self, tr):
        if self.is_liked(tr):
            self.liked = [t for t in self.liked if t.permalink_url != tr.permalink_url]
        else:
            self.liked.insert(0, tr)
        self.save_liked()

    def add_playlist(self, name):
        if name and name not in self.playlists:
            self.playlists[name] = []; self.save_playlist(name)

    def rename_playlist(self, old, new):
        if old in self.playlists and new and new not in self.playlists:
            self.playlists[new] = self.playlists.pop(old)
            self.save_playlist(new)
            try: (PL_DIR/f"{old}.json").unlink()
            except Exception: pass

    def delete_playlist(self, name):
        if name in self.playlists:
            del self.playlists[name]
            try: (PL_DIR/f"{name}.json").unlink()
            except Exception: pass

    def add_to_playlist(self, name, tr):
        if name in self.playlists and not any(t.permalink_url == tr.permalink_url for t in self.playlists[name]):
            self.playlists[name].insert(0, tr); self.save_playlist(name)

    def remove_from_playlist(self, name, tr):
        if name in self.playlists:
            self.playlists[name] = [t for t in self.playlists[name] if t.permalink_url != tr.permalink_url]
            self.save_playlist(name)


class History:
    FILE = CONFIG_DIR / "history.json"
    MAX = 200

    def __init__(self):
        self.tracks: list[Track] = []
        if self.FILE.exists():
            try:
                self.tracks = [Track(**d) for d in json.loads(self.FILE.read_text("utf-8"))][:self.MAX]
            except Exception:
                pass

    def push(self, tr):
        self.tracks = [t for t in self.tracks if t.permalink_url != tr.permalink_url]
        self.tracks.insert(0, tr); self.tracks = self.tracks[:self.MAX]
        try:
            self.FILE.write_text(json.dumps([asdict(t) for t in self.tracks], ensure_ascii=False), "utf-8")
        except Exception:
            pass

    def clear(self):
        self.tracks = []
        try: self.FILE.unlink(missing_ok=True)
        except Exception: pass



LIB = Library()
HIST = History()
SETTINGS = Settings()
