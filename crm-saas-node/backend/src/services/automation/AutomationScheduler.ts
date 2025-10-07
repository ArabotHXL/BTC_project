import * as cron from 'node-cron';
import { PrismaClient } from '@prisma/client';
import { RuleExecutor } from './RuleExecutor';

const prisma = new PrismaClient();

export class AutomationScheduler {
  private scheduledJobs: Map<string, ReturnType<typeof cron.schedule>> = new Map();
  private ruleExecutor: RuleExecutor;

  constructor() {
    this.ruleExecutor = new RuleExecutor();
  }

  /**
   * 启动所有SCHEDULED类型的规则
   */
  async start(): Promise<void> {
    const rules = await prisma.automationRule.findMany({
      where: {
        triggerType: 'SCHEDULED',
        enabled: true,
      },
    });

    for (const rule of rules) {
      this.scheduleRule(rule);
    }

    console.log(`✅ Started ${this.scheduledJobs.size} scheduled automation rules`);
  }

  /**
   * 调度单个规则
   */
  private scheduleRule(rule: any): void {
    const conditionsJson = rule.conditionsJson as any;
    const schedule = conditionsJson.schedule;

    if (!schedule || !cron.validate(schedule)) {
      console.error(`Invalid cron schedule for rule ${rule.name}: ${schedule}`);
      return;
    }

    const task = cron.schedule(schedule, async () => {
      try {
        console.log(`⏰ Executing scheduled rule: ${rule.name}`);
        
        // 对于SCHEDULED规则，需要查询符合条件的实体
        await this.executeScheduledRule(rule);
      } catch (error) {
        console.error(`Failed to execute scheduled rule ${rule.name}:`, error);
      }
    });

    this.scheduledJobs.set(rule.id, task);
  }

  /**
   * 执行定时规则（查询符合条件的实体）
   */
  private async executeScheduledRule(rule: any): Promise<void> {
    const conditionsJson = rule.conditionsJson as any;
    const conditions = conditionsJson.conditions as any[];
    
    const entityType = this.inferEntityType(conditions);
    
    if (!entityType) {
      console.warn(`Cannot infer entity type for rule ${rule.name}`);
      return;
    }
    
    const entities = await this.queryEntitiesByConditions(entityType, conditions);
    
    console.log(`Found ${entities.length} ${entityType}(s) matching rule ${rule.name}`);
    
    for (const entity of entities) {
      try {
        // 包装entity以匹配RuleExecutor期望的格式
        // RuleExecutor期望：{ invoice: { id, status, ... } }
        // queryEntitiesByConditions返回：{ id, status, ... }
        const wrappedEntity = {
          [entityType]: entity
        };
        
        await this.ruleExecutor.executeRule(
          rule.id,
          entityType,
          entity.id,
          wrappedEntity
        );
      } catch (error) {
        console.error(`Failed to execute rule for ${entityType} ${entity.id}:`, error);
      }
    }
  }

  /**
   * 推断实体类型（从条件字段）
   */
  private inferEntityType(conditions: any[]): string | null {
    for (const condition of conditions) {
      const field = condition.field;
      
      if (field.startsWith('lead.')) return 'lead';
      if (field.startsWith('deal.')) return 'deal';
      if (field.startsWith('invoice.')) return 'invoice';
      if (field.startsWith('account.')) return 'account';
      if (field.startsWith('shipment.')) return 'shipment';
      if (field.startsWith('asset.')) return 'asset';
      if (field.startsWith('payment.')) return 'payment';
    }
    
    return null;
  }

  /**
   * 根据条件查询实体
   */
  private async queryEntitiesByConditions(
    entityType: string,
    conditions: any[]
  ): Promise<any[]> {
    const where: any = {};
    const include: any = {};
    
    for (const condition of conditions) {
      const fullField = condition.field;
      const operator = condition.operator;
      const value = condition.value;
      
      // 移除实体前缀：lead.status → status
      const fieldPath = fullField.split('.').slice(1);
      
      if (fieldPath.length === 1) {
        // 直接字段
        const fieldName = this.toCamelCase(fieldPath[0]);
        this.mergeCondition(where, fieldName, operator, value);
      } else {
        // 嵌套关联字段：invoice.account.billing_email
        this.buildNestedWhere(where, include, fieldPath, operator, value);
      }
    }
    
    // 查询数据库
    const modelMap: Record<string, any> = {
      lead: prisma.lead,
      deal: prisma.deal,
      invoice: prisma.invoice,
      account: prisma.account,
      shipment: prisma.shipment,
      asset: prisma.minerAsset,
      payment: prisma.payment,
    };
    
    const model = modelMap[entityType];
    if (!model) {
      console.warn(`Unknown entity type: ${entityType}`);
      return [];
    }
    
    try {
      const queryOptions: any = { where };
      if (Object.keys(include).length > 0) {
        queryOptions.include = include;
      }
      
      return await model.findMany(queryOptions);
    } catch (error) {
      console.error(`Failed to query ${entityType}:`, error);
      return [];
    }
  }

