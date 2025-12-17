import jwt from 'jsonwebtoken';
import crypto from 'crypto';

export const generateToken = (payload: object, expiresIn?: string): string => {
  if (!process.env.JWT_SECRET) {
    throw new Error('JWT_SECRET is not defined in environment variables');
  }
  const expiry = expiresIn || process.env.JWT_EXPIRES_IN || '15m';
  return jwt.sign(payload, process.env.JWT_SECRET, { expiresIn: expiry });
};

export const verifyToken = (token: string) => {
  if (!process.env.JWT_SECRET) {
    throw new Error('JWT_SECRET is not defined in environment variables');
  }
  return jwt.verify(token, process.env.JWT_SECRET);
};

export const generateRefreshToken = (): string => {
  return crypto.randomBytes(40).toString('hex');
};
