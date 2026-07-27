# Azure Free Account and Sandbox Setup for AI-103

Last verified: 2026-07-27

This guide explains what a learner must set up before running live Azure labs for this repository. It does not create an Azure account for the learner.

## Current account reality

General Microsoft Learn Azure sandboxes that previously provided temporary Azure subscriptions for many modules are retired or unavailable. Plan AI-103 hands-on work around one of these options:

1. Azure free account for a new Azure customer.
2. Existing Azure subscription with explicit budget, quota, region, and teardown controls.
3. Azure for Students, when eligible.
4. Instructor-provided lab environment.

Do not assume every Microsoft Learn exercise still includes a free Azure sandbox. Some Microsoft Learn content may still include interactive browser labs, but those are different from a reusable Azure subscription for this project.

## Azure free account

Microsoft’s Azure account page describes the Azure free account as best for proof-of-concept and exploration. As of this verification date, Microsoft lists:

- Availability only to new Azure customers.
- Access to free monthly amounts for selected services.
- A $200 credit to use on Azure services within 30 days.
- Spending protection for the free-account credit-card path.
- A move to pay-as-you-go is required to continue after 30 days or after credit is used.

Important limitations for AI-103:

- Do not promise that every Azure AI or Foundry service is free.
- Service availability, quota, model availability, and free amounts can vary by region, account type, and service.
- Azure AI Foundry is free to explore at the platform level, but pricing occurs at deployment level, and underlying resources can also cost money.
- Provisioned throughput deployments can bill for reserved capacity rather than only consumed tokens; do not use provisioned deployments for casual study unless you know the billing model.

## Azure for Students

Azure for Students is a separate path for eligible students. Microsoft’s Azure for Students page currently describes:

- $100 Azure credit.
- No credit card required.
- Use for education, teaching, non-commercial research, and learning-related development.
- Eligibility tied to school/university status and renewal rules.

Use this when eligible; otherwise use a free account, existing subscription, or instructor lab.

## Required learner checklist

Before a live lab runs, record:

- Microsoft account selected for Azure sign-in.
- MFA enabled.
- Tenant selected.
- Subscription name and ID.
- Region selected.
- Budget name and amount.
- Cost alert recipients.
- Resource group naming prefix.
- Required providers registered.
- Quota check completed for the target service.
- Whether the lab uses free tier, paid consumption, or both.
- Teardown command or portal path.

## Account setup boundary

An agent or script in this repo must not:

- Create the Azure account for the learner.
- Enter payment details.
- Bypass MFA.
- Accept legal or billing terms on behalf of the learner.
- Promise that credit protection prevents every possible charge.
- Create live resources without an explicit live-lab opt-in.

An agent or script may:

- Validate that configuration variables exist.
- Check that a subscription is selected.
- Check current region and quota metadata.
- Generate a resource plan.
- Refuse to run when budget, teardown, or consent gates are missing.

## Exam-interface sandbox

The Microsoft certification exam sandbox is separate from Azure resource sandboxes. Use it to practice exam UI navigation, question types, marking questions for review, and assistive technology behavior. It does not provide Azure resources for labs.

## Sources

- Azure account options: https://azure.microsoft.com/en-us/pricing/purchase-options/azure-account
- Azure for Students: https://azure.microsoft.com/en-us/free/students
- Microsoft Q&A sandbox availability: https://learn.microsoft.com/en-us/answers/questions/5902797/sandbox-available
- Microsoft exam sandbox overview: https://learn.microsoft.com/en-us/shows/exam-readiness-zone/what-to-expect-on-your-microsoft-exam
- Microsoft Foundry overview and billing note: https://learn.microsoft.com/en-us/azure/ai-foundry/what-is-ai-foundry
- Azure OpenAI quota guidance: https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/quota
- Provisioned throughput billing: https://learn.microsoft.com/en-us/azure/foundry/openai/concepts/provisioned-throughput-billing
