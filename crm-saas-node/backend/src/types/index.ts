import { Request } from 'express';

export interface JWTPayload {
  userId: string;
  email: string;
  roleId: string;
}

export interface AuthenticatedUser {
  id: string;
  email: string;
  name: string;
  roleId: string;
  status: string;
  role?: {
    id: string;
    name: string;
    permissionsJson: any;
  };
}

export interface AuthRequest extends Request {
  user?: AuthenticatedUser;
}
