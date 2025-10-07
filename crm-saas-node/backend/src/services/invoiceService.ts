import { PrismaClient, Invoice, InvoiceStatus, InvoiceLineItemType, Prisma } from '@prisma/client';
import {
  CreateInvoiceDTO,
  UpdateInvoiceDTO,
  LineItemDTO,
  PaymentDTO,
  PaginatedResponse,
  InvoiceFilters,
  PaginationParams,
  NetRevenueBreakdown,
  AgingReport,
} from '../types';
import { eventPublisher, EventType } from '../events/publisher';

const prisma = new PrismaClient();

export class InvoiceService {
  private async generateInvoiceNumber(): Promise<string> {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    
    const lastInvoice = await prisma.invoice.findFirst({
      where: {
        invoiceNumber: {
          startsWith: `INV-${year}-${month}`,
        },
      },
      orderBy: {
        createdAt: 'desc',
      },
    });

    let sequence = 1;
    if (lastInvoice) {
      const lastSequence = parseInt(lastInvoice.invoiceNumber.split('-')[3]);
      sequence = lastSequence + 1;
    }

    return `INV-${year}-${month}-${String(sequence).padStart(5, '0')}`;
  }

  async getInvoices(
    filters: InvoiceFilters = {},
    pagination: PaginationParams = {}
  ): Promise<PaginatedResponse<Invoice>> {
    const { page = 1, pageSize = 20, sortBy = 'createdAt', sortOrder = 'desc' } = pagination;
    const skip = (page - 1) * pageSize;

    const where: Prisma.InvoiceWhereInput = {};
    
    if (filters.status) where.status = filters.status;
    if (filters.accountId) where.accountId = filters.accountId;
    if (filters.dueDateFrom || filters.dueDateTo) {
      where.dueDate = {};
      if (filters.dueDateFrom) where.dueDate.gte = new Date(filters.dueDateFrom);
      if (filters.dueDateTo) where.dueDate.lte = new Date(filters.dueDateTo);
    }

    const [invoices, total] = await Promise.all([
      prisma.invoice.findMany({
        where,
        skip,
        take: pageSize,
        orderBy: { [sortBy]: sortOrder },
        include: {
          account: {
            select: {
              id: true,
              name: true,
            },
          },
          lineItems: true,
          payments: true,
        },
      }),
      prisma.invoice.count({ where }),
    ]);

    return {
      data: invoices,
      pagination: {
        page,
        pageSize,
        total,
        totalPages: Math.ceil(total / pageSize),
      },
    };
  }

  async getInvoiceById(id: string): Promise<Invoice> {
    const invoice = await prisma.invoice.findUnique({
      where: { id },
      include: {
        account: true,
        contract: true,
        lineItems: true,
        payments: true,
      },
    });

    if (!invoice) {
      throw new Error('Invoice not found');
    }

    return invoice;
  }

  async getInvoicesByAccount(accountId: string): Promise<Invoice[]> {
    return prisma.invoice.findMany({
      where: { accountId },
      include: {
        lineItems: true,
        payments: true,
      },
      orderBy: {
        createdAt: 'desc',
      },
    });
  }

  async getOverdueInvoices(): Promise<Invoice[]> {
    const now = new Date();
    
    const invoices = await prisma.invoice.findMany({
      where: {
        status: { in: [InvoiceStatus.ISSUED, InvoiceStatus.PARTIAL, InvoiceStatus.OVERDUE] },
        dueDate: { lt: now },
      },
      include: {
        account: true,
        lineItems: true,
      },
      orderBy: {
        dueDate: 'asc',
      },
    });

    return invoices.filter(inv => 
      Number(inv.amountPaid) < Number(inv.totalAmount)
    );
  }

  async getAgingReport(): Promise<AgingReport> {
    const now = new Date();
    
    const invoices = await prisma.invoice.findMany({
      where: {
        status: { in: [InvoiceStatus.ISSUED, InvoiceStatus.PARTIAL, InvoiceStatus.OVERDUE] },
      },
      include: { account: true },
    });

    const aging: AgingReport = {
      current: 0,
      age30: 0,
      age60: 0,
      age90Plus: 0,
      total: 0,
    };

    for (const inv of invoices) {
      const outstanding = Number(inv.totalAmount) - Number(inv.amountPaid);
      
      if (outstanding <= 0) continue;
      
      const daysOverdue = Math.floor((now.getTime() - inv.dueDate.getTime()) / (1000 * 60 * 60 * 24));
      
      if (daysOverdue <= 30) {
        aging.current += outstanding;
      } else if (daysOverdue <= 60) {
        aging.age30 += outstanding;
      } else if (daysOverdue <= 90) {
        aging.age60 += outstanding;
      } else {
        aging.age90Plus += outstanding;
      }
      
      aging.total += outstanding;
    }

    return aging;
  }

