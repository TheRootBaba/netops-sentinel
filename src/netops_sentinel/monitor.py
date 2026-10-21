

import ipaddress
import json
import logging
import math
import platform
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
INVENTORY_FILE = PROJECT_ROOT / "inventory" / "endpoints.json"
RUNS_DIR = PROJECT_ROOT / "evidence" / "runs"
LOG_DIR = PROJECT_ROOT / "logs"

PING_COUNT = 3
PING_TIMEOUT_MS = 1000


def load_endpoints():
    """Load and validate endpoint names and IPv4 addresses."""
    with INVENTORY_FILE.open("r", encoding="utf-8-sig") as file:
        inventory = json.load(file)

    endpoints = (
        inventory.get("endpoints")
        if isinstance(inventory, dict)
        else inventory
    )

    if not isinstance(endpoints, list) or not endpoints:
        raise ValueError(
            "endpoints.json must contain a non-empty endpoint list."
        )

    validated = []
    seen_names = set()

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

        name = str(name).strip()
        if not name:
            raise ValueError("Endpoint names cannot be empty.")

        if name in seen_names:
            raise ValueError(f"Duplicate endpoint name: {name}")

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
            {"name": name, "ip_address": str(parsed_address)}
        )
        seen_names.add(name)

    return validated


def build_ping_command(ip_address, timeout_ms, count=PING_COUNT):
    """Build a bounded multi-ping command for Windows or Linux."""
    if platform.system().lower() == "windows":
        return [
            "ping",
            "-n",
            str(count),
            "-w",
            str(timeout_ms),
            ip_address,
        ]

    
    timeout_seconds = max(3, math.ceil(timeout_ms / 1000))
    return [
        "ping",
        "-n",
        "-c",
        str(count),
        "-W",
        str(timeout_seconds),
        ip_address,
    ]


def parse_ping_output(output, return_code):
    """Extract packet statistics from common Windows/Linux ping output."""
    sent = received = None

    
    match = re.search(
        r"(\d+)\s+packets transmitted,\s*(\d+)\s+"
        r"(?:packets )?received",
        output,
        re.IGNORECASE,
    )

    if match:
        sent = int(match.group(1))
        received = int(match.group(2))
    else:
        
        match = re.search(
            r"Sent\s*=\s*(\d+).*?Received\s*=\s*(\d+)",
            output,
            re.IGNORECASE | re.DOTALL,
        )
        if match:
            sent = int(match.group(1))
            received = int(match.group(2))

    if sent is None:
        sent = PING_COUNT
    if received is None:
        
        received = 1 if return_code == 0 else 0

    return sent, received


def check_endpoint(endpoint, timeout_ms=PING_TIMEOUT_MS):
    """Probe an endpoint multiple times without invoking a shell."""
    started = time.perf_counter()
    command = build_ping_command(
        endpoint["ip_address"], timeout_ms, PING_COUNT
    )

    if platform.system().lower() == "windows":
        process_timeout = (
            PING_COUNT * timeout_ms / 1000
        ) + 5
    else:
        per_ping_timeout = max(3, math.ceil(timeout_ms / 1000))
        process_timeout = PING_COUNT * per_ping_timeout + 3

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=process_timeout,
            check=False,
            shell=False,
        )

        duration_ms = round(
            (time.perf_counter() - started) * 1000, 2
        )
        output = (result.stdout or result.stderr).strip()
        sent, received = parse_ping_output(output, result.returncode)

        if received > 0 or result.returncode == 0:
            status = "reachable"
        else:
            status = "unreachable"

        return {
            "name": endpoint["name"],
            "ip_address": endpoint["ip_address"],
            "status": status,
            "duration_ms": duration_ms,
            "probes_sent": sent,
            "probes_received": received,
            "packet_loss_percent": round(
                max(0, sent - received) / sent * 100, 2
            ) if sent else None,
            "return_code": result.returncode,
            "output": output[-1500:],
        }

    except subprocess.TimeoutExpired:
        return {
            "name": endpoint["name"],
            "ip_address": endpoint["ip_address"],
            "status": "timeout",
            "duration_ms": round(
                (time.perf_counter() - started) * 1000, 2
            ),
            "probes_sent": PING_COUNT,
            "probes_received": 0,
            "packet_loss_percent": 100.0,
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
            "probes_sent": 0,
            "probes_received": 0,
            "packet_loss_percent": None,
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
        "probe_count_per_endpoint": PING_COUNT,
        "success_policy": (
            "Reachable if at least one of the configured ICMP probes "
            "receives a reply."
        ),
        "interpretation_note": (
            "A failed ICMP probe may indicate endpoint unavailability, "
            "ICMP filtering, packet loss, or a routing issue from the "
            "monitoring host. A failed probe alone does not prove the "
            "endpoint is down."
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
            "endpoint=%s ip=%s status=%s probes=%s/%s loss_percent=%s "
            "duration_ms=%s",
            result["name"],
            result["ip_address"],
            result["status"],
            result["probes_received"],
            result["probes_sent"],
            result["packet_loss_percent"],
            result["duration_ms"],
        )
        print(
            f'{result["name"]:<24} '
            f'{result["ip_address"]:<15} '
            f'{result["status"]:<12} '
            f'{result["probes_received"]}/{result["probes_sent"]} replies '
            f'({result["packet_loss_percent"]}% loss) '
            f'{result["duration_ms"]:>8} ms'
        )

    print(f"\nMonitoring host: {platform.node()}")
    print(f"Platform: {platform.system()}")
    print("Probe type: ICMPv4")
    print(f"Probes per endpoint: {PING_COUNT}")
    print(f"Targets checked: {len(results)}")
    print(f"Reachable: {reachable}")
    print(f"Not reachable: {not_reachable}")
    print(f"Report: {report_path.relative_to(PROJECT_ROOT)}")
    print("Log: logs/netops-sentinel.log")

    logging.info(
        "Monitoring run complete: checked=%d reachable=%d "
        "not_reachable=%d",
        len(results),
        reachable,
        not_reachable,
    )

    return 0 if reachable == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
