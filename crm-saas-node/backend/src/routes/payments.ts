import express from 'express';
import { authenticate } from '../middleware/auth';
import { requirePermission, Permission } from '../middleware/permissions';
import * as paymentController from '../controllers/paymentController';

const router = express.Router();

router.get('/', authenticate, requirePermission(Permission.INVOICE_READ), paymentController.getPayments);
router.post('/', authenticate, requirePermission(Permission.INVOICE_WRITE), paymentController.createPayment);
router.get('/:id', authenticate, requirePermission(Permission.INVOICE_READ), paymentController.getPaymentById);
router.put('/:id', authenticate, requirePermission(Permission.INVOICE_WRITE), paymentController.updatePayment);
router.put('/:id/confirm', authenticate, requirePermission(Permission.INVOICE_WRITE), paymentController.confirmPayment);
router.put('/:id/reject', authenticate, requirePermission(Permission.INVOICE_WRITE), paymentController.rejectPayment);
router.post('/:id/refund', authenticate, requirePermission(Permission.INVOICE_WRITE), paymentController.refundPayment);
router.get('/:id/treasury-status', authenticate, requirePermission(Permission.INVOICE_READ), paymentController.getTreasuryStatus);

export default router;
