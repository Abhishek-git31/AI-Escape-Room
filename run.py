"""Small launcher so I don't have to remember file names.

    python run.py v2   # recommended
    python run.py v1
"""

import sys


def main():
    version = sys.argv[1].lower() if len(sys.argv) > 1 else "v2"
    if version == "v1":
        from app_v1 import build
    elif version == "v2":
        from app_v2 import build
    else:
        print("Usage: python run.py v1 | v2")
        sys.exit(1)
    build().launch()


if __name__ == "__main__":
    main()
