"""Checks that an agent shows up online at the local relay; journal-warns and exits
nonzero otherwise, so a systemd timer (or OnFailure) can turn it into an alert.

    python3 online_watchdog.py --url http://127.0.0.1:8722 \
        --password-file ~/.local/state/remote-cli-agent/password.txt
"""
import argparse
import json
import os
import sys
import urllib.request


def main() -> int:
    ap = argparse.ArgumentParser(description="remote-cli online watchdog")
    ap.add_argument("--url", default="http://127.0.0.1:8722")
    ap.add_argument("--password-file",
                    default=os.path.expanduser("~/.local/state/remote-cli-agent/password.txt"))
    args = ap.parse_args()
    args.url = args.url.rstrip("/")   # a trailing slash would double it into //api/login

    try:
        with open(args.password_file, encoding="utf-8") as stream:
            password = stream.read().strip()
    except OSError:
        print(f"watchdog: cannot read {args.password_file}", file=sys.stderr)
        return 2
    if not password:
        print("watchdog: empty relay password", file=sys.stderr)
        return 2

    def post(path: str, payload: dict) -> tuple[int, str]:
        req = urllib.request.Request(args.url + path, method="POST",
                                     data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.status, resp.read().decode()
        except urllib.error.HTTPError as err:
            return err.code, err.read().decode()
        except (urllib.error.URLError, OSError) as err:
            print(f"watchdog: relay unreachable at {args.url}: {err}", file=sys.stderr)
            return 0, ""

    status, body = post("/api/login", {"password": password})
    if status != 200:
        print(f"watchdog: login failed (HTTP {status}) — password changed or relay broken",
              file=sys.stderr)
        return 1
    try:
        token = json.loads(body).get("token", "")
    except ValueError:
        print("watchdog: relay login answered non-JSON", file=sys.stderr)
        return 1

    req = urllib.request.Request(args.url + "/api/terminal",
                                 headers={"Authorization": "Bearer " + token})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            view = json.loads(resp.read().decode())
    except (urllib.error.URLError, OSError, ValueError) as err:
        print(f"watchdog: cannot read terminal view: {err}", file=sys.stderr)
        return 1

    device = view.get("device", {})
    if device.get("online") and device.get("enabled"):
        print("watchdog: online")
        return 0
    print("watchdog: agent is OFFLINE or remote access is disabled — "
          "check remote-cli-agent.service", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
