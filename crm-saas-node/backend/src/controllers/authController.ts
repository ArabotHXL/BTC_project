import { Response } from 'express';
import { PrismaClient } from '@prisma/client';
import { z } from 'zod';
import { hashPassword, comparePassword } from '../utils/password';
import { generateToken, verifyToken, generateRefreshToken } from '../utils/jwt';
import { AuthRequest, JWTPayload } from '../types';

const prisma = new PrismaClient();

const loginSchema = z.object({
  email: z.string().email(),
  password: z.string().min(6),
});

const registerSchema = z.object({
  email: z.string().email(),
  password: z.string().min(6),
  name: z.string().min(1),
});

const refreshSchema = z.object({
  refreshToken: z.string(),
});

export const login = async (req: AuthRequest, res: Response) => {
  try {
    const { email, password } = loginSchema.parse(req.body);

    const user = await prisma.user.findUnique({
      where: { email },
      include: { role: true },
    });

    if (!user) {
      return res.status(401).json({
        error: 'Unauthorized',
        message: 'Invalid email or password',
      });
    }

    const isPasswordValid = await comparePassword(password, user.passwordHash);

    if (!isPasswordValid) {
      return res.status(401).json({
        error: 'Unauthorized',
        message: 'Invalid email or password',
      });
    }

    if (user.status !== 'ACTIVE') {
      return res.status(401).json({
        error: 'Unauthorized',
        message: 'User account is not active',
      });
    }

    const payload: JWTPayload = {
      userId: user.id,
      email: user.email,
      roleId: user.roleId,
    };

    const accessToken = generateToken(payload);
    const refreshToken = generateRefreshToken();

    await prisma.refreshToken.create({
      data: {
        userId: user.id,
        token: refreshToken,
        expiresAt: new Date(Date.now() + (parseInt(process.env.REFRESH_TOKEN_EXPIRES_IN_DAYS || '30') * 24 * 60 * 60 * 1000)),
      },
    });

    await prisma.auditLog.create({
      data: {
        userId: user.id,
        action: 'LOGIN',
        resource: 'auth',
        details: {
          email: user.email,
          timestamp: new Date().toISOString(),
        },
        ip: req.ip || req.socket.remoteAddress,
      },
    });

    return res.status(200).json({
      message: 'Login successful',
      accessToken,
      refreshToken,
      user: {
        id: user.id,
        email: user.email,
        name: user.name,
        role: user.role.name,
        status: user.status,
      },
    });
  } catch (error) {
    if (error instanceof z.ZodError) {
      return res.status(422).json({
        error: 'Validation Error',
        message: 'Invalid input data',
        details: error.errors,
      });
    }

    console.error('Login error:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: 'An error occurred during login',
    });
  }
};

export const register = async (req: AuthRequest, res: Response) => {
  try {
    const { email, password, name } = registerSchema.parse(req.body);

    const existingUser = await prisma.user.findUnique({
      where: { email },
    });

    if (existingUser) {
      return res.status(422).json({
        error: 'Validation Error',
        message: 'Email already registered',
      });
    }

    const salesRole = await prisma.role.findFirst({
      where: { name: 'Sales' },
    });

    if (!salesRole) {
      return res.status(500).json({
        error: 'Internal Server Error',
        message: 'Default role not found',
      });
    }

    const passwordHash = await hashPassword(password);

    const user = await prisma.user.create({
      data: {
        email,
        passwordHash,
        name,
        roleId: salesRole.id,
        status: 'ACTIVE',
      },
      include: {
        role: true,
      },
    });

    const payload: JWTPayload = {
      userId: user.id,
      email: user.email,
      roleId: user.roleId,
    };

    const accessToken = generateToken(payload);
    const refreshToken = generateRefreshToken();

    await prisma.refreshToken.create({
      data: {
        userId: user.id,
        token: refreshToken,
        expiresAt: new Date(Date.now() + (parseInt(process.env.REFRESH_TOKEN_EXPIRES_IN_DAYS || '30') * 24 * 60 * 60 * 1000)),
      },
    });

    await prisma.auditLog.create({
      data: {
        userId: user.id,
        action: 'REGISTER',
        resource: 'auth',
        details: {
          email: user.email,
          timestamp: new Date().toISOString(),
        },
        ip: req.ip || req.socket.remoteAddress,
      },
    });

    return res.status(201).json({
      message: 'Registration successful',
      accessToken,
      refreshToken,
      user: {
        id: user.id,
        email: user.email,
        name: user.name,
        role: user.role.name,
        status: user.status,
      },
    });
  } catch (error) {
    if (error instanceof z.ZodError) {
      return res.status(422).json({
        error: 'Validation Error',
        message: 'Invalid input data',
        details: error.errors,
      });
    }

    console.error('Registration error:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: 'An error occurred during registration',
    });
  }
};

