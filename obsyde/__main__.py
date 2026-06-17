import os, sys

if not os.environ.get("OBSYDE_DEBUG"):
    os.environ.setdefault(
        "QT_LOGGING_RULES",
        "*.debug=false;*.info=false;*.warning=false;qt.multimedia.*=false;qt.*.warning=false",
    )

from obsyde.app import main

if __name__ == "__main__":
    main()
