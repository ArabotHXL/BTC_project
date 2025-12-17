import { Response } from 'express';
import { AuthRequest, BatchFilters, PaginationParams } from '../types';
import { minerBatchService } from '../services/minerBatchService';
import {
  createBatchSchema,
  updateBatchSchema,
  batchQuerySchema,
} from '../schemas/batchSchemas';

export const getBatches = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const queryValidation = batchQuerySchema.safeParse({
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
      arrivalDateFrom,
      arrivalDateTo,
      page,
      pageSize,
      sortBy,
      sortOrder,
    } = queryValidation.data;

    const filters: BatchFilters = {
      status,
      arrivalDateFrom,
      arrivalDateTo,
    };

    const pagination: PaginationParams = {
      page,
      pageSize,
      sortBy,
      sortOrder,
    };

    const result = await minerBatchService.getBatches(filters, pagination);

    return res.json(result);
  } catch (error) {
    console.error('Error in getBatches:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};

export const getBatchById = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const { id } = req.params;

    const batch = await minerBatchService.getBatchById(id);

    return res.json(batch);
  } catch (error) {
    if (error instanceof Error && error.message === 'Batch not found') {
      return res.status(404).json({ error: 'Not Found', message: error.message });
    }

    console.error('Error in getBatchById:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};

export const getBatchSummary = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const { id } = req.params;

    const summary = await minerBatchService.getBatchSummary(id);

    return res.json(summary);
  } catch (error) {
    if (error instanceof Error && error.message === 'Batch not found') {
      return res.status(404).json({ error: 'Not Found', message: error.message });
    }

    console.error('Error in getBatchSummary:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};

export const createBatch = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const validation = createBatchSchema.safeParse(req.body);

    if (!validation.success) {
      return res.status(400).json({
        error: 'Validation Error',
        details: validation.error.errors,
      });
    }

    const batch = await minerBatchService.createBatch(validation.data, req.user.id);

    return res.status(201).json(batch);
  } catch (error) {
    if (error instanceof Error && error.message === 'Batch number already exists') {
      return res.status(400).json({ error: 'Bad Request', message: error.message });
    }

    console.error('Error in createBatch:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};

export const updateBatch = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const { id } = req.params;

    const validation = updateBatchSchema.safeParse(req.body);

    if (!validation.success) {
      return res.status(400).json({
        error: 'Validation Error',
        details: validation.error.errors,
      });
    }

    const batch = await minerBatchService.updateBatch(id, validation.data);

    return res.json(batch);
  } catch (error) {
    if (error instanceof Error && error.message === 'Batch not found') {
      return res.status(404).json({ error: 'Not Found', message: error.message });
    }

    console.error('Error in updateBatch:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};

export const closeBatch = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const { id } = req.params;

    const batch = await minerBatchService.closeBatch(id);

    return res.json(batch);
  } catch (error) {
    if (error instanceof Error && error.message === 'Batch not found') {
      return res.status(404).json({ error: 'Not Found', message: error.message });
    }

    console.error('Error in closeBatch:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};
