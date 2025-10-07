import { PrismaClient } from '@prisma/client';
import { AutomationScheduler } from '../services/automation/AutomationScheduler';

const prisma = new PrismaClient();

async function main() {
  console.log('🧪 Testing scheduled automation rules...\n');
  
  const scheduler = new AutomationScheduler();
  
  const rules = await prisma.automationRule.findMany({
    where: {
      triggerType: 'SCHEDULED',
      enabled: true,
    },
  });
  
  console.log(`Found ${rules.length} SCHEDULED rules\n`);
  
  let passCount = 0;
  let failCount = 0;
  
  for (const rule of rules) {
    console.log(`Testing: ${rule.name}`);
    
    try {
      const conditionsJson = rule.conditionsJson as any;
      const conditions = conditionsJson.conditions as any[];
      
      // 测试实体类型推断
      const entityType = (scheduler as any).inferEntityType(conditions);
      if (!entityType) {
        throw new Error('Cannot infer entity type');
      }
      console.log(`  Entity type: ${entityType}`);
      
      // 测试Prisma查询构建
      const entities = await (scheduler as any).queryEntitiesByConditions(entityType, conditions);
      console.log(`  Matching entities: ${entities.length}`);
      
      // 测试executeScheduledRule（干运行）
      console.log(`  Executing rule (dry run)...`);
      await (scheduler as any).executeScheduledRule(rule);
      
      console.log(`  ✅ ${rule.name} PASSED\n`);
      passCount++;
    } catch (error: any) {
      console.error(`  ❌ ${rule.name} FAILED: ${error.message}`);
      if (error.stack) {
        console.error(`     Stack: ${error.stack.split('\n')[1]}`);
      }
      console.log('');
      failCount++;
    }
  }
  
  console.log(`\n📊 Test Results: ${passCount} passed, ${failCount} failed`);
  
  if (failCount > 0) {
    process.exit(1);
  }
}

main()
  .catch(console.error)
  .finally(() => prisma.$disconnect());
