import { Response } from 'express';
import { AuthRequest, DealFilters, PaginationParams } from '../types';
import { dealService } from '../services/dealService';
import {
  createDealSchema,
  updateDealSchema,
  updateStageSchema,
  loseDealSchema,
  generateContractSchema,
  dealQuerySchema,
  metricsQuerySchema,
} from '../schemas/dealSchemas';

export const getDeals = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const queryValidation = dealQuerySchema.safeParse({
      ...req.query,
      page: req.query.page ? Number(req.query.page) : undefined,
      pageSize: req.query.pageSize ? Number(req.query.pageSize) : undefined,
      minValue: req.query.minValue ? Number(req.query.minValue) : undefined,
      maxValue: req.query.maxValue ? Number(req.query.maxValue) : undefined,
    });

    if (!queryValidation.success) {
      return res.status(400).json({
        error: 'Validation Error',
        details: queryValidation.error.errors,
      });
    }

    const {
      stage,
      ownerId,
      minValue,
      maxValue,
      expectedCloseFrom,
      expectedCloseTo,
      page,
      pageSize,
      sortBy,
      sortOrder,
    } = queryValidation.data;

    const filters: DealFilters = {
      stage,
      ownerId,
      minValue,
      maxValue,
      expectedCloseFrom,
      expectedCloseTo,
    };

    const pagination: PaginationParams = {
      page,
      pageSize,
      sortBy,
      sortOrder,
    };

    const result = await dealService.getDeals(filters, pagination);

    return res.json(result);
  } catch (error) {
    console.error('Error in getDeals:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};

export const getDealById = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const { id } = req.params;

    const deal = await dealService.getDealById(id);

    return res.json(deal);
  } catch (error) {
    if (error instanceof Error && error.message === 'Deal not found') {
      return res.status(404).json({ error: 'Not Found', message: error.message });
    }

    console.error('Error in getDealById:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};

export const getPipeline = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const userId = req.query.userId as string | undefined;

    const pipeline = await dealService.getDealPipeline(userId);

    return res.json(pipeline);
  } catch (error) {
    console.error('Error in getPipeline:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};

export const getMetrics = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const queryValidation = metricsQuerySchema.safeParse(req.query);

    if (!queryValidation.success) {
      return res.status(400).json({
        error: 'Validation Error',
        details: queryValidation.error.errors,
      });
    }

    const metrics = await dealService.getDealMetrics(queryValidation.data.period);

    return res.json(metrics);
  } catch (error) {
    console.error('Error in getMetrics:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};

export const createDeal = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const validation = createDealSchema.safeParse(req.body);

    if (!validation.success) {
      return res.status(400).json({
        error: 'Validation Error',
        details: validation.error.errors,
      });
    }

    const deal = await dealService.createDeal(validation.data, req.user.id);

    return res.status(201).json(deal);
  } catch (error) {
    console.error('Error in createDeal:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};

export const updateDeal = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const { id } = req.params;

    const validation = updateDealSchema.safeParse(req.body);

    if (!validation.success) {
      return res.status(400).json({
        error: 'Validation Error',
        details: validation.error.errors,
      });
    }

    const deal = await dealService.updateDeal(id, validation.data, req.user.id);

    return res.json(deal);
  } catch (error) {
    if (error instanceof Error && error.message === 'Deal not found') {
      return res.status(404).json({ error: 'Not Found', message: error.message });
    }

    console.error('Error in updateDeal:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};

export const updateStage = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const { id } = req.params;

    const validation = updateStageSchema.safeParse(req.body);

    if (!validation.success) {
      return res.status(400).json({
        error: 'Validation Error',
        details: validation.error.errors,
      });
    }

    const deal = await dealService.updateDealStage(
      id,
      validation.data.stage,
      req.user.id,
      validation.data.notes
    );

    return res.json(deal);
  } catch (error) {
    if (error instanceof Error && error.message === 'Deal not found') {
      return res.status(404).json({ error: 'Not Found', message: error.message });
    }

    console.error('Error in updateStage:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};

export const winDeal = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const { id } = req.params;

    const deal = await dealService.winDeal(id, req.user.id);

    return res.json(deal);
  } catch (error) {
    if (error instanceof Error && error.message === 'Deal not found') {
      return res.status(404).json({ error: 'Not Found', message: error.message });
    }

    console.error('Error in winDeal:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};

export const loseDeal = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const { id } = req.params;

    const validation = loseDealSchema.safeParse(req.body);

    if (!validation.success) {
      return res.status(400).json({
        error: 'Validation Error',
        details: validation.error.errors,
      });
    }

    const deal = await dealService.loseDeal(
      id,
      validation.data.reason,
      req.user.id,
      validation.data.notes
    );

    return res.json(deal);
  } catch (error) {
    if (error instanceof Error && error.message === 'Deal not found') {
      return res.status(404).json({ error: 'Not Found', message: error.message });
    }

    console.error('Error in loseDeal:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};

export const generateContract = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const { id } = req.params;

    const validation = generateContractSchema.safeParse(req.body);

    if (!validation.success) {
      return res.status(400).json({
        error: 'Validation Error',
        details: validation.error.errors,
      });
    }

    const contract = await dealService.generateContract(id, validation.data, req.user.id);

    return res.status(201).json(contract);
  } catch (error) {
    if (error instanceof Error) {
      if (error.message === 'Deal not found') {
        return res.status(404).json({ error: 'Not Found', message: error.message });
      }
      if (
        error.message ===
        'Contract can only be generated for won deals or deals in negotiation'
      ) {
        return res.status(400).json({ error: 'Bad Request', message: error.message });
      }
    }

    console.error('Error in generateContract:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};

export const forecastRevenue = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const queryValidation = metricsQuerySchema.safeParse(req.query);

    if (!queryValidation.success) {
      return res.status(400).json({
        error: 'Validation Error',
        details: queryValidation.error.errors,
      });
    }

    const forecasts = await dealService.forecastRevenue(queryValidation.data.period);

    return res.json(forecasts);
  } catch (error) {
    console.error('Error in forecastRevenue:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};
