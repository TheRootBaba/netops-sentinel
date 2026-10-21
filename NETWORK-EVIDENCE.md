# NetOps Sentinel — Network Evidence and Validation

## 1. Project Information

| Field | Details |
|---|---|
| Project | NetOps Sentinel |
| Full name | Network Operations, Automation, Monitoring & Security Lab |
| Virtualization platform | GNS3 2.2.61 |
| Router platform | FRRouting 10.6.2 |
| Host operating system | Windows 11 |
| Routing method | Static routing |
| Network status | Operational baseline |
| Evidence date | October 19, 2026 |

## 2. Purpose

This document provides the technical record of the NetOps Sentinel network lab. It documents the topology, router configurations, endpoint addressing, connectivity testing, and configuration persistence.

The initial network has been tested end-to-end, and all reported ping tests succeed. The screenshots embedded throughout this document provide visual evidence of the lab and its configurations.

This document establishes the baseline against which future monitoring, automation, and security improvements will be measured.

## 3. Network Architecture

The lab consists of three FRRouting routers, five switches, five endpoints, five LAN networks, and two point-to-point transit networks.

### 3.1 Core Router

**Device:** MICHAEL-SCOTT-CORE

The core router connects the headquarters networks and provides routing toward the branch networks.

### 3.2 Branch Routers

**Device:** STANLEY-BRANCH-R1

Connects the Stanley branch LAN to the core-facing transit network and the Kelly branch transit network.

**Device:** KELLY-BRANCH-R1

Connects the Kelly branch LAN to the Stanley branch router.

### 3.3 Switching Infrastructure

| Switch | Purpose |
|---|---|
| JIM-PAM-USERS-SW | Headquarters users LAN |
| DWIGHT-SERVERS-SW | Headquarters servers LAN |
| CREED-MGMT-SW | Management LAN |
| STANLEY-BRANCH-SW | Stanley branch LAN |
| KELLY-BRANCH-SW | Kelly branch LAN |

### 3.4 Overall GNS3 Topology

**Evidence ID:** TOP-01  
**File:** `evidence/topology/topology.png`

![TOP-01 — NetOps Sentinel GNS3 network topology](../evidence/topology/topology.png)

**Observation:** The screenshot documents the overall GNS3 topology and the connections between the routers, switches, and endpoint devices.

**Result:** Topology evidence captured.

## 4. IP Addressing Plan

The lab uses five LAN subnets and two point-to-point transit subnets.

| Network | Subnet | Gateway or Transit Addresses |
|---|---|---|
| HQ Users | `10.10.10.0/24` | `10.10.10.1` |
| HQ Servers | `10.10.20.0/24` | `10.10.20.1` |
| Management | `10.10.99.0/24` | `10.10.99.1` |
| Stanley Branch LAN | `10.20.10.0/24` | `10.20.10.1` |
| Kelly Branch LAN | `10.30.10.0/24` | `10.30.10.1` |
| Core–Stanley Transit | `10.255.0.0/30` | Core: `10.255.0.1`; Stanley: `10.255.0.2` |
| Stanley–Kelly Transit | `10.255.0.4/30` | Stanley: `10.255.0.5`; Kelly: `10.255.0.6` |

The five LAN subnets provide connectivity for users, servers, management, and the two branch networks. The two transit subnets provide routed connectivity between the three routers.

## 5. Router Configuration Evidence

### 5.1 MICHAEL-SCOTT-CORE

**Evidence ID:** RTR-01  
**File:** `evidence/connectivity/MICHAEL-SCOTT-CONFIG.png`

![RTR-01 — MICHAEL-SCOTT-CORE router configuration](../evidence/connectivity/MICHAEL-SCOTT-CONFIG.png)

**Role:** Headquarters core routing.

**Evidence documents:** The router configuration shown in the captured console, used as part of the network baseline.

### 5.2 STANLEY-BRANCH-R1

**Evidence ID:** RTR-02  
**File:** `evidence/connectivity/STANLEY-BRANCH-CONFIG.png`

![RTR-02 — STANLEY-BRANCH-R1 router configuration](../evidence/connectivity/STANLEY-BRANCH-CONFIG.png)

