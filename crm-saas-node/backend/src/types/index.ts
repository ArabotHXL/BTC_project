import { Request } from 'express';
import { 
  LeadSource, 
  LeadStatus, 
  DealStage, 
  ContractStatus,
  InvoiceStatus,
  InvoiceLineItemType,
  PaymentMethod,
  PaymentStatus,
  MinerAssetStatus,
  BatchStatus,
  ShipmentStatus,
  MaintenanceType
} from '@prisma/client';

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

export interface LineItemDTO {
  type: InvoiceLineItemType;
  description: string;
  quantity: number;
  unitPrice: number;
  total: number;
}

export interface CreateInvoiceDTO {
  accountId: string;
  dealId?: string;
  contractId?: string;
  dueDate: string;
  items: LineItemDTO[];
  notes?: string;
}

export interface UpdateInvoiceDTO {
  dueDate?: string;
  status?: InvoiceStatus;
  notes?: string;
}

export interface PaymentDTO {
  amount: number;
  method: PaymentMethod;
  reference?: string;
  paidAt?: string;
}

export interface CreatePaymentDTO {
  invoiceId: string;
  amount: number;
  method: PaymentMethod;
  reference?: string;
  paymentDate?: string;
}

export interface UpdatePaymentDTO {
  amount?: number;
  method?: PaymentMethod;
  reference?: string;
  status?: PaymentStatus;
}

export interface NetRevenueBreakdown {
  miningOutput: number;
  electricityCost: number;
  serviceFee: number;
  netRevenue: number;
  margin: number;
}

export interface AgingReport {
  current: number;
  age30: number;
  age60: number;
  age90Plus: number;
  total: number;
}

export interface TreasuryStatus {
  synced: boolean;
  treasuryId: string;
  status: string;
  syncedAt?: string;
}

export interface CreateBillingCycleDTO {
  contractId: string;
  startDate: string;
  endDate: string;
  btcProduced?: number;
  powerConsumed?: number;
  serviceFee?: number;
}

export interface InvoiceFilters {
  status?: InvoiceStatus;
  accountId?: string;
  dueDateFrom?: string;
  dueDateTo?: string;
}

export interface PaymentFilters {
  status?: PaymentStatus;
  method?: PaymentMethod;
  invoiceId?: string;
  accountId?: string;
}

export interface CreateAssetDTO {
  accountId: string;
  model: string;
  serialNumber: string;
  hashrate?: number;
  power?: number;
  location?: string;
  purchasedAt?: string;
}

export interface UpdateAssetDTO {
  accountId?: string;
  model?: string;
  hashrate?: number;
  power?: number;
  location?: string;
  purchasedAt?: string;
}

export interface BulkAssetDTO {
  accountId: string;
  model: string;
  serialNumber: string;
  hashrate?: number;
  power?: number;
  location?: string;
  purchasedAt?: string;
}

export interface BulkImportResult {
  success: number;
  failed: number;
  errors: Array<{
    index: number;
    serialNumber: string;
    error: string;
  }>;
}

export interface InventorySummary {
  total: number;
  byStatus: Record<string, number>;
  byModel: Record<string, number>;
  byAccount: Record<string, number>;
}

export interface MaintenanceLogDTO {
  type: MaintenanceType;
  description: string;
  cost?: number;
  performedBy: string;
  performedAt: string;
  ticketId?: string;
}

export interface AssetFilters {
  status?: MinerAssetStatus;
  model?: string;
  accountId?: string;
  location?: string;
}

export interface CreateBatchDTO {
  batchNumber: string;
  totalUnits: number;
  arrivalDate?: string;
  status?: BatchStatus;
}

export interface UpdateBatchDTO {
  batchNumber?: string;
  totalUnits?: number;
  arrivalDate?: string;
  status?: BatchStatus;
}

export interface BatchSummary {
  batch: any;
  totalUnits: number;
  shipmentsCount: number;
  status: BatchStatus;
}

export interface BatchFilters {
  status?: BatchStatus;
  arrivalDateFrom?: string;
  arrivalDateTo?: string;
}

export interface CreateShipmentDTO {
  batchId: string;
  trackingNumber?: string;
  carrier?: string;
  shippedAt?: string;
  deliveredAt?: string;
  status?: ShipmentStatus;
}

export interface UpdateShipmentDTO {
  trackingNumber?: string;
  carrier?: string;
  shippedAt?: string;
  deliveredAt?: string;
  status?: ShipmentStatus;
}

export interface ShipmentFilters {
  status?: ShipmentStatus;
  carrier?: string;
  batchId?: string;
}
