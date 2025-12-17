import { Response } from 'express';
import { AuthRequest, ShipmentFilters, PaginationParams } from '../types';
import { shipmentService } from '../services/shipmentService';
import {
  createShipmentSchema,
  updateShipmentSchema,
  markAsShippedSchema,
  shipmentQuerySchema,
} from '../schemas/shipmentSchemas';

export const getShipments = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const queryValidation = shipmentQuerySchema.safeParse({
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
      carrier,
      batchId,
      page,
      pageSize,
      sortBy,
      sortOrder,
    } = queryValidation.data;

    const filters: ShipmentFilters = {
      status,
      carrier,
      batchId,
    };

    const pagination: PaginationParams = {
      page,
      pageSize,
      sortBy,
      sortOrder,
    };

    const result = await shipmentService.getShipments(filters, pagination);

    return res.json(result);
  } catch (error) {
    console.error('Error in getShipments:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};

export const getShipmentById = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const { id } = req.params;

    const shipment = await shipmentService.getShipmentById(id);

    return res.json(shipment);
  } catch (error) {
    if (error instanceof Error && error.message === 'Shipment not found') {
      return res.status(404).json({ error: 'Not Found', message: error.message });
    }

    console.error('Error in getShipmentById:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};

export const trackShipment = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const { trackingNumber } = req.params;

    const shipment = await shipmentService.trackShipment(trackingNumber);

    return res.json(shipment);
  } catch (error) {
    if (error instanceof Error && error.message === 'Shipment not found') {
      return res.status(404).json({ error: 'Not Found', message: error.message });
    }

    console.error('Error in trackShipment:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};

export const createShipment = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const validation = createShipmentSchema.safeParse(req.body);

    if (!validation.success) {
      return res.status(400).json({
        error: 'Validation Error',
        details: validation.error.errors,
      });
    }

    const shipment = await shipmentService.createShipment(validation.data, req.user.id);

    return res.status(201).json(shipment);
  } catch (error) {
    console.error('Error in createShipment:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};

export const updateShipment = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const { id } = req.params;

    const validation = updateShipmentSchema.safeParse(req.body);

    if (!validation.success) {
      return res.status(400).json({
        error: 'Validation Error',
        details: validation.error.errors,
      });
    }

    const shipment = await shipmentService.updateShipment(id, validation.data);

    return res.json(shipment);
  } catch (error) {
    if (error instanceof Error && error.message === 'Shipment not found') {
      return res.status(404).json({ error: 'Not Found', message: error.message });
    }

    console.error('Error in updateShipment:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};

export const markAsShipped = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const { id } = req.params;

    const validation = markAsShippedSchema.safeParse(req.body);

    if (!validation.success) {
      return res.status(400).json({
        error: 'Validation Error',
        details: validation.error.errors,
      });
    }

    const shipment = await shipmentService.markAsShipped(
      id,
      validation.data.trackingNumber,
      req.user.id
    );

    return res.json(shipment);
  } catch (error) {
    if (error instanceof Error && error.message === 'Shipment not found') {
      return res.status(404).json({ error: 'Not Found', message: error.message });
    }

    console.error('Error in markAsShipped:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};

export const markAsDelivered = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({ error: 'Unauthorized' });
    }

    const { id } = req.params;

    const shipment = await shipmentService.markAsDelivered(id, req.user.id);

    return res.json(shipment);
  } catch (error) {
    if (error instanceof Error && error.message === 'Shipment not found') {
      return res.status(404).json({ error: 'Not Found', message: error.message });
    }

    console.error('Error in markAsDelivered:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: error instanceof Error ? error.message : 'Unknown error',
    });
  }
};
