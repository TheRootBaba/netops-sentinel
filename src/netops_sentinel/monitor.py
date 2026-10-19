
"""Read-only IPv4 reachability monitoring for NetOps Sentinel."""

import ipaddress
import json
import logging
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
INVENTORY_FILE = PROJECT_ROOT / "inventory" / "endpoints.json"
RUNS_DIR = PROJECT_ROOT / "evidence" / "runs"
LOG_DIR = PROJECT_ROOT / "logs"


def load_endpoints():
    """Load and validate endpoint names and IPv4 addresses."""
    with INVENTORY_FILE.open("r", encoding="utf-8-sig") as file:
        inventory = json.load(file)

    if isinstance(inventory, dict):
        endpoints = inventory.get("endpoints")
    else:
        endpoints = inventory

    if not isinstance(endpoints, list) or not endpoints:
        raise ValueError(
            "endpoints.json must contain a non-empty endpoint list."
        )

    validated = []

    for endpoint in endpoints:
        if not isinstance(endpoint, dict):
            raise ValueError("Each endpoint must be a JSON object.")

        name = endpoint.get("name") or endpoint.get("hostname")
        address = (
            endpoint.get("ip_address")
            or endpoint.get("ip")
            or endpoint.get("address")
        )

        if not name or not address:
            raise ValueError(
                f"Endpoint is missing a name or IP address: {endpoint}"
            )

        try:
            parsed_address = ipaddress.ip_address(address)
        except ValueError as exc:
            raise ValueError(
                f"Invalid IP address for {name}: {address}"
            ) from exc

        if parsed_address.version != 4:
            raise ValueError(
                f"Only IPv4 endpoints are supported: {name} ({address})"
            )

        validated.append(
            {
                "name": str(name),
                "ip_address": str(parsed_address),
            }
        )

    return validated


def check_endpoint(endpoint, timeout_ms=1000):
    """Perform one bounded Windows ping without invoking a shell."""
    started = time.perf_counter()

    try:
        result = subprocess.run(
            [
                "ping",
                "-n",
                "1",
                "-w",
                str(timeout_ms),
                endpoint["ip_address"],
            ],
            capture_output=True,
            text=True,
            timeout=(timeout_ms / 1000) + 3,
            check=False,
            shell=False,
        )

        duration_ms = round(
            (time.perf_counter() - started) * 1000, 2
        )

        return {
            "name": endpoint["name"],
            "ip_address": endpoint["ip_address"],
            "status": (
                "reachable" if result.returncode == 0 else "unreachable"
            ),
            "duration_ms": duration_ms,
            "return_code": result.returncode,
            "output": (result.stdout or result.stderr).strip()[-1500:],
        }

    except subprocess.TimeoutExpired:
        return {
            "name": endpoint["name"],
            "ip_address": endpoint["ip_address"],
            "status": "timeout",
            "duration_ms": round(
                (time.perf_counter() - started) * 1000, 2
            ),
            "return_code": None,
            "output": "Ping process exceeded its time limit.",
        }

    except OSError as exc:
        return {
            "name": endpoint["name"],
            "ip_address": endpoint["ip_address"],
            "status": "error",
            "duration_ms": round(
                (time.perf_counter() - started) * 1000, 2
            ),
            "return_code": None,
            "output": str(exc),
        }


def main():
    """Run endpoint checks and save a timestamped JSON report."""
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        filename=LOG_DIR / "netops-sentinel.log",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        encoding="utf-8",
    )

    try:
        endpoints = load_endpoints()
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        logging.exception("Inventory loading failed")
        print(f"Inventory error: {exc}", file=sys.stderr)
        return 2

    started_at = datetime.now(timezone.utc)
    results = [check_endpoint(endpoint) for endpoint in endpoints]
    finished_at = datetime.now(timezone.utc)

    reachable = sum(
        result["status"] == "reachable" for result in results
    )
    not_reachable = len(results) - reachable

    report = {
        "project": "NetOps Sentinel",
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "monitoring_mode": "read-only",
        "monitoring_host": platform.node(),
        "monitoring_platform": platform.system(),
        "probe_type": "ICMPv4",
        "interpretation_note": (
            "A failed ICMP probe may indicate endpoint unavailability, "
            "ICMP filtering, or a missing route from the monitoring host. "
            "A failed probe alone does not prove the endpoint is down."
        ),
        "targets_checked": len(results),
        "reachable": reachable,
        "not_reachable": not_reachable,
        "results": results,
    }

    filename = started_at.strftime(
        "reachability-%Y%m%dT%H%M%SZ.json"
    )
    report_path = RUNS_DIR / filename

    try:
        report_path.write_text(
            json.dumps(report, indent=2) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        logging.exception("Could not save monitoring report")
        print(f"Report error: {exc}", file=sys.stderr)
        return 2

    for result in results:
        logging.info(
            "endpoint=%s ip=%s status=%s duration_ms=%s",
            result["name"],
            result["ip_address"],
            result["status"],
            result["duration_ms"],
        )

        print(
            f'{result["name"]:<24} '
            f'{result["ip_address"]:<15} '
            f'{result["status"]:<12} '
            f'{result["duration_ms"]:>8} ms'
        )

    print(f"\nMonitoring host: {platform.node()}")
    print(f"Platform: {platform.system()}")
    print(f"Probe type: ICMPv4")
    print(f"Targets checked: {len(results)}")
    print(f"Reachable: {reachable}")
    print(f"Not reachable: {not_reachable}")
    print(
        "Note: Failed probes may indicate routing or ICMP filtering, "
        "not only endpoint failure."
    )
    print(f"Report: {report_path.relative_to(PROJECT_ROOT)}")
    print("Log: logs/netops-sentinel.log")

    logging.info(
        "Monitoring run complete: checked=%d reachable=%d not_reachable=%d",
        len(results),
        reachable,
        not_reachable,
    )

    return 0 if reachable == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
