# NetOps Sentinel

**Network Operations, Automation, Monitoring & Security Lab**

NetOps Sentinel is a network operations lab project that validates a structured network inventory, performs read-only endpoint reachability checks, and records monitoring results as JSON evidence. The network is modeled and tested in a GNS3 environment.

## Project status

**Current scope:** inventory validation, endpoint reachability monitoring, and evidence collection.

The repository includes Python source code, JSON inventory files, automated tests, and selected network topology, connectivity, and configuration evidence. Runtime monitoring reports are generated separately and are not currently checked in.

## Implemented

- JSON-based inventory for devices, networks, endpoints, interfaces, and routing intent.
- Inventory validation with checks for expected data and addressing.
- Read-only endpoint reachability probes using the system ping utility.
- Linux and Windows probe support.
- JSON output for monitoring runs.
- Automated unit tests for inventory validation, endpoint loading, successful and failed probes, and probe timeouts.
- Screenshots and reports documenting selected lab tests.

## Lab topology

The documented baseline contains:

- 3 FRRouting routers
- 5 Ethernet switches
- 5 LANs
- 2 router-to-router transit networks
- 5 inventoried VPCS endpoints
- Static routing as the stated routing baseline

See [`docs/NETWORK-EVIDENCE.md`](docs/NETWORK-EVIDENCE.md) and [`evidence/topology/topology.png`](evidence/topology/topology.png) for the available topology and test evidence.

## Validation

Run from the repository root in PowerShell:

```powershell
$env:PYTHONPATH = "$PWD\src"

.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m netops_sentinel.validate_inventory

Remove-Item Env:\PYTHONPATH -ErrorAction SilentlyContinue
```

The recorded validation run passed **7 unit tests** and reported:

- Devices checked: 8
- Networks checked: 7
- Endpoints checked: 5
- Interfaces checked: 4
- Inventory validation: PASS

These results describe that test run. They do not independently establish the current health of every live network device or route.

## Evidence

- `evidence/topology/` — topology image.
- `evidence/connectivity/` — selected endpoint connectivity and configuration screenshots.
- `evidence/persistence/` — selected configuration persistence evidence.
- `evidence/runs/` — runtime location for timestamped JSON reachability reports; reports are not currently tracked in Git.
- `docs/NETWORK-EVIDENCE.md` — evidence index and test notes.

Evidence demonstrates only the scenarios and times represented by the files. Consult the evidence notes before drawing conclusions about the current live network.

## Current limitations

- Live router route tables have not yet been verified as part of the checked-in inventory.
- Static routing is the documented baseline; OSPF and other dynamic routing protocols are not claimed as implemented.
- Inventory validation does not replace live device-state verification.
- Reachability probes establish whether a target responds to the configured probe; they do not prove that every application or service on that target is healthy.
- Monitoring results reflect the time and conditions of each run and may differ from current network state.
- Database-backed persistence, a production API, and AI-assisted operations are future enhancements, not part of the current core implementation.
- The repository's current automated tests do not constitute a full end-to-end test suite for every GNS3 device and failure scenario.

## Safety

The current monitoring scope is read-only. Do not use this project as authorization to change router configuration.

Any future configuration automation should have a separate change plan, backups, explicit approval, post-change verification, and a rollback procedure.

## Technology

- Python
- JSON inventory and monitoring evidence
- GNS3
- FRRouting

## Roadmap

1. Improve live route and device-state verification.
2. Add configurable monitoring schedules and alerting.
3. Evaluate database persistence and a documented API/dashboard architecture.
4. Consider AI-assisted workflows only after reliable data collection, access controls, and auditability are established.

