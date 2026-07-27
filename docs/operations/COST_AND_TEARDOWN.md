# Cost Controls and Teardown for AI-103 Live Labs

Last verified: 2026-07-27

Use this document before enabling live Azure execution. The repository defaults to offline fixtures; live labs must be explicit.

## Cost-control baseline

Before any live resource is created:

1. Confirm the selected subscription and tenant.
2. Create or confirm an Azure budget.
3. Add budget-alert recipients.
4. Add tags to every planned resource.
5. Estimate cost for the smallest viable SKU.
6. Record whether the lab consumes free allowance, credit, paid usage, or provisioned capacity.
7. Define teardown before deployment.

Microsoft Cost Management budgets help track spending and send notifications when thresholds are met. Budgets do not automatically stop consumption or delete resources by themselves.

## Required tags

Every live lab resource should include:

- `project=AI-103`
- `purpose=study-lab`
- `owner=<learner>`
- `task=<manifest-task-or-lab-id>`
- `createdBy=AI---103`
- `deleteAfter=<YYYY-MM-DD>`

Tags help group and allocate costs in Cost Management and make teardown safer.

## Budget and alert rules

Recommended study defaults:

- Use the lowest practical budget for the subscription or resource group.
- Set actual-cost alerts at 50%, 80%, and 100%.
- Set forecast alerts when supported.
- Review Cost Analysis after live runs; cost and usage data can lag.
- Treat any untagged resource as a teardown defect.

For Foundry labs, monitor total solution cost, not only model calls. Foundry model, agent, tool, storage, search, networking, monitoring, and provisioned capacity can each contribute cost.

## Teardown checklist

After each live lab:

1. Export or save only non-sensitive learning artifacts.
2. Stop running compute or app services.
3. Delete lab resource groups when no longer needed.
4. Confirm all resources with `project=AI-103` are gone or intentionally retained.
5. Check Cost Analysis after the expected data delay.
6. Record teardown completion in the lab result.

If a learner wants to stop using Azure entirely, Microsoft documents cancellation through the Azure portal. Microsoft also recommends shutting down services and deleting resources/resource groups before cancellation when appropriate.

## Live-lab refusal rules

The repo should refuse live execution when:

- No explicit live-lab opt-in is present.
- No subscription ID is configured.
- No budget or cost gate is documented.
- The target region or quota is unknown.
- The lab would use provisioned throughput without an explicit capacity-cost acknowledgement.
- The teardown plan is missing.
- The learner is asking the agent to create an account, enter billing details, or accept terms.

## Sources

- Create and manage budgets: https://learn.microsoft.com/en-us/azure/cost-management-billing/costs/tutorial-acm-create-budgets
- Plan and manage Azure costs: https://learn.microsoft.com/en-us/azure/cost-management-billing/understand/plan-manage-costs
- Cost Management overview: https://learn.microsoft.com/en-us/azure/cost-management-billing/costs/overview-cost-management
- Cancel and delete your Azure subscription: https://learn.microsoft.com/en-us/azure/cost-management-billing/manage/cancel-azure-subscription
- Azure subscription states: https://learn.microsoft.com/en-us/azure/cost-management-billing/manage/subscription-states
- Plan and manage costs for Microsoft Foundry: https://learn.microsoft.com/en-us/azure/foundry/concepts/manage-costs
- Provisioned throughput billing and cost management: https://learn.microsoft.com/en-us/azure/foundry/openai/concepts/provisioned-throughput-billing
