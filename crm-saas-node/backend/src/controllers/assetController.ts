import { Response } from 'express';
import { AuthRequest, AssetFilters, PaginationParams } from '../types';
import { minerAssetService } from '../services/minerAssetService';
import {
  createAssetSchema,
  updateAssetSchema,
  bulkImportSchema,
  updateStatusSchema,
  deployAssetSchema,
  maintenanceLogSchema,
  stopMiningSchema,
  decommissionSchema,
  assetQuerySchema,
} from '../schemas/assetSchemas';

export const getAssets = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const queryValidation = assetQuerySchema.safeParse({
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

    const {
      status,
      model,
      accountId,
      location,
      page,
      pageSize,
      sortBy,
      sortOrder,
    } = queryValidation.data;

    const filters: AssetFilters = {
      status,
      model,
      accountId,
      location,
    };

    const pagination: PaginationParams = {
      page,
      pageSize,
      sortBy,
      sortOrder,
    };

    const result = await minerAssetService.getAssets(filters, pagination);

    return res.json(result);
  } catch (error) {
    console.error('Error in getAssets:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};

export const getAssetById = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const { id } = req.params;

    const asset = await minerAssetService.getAssetById(id);

    return res.json(asset);
  } catch (error) {
    if (error instanceof Error && error.message === 'Asset not found') {
      return res.status(404).json({ error: 'Not Found', message: error.message });
    }

    console.error('Error in getAssetById:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};

export const getAssetBySN = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const { serialNumber } = req.params;

    const asset = await minerAssetService.getAssetBySerialNumber(serialNumber);

    return res.json(asset);
  } catch (error) {
    if (error instanceof Error && error.message === 'Asset not found') {
      return res.status(404).json({ error: 'Not Found', message: error.message });
    }

    console.error('Error in getAssetBySN:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};

export const getInventory = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const accountId = req.query.accountId as string | undefined;

    const summary = await minerAssetService.getInventorySummary(accountId);

    return res.json(summary);
  } catch (error) {
    console.error('Error in getInventory:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};

export const createAsset = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const validation = createAssetSchema.safeParse(req.body);

    if (!validation.success) {
      return res.status(400).json({
        error: 'Validation Error',
        details: validation.error.errors,
      });
    }

    const asset = await minerAssetService.createAsset(validation.data, req.user.id);

    return res.status(201).json(asset);
  } catch (error) {
    if (error instanceof Error && error.message === 'Serial number already exists') {
      return res.status(400).json({ error: 'Bad Request', message: error.message });
    }

    console.error('Error in createAsset:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};

/**
 * PUT /api/assets/:id
 * Updates asset metadata (model, hashrate, power, location, etc.)
 * 
 * ⚠️ IMPORTANT: Status changes are NOT allowed through this endpoint.
 * Use dedicated endpoints for status transitions:
 * - PUT /assets/:id/status - General status update with validation
 * - POST /assets/:id/deploy - Deploy asset
 * - POST /assets/:id/start-mining - Start mining
 * - POST /assets/:id/stop-mining - Stop mining
 * - POST /assets/:id/decommission - Decommission asset
 * - POST /assets/:id/maintenance - Create maintenance log
 * 
 * This ensures all status changes are properly validated and emit events.
 */
export const updateAsset = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const { id } = req.params;

    const validation = updateAssetSchema.safeParse(req.body);

    if (!validation.success) {
      return res.status(400).json({
        error: 'Validation Error',
        details: validation.error.errors,
        message: 'Validation failed. Note: Status cannot be updated directly. Use dedicated status endpoints.',
      });
    }

    const asset = await minerAssetService.updateAsset(id, validation.data, req.user.id);

    return res.json({
      success: true,
      data: asset,
      message: 'Asset updated successfully. Use PUT /assets/:id/status to change status.',
    });
  } catch (error) {
    if (error instanceof Error && error.message === 'Asset not found') {
      return res.status(404).json({ error: 'Not Found', message: error.message });
    }

    console.error('Error in updateAsset:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};

export const bulkImport = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const validation = bulkImportSchema.safeParse(req.body);

    if (!validation.success) {
      return res.status(400).json({
        error: 'Validation Error',
        details: validation.error.errors,
      });
    }

    const result = await minerAssetService.bulkImport(validation.data, req.user.id);

    return res.status(201).json(result);
  } catch (error) {
    console.error('Error in bulkImport:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};

export const updateStatus = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const { id } = req.params;

    const validation = updateStatusSchema.safeParse(req.body);

    if (!validation.success) {
      return res.status(400).json({
        error: 'Validation Error',
        details: validation.error.errors,
      });
    }

    const asset = await minerAssetService.updateStatus(
      id,
      validation.data.status,
      req.user.id,
      validation.data.notes
    );

    return res.json(asset);
  } catch (error) {
    if (error instanceof Error && error.message === 'Asset not found') {
      return res.status(404).json({ error: 'Not Found', message: error.message });
    }

    console.error('Error in updateStatus:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};

export const deployAsset = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const { id } = req.params;

    const validation = deployAssetSchema.safeParse(req.body);

    if (!validation.success) {
      return res.status(400).json({
        error: 'Validation Error',
        details: validation.error.errors,
      });
    }

    const asset = await minerAssetService.deploy(id, validation.data.location, req.user.id);

    return res.json(asset);
  } catch (error) {
    if (error instanceof Error && error.message === 'Asset not found') {
      return res.status(404).json({ error: 'Not Found', message: error.message });
    }

    console.error('Error in deployAsset:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};

export const startMining = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const { id } = req.params;

    const asset = await minerAssetService.startMining(id, req.user.id);

    return res.json(asset);
  } catch (error) {
    if (error instanceof Error) {
      if (error.message === 'Asset not found') {
        return res.status(404).json({ error: 'Not Found', message: error.message });
      }
      if (error.message === 'Cannot start mining on offline asset') {
        return res.status(400).json({ error: 'Bad Request', message: error.message });
      }
    }

    console.error('Error in startMining:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};

export const stopMining = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const { id } = req.params;

    const validation = stopMiningSchema.safeParse(req.body);

    if (!validation.success) {
      return res.status(400).json({
        error: 'Validation Error',
        details: validation.error.errors,
      });
    }

    const asset = await minerAssetService.stopMining(id, validation.data.reason, req.user.id);

    return res.json(asset);
  } catch (error) {
    if (error instanceof Error && error.message === 'Asset not found') {
      return res.status(404).json({ error: 'Not Found', message: error.message });
    }

    console.error('Error in stopMining:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};

export const decommissionAsset = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const { id } = req.params;

    const validation = decommissionSchema.safeParse(req.body);

    if (!validation.success) {
      return res.status(400).json({
        error: 'Validation Error',
        details: validation.error.errors,
      });
    }

    const asset = await minerAssetService.decommission(id, validation.data.reason, req.user.id);

    return res.json(asset);
  } catch (error) {
    if (error instanceof Error && error.message === 'Asset not found') {
      return res.status(404).json({ error: 'Not Found', message: error.message });
    }

    console.error('Error in decommissionAsset:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};

export const createMaintenance = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const { id } = req.params;

    const validation = maintenanceLogSchema.safeParse(req.body);

    if (!validation.success) {
      return res.status(400).json({
        error: 'Validation Error',
        details: validation.error.errors,
      });
    }

    const log = await minerAssetService.createMaintenanceLog(id, validation.data);

    return res.status(201).json(log);
  } catch (error) {
    console.error('Error in createMaintenance:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};

export const getMaintenanceHistory = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const { id } = req.params;

    const history = await minerAssetService.getMaintenanceHistory(id);

    return res.json(history);
  } catch (error) {
    console.error('Error in getMaintenanceHistory:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};
