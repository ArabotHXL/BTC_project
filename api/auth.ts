/**
 * Authentication Middleware for TypeScript API
 */

import { Request, Response, NextFunction } from 'express';

const API_KEY = process.env.TS_API_KEY || 'hashinsight_dev_key_2025';

export function requireAuth(req: Request, res: Response, next: NextFunction) {
  const authHeader = req.headers.authorization;
  
  if (!authHeader) {
    return res.status(401).json({ error: 'Missing Authorization header' });
  }

  const [scheme, token] = authHeader.split(' ');
  
  if (scheme !== 'Bearer' || token !== API_KEY) {
    return res.status(403).json({ error: 'Invalid API key' });
  }

  next();
}

export function requireConfirmation(req: Request, res: Response, next: NextFunction) {
  const { confirmed } = req.body;
  
  if (!confirmed) {
    return res.status(400).json({ 
      error: 'Confirmation required for control operations',
      message: 'Set confirmed: true in request body'
    });
  }

  next();
}