export const refresh = async (req: AuthRequest, res: Response) => {
  try {
    const { refreshToken } = refreshSchema.parse(req.body);

    if (!refreshToken) {
      return res.status(400).json({
        error: 'Bad Request',
        message: 'Refresh token required',
      });
    }

    const storedToken = await prisma.refreshToken.findUnique({
      where: { token: refreshToken },
      include: { user: { include: { role: true } } },
    });

    if (!storedToken || storedToken.expiresAt < new Date()) {
      return res.status(401).json({
        error: 'Unauthorized',
        message: 'Invalid or expired refresh token',
      });
    }

    if (storedToken.user.status !== 'ACTIVE') {
      return res.status(401).json({
        error: 'Unauthorized',
        message: 'User account is not active',
      });
    }

    const payload: JWTPayload = {
      userId: storedToken.user.id,
      email: storedToken.user.email,
      roleId: storedToken.user.roleId,
    };

    const accessToken = generateToken(payload);
    const newRefreshToken = generateRefreshToken();

    await prisma.refreshToken.create({
      data: {
        userId: storedToken.user.id,
        token: newRefreshToken,
        expiresAt: new Date(Date.now() + (parseInt(process.env.REFRESH_TOKEN_EXPIRES_IN_DAYS || '30') * 24 * 60 * 60 * 1000)),
      },
    });

    await prisma.refreshToken.delete({ where: { id: storedToken.id } });

    return res.status(200).json({
      message: 'Token refreshed successfully',
      accessToken,
      refreshToken: newRefreshToken,
    });
  } catch (error) {
    if (error instanceof z.ZodError) {
      return res.status(422).json({
        error: 'Validation Error',
        message: 'Invalid input data',
        details: error.errors,
      });
    }

    console.error('Token refresh error:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: 'An error occurred during token refresh',
    });
  }
};

export const logout = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({
        error: 'Unauthorized',
        message: 'Authentication required',
      });
    }

    const { refreshToken } = req.body;

    if (!refreshToken) {
      return res.status(400).json({
        error: 'Bad Request',
        message: 'Refresh token required',
      });
    }

    const storedToken = await prisma.refreshToken.findFirst({
      where: { 
        userId: req.user.id,
        token: refreshToken,
      },
    });

    if (!storedToken) {
      return res.status(400).json({
        error: 'Bad Request',
        message: 'Invalid refresh token',
      });
    }

    await prisma.refreshToken.delete({
      where: { 
        id: storedToken.id,
      },
    });

    await prisma.auditLog.create({
      data: {
        userId: req.user.id,
        action: 'LOGOUT',
        resource: 'auth',
        details: {
          email: req.user.email,
          tokenId: storedToken.id,
          timestamp: new Date().toISOString(),
        },
        ip: req.ip || req.socket.remoteAddress,
      },
    });

    return res.status(200).json({
      message: 'Logout successful',
    });
  } catch (error) {
    console.error('Logout error:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: 'An error occurred during logout',
    });
  }
};

export const logoutAll = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({
        error: 'Unauthorized',
        message: 'Authentication required',
      });
    }

    const result = await prisma.refreshToken.deleteMany({
      where: { 
        userId: req.user.id,
      },
    });

    await prisma.auditLog.create({
      data: {
        userId: req.user.id,
        action: 'LOGOUT_ALL',
        resource: 'auth',
        details: {
          email: req.user.email,
          tokensDeleted: result.count,
          timestamp: new Date().toISOString(),
        },
        ip: req.ip || req.socket.remoteAddress,
      },
    });

    return res.status(200).json({
      message: `Logged out from ${result.count} device(s)`,
      devicesLoggedOut: result.count,
    });
  } catch (error) {
    console.error('Logout all error:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: 'An error occurred during logout',
    });
  }
};

export const me = async (req: AuthRequest, res: Response) => {
  try {
    if (!req.user) {
      return res.status(401).json({
        error: 'Unauthorized',
        message: 'Authentication required',
      });
    }

    const user = await prisma.user.findUnique({
      where: { id: req.user.id },
      include: {
        role: {
          include: {
            permissions: true,
          },
        },
      },
    });

    if (!user) {
      return res.status(404).json({
        error: 'Not Found',
        message: 'User not found',
      });
    }

    return res.status(200).json({
      user: {
        id: user.id,
        email: user.email,
        name: user.name,
        role: {
          id: user.role.id,
          name: user.role.name,
          permissions: user.role.permissionsJson,
        },
        status: user.status,
        createdAt: user.createdAt,
        updatedAt: user.updatedAt,
      },
    });
  } catch (error) {
    console.error('Get user error:', error);
    return res.status(500).json({
      error: 'Internal Server Error',
      message: 'An error occurred while fetching user data',
    });
  }
};
