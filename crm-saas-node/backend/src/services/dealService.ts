import { PrismaClient, Deal, DealStage, Contract, ContractStatus, ActivityType, EntityType, Forecast as PrismaForecast } from '@prisma/client';
import {
  CreateDealDTO,
  UpdateDealDTO,
  ContractDTO,
  DealMetrics,
  PipelineView,
  PaginatedResponse,
  DealFilters,
  PaginationParams,
} from '../types';
import { eventPublisher, EventType } from '../events/publisher';

const prisma = new PrismaClient();

const STAGE_PROBABILITIES: Record<DealStage, number> = {
  PROSPECTING: 10,
  QUALIFICATION: 25,
  PROPOSAL: 50,
  NEGOTIATION: 75,
  CLOSED_WON: 100,
  CLOSED_LOST: 0,
};

const STAGE_ORDER: DealStage[] = [
  DealStage.PROSPECTING,
  DealStage.QUALIFICATION,
  DealStage.PROPOSAL,
  DealStage.NEGOTIATION,
  DealStage.CLOSED_WON,
];

export class DealService {
  async getDeals(
    filters: DealFilters = {},
    pagination: PaginationParams = {}
  ): Promise<PaginatedResponse<Deal>> {
    const { page = 1, pageSize = 20, sortBy = 'createdAt', sortOrder = 'desc' } = pagination;
    const skip = (page - 1) * pageSize;

    const where: any = {};
    
    if (filters.stage) where.stage = filters.stage;
    if (filters.ownerId) where.ownerId = filters.ownerId;
    if (filters.minValue !== undefined) {
      where.value = { ...where.value, gte: filters.minValue };
    }
    if (filters.maxValue !== undefined) {
      where.value = { ...where.value, lte: filters.maxValue };
    }
    if (filters.expectedCloseFrom) {
      where.expectedClose = { ...where.expectedClose, gte: new Date(filters.expectedCloseFrom) };
    }
    if (filters.expectedCloseTo) {
      where.expectedClose = { ...where.expectedClose, lte: new Date(filters.expectedCloseTo) };
    }

    const [deals, total] = await Promise.all([
      prisma.deal.findMany({
        where,
        skip,
        take: pageSize,
        orderBy: { [sortBy]: sortOrder },
        include: {
          account: {
            select: {
              id: true,
              name: true,
              industry: true,
            },
          },
          owner: {
            select: {
              id: true,
              name: true,
              email: true,
            },
          },
          lead: {
            select: {
              id: true,
              company: true,
              contactName: true,
            },
          },
        },
      }),
      prisma.deal.count({ where }),
    ]);

    return {
      data: deals,
      pagination: {
        page,
        pageSize,
        total,
        totalPages: Math.ceil(total / pageSize),
      },
    };
  }

  async getDealById(id: string): Promise<Deal> {
    const deal = await prisma.deal.findUnique({
      where: { id },
      include: {
        account: true,
        owner: true,
        lead: true,
        contracts: true,
      },
    });

    if (!deal) {
      throw new Error('Deal not found');
    }

    return deal;
  }

  async getDealPipeline(userId?: string): Promise<PipelineView> {
    const where = userId ? { ownerId: userId } : {};
    
    const deals = await prisma.deal.findMany({
      where: {
        ...where,
        stage: {
          notIn: [DealStage.CLOSED_WON, DealStage.CLOSED_LOST],
        },
      },
      include: {
        account: true,
        owner: true,
      },
    });

    const stages = STAGE_ORDER.filter(
      (stage) => stage !== DealStage.CLOSED_WON && stage !== DealStage.CLOSED_LOST
    ).map((stage) => {
      const stageDeals = deals.filter((d) => d.stage === stage);
      const totalValue = stageDeals.reduce((sum, d) => sum + Number(d.value), 0);

      return {
        stage,
        deals: stageDeals,
        totalValue,
        count: stageDeals.length,
      };
    });

    const totalValue = deals.reduce((sum, d) => sum + Number(d.value), 0);
    const weightedValue = deals.reduce(
      (sum, d) => sum + Number(d.value) * ((d.probability || STAGE_PROBABILITIES[d.stage]) / 100),
      0
    );

    return {
      stages,
      totalValue,
      weightedValue,
    };
  }

