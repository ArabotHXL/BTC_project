import { PrismaClient } from '@prisma/client';
import { RuleParser } from './RuleParser';

const prisma = new PrismaClient();

export class RuleImporter {
  private parser: RuleParser;

  constructor() {
    this.parser = new RuleParser();
  }

  /**
   * 从目录导入所有YAML规则到数据库
   */
  async importRulesFromDirectory(directory: string): Promise<void> {
    const rules = await this.parser.loadRulesFromDirectory(directory);
    
    console.log(`Found ${rules.length} rules to import`);
    
    for (const rule of rules) {
      await this.importRule(rule);
    }
    
    console.log(`✅ Imported ${rules.length} automation rules`);
  }

  /**
   * 导入单个规则
   */
  async importRule(rule: any): Promise<void> {
    const dbFormat = this.parser.toDatabaseFormat(rule);
    
    const existing = await prisma.automationRule.findFirst({
      where: { name: rule.name },
    });
    
    if (existing) {
      await prisma.automationRule.update({
        where: { id: existing.id },
        data: dbFormat,
      });
      console.log(`Updated rule: ${rule.name}`);
    } else {
      await prisma.automationRule.create({
        data: dbFormat,
      });
      console.log(`Created rule: ${rule.name}`);
    }
  }

  /**
   * 清空所有自动化规则
   */
  async clearAllRules(): Promise<void> {
    await prisma.automationRule.deleteMany({});
    console.log('Cleared all automation rules');
  }
}
