import express from 'express';
import { authenticate } from '../middleware/auth';
import { requirePermission, Permission } from '../middleware/permissions';
import * as invoiceController from '../controllers/invoiceController';

const router = express.Router();

router.get('/', authenticate, requirePermission(Permission.INVOICE_READ), invoiceController.getInvoices);
router.post('/', authenticate, requirePermission(Permission.INVOICE_WRITE), invoiceController.createInvoice);
router.post('/from-deal/:dealId', authenticate, requirePermission(Permission.INVOICE_WRITE), invoiceController.createFromDeal);
router.get('/aging', authenticate, requirePermission(Permission.INVOICE_READ), invoiceController.getAgingReport);
router.get('/overdue', authenticate, requirePermission(Permission.INVOICE_READ), invoiceController.getOverdueInvoices);
router.get('/:id', authenticate, requirePermission(Permission.INVOICE_READ), invoiceController.getInvoiceById);
router.put('/:id', authenticate, requirePermission(Permission.INVOICE_WRITE), invoiceController.updateInvoice);
router.post('/:id/line-items', authenticate, requirePermission(Permission.INVOICE_WRITE), invoiceController.addLineItem);
router.delete('/:id/line-items/:lineItemId', authenticate, requirePermission(Permission.INVOICE_WRITE), invoiceController.removeLineItem);
router.put('/:id/issue', authenticate, requirePermission(Permission.INVOICE_WRITE), invoiceController.issueInvoice);
router.post('/:id/void', authenticate, requirePermission(Permission.INVOICE_WRITE), invoiceController.voidInvoice);
router.post('/:id/payment', authenticate, requirePermission(Permission.INVOICE_WRITE), invoiceController.recordPayment);
router.get('/:id/net-revenue', authenticate, requirePermission(Permission.INVOICE_READ), invoiceController.getNetRevenue);

export default router;
