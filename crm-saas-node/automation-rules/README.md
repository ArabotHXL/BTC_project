# Automation Rules

## Overview

This directory contains YAML-based automation rules for the CRM system. Rules are automatically loaded and executed by the automation engine based on triggers (events or schedules).

## Rule Structure

Each rule file follows this YAML structure:

```yaml
name: "Rule Name"
description: "Rule description"
trigger:
  type: LEAD_CREATED | DEAL_STAGE_CHANGED | INVOICE_OVERDUE | SCHEDULED
  event: "event.type" # For event-based triggers
  schedule: "0 9 * * *" # For SCHEDULED triggers (cron format)

conditions:
  - field: "lead.status"
    operator: "equals" | "not_equals" | "contains" | "greater_than" | "less_than" | "in" | "not_in"
    value: "NEW"
  - field: "lead.created_at"
    operator: "older_than"
    value: "24h"

actions:
  - type: "send_email"
    params:
      to: "{{lead.assigned_to.email}}"
      subject: "Follow up required: {{lead.company_name}}"
      template: "lead_follow_up"
  - type: "update_field"
    params:
      entity: "lead"
      field: "status"
      value: "FOLLOW_UP_REQUIRED"
```

## Trigger Types

- **LEAD_CREATED**: Triggered when a new lead is captured
- **DEAL_STAGE_CHANGED**: Triggered when a deal stage changes
- **INVOICE_OVERDUE**: Triggered for overdue invoice checks
- **SCHEDULED**: Triggered on a cron schedule
- **TICKET_CREATED**: Triggered when a support ticket is created
- **ASSET_OFFLINE**: Triggered when an asset goes offline

## Condition Operators

- **equals**: Exact match
- **not_equals**: Not equal
- **greater_than**: Numeric greater than
- **less_than**: Numeric less than
- **greater_than_or_equal**: Numeric greater than or equal
- **contains**: String contains
- **in**: Value is in array
- **not_in**: Value is not in array
- **is_null**: Field is null/undefined
- **is_not_null**: Field has a value
- **older_than**: Date is older than duration (e.g., "24h", "7d")
- **before**: Date is before reference
- **is_today**: Date matches today

## Action Types

- **send_email**: Send email notification
- **update_field**: Update entity field
- **create_notification**: Create in-app notification
- **create_task**: Create task/activity
- **assign_round_robin**: Assign to team member (round-robin)
- **create_invoice**: Generate invoice
- **release_reserved_assets**: Release reserved inventory
- **start_mining_monitoring**: Start monitoring asset
- **trigger_fulfillment**: Trigger order fulfillment
- **create_ticket**: Create support ticket
- **apply_discount**: Apply discount to account

## Variable Interpolation

Use `{{field.path}}` syntax to interpolate values from the entity:
- `{{lead.company_name}}`
- `{{deal.account.email}}`
- `{{invoice.number}}`

## Available Rules

1. **lead-24h-follow-up.yaml** - Remind sales reps about uncontacted leads after 24h
2. **lead-auto-assignment.yaml** - Auto-assign new leads to sales team (round-robin)
3. **deal-auto-advance.yaml** - Advance deals to negotiation stage automatically
4. **invoice-auto-generation.yaml** - Generate invoice when contract is signed
5. **invoice-overdue-reminder.yaml** - Send escalating reminders for overdue invoices
6. **order-release-7days.yaml** - Cancel unpaid orders after 7 days
7. **asset-deployment-notification.yaml** - Notify customer when asset is deployed
8. **payment-confirmed-update-deal.yaml** - Update deal status when payment confirmed
9. **shipment-delayed-alert.yaml** - Alert operations team about delayed shipments
10. **customer-birthday-greeting.yaml** - Send birthday greetings with special offers

## Usage

Rules are automatically loaded on application startup. To add a new rule:

1. Create a YAML file in this directory
2. Follow the rule structure above
3. Restart the automation service to load the rule

To disable a rule, either:
- Remove/rename the YAML file
- Set `enabled: false` in the database for that rule
