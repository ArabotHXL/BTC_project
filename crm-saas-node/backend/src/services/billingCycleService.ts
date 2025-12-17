import { PrismaClient, BillingCycle, Invoice, InvoiceLineItemType } from '@prisma/client';
import { CreateBillingCycleDTO } from '../types';
import { invoiceService } from './invoiceService';

const prisma = new PrismaClient();

export class BillingCycleService {
  async getBillingCycles(filters: { contractId?: string } = {}): Promise<BillingCycle[]> {
    const where: any = {};
    
    if (filters.contractId) where.contractId = filters.contractId;

    return prisma.billingCycle.findMany({
      where,
      include: {
        contract: {
          include: {
            account: true,
          },
        },
      },
      orderBy: {
        startDate: 'desc',
      },
    });
  }

  async getActiveCycles(): Promise<BillingCycle[]> {
    const now = new Date();
    
    return prisma.billingCycle.findMany({
      where: {
        startDate: {
          lte: now,
        },
        endDate: {
          gte: now,
        },
      },
      include: {
        contract: {
          include: {
            account: true,
          },
        },
      },
    });
  }

  async createBillingCycle(data: CreateBillingCycleDTO): Promise<BillingCycle> {
    const contract = await prisma.contract.findUnique({
      where: { id: data.contractId },
    });

    if (!contract) {
      throw new Error('Contract not found');
    }

    const billingCycle = await prisma.billingCycle.create({
      data: {
        contractId: data.contractId,
        startDate: new Date(data.startDate),
        endDate: new Date(data.endDate),
        btcProduced: data.btcProduced,
        powerConsumed: data.powerConsumed,
        serviceFee: data.serviceFee,
      },
      include: {
        contract: {
          include: {
            account: true,
          },
        },
      },
    });

    return billingCycle;
  }

  async closeBillingCycle(id: string): Promise<BillingCycle> {
    const cycle = await prisma.billingCycle.findUnique({
      where: { id },
      include: {
        contract: true,
      },
    });

    if (!cycle) {
      throw new Error('Billing cycle not found');
    }

    const now = new Date();
    const updatedCycle = await prisma.billingCycle.update({
      where: { id },
      data: {
        endDate: now,
      },
      include: {
        contract: {
          include: {
            account: true,
          },
        },
      },
    });

    return updatedCycle;
  }

  async generateInvoicesForCycle(cycleId: string): Promise<Invoice[]> {
    const cycle = await prisma.billingCycle.findUnique({
      where: { id: cycleId },
      include: {
        contract: {
          include: {
            account: true,
          },
        },
      },
    });

    if (!cycle) {
      throw new Error('Billing cycle not found');
    }

    const lineItems = [];

    if (cycle.btcProduced) {
      const btcPrice = 50000;
      lineItems.push({
        type: InvoiceLineItemType.MINING_OUTPUT,
        description: `BTC Mining Output (${cycle.btcProduced} BTC)`,
        quantity: Number(cycle.btcProduced),
        unitPrice: btcPrice,
        total: Number(cycle.btcProduced) * btcPrice,
      });
    }

    if (cycle.powerConsumed) {
      lineItems.push({
        type: InvoiceLineItemType.ELECTRICITY,
        description: `Electricity Cost (${cycle.powerConsumed} kWh)`,
        quantity: Number(cycle.powerConsumed),
        unitPrice: 0.1,
        total: Number(cycle.powerConsumed) * 0.1,
      });
    }

    if (cycle.serviceFee) {
      lineItems.push({
        type: InvoiceLineItemType.SERVICE_FEE,
        description: 'Monthly Service Fee',
        quantity: 1,
        unitPrice: Number(cycle.serviceFee),
        total: Number(cycle.serviceFee),
      });
    }

    if (lineItems.length === 0) {
      throw new Error('No billing data available for this cycle');
    }

    const dueDate = new Date(cycle.endDate);
    dueDate.setDate(dueDate.getDate() + 30);

    const invoice = await invoiceService.createInvoice({
      accountId: cycle.contract.accountId,
      contractId: cycle.contractId,
      dueDate: dueDate.toISOString(),
      items: lineItems,
      notes: `Auto-generated invoice for billing cycle ${cycle.startDate.toISOString().split('T')[0]} to ${cycle.endDate.toISOString().split('T')[0]}`,
    });

    return [invoice];
  }

  async autoGenerateMonthlyInvoices(): Promise<number> {
    const lastMonth = new Date();
    lastMonth.setMonth(lastMonth.getMonth() - 1);
    lastMonth.setDate(1);

    const lastMonthEnd = new Date(lastMonth);
    lastMonthEnd.setMonth(lastMonthEnd.getMonth() + 1);
    lastMonthEnd.setDate(0);

    const cycles = await prisma.billingCycle.findMany({
      where: {
        endDate: {
          gte: lastMonth,
          lte: lastMonthEnd,
        },
      },
      include: {
        contract: true,
      },
    });

    let count = 0;
    for (const cycle of cycles) {
      try {
        await this.generateInvoicesForCycle(cycle.id);
        count++;
      } catch (error) {
        console.error(`Failed to generate invoice for cycle ${cycle.id}:`, error);
      }
    }

    return count;
  }
}

export const billingCycleService = new BillingCycleService();
