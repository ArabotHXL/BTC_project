import { PrismaClient, Lead, LeadStatus, LeadSource, Deal, ActivityType, EntityType, DealStage, AccountSize } from '@prisma/client';
import {
  CreateLeadDTO,
  UpdateLeadDTO,
  ConvertToDealDTO,
  LeadStats,
  PaginatedResponse,
  LeadFilters,
  PaginationParams,
} from '../types';
import { eventPublisher, EventType } from '../events/publisher';

const prisma = new PrismaClient();

export class LeadService {
  async getLeads(
    filters: LeadFilters = {},
    pagination: PaginationParams = {}
  ): Promise<PaginatedResponse<Lead>> {
    const { page = 1, pageSize = 20, sortBy = 'createdAt', sortOrder = 'desc' } = pagination;
    const skip = (page - 1) * pageSize;

    const where: any = {};
    
    if (filters.status) where.status = filters.status;
    if (filters.source) where.source = filters.source;
    if (filters.assignedTo) where.assignedTo = filters.assignedTo;
    if (filters.minScore !== undefined) {
      where.score = { ...where.score, gte: filters.minScore };
    }
    if (filters.maxScore !== undefined) {
      where.score = { ...where.score, lte: filters.maxScore };
    }

    const [leads, total] = await Promise.all([
      prisma.lead.findMany({
        where,
        skip,
        take: pageSize,
        orderBy: { [sortBy]: sortOrder },
        include: {
          assignee: {
            select: {
              id: true,
              name: true,
              email: true,
            },
          },
        },
      }),
      prisma.lead.count({ where }),
    ]);

    return {
      data: leads,
      pagination: {
        page,
        pageSize,
        total,
        totalPages: Math.ceil(total / pageSize),
      },
    };
  }

  async getLeadById(id: string): Promise<Lead> {
    const lead = await prisma.lead.findUnique({
      where: { id },
      include: {
        assignee: {
          select: {
            id: true,
            name: true,
            email: true,
          },
        },
        deals: true,
      },
    });

    if (!lead) {
      throw new Error('Lead not found');
    }

    return lead;
  }

  async getLeadStats(userId?: string): Promise<LeadStats> {
    const where = userId ? { assignedTo: userId } : {};

    const [leads, totalConverted] = await Promise.all([
      prisma.lead.findMany({ where }),
      prisma.lead.count({ where: { ...where, status: LeadStatus.CONVERTED } }),
    ]);

    const byStatus: Record<LeadStatus, number> = {
      NEW: 0,
      CONTACTED: 0,
      QUALIFIED: 0,
      UNQUALIFIED: 0,
      CONVERTED: 0,
      LOST: 0,
    };

    const bySource: Record<LeadSource, number> = {
      WEBSITE: 0,
      REFERRAL: 0,
      EMAIL: 0,
      PHONE: 0,
      SOCIAL_MEDIA: 0,
      TRADE_SHOW: 0,
      PARTNER: 0,
      OTHER: 0,
    };

    let totalScore = 0;

    leads.forEach((lead) => {
      byStatus[lead.status]++;
      bySource[lead.source]++;
      totalScore += lead.score || 0;
    });

    return {
      total: leads.length,
      byStatus,
      bySource,
      avgScore: leads.length > 0 ? totalScore / leads.length : 0,
      conversionRate: leads.length > 0 ? (totalConverted / leads.length) * 100 : 0,
    };
  }

  async createLead(data: CreateLeadDTO, userId: string): Promise<Lead> {
    const score = this.calculateLeadScore(data);

    const lead = await prisma.lead.create({
      data: {
        ...data,
        score,
      },
      include: {
        assignee: true,
      },
    });

    await this.createActivity(lead.id, userId, 'Lead created', ActivityType.TASK);

    await eventPublisher.publish(EventType.LEAD_CAPTURED, {
      id: lead.id,
      entityType: 'LEAD',
      userId,
      ...lead,
    });

    return lead;
  }

  async updateLead(id: string, data: UpdateLeadDTO, userId: string): Promise<Lead> {
    const existingLead = await this.getLeadById(id);

    const updatedLead = await prisma.lead.update({
      where: { id },
      data,
      include: {
        assignee: true,
      },
    });

    if (existingLead.status !== updatedLead.status) {
      await this.createActivity(
        id,
        userId,
        `Lead status changed from ${existingLead.status} to ${updatedLead.status}`,
        ActivityType.TASK
      );
    }

    return updatedLead;
  }

  async assignLead(id: string, userId: string, assignerId: string): Promise<Lead> {
    const lead = await prisma.lead.update({
      where: { id },
      data: { assignedTo: userId },
      include: {
        assignee: true,
      },
    });

    await this.createActivity(id, assignerId, `Lead assigned to ${lead.assignee?.name}`, ActivityType.TASK);

    return lead;
  }

  async updateLeadScore(id: string, score: number): Promise<Lead> {
    return await prisma.lead.update({
      where: { id },
      data: { score },
    });
  }

