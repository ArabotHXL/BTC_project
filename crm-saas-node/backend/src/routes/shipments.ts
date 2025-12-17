import express from 'express';
import { authenticate } from '../middleware/auth';
import { requirePermission, Permission } from '../middleware/permissions';
import * as shipmentController from '../controllers/shipmentController';

const router = express.Router();

router.get('/', authenticate, requirePermission(Permission.ASSET_READ), shipmentController.getShipments);
router.post('/', authenticate, requirePermission(Permission.ASSET_WRITE), shipmentController.createShipment);
router.get('/track/:trackingNumber', authenticate, requirePermission(Permission.ASSET_READ), shipmentController.trackShipment);
router.get('/:id', authenticate, requirePermission(Permission.ASSET_READ), shipmentController.getShipmentById);
router.put('/:id', authenticate, requirePermission(Permission.ASSET_WRITE), shipmentController.updateShipment);
router.put('/:id/ship', authenticate, requirePermission(Permission.ASSET_WRITE), shipmentController.markAsShipped);
router.put('/:id/deliver', authenticate, requirePermission(Permission.ASSET_WRITE), shipmentController.markAsDelivered);

export default router;
