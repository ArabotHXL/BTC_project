import { PrismaClient, Payment, PaymentStatus, Prisma } from '@prisma/client';
import {
  CreatePaymentDTO,
  UpdatePaymentDTO,
  PaymentDTO,
  PaginatedResponse,
  PaymentFilters,
  PaginationParams,
  TreasuryStatus,
} from '../types';
import { eventPublisher, EventType } from '../events/publisher';

const prisma = new PrismaClient();

export class PaymentService {
  async getPayments(
    filters: PaymentFilters = {},
    pagination: PaginationParams = {}
  ): Promise<PaginatedResponse<Payment>> {
    const { page = 1, pageSize = 20, sortBy = 'createdAt', sortOrder = 'desc' } = pagination;
    const skip = (page - 1) * pageSize;

    const where: Prisma.PaymentWhereInput = {};
    
    if (filters.status) where.status = filters.status;
    if (filters.method) where.method = filters.method;
    if (filters.invoiceId) where.invoiceId = filters.invoiceId;
    if (filters.accountId) {
      where.invoice = {
        accountId: filters.accountId,
      };
    }

    const [payments, total] = await Promise.all([
      prisma.payment.findMany({
        where,
        skip,
        take: pageSize,
        orderBy: { [sortBy]: sortOrder },
        include: {
          invoice: {
            include: {
              account: {
                select: {
                  id: true,
                  name: true,
                },
              },
            },
          },
        },
      }),
      prisma.payment.count({ where }),
    ]);

    return {
      data: payments,
      pagination: {
        page,
        pageSize,
        total,
        totalPages: Math.ceil(total / pageSize),
      },
    };
  }

  async getPaymentById(id: string): Promise<Payment> {
    const payment = await prisma.payment.findUnique({
      where: { id },
      include: {
        invoice: {
          include: {
            account: true,
          },
        },
      },
    });

    if (!payment) {
      throw new Error('Payment not found');
    }

    return payment;
  }

  async getPaymentsByInvoice(invoiceId: string): Promise<Payment[]> {
    return prisma.payment.findMany({
      where: { invoiceId },
      orderBy: {
        createdAt: 'desc',
      },
    });
  }

  async getPaymentsByAccount(accountId: string): Promise<Payment[]> {
    return prisma.payment.findMany({
      where: {
        invoice: {
          accountId,
        },
      },
      include: {
        invoice: true,
      },
      orderBy: {
        createdAt: 'desc',
      },
    });
  }

  async createPayment(data: CreatePaymentDTO): Promise<Payment> {
    const invoice = await prisma.invoice.findUnique({
      where: { id: data.invoiceId },
    });

    if (!invoice) {
      throw new Error('Invoice not found');
    }

    const payment = await prisma.payment.create({
      data: {
        invoiceId: data.invoiceId,
        amount: data.amount,
        method: data.method,
        reference: data.reference,
        paymentDate: data.paymentDate ? new Date(data.paymentDate) : new Date(),
        status: PaymentStatus.PENDING,
      },
      include: {
        invoice: true,
      },
    });

    await eventPublisher.publish(EventType.PAYMENT_RECEIVED, {
      id: payment.id,
      entityType: 'PAYMENT',
      invoiceId: payment.invoiceId,
      amount: payment.amount,
    });

    return payment;
  }

  async updatePayment(id: string, data: UpdatePaymentDTO): Promise<Payment> {
    const payment = await prisma.payment.update({
      where: { id },
      data: {
        ...(data.amount && { amount: data.amount }),
        ...(data.method && { method: data.method }),
        ...(data.reference !== undefined && { reference: data.reference }),
        ...(data.status && { status: data.status }),
      },
      include: {
        invoice: true,
      },
    });

    return payment;
  }

  async recordPayment(invoiceId: string, data: PaymentDTO): Promise<Payment> {
    const invoice = await prisma.invoice.findUnique({
      where: { id: invoiceId },
    });

    if (!invoice) {
      throw new Error('Invoice not found');
    }

    const payment = await prisma.payment.create({
      data: {
        invoiceId,
        amount: data.amount,
        method: data.method,
        reference: data.reference,
        paymentDate: data.paidAt ? new Date(data.paidAt) : new Date(),
        status: PaymentStatus.PENDING,
      },
      include: {
        invoice: true,
      },
    });

    return payment;
  }