  async qualifyLead(id: string, userId: string): Promise<Lead> {
    const lead = await prisma.lead.update({
      where: { id },
      data: { status: LeadStatus.QUALIFIED },
      include: {
        assignee: true,
      },
    });

    await this.createActivity(id, userId, 'Lead qualified', ActivityType.TASK);

    await eventPublisher.publish(EventType.LEAD_QUALIFIED, {
      id: lead.id,
      entityType: 'LEAD',
      userId,
      ...lead,
    });

    return lead;
  }

  async disqualifyLead(id: string, reason: string, userId: string): Promise<Lead> {
    const lead = await prisma.lead.update({
      where: { id },
      data: { status: LeadStatus.UNQUALIFIED },
      include: {
        assignee: true,
      },
    });

    await this.createActivity(id, userId, `Lead disqualified: ${reason}`, ActivityType.TASK);

    await eventPublisher.publish(EventType.LEAD_DISQUALIFIED, {
      id: lead.id,
      entityType: 'LEAD',
      userId,
      reason,
      ...lead,
    });

    return lead;
  }

  async convertToDeal(id: string, data: ConvertToDealDTO, userId: string): Promise<Deal> {
    const lead = await this.getLeadById(id);

    if (lead.status !== LeadStatus.QUALIFIED) {
      throw new Error('Only QUALIFIED leads can be converted to deals');
    }

    let accountId = data.accountId;

    if (!accountId && data.accountName) {
      const account = await prisma.account.create({
        data: {
          name: data.accountName,
          industry: data.accountIndustry,
          size: this.determineAccountSize(data.accountName),
          status: 'PROSPECT',
          ownerId: userId,
        },
      });
      accountId = account.id;
    }

    if (!accountId) {
      throw new Error('Account ID or Account Name is required');
    }

    const deal = await prisma.deal.create({
      data: {
        leadId: id,
        accountId,
        title: data.dealTitle,
        value: data.value,
        expectedClose: new Date(data.expectedClose),
        stage: DealStage.PROSPECTING,
        probability: 10,
        ownerId: userId,
      },
      include: {
        account: true,
        owner: true,
      },
    });

    await prisma.lead.update({
      where: { id },
      data: { status: LeadStatus.CONVERTED },
    });

    await this.createActivity(id, userId, `Lead converted to deal: ${data.dealTitle}`, ActivityType.TASK);

    await eventPublisher.publish(EventType.LEAD_CONVERTED, {
      id: lead.id,
      entityType: 'LEAD',
      userId,
      dealId: deal.id,
      ...lead,
    });

    return deal;
  }

  async bulkAssign(leadIds: string[], userId: string, assignerId: string): Promise<number> {
    const result = await prisma.lead.updateMany({
      where: { id: { in: leadIds } },
      data: { assignedTo: userId },
    });

    for (const leadId of leadIds) {
      await this.createActivity(
        leadId,
        assignerId,
        `Bulk assigned to user ${userId}`,
        ActivityType.TASK
      );
    }

    return result.count;
  }

  async bulkUpdateStatus(leadIds: string[], status: LeadStatus, userId: string): Promise<number> {
    const result = await prisma.lead.updateMany({
      where: { id: { in: leadIds } },
      data: { status },
    });

    for (const leadId of leadIds) {
      await this.createActivity(
        leadId,
        userId,
        `Bulk status update to ${status}`,
        ActivityType.TASK
      );
    }

    return result.count;
  }

  private calculateLeadScore(data: CreateLeadDTO): number {
    let score = 0;

    const sourceScores: Record<LeadSource, number> = {
      REFERRAL: 40,
      PARTNER: 35,
      TRADE_SHOW: 30,
      WEBSITE: 25,
      SOCIAL_MEDIA: 20,
      EMAIL: 15,
      PHONE: 15,
      OTHER: 10,
    };

    score += sourceScores[data.source] || 0;

    if (data.email) score += 20;
    if (data.phone) score += 15;
    if (data.title && (data.title.toLowerCase().includes('ceo') || data.title.toLowerCase().includes('director'))) {
      score += 25;
    }

    return Math.min(score, 100);
  }

  private determineAccountSize(accountName: string): AccountSize {
    if (accountName.toLowerCase().includes('enterprise') || accountName.toLowerCase().includes('corporation')) {
      return AccountSize.ENTERPRISE;
    }
    if (accountName.toLowerCase().includes('inc') || accountName.toLowerCase().includes('ltd')) {
      return AccountSize.LARGE;
    }
    return AccountSize.MEDIUM;
  }

  private async createActivity(
    entityId: string,
    userId: string,
    description: string,
    type: ActivityType
  ): Promise<void> {
    await prisma.activity.create({
      data: {
        type,
        entityType: EntityType.LEAD,
        entityId,
        userId,
        subject: description,
        description,
        completedAt: new Date(),
      },
    });
  }
}

export const leadService = new LeadService();
