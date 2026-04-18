import sys

from tanuki_core.app_runtime import run_application


if __name__ == "__main__":
    try:
        sys.exit(run_application())
    except FileNotFoundError:
        sys.exit()
