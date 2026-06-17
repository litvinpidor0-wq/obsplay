import os, sys
from datetime import datetime

def debug(*args, **kwargs):
    if os.environ.get("OBSYDE_DEBUG") or os.environ.get("DEBUG"):
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"[{ts}]", *args, **kwargs, file=sys.stderr)
