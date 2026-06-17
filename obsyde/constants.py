import base64
from pathlib import Path

C_BG = "#0d0c18"
C_BG2 = "#15142a"
C_SURFACE = "rgba(255,255,255,0.04)"
C_SURFACE2 = "rgba(255,255,255,0.08)"
C_BORDER = "rgba(255,255,255,0.10)"
C_TEXT = "#e9e9f2"
C_TEXT_DIM = "#9a9ab0"
C_ACCENT = "#b48bff"
C_ACCENT2 = "#7aa2ff"
C_LIKE = "#ff5b8a"

CONFIG_DIR = Path.home() / ".obsyde"
CONFIG_DIR.mkdir(exist_ok=True)
PL_DIR = CONFIG_DIR / "playlists"
PL_DIR.mkdir(exist_ok=True)

_API = base64.b64decode("aHR0cHM6Ly9hcGktdjIuc291bmRjbG91ZC5jb20=").decode()
_HOST = base64.b64decode("aHR0cHM6Ly9zb3VuZGNsb3VkLmNvbQ==").decode()
