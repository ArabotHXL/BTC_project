# Automation Rules Setup

## Import Rules to Database

```bash
cd crm-saas-node/backend
npm run import:rules
```

This will load all YAML rules from `automation-rules/` into the AutomationRule table.

## Start Automation Scheduler

The scheduler is automatically started when the worker process starts.

## Test Scheduled Rules

Before deploying, test that all scheduled rules can query entities correctly:

```bash
npm run test:rules
```

This will:
1. Load all SCHEDULED rules from database
2. Test entity type inference
3. Test Prisma query construction
4. Report any errors

Expected output:
```
🧪 Testing scheduled automation rules...

Found 6 SCHEDULED rules

Testing: Lead 24h Follow-up Reminder
  Entity type: lead
  Matching entities: 3
  ✅ Lead 24h Follow-up Reminder OK

...
```

## Verify Rules

Query the database:
```sql
SELECT name, trigger_type, enabled, last_run FROM automation_rules;
```

## Manual Execution

For testing, you can manually trigger a rule:
```typescript
import { RuleExecutor } from './services/automation';

const executor = new RuleExecutor();
await executor.executeRule(ruleId, 'lead', leadId, leadData);
```