  /**
   * 递归构建嵌套where和include
   */
  private buildNestedWhere(
    where: any,
    include: any,
    fieldPath: string[],
    operator: string,
    value: any
  ): void {
    if (fieldPath.length === 1) {
      // 叶子节点：应用条件
      const fieldName = this.toCamelCase(fieldPath[0]);
      this.mergeCondition(where, fieldName, operator, value);
    } else {
      // 中间节点：递归构建
      const relationName = this.toCamelCase(fieldPath[0]); // camelCase关系名
      const remainingPath = fieldPath.slice(1);
      
      // 确定关系类型（to-one使用is，to-many使用some）
      // 简化：假设单数=to-one，复数=to-many
      const isToMany = relationName.endsWith('s') && !relationName.endsWith('ss');
      const filterKey = isToMany ? 'some' : 'is';
      
      if (!where[relationName]) {
        where[relationName] = { [filterKey]: {} };
      }
      if (!include[relationName]) {
        include[relationName] = true;
      }
      
      // 如果include[relationName]是true，需要转换为对象以支持嵌套include
      if (include[relationName] === true && remainingPath.length > 1) {
        include[relationName] = { include: {} };
      }
      
      const nestedInclude = typeof include[relationName] === 'object' 
        ? (include[relationName].include || {})
        : {};
      
      this.buildNestedWhere(
        where[relationName][filterKey],  // 递归到is/some内部
        nestedInclude,
        remainingPath,
        operator,
        value
      );
      
      if (typeof include[relationName] === 'object') {
        include[relationName].include = nestedInclude;
      }
    }
  }

  /**
   * 合并条件（支持多条件）
   */
  private mergeCondition(where: any, field: string, operator: string, value: any): void {
    const condition = this.buildCondition(operator, value);
    
    if (!where[field]) {
      where[field] = condition;
    } else if (typeof where[field] === 'object' && typeof condition === 'object') {
      // 合并对象条件：{ gt: 10 } + { lt: 100 } → { gt: 10, lt: 100 }
      where[field] = { ...where[field], ...condition };
    } else {
      // 冲突的条件（如equals + equals），使用AND
      where.AND = where.AND || [];
      where.AND.push({ [field]: condition });
    }
  }

  /**
   * 构建单个条件对象
   */
  private buildCondition(operator: string, value: any): any {
    switch (operator) {
      case 'equals':
        return value;
      case 'not_equals':
        return { not: value };
      case 'greater_than':
        return { gt: value };
      case 'greater_than_or_equal':
        return { gte: value };
      case 'less_than':
        return { lt: value };
      case 'in':
        return { in: value };
      case 'is_null':
        return null;
      case 'is_not_null':
        return { not: null };
      case 'older_than':
        return { lt: this.parseOlderThan(value) };
      case 'before':
        return { lt: this.parseDate(value) };
      case 'is_today':
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        const tomorrow = new Date(today);
        tomorrow.setDate(tomorrow.getDate() + 1);
        return { gte: today, lt: tomorrow };
      default:
        console.warn(`Unknown operator: ${operator}`);
        return value;
    }
  }

  /**
   * 转换为camelCase（snake_case → camelCase）
   */
  private toCamelCase(str: string): string {
    return str.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase());
  }

  /**
   * 解析older_than时间字符串
   */
  private parseOlderThan(duration: string): Date {
    const match = duration.match(/^(\d+)([hdwm])$/);
    if (!match) return new Date();
    
    const [, amount, unit] = match;
    const now = new Date();
    const milliseconds = {
      h: 3600000,
      d: 86400000,
      w: 604800000,
      m: 2592000000,
    }[unit] || 0;
    
    return new Date(now.getTime() - parseInt(amount) * milliseconds);
  }

  /**
   * 解析日期字符串
   */
  private parseDate(value: string): Date {
    if (value === 'today') {
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      return today;
    }
    
    return new Date(value);
  }

  /**
   * 停止所有定时任务
   */
  stop(): void {
    for (const [ruleId, task] of this.scheduledJobs) {
      task.stop();
    }
    this.scheduledJobs.clear();
    console.log('⏹️ Stopped all scheduled automation rules');
  }

  /**
   * 重新加载规则（停止并重新启动）
   */
  async reload(): Promise<void> {
    this.stop();
    await this.start();
  }
}
