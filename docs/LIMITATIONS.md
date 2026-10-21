# Current Limitations and Verification Boundaries

## What has been tested

The current recorded Python test run passed seven unit tests covering inventory validation, endpoint loading, probe success and failure, and probe timeout behavior. The inventory validator also passed for the checked-in inventory.

These checks establish that the tested code paths passed in that environment. They are not proof of continuous availability or complete network correctness.

## What the evidence supports

The repository contains selected topology, endpoint connectivity, configuration, persistence, and reachability-report evidence. Each artifact should be interpreted according to its timestamp and the scenario it captures.

A screenshot or successful reachability report does not establish that the same condition persists now.

## Routing and device state

The checked-in routing inventory identifies static routing as the intended baseline and explicitly indicates that live configuration has not been verified. Live route-table output is needed before making stronger claims about active routes or end-to-end routing correctness.

OSPF, VLAN/trunk implementation, and dynamic routing must not be described as completed unless corresponding implementation and verification evidence is added.

## Monitoring scope

Reachability monitoring uses ping responses as a basic signal. A failed probe may indicate unreachability, filtering, loss, or another probe-related condition; a successful probe does not prove application-level health.

The existing tests cover selected probe behaviors, not every operating-system version, network failure, or device configuration.

## Not currently included in the core release

- Database-backed persistence
- A production-grade API or dashboard integration
- AI-agent-driven network operations
- Automated router configuration changes
- Comprehensive live route and device-state verification

These are possible future improvements, not current capabilities.
