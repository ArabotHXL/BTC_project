import { Response, NextFunction } from 'express';
import { PrismaClient } from '@prisma/client';
import { AuthRequest } from '../types';

const prisma = new PrismaClient();

export enum Permission {
  LEAD_READ = 'lead:read',
  LEAD_WRITE = 'lead:write',
  DEAL_READ = 'deal:read',
  DEAL_WRITE = 'deal:write',
  INVOICE_READ = 'invoice:read',
  INVOICE_WRITE = 'invoice:write',
  ASSET_READ = 'asset:read',
  ASSET_WRITE = 'asset:write',
  TICKET_READ = 'ticket:read',
  TICKET_WRITE = 'ticket:write',
  USER_MANAGE = 'user:manage',
  SYSTEM_CONFIG = 'system:config',
  CONTRACT_READ = 'contract:read',
  CONTRACT_WRITE = 'contract:write',
  PAYMENT_READ = 'payment:read',
  PAYMENT_WRITE = 'payment:write',
  MAINTENANCE_READ = 'maintenance:read',
  MAINTENANCE_WRITE = 'maintenance:write',
  INVENTORY_READ = 'inventory:read',
  INVENTORY_WRITE = 'inventory:write',
  ACCOUNT_READ = 'account:read',
  ACCOUNT_WRITE = 'account:write',
  CONTACT_READ = 'contact:read',
  CONTACT_WRITE = 'contact:write',
  BILLING_READ = 'billing:read',
  BILLING_WRITE = 'billing:write',
}

const hasPermission = (userPermissions: any, requiredPermission: Permission): boolean => {
  if (!userPermissions) return false;

  if (userPermissions.all) {
    return true;
  }

  const [resource, action] = requiredPermission.split(':');

  if (userPermissions[resource]) {
    return userPermissions[resource].includes(action);
  }

  return false;
};

export const requirePermission = (permission: Permission) => {
  return async (req: AuthRequest, res: Response, next: NextFunction) => {
    try {
      if (!req.user) {
        return res.status(401).json({
          error: 'Unauthorized',
          message: 'Authentication required',
        });
      }

      const userRole = await prisma.role.findUnique({
        where: { id: req.user.roleId },
      });

      if (!userRole) {
        return res.status(403).json({
          error: 'Forbidden',
          message: 'Role not found',
        });
      }

      const permissions = userRole.permissionsJson as any;

      if (!hasPermission(permissions, permission)) {
        return res.status(403).json({
          error: 'Forbidden',
          message: 'Insufficient permissions',
        });
      }

      next();
    } catch (error) {
      return res.status(500).json({
        error: 'Internal Server Error',
        message: 'Permission check failed',
      });
    }
  };
};

export const requireAnyPermission = (permissions: Permission[]) => {
  return async (req: AuthRequest, res: Response, next: NextFunction) => {
    try {
      if (!req.user) {
        return res.status(401).json({
          error: 'Unauthorized',
          message: 'Authentication required',
        });
      }

      const userRole = await prisma.role.findUnique({
        where: { id: req.user.roleId },
      });

      if (!userRole) {
        return res.status(403).json({
          error: 'Forbidden',
          message: 'Role not found',
        });
      }

      const rolePermissions = userRole.permissionsJson as any;

      const hasAnyPermission = permissions.some(permission => 
        hasPermission(rolePermissions, permission)
      );

      if (!hasAnyPermission) {
        return res.status(403).json({
          error: 'Forbidden',
          message: 'Insufficient permissions',
        });
      }

      next();
    } catch (error) {
      return res.status(500).json({
        error: 'Internal Server Error',
        message: 'Permission check failed',
      });
    }
  };
};

export const requireAllPermissions = (permissions: Permission[]) => {
  return async (req: AuthRequest, res: Response, next: NextFunction) => {
    try {
      if (!req.user) {
        return res.status(401).json({
          error: 'Unauthorized',
          message: 'Authentication required',
        });
      }

      const userRole = await prisma.role.findUnique({
        where: { id: req.user.roleId },
      });

      if (!userRole) {
        return res.status(403).json({
          error: 'Forbidden',
          message: 'Role not found',
        });
      }

      const rolePermissions = userRole.permissionsJson as any;

      const hasAllPermissions = permissions.every(permission => 
        hasPermission(rolePermissions, permission)
      );

      if (!hasAllPermissions) {
        return res.status(403).json({
          error: 'Forbidden',
          message: 'Insufficient permissions',
        });
      }

      next();
    } catch (error) {
      return res.status(500).json({
        error: 'Internal Server Error',
        message: 'Permission check failed',
      });
    }
  };
};
