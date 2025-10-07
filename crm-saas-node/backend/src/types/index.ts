import { Request } from 'express';
import { LeadSource, LeadStatus, DealStage, ContractStatus } from '@prisma/client';

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

export interface PaginatedResponse<T> {
  data: T[];
  pagination: {
    page: number;
    pageSize: number;
    total: number;
    totalPages: number;
  };
}

export interface CreateLeadDTO {
  source: LeadSource;
  company: string;
  contactName: string;
  email?: string;
  phone?: string;
  title?: string;
  assignedTo?: string;
}

export interface UpdateLeadDTO {
  source?: LeadSource;
  company?: string;
  contactName?: string;
  email?: string;
  phone?: string;
  title?: string;
  status?: LeadStatus;
  score?: number;
  assignedTo?: string;
}

export interface ConvertToDealDTO {
  dealTitle: string;
  value: number;
  expectedClose: string;
  accountId?: string;
  accountName?: string;
  accountIndustry?: string;
}

export interface LeadStats {
  total: number;
  byStatus: Record<LeadStatus, number>;
  bySource: Record<LeadSource, number>;
  avgScore: number;
  conversionRate: number;
}

export interface CreateDealDTO {
  leadId?: string;
  accountId: string;
  title: string;
  value: number;
  stage?: DealStage;
  probability?: number;
  expectedClose?: string;
}

export interface UpdateDealDTO {
  title?: string;
  value?: number;
  stage?: DealStage;
  probability?: number;
  expectedClose?: string;
}

export interface ContractDTO {
  startDate: string;
  endDate: string;
  terms: string;
  value?: number;
}

export interface DealMetrics {
  totalValue: number;
  wonValue: number;
  lostValue: number;
  pipelineValue: number;
  avgDealSize: number;
  winRate: number;
  avgDealCycle: number;
}

export interface PipelineView {
  stages: {
    stage: DealStage;
    deals: any[];
    totalValue: number;
    count: number;
  }[];
  totalValue: number;
  weightedValue: number;
}

export interface LeadFilters {
  status?: LeadStatus;
  source?: LeadSource;
  assignedTo?: string;
  minScore?: number;
  maxScore?: number;
}

export interface DealFilters {
  stage?: DealStage;
  ownerId?: string;
  minValue?: number;
  maxValue?: number;
  expectedCloseFrom?: string;
  expectedCloseTo?: string;
}

export interface PaginationParams {
  page?: number;
  pageSize?: number;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
}
