import express from 'express';
import { authenticate } from '../middleware/auth';
import { requirePermission, Permission } from '../middleware/permissions';
import * as assetController from '../controllers/assetController';

const router = express.Router();

router.get('/', authenticate, requirePermission(Permission.ASSET_READ), assetController.getAssets);
router.post('/', authenticate, requirePermission(Permission.ASSET_WRITE), assetController.createAsset);
router.post('/bulk-import', authenticate, requirePermission(Permission.ASSET_WRITE), assetController.bulkImport);
router.get('/inventory', authenticate, requirePermission(Permission.ASSET_READ), assetController.getInventory);
router.get('/sn/:serialNumber', authenticate, requirePermission(Permission.ASSET_READ), assetController.getAssetBySN);
router.get('/:id', authenticate, requirePermission(Permission.ASSET_READ), assetController.getAssetById);
router.put('/:id', authenticate, requirePermission(Permission.ASSET_WRITE), assetController.updateAsset);
router.put('/:id/status', authenticate, requirePermission(Permission.ASSET_WRITE), assetController.updateStatus);
router.post('/:id/deploy', authenticate, requirePermission(Permission.ASSET_WRITE), assetController.deployAsset);
router.post('/:id/start-mining', authenticate, requirePermission(Permission.ASSET_WRITE), assetController.startMining);
router.post('/:id/stop-mining', authenticate, requirePermission(Permission.ASSET_WRITE), assetController.stopMining);
router.post('/:id/decommission', authenticate, requirePermission(Permission.ASSET_WRITE), assetController.decommissionAsset);
router.post('/:id/maintenance', authenticate, requirePermission(Permission.ASSET_WRITE), assetController.createMaintenance);
router.get('/:id/maintenance-history', authenticate, requirePermission(Permission.ASSET_READ), assetController.getMaintenanceHistory);

export default router;
