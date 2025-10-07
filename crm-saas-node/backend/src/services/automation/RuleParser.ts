import yaml from 'js-yaml';
import fs from 'fs/promises';
import path from 'path';
import { AutomationTrigger } from '@prisma/client';

export interface AutomationRuleYAML {
  name: string;
  description?: string;
  trigger: {
    type: AutomationTrigger;
    event?: string;
    schedule?: string;
  };
  conditions: Array<{
    field: string;
    operator: string;
    value: any;
  }>;
  actions: Array<{
    type: string;
    params: Record<string, any>;
  }>;
}

export class RuleParser {
  /**
   * 解析单个YAML规则文件
   */
  async parseRuleFile(filePath: string): Promise<AutomationRuleYAML> {
    const content = await fs.readFile(filePath, 'utf8');
    const rule = yaml.load(content) as AutomationRuleYAML;
    
    this.validateRule(rule);
    return rule;
  }

  /**
   * 加载目录下所有YAML规则
   */
  async loadRulesFromDirectory(directory: string): Promise<AutomationRuleYAML[]> {
    const files = await fs.readdir(directory);
    const yamlFiles = files.filter(f => f.endsWith('.yaml') || f.endsWith('.yml'));
    
    const rules: AutomationRuleYAML[] = [];
    
    for (const file of yamlFiles) {
      try {
        const filePath = path.join(directory, file);
        const rule = await this.parseRuleFile(filePath);
        rules.push(rule);
      } catch (error) {
        console.error(`Failed to parse ${file}:`, error);
      }
    }
    
    return rules;
  }

  /**
   * 转换为数据库格式
   */
  toDatabaseFormat(rule: AutomationRuleYAML) {
    return {
      name: rule.name,
      triggerType: rule.trigger.type,
      conditionsJson: {
        conditions: rule.conditions,
        event: rule.trigger.event,
        schedule: rule.trigger.schedule,
      },
      actionsJson: {
        actions: rule.actions,
      },
      enabled: true,
    };
  }

  /**
   * 验证规则格式
   */
  private validateRule(rule: any): void {
    if (!rule.name || typeof rule.name !== 'string') {
      throw new Error('Rule must have a name');
    }
    
    if (!rule.trigger || !rule.trigger.type) {
      throw new Error('Rule must have a trigger type');
    }
    
    if (!Array.isArray(rule.conditions)) {
      throw new Error('Conditions must be an array');
    }
    
    if (!Array.isArray(rule.actions)) {
      throw new Error('Actions must be an array');
    }
  }
}
