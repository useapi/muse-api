"""Live routing check: call every read-only tool against api.useapi.net with a
fake token. Each call must answer 401 (the route exists and checks the token),
never 404 (a wrong path) or 400 (a malformed id or parameter).

It never sends a real token and never calls an endpoint that generates,
uploads, chats or uses the Muse allowance.

Run from the plugin folder:  python dev/routing_check.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "dev"))

from endpoints import ENDPOINTS  # noqa: E402
from useapi_muse.client import Client, UseapiError  # noqa: E402
from useapi_muse.handlers import HANDLERS, Ctx  # noqa: E402

FAKE_TOKEN = "user:12345-glamahealthcheck"
EMAIL = "example@gmail.com"
HEX = EMAIL.encode().hex()
# A job id starts with its creation time (MMDDhhmmss + ms); an id older than 7 days answers 410 before the token check.
JOB = (
    time.strftime("j%m%d%H%M%S000000000v", time.gmtime())
    + "-u12345-email:example@gmail.com-task:20842037-a004-4dba-b640-225a8197385b-bot:muse"
)
ASSET = f"user:12345-email:{HEX}-video:media-generation-create-one-video-0-def1ac18-8024-4a8b-9bce-a2700d683f45.mp4"
CHAT = "c-u12345-email:example@gmail.com-chat:272b73f4-6fcb-42c2-9ec7-75cc0c020940-bot:muse"

READ_ONLY = {
    "list_accounts": {},
    "get_account": {"email": EMAIL},
    "list_jobs": {},
    "get_job": {"jobid": JOB, "wait": False},
    "list_assets": {"email": EMAIL},
    "get_asset": {"asset_id": ASSET},
    "get_chat": {"chat_id": CHAT, "return_file": False},
    "list_chats": {"email": EMAIL},
}


def main() -> int:
    ctx = Ctx(client=Client(FAKE_TOKEN))
    failures = 0
    for name, params in READ_ONLY.items():
        try:
            list(HANDLERS[name](ctx, params))
            status = 200
        except UseapiError as e:
            status = e.status
        ok = status == 401
        failures += not ok
        print(f"{'ok  ' if ok else 'FAIL'} {status} {name:15} {ENDPOINTS[name][0]}")
    print(f"{len(READ_ONLY) - failures}/{len(READ_ONLY)} routes answered 401")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
