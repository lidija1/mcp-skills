import sys
import time
from pathlib import Path
import os

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from mcp_tools.lob_recorder.browser_session import start_session


def main() -> int:
    if len(sys.argv) == 3:
        lob_name, program = sys.argv[1], sys.argv[2]
    else:
        lob_name = os.getenv("LOB_RECORDER_LOB_NAME", "")
        program = os.getenv("LOB_RECORDER_PROGRAM", "")
        if not lob_name or not program:
            print("Usage: launch_recording.py <lob_name> <program>", file=sys.stderr)
            return 2

    print(start_session(lob_name, program), flush=True)

    try:
        time.sleep(86400)
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
