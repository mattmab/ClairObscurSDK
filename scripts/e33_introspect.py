"""Port of Mattmab's MIT BL4Introspection client; local files, no sockets.
License: src/expedition33/introspection/LICENSE."""
from __future__ import annotations
import argparse
import json
import os
import math
from pathlib import Path
import sys
import time
import uuid

DEFAULT_DATA = Path(__file__).resolve().parents[1] / "settings" / "E33Introspection"


def send(request, data=DEFAULT_DATA, timeout=15.0):
    if not isinstance(request, dict):
        raise ValueError("Request must be a JSON object")
    if not math.isfinite(timeout) or not 0 < timeout <= 300:
        raise ValueError("Timeout must be finite and in (0, 300]")
    data = Path(data)
    # The game's heartbeat writer can briefly hold this file on Windows.
    # Retry only this read, BEFORE generating/enqueuing a request. Mutations
    # themselves are never retried when their execution outcome is unknown.
    for attempt in range(6):
        try:
            status = json.loads((data / "status.json").read_text(encoding="utf-8"))
            break
        except (PermissionError, json.JSONDecodeError):
            if attempt == 5:raise
            time.sleep(0.05)
    if not status["enabled"] or time.time() - status["heartbeat"] > 5:
        raise RuntimeError("No fresh controller heartbeat. Run launch.cmd introspection with the supported game running.")
    request_id = uuid.uuid4().hex
    request = dict(request, session=status["session"], expires=time.time() + timeout)
    pending = data / "requests" / (request_id + ".json")
    temp = pending.with_suffix(".tmp")
    response = data / "responses" / (request_id + ".json")
    payload = json.dumps(request, allow_nan=False)
    if len(payload.encode("utf-8")) > 65536:
        raise ValueError("Request exceeds 64 KiB")
    temp.write_text(payload, encoding="utf-8")
    os.replace(temp, pending)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if response.exists():
            result = json.loads(response.read_text(encoding="utf-8"))
            if result.get("id") != request_id or result.get("session") != status["session"]:
                raise RuntimeError("Response identity mismatch")
            return result
        time.sleep(0.1)
    # Expiry prevents unclaimed work from executing later. Never retry mutations automatically.
    raise TimeoutError(f"No response for {request_id}. Outcome unknown if already claimed; inspect {response} before retrying.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--timeout", type=float, default=15)
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("status", help="Read local heartbeat without waiting for the game")
    p = sub.add_parser("request", help="Send a JSON request file, or - for stdin")
    p.add_argument("file")
    for action in ("roots", "search", "schema"):
        p = sub.add_parser(action)
        if action != "roots":
            p.add_argument("--class", dest="class_name", default="Object" if action == "search" else None, required=action == "schema")
            p.add_argument("--offset", type=int, default=0)
            p.add_argument("--limit", type=int, default=100)
        if action == "search":
            p.add_argument("--query", default="")
    args = parser.parse_args()
    try:
        if args.action == "status":
            result = json.loads((args.data / "status.json").read_text(encoding="utf-8"))
            result["fresh"] = bool(result["enabled"] and time.time() - result["heartbeat"] <= 5)
        else:
            if args.timeout <= 0 or args.timeout > 300:
                raise ValueError("Timeout must be in (0, 300]")
            if args.action == "request":
                request = json.loads(sys.stdin.read() if args.file == "-" else Path(args.file).read_text(encoding="utf-8"))
            else:
                request = {"op": args.action}
                if args.action != "roots":
                    request.update({"class": args.class_name, "offset": args.offset, "limit": args.limit})
                if args.action == "search":
                    request["query"] = args.query
            result = send(request, args.data, args.timeout)
        print(json.dumps(result, indent=2))
        return 0 if result.get("ok", result.get("fresh", True)) else 1
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