  async getDealMetrics(period: string = 'month'): Promise<DealMetrics> {
    const now = new Date();
    const startDate = this.getPeriodStartDate(now, period);

    const deals = await prisma.deal.findMany({
      where: {
        createdAt: {
          gte: startDate,
        },
      },
    });

    const wonDeals = deals.filter((d) => d.stage === DealStage.CLOSED_WON);
    const lostDeals = deals.filter((d) => d.stage === DealStage.CLOSED_LOST);
    const pipelineDeals = deals.filter(
      (d) => d.stage !== DealStage.CLOSED_WON && d.stage !== DealStage.CLOSED_LOST
    );

    const totalValue = deals.reduce((sum, d) => sum + Number(d.value), 0);
    const wonValue = wonDeals.reduce((sum, d) => sum + Number(d.value), 0);
    const lostValue = lostDeals.reduce((sum, d) => sum + Number(d.value), 0);
    const pipelineValue = pipelineDeals.reduce((sum, d) => sum + Number(d.value), 0);

    const avgDealCycle = await this.calculateAvgDealCycle(wonDeals);

    return {
      totalValue,
      wonValue,
      lostValue,
      pipelineValue,
      avgDealSize: deals.length > 0 ? totalValue / deals.length : 0,
      winRate: wonDeals.length + lostDeals.length > 0 
        ? (wonDeals.length / (wonDeals.length + lostDeals.length)) * 100 
        : 0,
      avgDealCycle,
    };
  }

  async createDeal(data: CreateDealDTO, userId: string): Promise<Deal> {
    const probability = data.probability || STAGE_PROBABILITIES[data.stage || DealStage.PROSPECTING];

    const deal = await prisma.deal.create({
      data: {
        ...data,
        stage: data.stage || DealStage.PROSPECTING,
        probability,
        ownerId: userId,
        expectedClose: data.expectedClose ? new Date(data.expectedClose) : null,
      },
      include: {
        account: true,
        owner: true,
      },
    });

    await this.createActivity(deal.id, userId, `Deal created: ${deal.title}`, ActivityType.TASK);

    await eventPublisher.publish(EventType.DEAL_CREATED, {
      id: deal.id,
      entityType: 'DEAL',
      userId,
      ...deal,
    });

    return deal;
  }

  async updateDeal(id: string, data: UpdateDealDTO, userId: string): Promise<Deal> {
    const deal = await prisma.deal.update({
      where: { id },
      data: {
        ...data,
        expectedClose: data.expectedClose ? new Date(data.expectedClose) : undefined,
      },
      include: {
        account: true,
        owner: true,
      },
    });

    await this.createActivity(id, userId, `Deal updated`, ActivityType.TASK);

    return deal;
  }

  async updateDealStage(id: string, stage: DealStage, userId: string, notes?: string): Promise<Deal> {
    const existingDeal = await this.getDealById(id);
    const probability = STAGE_PROBABILITIES[stage];

    const deal = await prisma.deal.update({
      where: { id },
      data: {
        stage,
        probability,
      },
      include: {
        account: true,
        owner: true,
      },
    });

    const activityDesc = notes 
      ? `Deal stage changed from ${existingDeal.stage} to ${stage}. Notes: ${notes}`
      : `Deal stage changed from ${existingDeal.stage} to ${stage}`;

    await this.createActivity(id, userId, activityDesc, ActivityType.TASK);

    await eventPublisher.publish(EventType.DEAL_STAGE_CHANGED, {
      id: deal.id,
      entityType: 'DEAL',
      userId,
      previousStage: existingDeal.stage,
      newStage: stage,
      notes,
      ...deal,
    });

    return deal;
  }

  async updateProbability(id: string, probability: number): Promise<Deal> {
    return await prisma.deal.update({
      where: { id },
      data: { probability },
    });
  }

  async moveToNextStage(id: string, userId: string): Promise<Deal> {
    const deal = await this.getDealById(id);
    const currentIndex = STAGE_ORDER.indexOf(deal.stage);

    if (currentIndex === -1 || currentIndex >= STAGE_ORDER.length - 1) {
      throw new Error('Cannot move to next stage');
    }

    const nextStage = STAGE_ORDER[currentIndex + 1];
    return await this.updateDealStage(id, nextStage, userId);
  }

  async winDeal(id: string, userId: string): Promise<Deal> {
    const deal = await prisma.deal.update({
      where: { id },
      data: {
        stage: DealStage.CLOSED_WON,
        probability: 100,
      },
      include: {
        account: true,
        owner: true,
      },
    });

    await this.createActivity(id, userId, `Deal won! 🎉`, ActivityType.TASK);

    await eventPublisher.publish(EventType.DEAL_WON, {
      id: deal.id,
      entityType: 'DEAL',
      userId,
      ...deal,
    });

    return deal;
  }

  async loseDeal(id: string, reason: string, userId: string, notes?: string): Promise<Deal> {
    const deal = await prisma.deal.update({
      where: { id },
      data: {
        stage: DealStage.CLOSED_LOST,
        probability: 0,
      },
      include: {
        account: true,
        owner: true,
      },
    });

    const activityDesc = notes 
      ? `Deal lost. Reason: ${reason}. Notes: ${notes}`
      : `Deal lost. Reason: ${reason}`;

    await this.createActivity(id, userId, activityDesc, ActivityType.TASK);

    await eventPublisher.publish(EventType.DEAL_LOST, {
      id: deal.id,
      entityType: 'DEAL',
      userId,
      reason,
      notes,
      ...deal,
    });

    return deal;
  }