  async createInvoice(data: CreateInvoiceDTO): Promise<Invoice> {
    const invoiceNumber = await this.generateInvoiceNumber();
    const totalAmount = data.items.reduce((sum, item) => sum + item.total, 0);

    const invoice = await prisma.invoice.create({
      data: {
        accountId: data.accountId,
        contractId: data.contractId,
        invoiceNumber,
        issueDate: new Date(),
        dueDate: new Date(data.dueDate),
        totalAmount,
        amountPaid: 0,
        status: InvoiceStatus.DRAFT,
        lineItems: {
          create: data.items.map(item => ({
            type: item.type,
            description: item.description,
            quantity: item.quantity,
            unitPrice: item.unitPrice,
            amount: item.total,
          })),
        },
      },
      include: {
        account: true,
        lineItems: true,
      },
    });

    await eventPublisher.publish(EventType.INVOICE_CREATED, {
      id: invoice.id,
      entityType: 'INVOICE',
      accountId: invoice.accountId,
      invoiceNumber: invoice.invoiceNumber,
      totalAmount: invoice.totalAmount,
    });

    return invoice;
  }

  async createFromDeal(dealId: string): Promise<Invoice> {
    const deal = await prisma.deal.findUnique({
      where: { id: dealId },
      include: {
        account: true,
      },
    });

    if (!deal) {
      throw new Error('Deal not found');
    }

    if (deal.stage !== 'CLOSED_WON') {
      throw new Error('Deal must be CLOSED_WON to generate invoice');
    }

    const invoiceNumber = await this.generateInvoiceNumber();
    const dueDate = new Date();
    dueDate.setDate(dueDate.getDate() + 30);

    const invoice = await prisma.invoice.create({
      data: {
        accountId: deal.accountId,
        invoiceNumber,
        issueDate: new Date(),
        dueDate,
        totalAmount: deal.value,
        amountPaid: 0,
        status: InvoiceStatus.DRAFT,
        lineItems: {
          create: [
            {
              type: InvoiceLineItemType.OTHER,
              description: `Invoice for Deal: ${deal.title}`,
              quantity: 1,
              unitPrice: deal.value,
              amount: deal.value,
            },
          ],
        },
      },
      include: {
        account: true,
        lineItems: true,
      },
    });

    await eventPublisher.publish(EventType.INVOICE_CREATED, {
      id: invoice.id,
      entityType: 'INVOICE',
      accountId: invoice.accountId,
      invoiceNumber: invoice.invoiceNumber,
      dealId: deal.id,
    });

    return invoice;
  }

  async updateInvoice(id: string, data: UpdateInvoiceDTO): Promise<Invoice> {
    const invoice = await prisma.invoice.update({
      where: { id },
      data: {
        ...(data.dueDate && { dueDate: new Date(data.dueDate) }),
        ...(data.status && { status: data.status }),
      },
      include: {
        account: true,
        lineItems: true,
        payments: true,
      },
    });

    return invoice;
  }

  async addLineItem(id: string, item: LineItemDTO): Promise<Invoice> {
    const invoice = await this.getInvoiceById(id);

    if (invoice.status !== InvoiceStatus.DRAFT) {
      throw new Error('Can only add line items to draft invoices');
    }

    await prisma.invoiceLineItem.create({
      data: {
        invoiceId: id,
        type: item.type,
        description: item.description,
        quantity: item.quantity,
        unitPrice: item.unitPrice,
        amount: item.total,
      },
    });

    return this.recalculateAll(id);
  }

  async removeLineItem(invoiceId: string, lineItemId: string): Promise<Invoice> {
    const invoice = await this.getInvoiceById(invoiceId);

    if (invoice.status !== InvoiceStatus.DRAFT) {
      throw new Error('Can only remove line items from draft invoices');
    }

    await prisma.invoiceLineItem.delete({
      where: { id: lineItemId },
    });

    return this.recalculateAll(invoiceId);
  }

