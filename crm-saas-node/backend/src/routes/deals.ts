import express from 'express';
import { authenticate } from '../middleware/auth';
import { requirePermission, Permission } from '../middleware/permissions';
import * as dealController from '../controllers/dealController';

const router = express.Router();

router.get('/', authenticate, requirePermission(Permission.DEAL_READ), dealController.getDeals);
router.get('/pipeline', authenticate, requirePermission(Permission.DEAL_READ), dealController.getPipeline);
router.get('/metrics', authenticate, requirePermission(Permission.DEAL_READ), dealController.getMetrics);
router.get('/forecast', authenticate, requirePermission(Permission.DEAL_READ), dealController.forecastRevenue);
router.post('/', authenticate, requirePermission(Permission.DEAL_WRITE), dealController.createDeal);
router.get('/:id', authenticate, requirePermission(Permission.DEAL_READ), dealController.getDealById);
router.put('/:id', authenticate, requirePermission(Permission.DEAL_WRITE), dealController.updateDeal);
router.put('/:id/stage', authenticate, requirePermission(Permission.DEAL_WRITE), dealController.updateStage);
router.post('/:id/win', authenticate, requirePermission(Permission.DEAL_WRITE), dealController.winDeal);
router.post('/:id/lose', authenticate, requirePermission(Permission.DEAL_WRITE), dealController.loseDeal);
router.post('/:id/contract', authenticate, requirePermission(Permission.DEAL_WRITE), dealController.generateContract);

export default router;
