import express from 'express';
import { authenticate } from '../middleware/auth';
import { requirePermission, Permission } from '../middleware/permissions';
import * as leadController from '../controllers/leadController';

const router = express.Router();

router.get('/', authenticate, requirePermission(Permission.LEAD_READ), leadController.getLeads);
router.post('/', authenticate, requirePermission(Permission.LEAD_WRITE), leadController.createLead);
router.get('/stats', authenticate, requirePermission(Permission.LEAD_READ), leadController.getLeadStats);
router.get('/:id', authenticate, requirePermission(Permission.LEAD_READ), leadController.getLeadById);
router.put('/:id', authenticate, requirePermission(Permission.LEAD_WRITE), leadController.updateLead);
router.post('/:id/convert', authenticate, requirePermission(Permission.DEAL_WRITE), leadController.convertLead);
router.post('/:id/qualify', authenticate, requirePermission(Permission.LEAD_WRITE), leadController.qualifyLead);
router.post('/:id/disqualify', authenticate, requirePermission(Permission.LEAD_WRITE), leadController.disqualifyLead);
router.post('/bulk/assign', authenticate, requirePermission(Permission.LEAD_WRITE), leadController.bulkAssign);
router.post('/bulk/status', authenticate, requirePermission(Permission.LEAD_WRITE), leadController.bulkUpdateStatus);

export default router;