**Role:** Branch routing and transit connectivity between the core and Kelly branch.

**Evidence documents:** The router configuration shown in the captured console, used as part of the network baseline.

### 5.3 KELLY-BRANCH-R1

**Evidence ID:** RTR-03  
**File:** `evidence/connectivity/KELLY-BRANCH-CONFIG.png`

![RTR-03 — KELLY-BRANCH-R1 router configuration](../evidence/connectivity/KELLY-BRANCH-CONFIG.png)

**Role:** Kelly branch routing.

**Evidence documents:** The router configuration shown in the captured console, used as part of the network baseline.

## 6. Endpoint Configuration Evidence

The following screenshots document the five endpoint consoles and their network configuration. The intended IP addresses and gateways are recorded alongside each endpoint.

### 6.1 PAM-HQ-PC

**Evidence ID:** EP-01  
**File:** `evidence/connectivity/PAM-HQ-PC.png`

![EP-01 — PAM-HQ-PC endpoint configuration](../evidence/connectivity/PAM-HQ-PC.png)

| Property | Intended value |
|---|---|
| Network | HQ Users |
| IP address | `10.10.10.10/24` |
| Default gateway | `10.10.10.1` |

**Role:** Headquarters user endpoint and a source for end-to-end connectivity testing.

### 6.2 DWIGHT-SERVER-PC

**Evidence ID:** EP-02  
**File:** `evidence/connectivity/DWIGHT-SERVER-PC.png`

![EP-02 — DWIGHT-SERVER-PC endpoint configuration](../evidence/connectivity/DWIGHT-SERVER-PC.png)

| Property | Intended value |
|---|---|
| Network | HQ Servers |
| IP address | `10.10.20.10/24` |
| Default gateway | `10.10.20.1` |

**Role:** Headquarters server-network endpoint.

### 6.3 CREED-MGMT-PC

**Evidence ID:** EP-03  
**File:** `evidence/connectivity/CREED-MGMT-PC.png`

![EP-03 — CREED-MGMT-PC endpoint configuration](../evidence/connectivity/CREED-MGMT-PC.png)

| Property | Intended value |
|---|---|
| Network | Management |
| IP address | `10.10.99.10/24` |
| Default gateway | `10.10.99.1` |

**Role:** Management-network endpoint.

### 6.4 STANLEY-BRANCH-PC

**Evidence ID:** EP-04  
**File:** `evidence/connectivity/STANLEY-BRANCH-PC.png`

![EP-04 — STANLEY-BRANCH-PC endpoint configuration](../evidence/connectivity/STANLEY-BRANCH-PC.png)

| Property | Intended value |
|---|---|
| Network | Stanley Branch LAN |
| IP address | `10.20.10.10/24` |
| Default gateway | `10.20.10.1` |

**Role:** Stanley branch endpoint.

### 6.5 KELLY-BRANCH-PC

**Evidence ID:** EP-05  
**File:** `evidence/connectivity/KELLY-BRANCH-PC.png`

![EP-05 — KELLY-BRANCH-PC endpoint configuration](../evidence/connectivity/KELLY-BRANCH-PC.png)

| Property | Intended value |
|---|---|
| Network | Kelly Branch LAN |
| IP address | `10.30.10.10/24` |
| Default gateway | `10.30.10.1` |

**Role:** Kelly branch endpoint.

## 7. End-to-End Connectivity Validation

The initial network baseline has been tested end-to-end. All reported ping tests succeed.

The following table records the core connectivity checks that establish the baseline.

| Test ID | Source | Destination | Result |
|---|---|---|---|
| CON-01 | PAM-HQ-PC | HQ gateway `10.10.10.1` | Pass |
| CON-02 | PAM-HQ-PC | DWIGHT-SERVER-PC `10.10.20.10` | Pass |
| CON-03 | PAM-HQ-PC | CREED-MGMT-PC `10.10.99.10` | Pass |
| CON-04 | PAM-HQ-PC | STANLEY-BRANCH-PC `10.20.10.10` | Pass |
| CON-05 | PAM-HQ-PC | KELLY-BRANCH-PC `10.30.10.10` | Pass |