  async confirmPayment(id: string): Promise<Payment> {
    const existingPayment = await prisma.payment.findUnique({
      where: { id },
      include: { invoice: true },
    });

    if (!existingPayment) {
      throw new Error('Payment not found');
    }

    if (existingPayment.status !== PaymentStatus.PENDING) {
      throw new Error('Payment is not in PENDING status');
    }

    const payment = await prisma.payment.update({
      where: { id },
      data: { 
        status: PaymentStatus.CONFIRMED
      },
      include: { invoice: true },
    });

    await this.syncToTreasury(id);

    const invoice = payment.invoice;
    const newAmountPaid = Number(invoice.amountPaid) + Number(payment.amount);
    
    let newStatus = invoice.status;
    if (newAmountPaid >= Number(invoice.totalAmount)) {
      newStatus = 'PAID';
    } else if (newAmountPaid > 0 && invoice.status === 'ISSUED') {
      newStatus = 'PARTIAL';
    }

    await prisma.invoice.update({
      where: { id: invoice.id },
      data: {
        amountPaid: newAmountPaid,
        status: newStatus,
      },
    });

    await eventPublisher.publish(EventType.PAYMENT_CONFIRMED, {
      id: payment.id,
      entityType: 'PAYMENT',
      invoiceId: payment.invoiceId,
      amount: payment.amount,
    });

    return payment;
  }

  async rejectPayment(id: string, reason: string): Promise<Payment> {
    const payment = await this.getPaymentById(id);

    if (payment.status !== PaymentStatus.PENDING) {
      throw new Error('Only pending payments can be rejected');
    }

    const updatedPayment = await prisma.payment.update({
      where: { id },
      data: {
        status: PaymentStatus.REJECTED,
      },
      include: {
        invoice: true,
      },
    });

    return updatedPayment;
  }

  async refundPayment(id: string, amount: number): Promise<Payment> {
    const payment = await this.getPaymentById(id);

    if (payment.status !== PaymentStatus.CONFIRMED && payment.status !== PaymentStatus.CLEARED) {
      throw new Error('Only confirmed or cleared payments can be refunded');
    }

    if (amount > Number(payment.amount)) {
      throw new Error('Refund amount cannot exceed payment amount');
    }

    const updatedPayment = await prisma.payment.update({
      where: { id },
      data: {
        status: PaymentStatus.REFUNDED,
      },
      include: {
        invoice: true,
      },
    });

    const invoice = await prisma.invoice.findUnique({
      where: { id: payment.invoiceId },
      include: { payments: true },
    });

    if (invoice) {
      const totalPaid = invoice.payments
        .filter(p => [PaymentStatus.CONFIRMED, PaymentStatus.CLEARED, PaymentStatus.COMPLETED].includes(p.status))
        .reduce((sum, p) => sum + Number(p.amount), 0);

      let newStatus: string;
      if (totalPaid >= Number(invoice.totalAmount)) {
        newStatus = 'PAID';
      } else if (totalPaid > 0) {
        newStatus = 'PARTIAL';
      } else {
        newStatus = 'ISSUED';
      }

      await prisma.invoice.update({
        where: { id: payment.invoiceId },
        data: {
          amountPaid: totalPaid,
          status: newStatus,
        },
      });
    }

    await eventPublisher.publish(EventType.PAYMENT_REFUNDED, {
      id: updatedPayment.id,
      entityType: 'PAYMENT',
      invoiceId: updatedPayment.invoiceId,
      amount: amount,
    });

    return updatedPayment;
  }

  async allocatePayment(id: string, invoiceId: string, amount: number): Promise<void> {
    const payment = await this.getPaymentById(id);

    if (Number(payment.amount) < amount) {
      throw new Error('Allocation amount exceeds payment amount');
    }

    console.log(`Allocating payment ${id} amount ${amount} to invoice ${invoiceId}`);
  }

  async syncToTreasury(paymentId: string): Promise<boolean> {
    const payment = await this.getPaymentById(paymentId);
    
    console.log(`Syncing payment ${paymentId} to Treasury (placeholder)`);
    
    return true;
  }

  async getTreasuryStatus(paymentId: string): Promise<TreasuryStatus> {
    const payment = await this.getPaymentById(paymentId);
    
    return {
      synced: true,
      treasuryId: `TREAS-${paymentId.substring(0, 8)}`,
      status: 'completed',
      syncedAt: new Date().toISOString(),
    };
  }
}

export const paymentService = new PaymentService();