  async issueInvoice(id: string): Promise<Invoice> {
    const invoice = await this.getInvoiceById(id);

    if (invoice.status !== InvoiceStatus.DRAFT) {
      throw new Error('Only draft invoices can be issued');
    }

    const updatedInvoice = await prisma.invoice.update({
      where: { id },
      data: {
        status: InvoiceStatus.ISSUED,
        issueDate: new Date(),
      },
      include: {
        account: true,
        lineItems: true,
      },
    });

    await eventPublisher.publish(EventType.INVOICE_ISSUED, {
      id: updatedInvoice.id,
      entityType: 'INVOICE',
      accountId: updatedInvoice.accountId,
      invoiceNumber: updatedInvoice.invoiceNumber,
    });

    return updatedInvoice;
  }

  async sendInvoice(id: string, email: string): Promise<boolean> {
    const invoice = await this.getInvoiceById(id);

    console.log(`Sending invoice ${invoice.invoiceNumber} to ${email}`);
    
    return true;
  }

  async voidInvoice(id: string, reason: string): Promise<Invoice> {
    const invoice = await this.getInvoiceById(id);

    if (invoice.status === InvoiceStatus.PAID) {
      throw new Error('Cannot void a paid invoice');
    }

    const updatedInvoice = await prisma.invoice.update({
      where: { id },
      data: {
        status: InvoiceStatus.CANCELLED,
      },
      include: {
        account: true,
        lineItems: true,
      },
    });

    return updatedInvoice;
  }

  async markAsPaid(id: string, paymentData: PaymentDTO): Promise<Invoice> {
    const invoice = await this.getInvoiceById(id);

    const updatedInvoice = await prisma.invoice.update({
      where: { id },
      data: {
        amountPaid: Number(invoice.totalAmount),
        status: InvoiceStatus.PAID,
      },
      include: {
        account: true,
        lineItems: true,
        payments: true,
      },
    });

    await eventPublisher.publish(EventType.INVOICE_PAID, {
      id: updatedInvoice.id,
      entityType: 'INVOICE',
      accountId: updatedInvoice.accountId,
      invoiceNumber: updatedInvoice.invoiceNumber,
      amount: updatedInvoice.totalAmount,
    });

    return updatedInvoice;
  }

  async calculateTotal(invoiceId: string): Promise<number> {
    const invoice = await prisma.invoice.findUnique({
      where: { id: invoiceId },
      include: { lineItems: true },
    });

    if (!invoice) {
      throw new Error('Invoice not found');
    }

    return invoice.lineItems.reduce((sum: number, item: any) => sum + Number(item.amount), 0);
  }

  async calculateNetRevenue(invoiceId: string): Promise<NetRevenueBreakdown> {
    const invoice = await prisma.invoice.findUnique({
      where: { id: invoiceId },
      include: { lineItems: true },
    });

    if (!invoice) {
      throw new Error('Invoice not found');
    }

    let miningOutput = 0;
    let electricityCost = 0;
    let serviceFee = 0;

    for (const item of invoice.lineItems) {
      const amount = Number(item.amount);
      switch (item.type) {
        case InvoiceLineItemType.MINING_OUTPUT:
          miningOutput += amount;
          break;
        case InvoiceLineItemType.ELECTRICITY:
          electricityCost += amount;
          break;
        case InvoiceLineItemType.SERVICE_FEE:
          serviceFee += amount;
          break;
      }
    }

    const netRevenue = miningOutput - electricityCost - serviceFee;
    const margin = miningOutput > 0 ? (netRevenue / miningOutput) * 100 : 0;

    return {
      miningOutput,
      electricityCost,
      serviceFee,
      netRevenue,
      margin,
    };
  }

  async recalculateAll(invoiceId: string): Promise<Invoice> {
    const total = await this.calculateTotal(invoiceId);

    const invoice = await prisma.invoice.update({
      where: { id: invoiceId },
      data: {
        totalAmount: total,
      },
      include: {
        account: true,
        lineItems: true,
        payments: true,
      },
    });

    return invoice;
  }
}

export const invoiceService = new InvoiceService();