These results establish successful reachability across the listed destinations. The endpoint screenshots in Section 6 provide the endpoint configuration evidence associated with this baseline.

## 8. Configuration Persistence Evidence

The following router screenshots were captured immediately after the routers were restarted. They document the router configurations observed after restart.

### 8.1 MICHAEL-SCOTT-CORE

**Evidence ID:** PER-01  
**File:** `evidence/persistence/MICHAEL-SCOTT-CONFIG.png`

![PER-01 — MICHAEL-SCOTT-CORE post-restart configuration](../evidence/persistence/MICHAEL-SCOTT-CONFIG.png)

**Observation:** Captured immediately after restart.

**Purpose:** Records the core router's post-restart configuration for comparison with the intended network baseline.

### 8.2 STANLEY-BRANCH-R1

**Evidence ID:** PER-02  
**File:** `evidence/persistence/STANLEY-BRANCH-CONFIG.png`

![PER-02 — STANLEY-BRANCH-R1 post-restart configuration](../evidence/persistence/STANLEY-BRANCH-CONFIG.png)

**Observation:** Captured immediately after restart.

**Purpose:** Records the Stanley router's post-restart configuration for comparison with the intended network baseline.

### 8.3 KELLY-BRANCH-R1

**Evidence ID:** PER-03  
**File:** `evidence/persistence/KELLY-BRANCH-CONFIG.png`

![PER-03 — KELLY-BRANCH-R1 post-restart configuration](../evidence/persistence/KELLY-BRANCH-CONFIG.png)

**Observation:** Captured immediately after restart.

**Purpose:** Records the Kelly router's post-restart configuration for comparison with the intended network baseline.

### Full LAN Connectivity Verification

- **Test source:** PAM-HQ-PC (`10.10.10.10`)
- **Test method:** ICMP ping from the GNS3 VPCS console
- **Result:** PASS — all five endpoint addresses responded to two consecutive ping requests.

| Destination | Network | Result |
|---|---|---|
| `10.10.10.1` | HQ Users gateway | PASS |
| `10.10.20.10` | HQ Servers | PASS |
| `10.10.99.10` | Management | PASS |
| `10.20.10.10` | Stanley Branch | PASS |
| `10.30.10.10` | Kelly Branch | PASS |

**Evidence:** `../evidence/connectivity/PAM-HQ-ALL-LAN-CONNECTIVITY.png`

**Scope:** This verifies connectivity from PAM-HQ-PC to the listed destinations at the time of testing. It does not independently verify every source-to-destination combination or Windows-host reachability.

## 9. Findings and Design Decisions

- The lab contains seven IP networks: five LAN subnets and two router-to-router transit subnets.
- The network baseline uses static routing.
- Three FRRouting routers provide connectivity between the headquarters and branch networks.
- Five switches connect the endpoint LANs.
- The five endpoint IP addresses and gateways are recorded in the project inventory.
- The initial end-to-end connectivity tests succeed.
- Router post-restart screenshots are retained as persistence evidence.
- OSPF, VLANs, and trunking are not part of the current implemented baseline.

## 10. Evidence Management

All evidence is maintained within the project repository:

- `evidence/topology/` — overall GNS3 topology.
- `evidence/connectivity/` — router configuration and endpoint screenshots.
- `evidence/persistence/` — post-restart router screenshots.
- `docs/NETWORK-EVIDENCE.md` — this evidence register and technical record.

Screenshots are embedded using relative Markdown paths so that the images render when the repository is opened in VS Code or viewed through a compatible Git repository interface.

Original evidence is preserved. Credentials, tokens, private keys, and other secrets must not be included in screenshots or committed to Git.

## 11. Baseline Conclusion

The NetOps Sentinel lab has an established network design with three routers, five switches, five endpoint LANs, and two transit networks.

The initial end-to-end connectivity tests are successful, and the captured screenshots document the topology, router configurations, endpoint configurations, and router state immediately after restart.

This baseline provides the foundation for the next phase of NetOps Sentinel: implementing read-only monitoring, structured test results, and automated evidence collection.
