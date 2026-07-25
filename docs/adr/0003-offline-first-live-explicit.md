# ADR 0003: Offline First and Live Explicit

Status: Accepted

## Context

The existing ALO works locally without Azure credentials. The target product needs real Azure and Microsoft Foundry calls, but those calls can create cost, leak data, or fail due to account, quota, or regional availability.

## Decision

Offline mode is the default. Network, Azure, and model calls require explicit live-mode activation through CLI flags or protected CI dispatch. Live execution must perform account, region, quota, cost, tagging, and teardown preflight before provisioning or calling services.

## Consequences

- Pull-request CI cannot require Azure secrets.
- Live CI runs only through manual `workflow_dispatch` and the protected `live-azure` environment.
- Local labs must provide offline fixtures or simulations.
- Budget alerts are documented as alerts, not hard spending caps.
- The system must never create subscriptions or billable resources without explicit user approval.
- Teardown verification is part of live lab success.