  async generateContract(id: string, data: ContractDTO, userId: string): Promise<Contract> {
    const deal = await this.getDealById(id);

    if (deal.stage !== DealStage.CLOSED_WON && deal.stage !== DealStage.NEGOTIATION) {
      throw new Error('Contract can only be generated for won deals or deals in negotiation');
    }

    const contractNumber = await this.generateContractNumber();

    const contract = await prisma.contract.create({
      data: {
        dealId: id,
        accountId: deal.accountId,
        contractNumber,
        startDate: new Date(data.startDate),
        endDate: new Date(data.endDate),
        value: data.value ? data.value : deal.value,
        status: ContractStatus.DRAFT,
      },
      include: {
        account: true,
        deal: true,
      },
    });

    await this.createActivity(id, userId, `Contract generated: ${contractNumber}`, ActivityType.TASK);

    await eventPublisher.publish(EventType.CONTRACT_GENERATED, {
      id: contract.id,
      entityType: 'CONTRACT',
      userId,
      dealId: id,
      ...contract,
    });

    return contract;
  }

  async calculateWinProbability(dealId: string): Promise<number> {
    const deal = await this.getDealById(dealId);
    
    let probability = STAGE_PROBABILITIES[deal.stage];

    const dealAge = Math.floor(
      (Date.now() - deal.createdAt.getTime()) / (1000 * 60 * 60 * 24)
    );

    if (dealAge > 90) {
      probability = Math.max(0, probability - 20);
    } else if (dealAge > 60) {
      probability = Math.max(0, probability - 10);
    }

    const dealValue = Number(deal.value);
    if (dealValue > 100000) {
      probability = Math.max(0, probability - 5);
    }

    return Math.min(100, Math.max(0, probability));
  }

  async forecastRevenue(period: string = 'month'): Promise<PrismaForecast[]> {
    const now = new Date();
    const endDate = this.getPeriodEndDate(now, period);

    const deals = await prisma.deal.findMany({
      where: {
        expectedClose: {
          gte: now,
          lte: endDate,
        },
        stage: {
          notIn: [DealStage.CLOSED_WON, DealStage.CLOSED_LOST],
        },
      },
    });

    const forecasts: PrismaForecast[] = [];

    for (const deal of deals) {
      const probability = await this.calculateWinProbability(deal.id);
      const predictedValue = Number(deal.value) * (probability / 100);

      const forecast = await prisma.forecast.create({
        data: {
          entityType: EntityType.DEAL,
          entityId: deal.id,
          metric: 'REVENUE',
          predictedValue,
          confidence: probability,
          forecastDate: deal.expectedClose || new Date(),
        },
      });

      forecasts.push(forecast);
    }

    return forecasts;
  }

  private async calculateAvgDealCycle(wonDeals: Deal[]): Promise<number> {
    if (wonDeals.length === 0) return 0;

    const totalDays = wonDeals.reduce((sum, deal) => {
      const days = Math.floor(
        (deal.updatedAt.getTime() - deal.createdAt.getTime()) / (1000 * 60 * 60 * 24)
      );
      return sum + days;
    }, 0);

    return totalDays / wonDeals.length;
  }

  private async generateContractNumber(): Promise<string> {
    const count = await prisma.contract.count();
    const year = new Date().getFullYear();
    return `CON-${year}-${String(count + 1).padStart(5, '0')}`;
  }

  private getPeriodStartDate(now: Date, period: string): Date {
    const date = new Date(now);
    
    switch (period) {
      case 'week':
        date.setDate(date.getDate() - 7);
        break;
      case 'month':
        date.setMonth(date.getMonth() - 1);
        break;
      case 'quarter':
        date.setMonth(date.getMonth() - 3);
        break;
      case 'year':
        date.setFullYear(date.getFullYear() - 1);
        break;
      default:
        date.setMonth(date.getMonth() - 1);
    }
    
    return date;
  }

  private getPeriodEndDate(now: Date, period: string): Date {
    const date = new Date(now);
    
    switch (period) {
      case 'week':
        date.setDate(date.getDate() + 7);
        break;
      case 'month':
        date.setMonth(date.getMonth() + 1);
        break;
      case 'quarter':
        date.setMonth(date.getMonth() + 3);
        break;
      case 'year':
        date.setFullYear(date.getFullYear() + 1);
        break;
      default:
        date.setMonth(date.getMonth() + 1);
    }
    
    return date;
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
        entityType: EntityType.DEAL,
        entityId,
        userId,
        subject: description,
        description,
        completedAt: new Date(),
      },
    });
  }
}

export const dealService = new DealService();
