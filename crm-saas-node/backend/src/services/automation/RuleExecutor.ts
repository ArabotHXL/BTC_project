import { PrismaClient, AutomationStatus } from '@prisma/client';

const prisma = new PrismaClient();

interface RuleCondition {
  field: string;
  operator: string;
  value: any;
}

interface RuleAction {
  type: string;
  params: Record<string, any>;
}

export class RuleExecutor {
  /**
   * 执行自动化规则
   */
  async executeRule(
    ruleId: string,
    entityType: string,
    entityId: string,
    entityData: any
  ): Promise<void> {
    const rule = await prisma.automationRule.findUnique({
      where: { id: ruleId },
    });

    if (!rule || !rule.enabled) {
      return;
    }

    try {
      // 检查条件
      const conditionsJson = rule.conditionsJson as any;
      const conditions = conditionsJson.conditions as RuleCondition[];
      
      if (!this.evaluateConditions(conditions, entityData)) {
        await this.logExecution(ruleId, entityType, entityId, 'SKIPPED', 'Conditions not met');
        return;
      }

      // 执行动作
      const actionsJson = rule.actionsJson as any;
      const actions = actionsJson.actions as RuleAction[];
      
      for (const action of actions) {
        await this.executeAction(action, entityData);
      }

      // 更新lastRun
      await prisma.automationRule.update({
        where: { id: ruleId },
        data: { lastRun: new Date() },
      });

      await this.logExecution(ruleId, entityType, entityId, 'SUCCESS');
    } catch (error: any) {
      await this.logExecution(ruleId, entityType, entityId, 'FAILED', error.message);
      throw error;
    }
  }

  /**
   * 评估条件
   */
  private evaluateConditions(conditions: RuleCondition[], data: any): boolean {
    for (const condition of conditions) {
      const value = this.getFieldValue(condition.field, data);
      
      if (!this.evaluateCondition(condition.operator, value, condition.value)) {
        return false;
      }
    }
    
    return true;
  }

  /**
   * 评估单个条件
   */
  private evaluateCondition(operator: string, actual: any, expected: any): boolean {
    switch (operator) {
      case 'equals':
        return actual === expected;
      case 'not_equals':
        return actual !== expected;
      case 'greater_than':
        return actual > expected;
      case 'less_than':
        return actual < expected;
      case 'greater_than_or_equal':
        return actual >= expected;
      case 'contains':
        return String(actual).includes(expected);
      case 'in':
        return Array.isArray(expected) && expected.includes(actual);
      case 'not_in':
        return Array.isArray(expected) && !expected.includes(actual);
      case 'is_null':
        return actual == null;
      case 'is_not_null':
        return actual != null;
      case 'older_than':
        return this.isOlderThan(actual, expected);
      case 'before':
        return this.isBefore(actual, expected);
      case 'is_today':
        return this.isToday(actual);
      default:
        console.warn(`Unknown operator: ${operator}`);
        return false;
    }
  }

  /**
   * 执行动作
   */
  private async executeAction(action: RuleAction, data: any): Promise<void> {
    console.log(`Executing action: ${action.type}`, action.params);
    
    switch (action.type) {
      case 'send_email':
        await this.sendEmail(action.params, data);
        break;
      case 'update_field':
        await this.updateField(action.params, data);
        break;
      case 'create_notification':
        await this.createNotification(action.params, data);
        break;
      case 'create_task':
        await this.createTask(action.params, data);
        break;
      case 'assign_round_robin':
        await this.assignRoundRobin(action.params, data);
        break;
      case 'create_invoice':
        await this.createInvoice(action.params, data);
        break;
      case 'release_reserved_assets':
        await this.releaseReservedAssets(action.params, data);
        break;
      case 'start_mining_monitoring':
        await this.startMiningMonitoring(action.params, data);
        break;
      case 'trigger_fulfillment':
        await this.triggerFulfillment(action.params, data);
        break;
      case 'create_ticket':
        await this.createTicket(action.params, data);
        break;
      case 'apply_discount':
        await this.applyDiscount(action.params, data);
        break;
      case 'update_payment_invoice_deal':
        await this.updatePaymentInvoiceDeal(action.params, data);
        break;
      default:
        console.warn(`Unknown action type: ${action.type}`);
    }
  }

  /**
   * 辅助方法 - 获取字段值
   */
  private getFieldValue(field: string, data: any): any {
    const parts = field.split('.');
    let value = data;
    
    for (const part of parts) {
      // 总是转换为camelCase（Prisma实体格式）
      const camelCasePart = part.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase());
      
      // 优先尝试camelCase（Prisma）
      if (value?.[camelCasePart] !== undefined) {
        value = value[camelCasePart];
      } else if (value?.[part] !== undefined) {
        // fallback到原始名称
        value = value[part];
      } else {
        // 都找不到
        return undefined;
      }
    }
    
