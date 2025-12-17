import express from 'express';
import { authenticate } from '../middleware/auth';
import { requirePermission, Permission } from '../middleware/permissions';
import * as batchController from '../controllers/batchController';

const router = express.Router();

router.get('/', authenticate, requirePermission(Permission.ASSET_READ), batchController.getBatches);
router.post('/', authenticate, requirePermission(Permission.ASSET_WRITE), batchController.createBatch);
router.get('/:id', authenticate, requirePermission(Permission.ASSET_READ), batchController.getBatchById);
router.put('/:id', authenticate, requirePermission(Permission.ASSET_WRITE), batchController.updateBatch);
router.post('/:id/close', authenticate, requirePermission(Permission.ASSET_WRITE), batchController.closeBatch);
router.get('/:id/summary', authenticate, requirePermission(Permission.ASSET_READ), batchController.getBatchSummary);

export default router;
