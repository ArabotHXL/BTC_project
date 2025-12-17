import { Response } from 'express';
import { AuthRequest, InvoiceFilters, PaginationParams } from '../types';
import { invoiceService } from '../services/invoiceService';
import { paymentService } from '../services/paymentService';
import {
  createInvoiceSchema,
  updateInvoiceSchema,
  recordPaymentSchema,
  addLineItemSchema,
  voidInvoiceSchema,
  sendInvoiceSchema,
  invoiceQuerySchema,
} from '../schemas/invoiceSchemas';

export const getInvoices = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const queryValidation = invoiceQuerySchema.safeParse({
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

    const { status, accountId, dueDateFrom, dueDateTo, page, pageSize, sortBy, sortOrder } =
      queryValidation.data;

    const filters: InvoiceFilters = {
      status,
      accountId,
      dueDateFrom,
      dueDateTo,
    };

    const pagination: PaginationParams = {
      page,
      pageSize,
      sortBy,
      sortOrder,
    };

    const result = await invoiceService.getInvoices(filters, pagination);

    return res.json(result);
  } catch (error) {
    console.error('Error in getInvoices:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};

export const getInvoiceById = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const { id } = req.params;

    const invoice = await invoiceService.getInvoiceById(id);

    return res.json(invoice);
  } catch (error) {
    if (error instanceof Error && error.message === 'Invoice not found') {
      return res.status(404).json({ error: 'Not Found', message: error.message });
    }

    console.error('Error in getInvoiceById:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};

export const getOverdueInvoices = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const invoices = await invoiceService.getOverdueInvoices();

    return res.json(invoices);
  } catch (error) {
    console.error('Error in getOverdueInvoices:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};

export const getAgingReport = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const report = await invoiceService.getAgingReport();

    return res.json(report);
  } catch (error) {
    console.error('Error in getAgingReport:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};

export const createInvoice = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const validation = createInvoiceSchema.safeParse(req.body);

    if (!validation.success) {
      return res.status(400).json({
        error: 'Validation Error',
        details: validation.error.errors,
      });
    }

    const invoice = await invoiceService.createInvoice(validation.data);

    return res.status(201).json(invoice);
  } catch (error) {
    console.error('Error in createInvoice:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};

export const createFromDeal = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const { dealId } = req.params;

    const invoice = await invoiceService.createFromDeal(dealId);

    return res.status(201).json(invoice);
  } catch (error) {
    if (error instanceof Error) {
      if (error.message === 'Deal not found') {
        return res.status(404).json({ error: 'Not Found', message: error.message });
      }
      if (error.message === 'Deal must be CLOSED_WON to generate invoice') {
        return res.status(400).json({ error: 'Bad Request', message: error.message });
      }
    }

    console.error('Error in createFromDeal:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};

export const updateInvoice = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const { id } = req.params;
    const validation = updateInvoiceSchema.safeParse(req.body);

    if (!validation.success) {
      return res.status(400).json({
        error: 'Validation Error',
        details: validation.error.errors,
      });
    }

    const invoice = await invoiceService.updateInvoice(id, validation.data);

    return res.json(invoice);
  } catch (error) {
    if (error instanceof Error && error.message === 'Invoice not found') {
      return res.status(404).json({ error: 'Not Found', message: error.message });
    }

    console.error('Error in updateInvoice:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};

export const addLineItem = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const { id } = req.params;
    const validation = addLineItemSchema.safeParse(req.body);

    if (!validation.success) {
      return res.status(400).json({
        error: 'Validation Error',
        details: validation.error.errors,
      });
    }

    const invoice = await invoiceService.addLineItem(id, validation.data);

    return res.json(invoice);
  } catch (error) {
    if (error instanceof Error) {
      if (error.message === 'Invoice not found') {
        return res.status(404).json({ error: 'Not Found', message: error.message });
      }
      if (error.message === 'Can only add line items to draft invoices') {
        return res.status(400).json({ error: 'Bad Request', message: error.message });
      }
    }

    console.error('Error in addLineItem:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};

export const removeLineItem = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const { id, lineItemId } = req.params;

    const invoice = await invoiceService.removeLineItem(id, lineItemId);

    return res.json(invoice);
  } catch (error) {
    if (error instanceof Error) {
      if (error.message === 'Invoice not found') {
        return res.status(404).json({ error: 'Not Found', message: error.message });
      }
      if (error.message === 'Can only remove line items from draft invoices') {
        return res.status(400).json({ error: 'Bad Request', message: error.message });
      }
    }

    console.error('Error in removeLineItem:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};

export const issueInvoice = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const { id } = req.params;
    const { email } = req.body;

    const invoice = await invoiceService.issueInvoice(id);

    if (email) {
      await invoiceService.sendInvoice(id, email);
    }

    return res.json(invoice);
  } catch (error) {
    if (error instanceof Error) {
      if (error.message === 'Invoice not found') {
        return res.status(404).json({ error: 'Not Found', message: error.message });
      }
      if (error.message === 'Only draft invoices can be issued') {
        return res.status(400).json({ error: 'Bad Request', message: error.message });
      }
    }

    console.error('Error in issueInvoice:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};

export const voidInvoice = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const { id } = req.params;
    const validation = voidInvoiceSchema.safeParse(req.body);

    if (!validation.success) {
      return res.status(400).json({
        error: 'Validation Error',
        details: validation.error.errors,
      });
    }

    const invoice = await invoiceService.voidInvoice(id, validation.data.reason);

    return res.json(invoice);
  } catch (error) {
    if (error instanceof Error) {
      if (error.message === 'Invoice not found') {
        return res.status(404).json({ error: 'Not Found', message: error.message });
      }
      if (error.message === 'Cannot void a paid invoice') {
        return res.status(400).json({ error: 'Bad Request', message: error.message });
      }
    }

    console.error('Error in voidInvoice:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};

export const recordPayment = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const { id } = req.params;
    const validation = recordPaymentSchema.safeParse(req.body);

    if (!validation.success) {
      return res.status(400).json({
        error: 'Validation Error',
        details: validation.error.errors,
      });
    }

    const payment = await paymentService.recordPayment(id, validation.data);

    return res.status(201).json(payment);
  } catch (error) {
    if (error instanceof Error && error.message === 'Invoice not found') {
      return res.status(404).json({ error: 'Not Found', message: error.message });
    }

    console.error('Error in recordPayment:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};

export const getNetRevenue = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const { id } = req.params;

    const netRevenue = await invoiceService.calculateNetRevenue(id);

    return res.json(netRevenue);
  } catch (error) {
    if (error instanceof Error && error.message === 'Invoice not found') {
      return res.status(404).json({ error: 'Not Found', message: error.message });
    }

    console.error('Error in getNetRevenue:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};
