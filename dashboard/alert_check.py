#!/usr/bin/env python3
import json
from pathlib import Path

DATA = Path("/home/gns3/netops-sentinel-data")
REPORTS = DATA / "evidence" / "runs"
INCIDENTS = DATA / "incidents" / "incidents.json"
STATE = DATA / "incidents" / "alert_state.json"


def read_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def main():
    reports = sorted(REPORTS.glob("reachability-*.json"))
    if not reports:
        print("No monitoring reports found.")
        return

    state = read_json(STATE, {
        "last_report": "",
        "failures": {},
        "active": {},
    })

    last_report = state.get("last_report", "")
    pending = [p for p in reports if p.name > last_report]

    if not pending:
        print("No new reports to process.")
        return

    incidents = read_json(INCIDENTS, {"events": []})
    events = incidents.get("events", [])
    failures = state.setdefault("failures", {})
    active = state.setdefault("active", {})
    processed = 0

    for path in pending:
        report = read_json(path, {})
        results = report.get("results", [])
        if not results:
            print("Skipping report without results:", path.name)
            continue

        report_time = report.get(
            "finished_at", report.get("started_at", "")
        )

        for result in results:
            name = result.get("name")
            status = result.get("status")
            if not name:
                continue

            if status == "reachable":
                failures[name] = 0

                if active.get(name, False):
                    events.append({
                        "time": report_time,
                        "endpoint": name,
                        "event": "RECOVERY",
                        "details": (
                            f"{result.get('ip_address', '')} responded again; "
                            "ICMP reachability restored."
                        ),
                    })
                    active[name] = False
                    print("RECOVERY:", name)

            elif status == "unreachable":
                failures[name] = failures.get(name, 0) + 1

                if failures[name] >= 2 and not active.get(name, False):
                    events.append({
                        "time": report_time,
                        "endpoint": name,
                        "event": "OUTAGE",
                        "details": (
                            f"{result.get('ip_address', '')} failed "
                            f"{failures[name]} consecutive monitoring reports."
                        ),
                    })
                    active[name] = True
                    print("OUTAGE:", name)

        state["last_report"] = path.name
        processed += 1
        print("Processed:", path.name)

    incidents["events"] = events[-500:]
    incidents["last_report"] = state.get("last_report", last_report)
    incidents["failures"] = failures
    incidents["active"] = active
    incidents["updated_at"] = (
        report_time if processed else incidents.get("updated_at", "")
    )

    write_json(INCIDENTS, incidents)
    write_json(STATE, state)

    print("Reports processed:", processed)
    print("Incident events stored:", len(incidents["events"]))


if __name__ == "__main__":
    main()
