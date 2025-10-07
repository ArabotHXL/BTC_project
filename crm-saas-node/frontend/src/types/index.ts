// User type
export interface User {
  id: number;
  email: string;
  username: string;
  role: string;
}

// Lead types
export interface Lead {
  id: number;
  name: string;
  email: string;
  phone?: string;
  source: 'WEBSITE' | 'REFERRAL' | 'PARTNER' | 'OTHER';
  company?: string;
  score?: number;
  status: 'NEW' | 'CONTACTED' | 'QUALIFIED' | 'CONVERTED' | 'LOST';
  notes?: string;
  createdAt: string;
  updatedAt: string;
}

// Deal types
export interface Deal {
  id: number;
  title: string;
  accountId: number;
  amount: number;
  probability: number;
  stage: 'PROSPECTING' | 'QUALIFIED' | 'PROPOSAL' | 'NEGOTIATION' | 'CLOSED_WON' | 'CLOSED_LOST';
  expectedCloseDate?: string;
  createdAt: string;
  updatedAt: string;
}

// Invoice types
export interface Invoice {
  id: number;
  invoiceNumber: string;
  accountId: number;
  amount: number;
  amountPaid: number;
  status: 'DRAFT' | 'SENT' | 'PARTIAL' | 'PAID' | 'OVERDUE';
  dueDate: string;
  issuedAt: string;
  createdAt: string;
  updatedAt: string;
}

// Payment types
export interface Payment {
  id: number;
  invoiceId: number;
  amount: number;
  paymentMethod: string;
  status: 'PENDING' | 'CONFIRMED' | 'CLEARED';
  paidAt: string;
  createdAt: string;
}

// Asset types
export interface Asset {
  id: number;
  serialNumber: string;
  model: string;
  status: string;
  accountId?: number;
  purchasePrice: number;
  purchaseDate: string;
  createdAt: string;
}

// Dashboard metrics
export interface DashboardMetrics {
  totalLeads: number;
  activeDeals: number;
  pendingInvoices: number;
  totalAssets: number;
}

// API response types
export interface ApiResponse<T> {
  success?: boolean;
  data?: T;
  message?: string;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  pageSize: number;
}
