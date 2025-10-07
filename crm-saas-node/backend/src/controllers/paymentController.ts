import { Response } from 'express';
import { AuthRequest, PaymentFilters, PaginationParams } from '../types';
import { paymentService } from '../services/paymentService';
import {
  createPaymentSchema,
  updatePaymentSchema,
  refundPaymentSchema,
  rejectPaymentSchema,
  paymentQuerySchema,
} from '../schemas/paymentSchemas';

export const getPayments = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const queryValidation = paymentQuerySchema.safeParse({
      ...req.query,
      page: req.query.page ? Number(req.query.page) : undefined,
      pageSize: req.query.pageSize ? Number(req.query.pageSize) : undefined,
    });

    if (!queryValidation.success) {
      return res.status(400).json({
        error: 'Validation Error',
        details: queryValidation.error.errors,
      });
    }

    const { status, method, invoiceId, accountId, page, pageSize, sortBy, sortOrder } =
      queryValidation.data;

    const filters: PaymentFilters = {
      status,
      method,
      invoiceId,
      accountId,
    };

    const pagination: PaginationParams = {
      page,
      pageSize,
      sortBy,
      sortOrder,
    };

    const result = await paymentService.getPayments(filters, pagination);

    return res.json(result);
  } catch (error) {
    console.error('Error in getPayments:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};

export const getPaymentById = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const { id } = req.params;

    const payment = await paymentService.getPaymentById(id);

    return res.json(payment);
  } catch (error) {
    if (error instanceof Error && error.message === 'Payment not found') {
      return res.status(404).json({ error: 'Not Found', message: error.message });
    }

    console.error('Error in getPaymentById:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};

export const createPayment = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const validation = createPaymentSchema.safeParse(req.body);

    if (!validation.success) {
      return res.status(400).json({
        error: 'Validation Error',
        details: validation.error.errors,
      });
    }

    const payment = await paymentService.createPayment(validation.data);

    return res.status(201).json(payment);
  } catch (error) {
    if (error instanceof Error && error.message === 'Invoice not found') {
      return res.status(404).json({ error: 'Not Found', message: error.message });
    }

    console.error('Error in createPayment:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};

export const updatePayment = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const { id } = req.params;
    const validation = updatePaymentSchema.safeParse(req.body);

    if (!validation.success) {
      return res.status(400).json({
        error: 'Validation Error',
        details: validation.error.errors,
      });
    }

    const payment = await paymentService.updatePayment(id, validation.data);

    return res.json(payment);
  } catch (error) {
    if (error instanceof Error && error.message === 'Payment not found') {
      return res.status(404).json({ error: 'Not Found', message: error.message });
    }

    console.error('Error in updatePayment:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};

export const confirmPayment = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const { id } = req.params;

    const payment = await paymentService.confirmPayment(id);

    return res.json(payment);
  } catch (error) {
    if (error instanceof Error) {
      if (error.message === 'Payment not found') {
        return res.status(404).json({ error: 'Not Found', message: error.message });
      }
      if (error.message === 'Only pending payments can be confirmed') {
        return res.status(400).json({ error: 'Bad Request', message: error.message });
      }
    }

    console.error('Error in confirmPayment:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};

export const rejectPayment = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const { id } = req.params;
    const validation = rejectPaymentSchema.safeParse(req.body);

    if (!validation.success) {
      return res.status(400).json({
        error: 'Validation Error',
        details: validation.error.errors,
      });
    }

    const payment = await paymentService.rejectPayment(id, validation.data.reason);

    return res.json(payment);
  } catch (error) {
    if (error instanceof Error) {
      if (error.message === 'Payment not found') {
        return res.status(404).json({ error: 'Not Found', message: error.message });
      }
      if (error.message === 'Only pending payments can be rejected') {
        return res.status(400).json({ error: 'Bad Request', message: error.message });
      }
    }

    console.error('Error in rejectPayment:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};

export const refundPayment = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const { id } = req.params;
    const validation = refundPaymentSchema.safeParse(req.body);

    if (!validation.success) {
      return res.status(400).json({
        error: 'Validation Error',
        details: validation.error.errors,
      });
    }

    const payment = await paymentService.refundPayment(id, validation.data.amount);

    return res.json(payment);
  } catch (error) {
    if (error instanceof Error) {
      if (error.message === 'Payment not found') {
        return res.status(404).json({ error: 'Not Found', message: error.message });
      }
      if (error.message.includes('Only confirmed or cleared payments can be refunded') || 
          error.message.includes('Refund amount cannot exceed payment amount')) {
        return res.status(400).json({ error: 'Bad Request', message: error.message });
      }
    }

    console.error('Error in refundPayment:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};

export const getTreasuryStatus = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const { id } = req.params;

    const status = await paymentService.getTreasuryStatus(id);

    return res.json(status);
  } catch (error) {
    if (error instanceof Error && error.message === 'Payment not found') {
      return res.status(404).json({ error: 'Not Found', message: error.message });
    }

    console.error('Error in getTreasuryStatus:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};
