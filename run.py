# -*- coding: utf-8 -*-
"""Collect current data, record source dates, and rebuild the dashboard."""
import json
import os
import sys
from datetime import datetime, timezone, timedelta
import update
import build

KST = timezone(timedelta(hours=9))


def main():
    started = datetime.now(KST).isoformat(timespec="seconds")
    result = update.main()
    payload = build.build_payload()
    items = []
    for item in payload:
        latest = item.get("last_date", "")
        days = (datetime.now(KST).date() - datetime.fromisoformat(latest).date()).days if latest else None
        tolerance = 10 if item["id"] in ("eia_gas", "topcon") else 4
        items.append({"id": item["id"], "name": item["name"], "latest_date": latest,
                      "stale": days is None or days > tolerance})
    status = dict(started_at=started, finished_at=datetime.now(KST).isoformat(timespec="seconds"),
                  **result, items=items)
    status["state"] = "failed" if result["ok"] == 0 else ("partial" if result["fail"] else "ok")
    path = os.path.join(update.DATA, "update_status.json")
    with open(path + ".tmp", "w", encoding="utf-8") as f:
        json.dump(status, f, ensure_ascii=False, indent=2)
    os.replace(path + ".tmp", path)
    # Rebuild the warning even on failure; never label retained prices as current.
    build.build()
    print("Data dates: " + ", ".join(x["id"] + "=" + (x["latest_date"] or "none") for x in items))
    return 1 if status["state"] == "failed" else (2 if status["state"] == "partial" else 0)


if __name__ == "__main__":
    raise SystemExit(main())