    return value;
  }

  /**
   * 辅助方法 - 检查日期是否早于指定时长
   */
  private isOlderThan(date: Date | string, duration: string): boolean {
    if (!date) return false;
    
    const targetDate = new Date(date);
    const now = new Date();
    const diff = now.getTime() - targetDate.getTime();
    
    const match = duration.match(/^(\d+)([hdwm])$/);
    if (!match) return false;
    
    const [, amount, unit] = match;
    const milliseconds = {
      h: 3600000,
      d: 86400000,
      w: 604800000,
      m: 2592000000,
    }[unit] || 0;
    
    return diff > parseInt(amount) * milliseconds;
  }

  /**
   * 辅助方法 - 检查日期是否在某个日期之前
   */
  private isBefore(date: Date | string, reference: string): boolean {
    if (!date) return false;
    
    const targetDate = new Date(date);
    const referenceDate = reference === 'today' ? new Date() : new Date(reference);
    
    return targetDate < referenceDate;
  }

  /**
   * 辅助方法 - 检查是否是今天
   */
  private isToday(date: Date | string): boolean {
    if (!date) return false;
    
    const targetDate = new Date(date);
    const today = new Date();
    
    return targetDate.getDate() === today.getDate() &&
           targetDate.getMonth() === today.getMonth() &&
           targetDate.getFullYear() === today.getFullYear();
  }

  /**
   * 记录执行日志
   */
  private async logExecution(
    ruleId: string,
    entityType: string,
    entityId: string,
    status: AutomationStatus,
    errorMessage?: string
  ): Promise<void> {
    await prisma.automationLog.create({
      data: {
        ruleId,
        entityType: entityType as any,
        entityId,
        status,
        errorMessage,
        executedAt: new Date(),
      },
    });
  }

  // ==========================================
  // Action handlers (placeholder implementations)
  // ==========================================

  private async sendEmail(params: any, data: any) {
    console.log('📧 Sending email:', params);
    // TODO: Implement email sending logic
  }

  private async updateField(params: any, data: any) {
    console.log('🔄 Updating field:', params);
    // TODO: Implement field update logic
  }

  private async createNotification(params: any, data: any) {
    console.log('🔔 Creating notification:', params);
    // TODO: Implement notification creation
  }

  private async createTask(params: any, data: any) {
    console.log('📝 Creating task:', params);
    // TODO: Implement task creation
  }

  private async assignRoundRobin(params: any, data: any) {
    console.log('👥 Assigning round-robin:', params);
    // TODO: Implement round-robin assignment
  }

  private async createInvoice(params: any, data: any) {
    console.log('💰 Creating invoice:', params);
    // TODO: Implement invoice creation
  }

  private async releaseReservedAssets(params: any, data: any) {
    console.log('📦 Releasing reserved assets:', params);
    // TODO: Implement asset release
  }

  private async startMiningMonitoring(params: any, data: any) {
    console.log('⛏️ Starting mining monitoring:', params);
    // TODO: Implement mining monitoring
  }

  private async triggerFulfillment(params: any, data: any) {
    console.log('🚀 Triggering fulfillment:', params);
    // TODO: Implement fulfillment trigger
  }

  private async createTicket(params: any, data: any) {
    console.log('🎫 Creating ticket:', params);
    // TODO: Implement ticket creation
  }

  private async applyDiscount(params: any, data: any) {
    console.log('🎁 Applying discount:', params);
    // TODO: Implement discount application
  }

  private async updatePaymentInvoiceDeal(params: any, data: any): Promise<void> {
    const paymentId = params.payment_id || data.id;
    
    // 查询payment及其关联的invoice和contract.deal
    const payment = await prisma.payment.findUnique({
      where: { id: paymentId },
      include: {
        invoice: {
          include: {
            contract: {
              include: {
                deal: true,
              },
            },
          },
        },
      },
    });
    
    if (!payment || !payment.invoice) {
      console.warn('Payment or invoice not found');
      return;
    }
    
    const invoice = payment.invoice;
    
    // 检查是否全额支付
    if (invoice.amountPaid >= invoice.totalAmount) {
      // 更新Invoice状态
      await prisma.invoice.update({
        where: { id: invoice.id },
        data: { status: 'PAID' },
      });
      
      // 更新关联的Deal（如果存在）
      if (invoice.contract?.deal) {
        await prisma.deal.update({
          where: { id: invoice.contract.deal.id },
          data: { stage: 'CLOSED_WON' },
        });
        
        console.log(`Updated invoice ${invoice.id} and deal ${invoice.contract.deal.id} for payment ${paymentId}`);
      } else {
        console.log(`Updated invoice ${invoice.id} for payment ${paymentId}`);
      }
    }
  }
}
