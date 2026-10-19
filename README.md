# NetOps Sentinel

Network Operations, Automation, Monitoring & Security Lab.

## Current network baseline
- 3 FRRouting routers
- 5 switches
- 5 LANs
- 2 router-to-router transit networks
- Static routing only
- OSPF, VLANs and trunks are not implemented yet

## Technology stack
- Python 3.12
- JSON network inventory
- PostgreSQL database (planned)
- FastAPI backend (planned)
- React + TypeScript dashboard (planned)

## Validate the inventory
```powershell
$env:PYTHONPATH = "$PWD\src"
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m netops_sentinel.validate_inventory
Remove-Item Env:\PYTHONPATH
```

## Safety
Initial monitoring will be read-only. Router configuration changes will require a separate plan, backup, approval, verification and rollback procedure.
