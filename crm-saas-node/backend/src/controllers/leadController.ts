import { Response } from 'express';
import { AuthRequest, LeadFilters, PaginationParams } from '../types';
import { leadService } from '../services/leadService';
import {
  createLeadSchema,
  updateLeadSchema,
  convertLeadSchema,
  bulkAssignSchema,
  bulkUpdateStatusSchema,
  disqualifyLeadSchema,
  leadQuerySchema,
} from '../schemas/leadSchemas';
import { ZodError } from 'zod';

export const getLeads = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const queryValidation = leadQuerySchema.safeParse({
      ...req.query,
      page: req.query.page ? Number(req.query.page) : undefined,
      pageSize: req.query.pageSize ? Number(req.query.pageSize) : undefined,
      minScore: req.query.minScore ? Number(req.query.minScore) : undefined,
      maxScore: req.query.maxScore ? Number(req.query.maxScore) : undefined,
    });

    if (!queryValidation.success) {
      return res.status(400).json({
        error: 'Validation Error',
        details: queryValidation.error.errors,
      });
    }

    const { status, source, assignedTo, minScore, maxScore, page, pageSize, sortBy, sortOrder } =
      queryValidation.data;

    const filters: LeadFilters = {
      status,
      source,
      assignedTo,
      minScore,
      maxScore,
    };

    const pagination: PaginationParams = {
      page,
      pageSize,
      sortBy,
      sortOrder,
    };

    const result = await leadService.getLeads(filters, pagination);

    return res.json(result);
  } catch (error) {
    console.error('Error in getLeads:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};

export const getLeadById = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const { id } = req.params;

    const lead = await leadService.getLeadById(id);

    return res.json(lead);
  } catch (error) {
    if (error instanceof Error && error.message === 'Lead not found') {
      return res.status(404).json({ error: 'Not Found', message: error.message });
    }

    console.error('Error in getLeadById:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};

export const getLeadStats = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const userId = req.query.userId as string | undefined;

    const stats = await leadService.getLeadStats(userId);

    return res.json(stats);
  } catch (error) {
    console.error('Error in getLeadStats:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};

export const createLead = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const validation = createLeadSchema.safeParse(req.body);

    if (!validation.success) {
      return res.status(400).json({
        error: 'Validation Error',
        details: validation.error.errors,
      });
    }

    const lead = await leadService.createLead(validation.data, req.user.id);

    return res.status(201).json(lead);
  } catch (error) {
    console.error('Error in createLead:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};

export const updateLead = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const { id } = req.params;

    const validation = updateLeadSchema.safeParse(req.body);

    if (!validation.success) {
      return res.status(400).json({
        error: 'Validation Error',
        details: validation.error.errors,
      });
    }

    const lead = await leadService.updateLead(id, validation.data, req.user.id);

    return res.json(lead);
  } catch (error) {
    if (error instanceof Error && error.message === 'Lead not found') {
      return res.status(404).json({ error: 'Not Found', message: error.message });
    }

    console.error('Error in updateLead:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};

export const convertLead = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const { id } = req.params;

    const validation = convertLeadSchema.safeParse(req.body);

    if (!validation.success) {
      return res.status(400).json({
        error: 'Validation Error',
        details: validation.error.errors,
      });
    }

    const deal = await leadService.convertToDeal(id, validation.data, req.user.id);

    return res.status(201).json(deal);
  } catch (error) {
    if (error instanceof Error) {
      if (error.message === 'Lead not found') {
        return res.status(404).json({ error: 'Not Found', message: error.message });
      }
      if (error.message === 'Only QUALIFIED leads can be converted to deals') {
        return res.status(400).json({ error: 'Bad Request', message: error.message });
      }
    }

    console.error('Error in convertLead:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};

export const qualifyLead = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const { id } = req.params;

    const lead = await leadService.qualifyLead(id, req.user.id);

    return res.json(lead);
  } catch (error) {
    if (error instanceof Error && error.message === 'Lead not found') {
      return res.status(404).json({ error: 'Not Found', message: error.message });
    }

    console.error('Error in qualifyLead:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};

export const disqualifyLead = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const { id } = req.params;

    const validation = disqualifyLeadSchema.safeParse(req.body);

    if (!validation.success) {
      return res.status(400).json({
        error: 'Validation Error',
        details: validation.error.errors,
      });
    }

    const lead = await leadService.disqualifyLead(id, validation.data.reason, req.user.id);

    return res.json(lead);
  } catch (error) {
    if (error instanceof Error && error.message === 'Lead not found') {
      return res.status(404).json({ error: 'Not Found', message: error.message });
    }

    console.error('Error in disqualifyLead:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};

export const bulkAssign = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const validation = bulkAssignSchema.safeParse(req.body);

    if (!validation.success) {
      return res.status(400).json({
        error: 'Validation Error',
        details: validation.error.errors,
      });
    }

    const count = await leadService.bulkAssign(
      validation.data.leadIds,
      validation.data.userId,
      req.user.id
    );

    return res.json({ success: true, count });
  } catch (error) {
    console.error('Error in bulkAssign:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};

export const bulkUpdateStatus = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const validation = bulkUpdateStatusSchema.safeParse(req.body);

    if (!validation.success) {
      return res.status(400).json({
        error: 'Validation Error',
        details: validation.error.errors,
      });
    }

    const count = await leadService.bulkUpdateStatus(
      validation.data.leadIds,
      validation.data.status,
      req.user.id
    );

    return res.json({ success: true, count });
  } catch (error) {
    console.error('Error in bulkUpdateStatus:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};
