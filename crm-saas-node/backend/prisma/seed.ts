import { PrismaClient } from '@prisma/client';
import {
  UserStatus,
  AccountStatus,
  AccountSize,
  LeadSource,
  LeadStatus,
  DealStage,
  ContractStatus,
  ActivityType,
  EntityType,
  InvoiceStatus,
  InvoiceLineItemType,
  PaymentMethod,
  PaymentStatus,
  MinerAssetStatus,
  BatchStatus,
  ShipmentStatus,
  TicketType,
  TicketPriority,
  TicketStatus,
  MaintenanceType,
  AutomationTrigger,
  AutomationStatus,
  EventQueueStatus,
} from '@prisma/client';

const prisma = new PrismaClient();

async function main() {
  console.log('🌱 Starting seed...');

  // Clean up existing data (in reverse order of dependencies)
  await prisma.automationLog.deleteMany();
  await prisma.automationRule.deleteMany();
  await prisma.forecast.deleteMany();
  await prisma.analyticSnapshot.deleteMany();
  await prisma.eventQueue.deleteMany();
  await prisma.webhook.deleteMany();
  await prisma.maintenanceLog.deleteMany();
  await prisma.opsTicket.deleteMany();
  await prisma.shipment.deleteMany();
  await prisma.minerBatch.deleteMany();
  await prisma.minerAsset.deleteMany();
  await prisma.inventory.deleteMany();
  await prisma.revenueRecognition.deleteMany();
  await prisma.billingCycle.deleteMany();
  await prisma.payment.deleteMany();
  await prisma.invoiceLineItem.deleteMany();
  await prisma.invoice.deleteMany();
  await prisma.tag.deleteMany();
  await prisma.note.deleteMany();
  await prisma.activity.deleteMany();
  await prisma.contract.deleteMany();
  await prisma.deal.deleteMany();
  await prisma.contact.deleteMany();
  await prisma.lead.deleteMany();
  await prisma.account.deleteMany();
  await prisma.apiKey.deleteMany();
  await prisma.auditLog.deleteMany();
  await prisma.permission.deleteMany();
  await prisma.user.deleteMany();
  await prisma.role.deleteMany();

  // ===================================
  // 1. ROLES & PERMISSIONS
  // ===================================
  
  const adminRole = await prisma.role.create({
    data: {
      name: 'Admin',
      permissionsJson: {
        all: ['read', 'write', 'delete', 'admin'],
      },
    },
  });

  const salesRole = await prisma.role.create({
    data: {
      name: 'Sales',
      permissionsJson: {
        leads: ['read', 'write'],
        deals: ['read', 'write'],
        accounts: ['read', 'write'],
        contacts: ['read', 'write'],
        contracts: ['read'],
      },
    },
  });

  const opsRole = await prisma.role.create({
    data: {
      name: 'Operations',
      permissionsJson: {
        assets: ['read', 'write'],
        tickets: ['read', 'write'],
        maintenance: ['read', 'write'],
        inventory: ['read', 'write'],
      },
    },
  });

  const financeRole = await prisma.role.create({
    data: {
      name: 'Finance',
      permissionsJson: {
        invoices: ['read', 'write'],
        payments: ['read', 'write'],
        contracts: ['read'],
        billing: ['read', 'write'],
      },
    },
  });

  console.log('✅ Created 4 roles');

  // Create permissions for roles
  const permissions = [
    { resource: 'users', action: 'read', roleId: adminRole.id },
    { resource: 'users', action: 'write', roleId: adminRole.id },
    { resource: 'leads', action: 'read', roleId: salesRole.id },
    { resource: 'leads', action: 'write', roleId: salesRole.id },
    { resource: 'deals', action: 'read', roleId: salesRole.id },
    { resource: 'deals', action: 'write', roleId: salesRole.id },
    { resource: 'assets', action: 'read', roleId: opsRole.id },
    { resource: 'assets', action: 'write', roleId: opsRole.id },
    { resource: 'invoices', action: 'read', roleId: financeRole.id },
    { resource: 'invoices', action: 'write', roleId: financeRole.id },
  ];

  await prisma.permission.createMany({ data: permissions });
  console.log('✅ Created permissions');

  // ===================================
  // 2. USERS
  // ===================================

  const adminUser = await prisma.user.create({
    data: {
      email: 'admin@hashinsight.com',
      passwordHash: '$2a$10$rH9pGQK8QZz8RDZXhZ8F7uqV3zW5Z8R9pG5Z8RDZXhZ8F7uqV3zW5', // hashed "admin123"
      name: 'Admin User',
      roleId: adminRole.id,
      status: UserStatus.ACTIVE,
    },
  });

  const salesUser = await prisma.user.create({
    data: {
      email: 'sales@hashinsight.com',
      passwordHash: '$2a$10$rH9pGQK8QZz8RDZXhZ8F7uqV3zW5Z8R9pG5Z8RDZXhZ8F7uqV3zW5', // hashed "sales123"
      name: 'Sales Manager',
      roleId: salesRole.id,
      status: UserStatus.ACTIVE,
    },
  });

  console.log('✅ Created 2 users');

  // ===================================
  // 3. LEADS
  // ===================================

  const leads = await prisma.lead.createMany({
    data: [
      {
        source: LeadSource.WEBSITE,
        company: 'Bitcoin Mining Co',
        contactName: 'John Smith',
        email: 'john@btcmining.com',
        phone: '+1-555-0101',
        status: LeadStatus.NEW,
        score: 85,
        assignedTo: salesUser.id,
      },
      {
        source: LeadSource.REFERRAL,
        company: 'Crypto Holdings Ltd',
        contactName: 'Sarah Johnson',
        email: 'sarah@cryptoholdings.com',
        phone: '+1-555-0102',
        status: LeadStatus.CONTACTED,
        score: 72,
        assignedTo: salesUser.id,
      },
      {
        source: LeadSource.TRADE_SHOW,
        company: 'Digital Assets Corp',
        contactName: 'Michael Chen',
        email: 'michael@digitalassets.com',
        phone: '+1-555-0103',
        status: LeadStatus.QUALIFIED,
        score: 90,
        assignedTo: salesUser.id,
      },
      {
        source: LeadSource.EMAIL,
        company: 'Hashrate Solutions',
        contactName: 'Emily Davis',
        email: 'emily@hashratesolutions.com',
        phone: '+1-555-0104',
        status: LeadStatus.CONVERTED,
        score: 95,
        assignedTo: salesUser.id,
      },
      {
        source: LeadSource.SOCIAL_MEDIA,
        company: 'Mining Ventures Inc',
        contactName: 'David Wilson',
        email: 'david@miningventures.com',
        phone: '+1-555-0105',
        status: LeadStatus.UNQUALIFIED,
        score: 40,
        assignedTo: salesUser.id,
      },
    ],
  });

  const allLeads = await prisma.lead.findMany();
  console.log('✅ Created 5 leads');

  // ===================================
  // 4. ACCOUNTS
  // ===================================

  const account1 = await prisma.account.create({
    data: {
      name: 'Bitcoin Mining Co',
      industry: 'Cryptocurrency Mining',
      size: AccountSize.LARGE,
      status: AccountStatus.ACTIVE,
      ownerId: salesUser.id,
    },
  });

  const account2 = await prisma.account.create({
    data: {
      name: 'Crypto Holdings Ltd',
      industry: 'Digital Asset Management',
      size: AccountSize.MEDIUM,
      status: AccountStatus.ACTIVE,
      ownerId: salesUser.id,
    },
  });

  const account3 = await prisma.account.create({
    data: {
      name: 'Digital Assets Corp',
      industry: 'Blockchain Technology',
      size: AccountSize.ENTERPRISE,
      status: AccountStatus.PROSPECT,
      ownerId: adminUser.id,
    },
  });

  console.log('✅ Created 3 accounts');

  // ===================================
  // 5. CONTACTS
  // ===================================

  await prisma.contact.createMany({
    data: [
      {
        accountId: account1.id,
        name: 'John Smith',
        email: 'john@btcmining.com',
        phone: '+1-555-0101',
        title: 'CEO',
        isPrimary: true,
      },
      {
        accountId: account2.id,
        name: 'Sarah Johnson',
        email: 'sarah@cryptoholdings.com',
        phone: '+1-555-0102',
        title: 'CTO',
        isPrimary: true,
      },
      {
        accountId: account3.id,
        name: 'Michael Chen',
        email: 'michael@digitalassets.com',
        phone: '+1-555-0103',
        title: 'Operations Director',
        isPrimary: true,
      },
    ],
  });

  console.log('✅ Created 3 contacts');

  // ===================================
  // 6. DEALS
  // ===================================

  const deal1 = await prisma.deal.create({
    data: {
      leadId: allLeads[0].id,
      accountId: account1.id,
      title: '500 S19 XP Hosting Contract',
      value: 2500000,
      stage: DealStage.NEGOTIATION,
      probability: 75,
      expectedClose: new Date('2025-11-30'),
      ownerId: salesUser.id,
    },
  });

  const deal2 = await prisma.deal.create({
    data: {
      leadId: allLeads[1].id,
      accountId: account2.id,
      title: '1000 Antminer S21 Purchase & Hosting',
      value: 5000000,
      stage: DealStage.PROPOSAL,
      probability: 60,
      expectedClose: new Date('2025-12-15'),
      ownerId: salesUser.id,
    },
  });

  console.log('✅ Created 2 deals');

  // ===================================
  // 7. CONTRACTS
  // ===================================

  const contract1 = await prisma.contract.create({
    data: {
      dealId: deal1.id,
      accountId: account1.id,
      contractNumber: 'CONT-2025-001',
      startDate: new Date('2025-11-01'),
      endDate: new Date('2026-11-01'),
      value: 2500000,
      status: ContractStatus.ACTIVE,
      signedDate: new Date('2025-10-15'),
    },
  });

  console.log('✅ Created 1 contract');

  // ===================================
  // 8. INVOICES
  // ===================================

  const invoice1 = await prisma.invoice.create({
    data: {
      accountId: account1.id,
      contractId: contract1.id,
      invoiceNumber: 'INV-2025-001',
      issueDate: new Date('2025-10-01'),
      dueDate: new Date('2025-10-31'),
      totalAmount: 50000,
      status: InvoiceStatus.PAID,
    },
  });

  await prisma.invoiceLineItem.createMany({
    data: [
      {
        invoiceId: invoice1.id,
        description: 'Hosting Fee - October 2025',
        quantity: 500,
        unitPrice: 80,
        amount: 40000,
        type: InvoiceLineItemType.HOSTING_FEE,
      },
      {
        invoiceId: invoice1.id,
        description: 'Electricity - October 2025',
        quantity: 1,
        unitPrice: 10000,
        amount: 10000,
        type: InvoiceLineItemType.ELECTRICITY,
      },
    ],
  });

  await prisma.payment.create({
    data: {
      invoiceId: invoice1.id,
      amount: 50000,
      paymentDate: new Date('2025-10-15'),
      method: PaymentMethod.BANK_TRANSFER,
      reference: 'WIRE-20251015-001',
      status: PaymentStatus.COMPLETED,
    },
  });

  console.log('✅ Created invoice and payment');

  // ===================================
  // 9. MINER ASSETS
  // ===================================

  const minerModels = [
    { model: 'Antminer S19 XP', hashrate: 140, power: 3010 },
    { model: 'Antminer S21', hashrate: 200, power: 3500 },
    { model: 'Whatsminer M50S', hashrate: 126, power: 3276 },
    { model: 'Antminer S19j Pro', hashrate: 104, power: 3068 },
    { model: 'Whatsminer M60', hashrate: 170, power: 3400 },
  ];

  const minerAssets = [];
  for (let i = 0; i < 10; i++) {
    const model = minerModels[i % minerModels.length];
    const asset = await prisma.minerAsset.create({
      data: {
        accountId: i < 6 ? account1.id : account2.id,
        model: model.model,
        serialNumber: `SN-2025-${String(i + 1).padStart(4, '0')}`,
        hashrate: model.hashrate,
        power: model.power,
        status: i < 8 ? MinerAssetStatus.OPERATIONAL : MinerAssetStatus.MAINTENANCE,
        location: i < 5 ? 'Texas DC-1' : 'Wyoming DC-2',
        purchasedAt: new Date('2025-09-01'),
      },
    });
    minerAssets.push(asset);
  }

  console.log('✅ Created 10 miner assets');

  // ===================================
  // 10. MINER BATCHES & SHIPMENTS
  // ===================================

  const batch1 = await prisma.minerBatch.create({
    data: {
      batchNumber: 'BATCH-2025-001',
      totalUnits: 500,
      arrivalDate: new Date('2025-11-15'),
      status: BatchStatus.IN_TRANSIT,
    },
  });

  await prisma.shipment.create({
    data: {
      batchId: batch1.id,
      trackingNumber: 'TRK-20251001-ABC123',
      carrier: 'DHL Express',
      shippedAt: new Date('2025-10-01'),
      status: ShipmentStatus.IN_TRANSIT,
    },
  });

  console.log('✅ Created batch and shipment');

  // ===================================
  // 11. AUTOMATION RULES
  // ===================================

  const rule1 = await prisma.automationRule.create({
    data: {
      name: 'Auto-assign high-score leads to senior sales',
      triggerType: AutomationTrigger.LEAD_CREATED,
      conditionsJson: {
        score: { gte: 80 },
      },
      actionsJson: {
        assign_to: salesUser.id,
        send_notification: true,
      },
      enabled: true,
    },
  });

  const rule2 = await prisma.automationRule.create({
    data: {
      name: 'Send reminder for overdue invoices',
      triggerType: AutomationTrigger.INVOICE_OVERDUE,
      conditionsJson: {
        days_overdue: { gte: 3 },
      },
      actionsJson: {
        send_email: true,
        create_task: true,
      },
      enabled: true,
    },
  });

  const rule3 = await prisma.automationRule.create({
    data: {
      name: 'Create ticket when asset goes offline',
      triggerType: AutomationTrigger.ASSET_OFFLINE,
      conditionsJson: {
        offline_duration: { gte: 30 },
      },
      actionsJson: {
        create_ticket: true,
        priority: 'HIGH',
        notify_ops: true,
      },
      enabled: true,
    },
  });

  console.log('✅ Created 3 automation rules');

  // ===================================
  // 12. ACTIVITIES & NOTES
  // ===================================

  await prisma.activity.createMany({
    data: [
      {
        type: ActivityType.CALL,
        entityType: EntityType.LEAD,
        entityId: allLeads[0].id,
        userId: salesUser.id,
        subject: 'Discovery call with Bitcoin Mining Co',
        description: 'Discussed hosting requirements and pricing',
        scheduledAt: new Date('2025-10-05'),
        completedAt: new Date('2025-10-05'),
      },
      {
        type: ActivityType.MEETING,
        entityType: EntityType.DEAL,
        entityId: deal1.id,
        userId: salesUser.id,
        subject: 'Contract negotiation meeting',
        scheduledAt: new Date('2025-10-20'),
      },
    ],
  });

  await prisma.note.createMany({
    data: [
      {
        entityType: EntityType.ACCOUNT,
        entityId: account1.id,
        userId: salesUser.id,
        content: 'Customer is very interested in expanding to 1000 units next quarter',
      },
      {
        entityType: EntityType.DEAL,
        entityId: deal2.id,
        userId: adminUser.id,
        content: 'Need to follow up on pricing proposal by end of week',
      },
    ],
  });

  console.log('✅ Created activities and notes');

  // ===================================
  // 13. TAGS
  // ===================================

  await prisma.tag.createMany({
    data: [
      { name: 'VIP', color: '#FFD700', entityType: EntityType.ACCOUNT, entityId: account1.id },
      { name: 'High Value', color: '#32CD32', entityType: EntityType.ACCOUNT, entityId: account2.id },
      { name: 'Hot', color: '#FF4500', entityType: EntityType.LEAD, entityId: allLeads[0].id },
      { name: 'Urgent', color: '#FF6347', entityType: EntityType.LEAD, entityId: allLeads[2].id },
      { name: 'Q1', color: '#4169E1', entityType: EntityType.DEAL, entityId: deal1.id },
      { name: 'High Priority', color: '#DC143C', entityType: EntityType.DEAL, entityId: deal1.id },
      { name: 'Q4', color: '#6A5ACD', entityType: EntityType.DEAL, entityId: deal2.id },
      { name: 'Long-term', color: '#20B2AA', entityType: EntityType.CONTRACT, entityId: contract1.id },
    ],
  });

  console.log('✅ Created tags');

  // ===================================
  // 14. ANALYTICS & FORECASTS
  // ===================================

  await prisma.analyticSnapshot.createMany({
    data: [
      {
        snapshotDate: new Date('2025-10-01'),
        metricType: 'total_revenue',
        metricValue: 150000,
        metadataJson: { currency: 'USD', period: 'monthly' },
      },
      {
        snapshotDate: new Date('2025-10-01'),
        metricType: 'active_accounts',
        metricValue: 15,
        metadataJson: { status: 'active' },
      },
      {
        snapshotDate: new Date('2025-10-01'),
        metricType: 'total_hashrate',
        metricValue: 1400,
        metadataJson: { unit: 'TH/s' },
      },
    ],
  });

  await prisma.forecast.createMany({
    data: [
      {
        entityType: EntityType.DEAL,
        entityId: deal1.id,
        metric: 'close_probability',
        predictedValue: 0.75,
        confidence: 0.85,
        forecastDate: new Date('2025-11-30'),
      },
      {
        entityType: EntityType.ACCOUNT,
        entityId: account1.id,
        metric: 'revenue_next_quarter',
        predictedValue: 175000,
        confidence: 0.78,
        forecastDate: new Date('2026-01-01'),
      },
    ],
  });

  console.log('✅ Created analytics and forecasts');

  // ===================================
  // 15. OPS TICKETS & MAINTENANCE
  // ===================================

  const ticket1 = await prisma.opsTicket.create({
    data: {
      accountId: account1.id,
      assetId: minerAssets[8].id,
      type: TicketType.HARDWARE_ISSUE,
      priority: TicketPriority.HIGH,
      status: TicketStatus.OPEN,
      subject: 'Miner hashrate degradation',
      description: 'Hashrate dropped by 15% over last 48 hours',
      assignedTo: adminUser.id,
    },
  });

  await prisma.maintenanceLog.create({
    data: {
      assetId: minerAssets[8].id,
      ticketId: ticket1.id,
      type: MaintenanceType.CORRECTIVE,
      description: 'Replaced cooling fan and cleaned heat sink',
      cost: 150,
      performedBy: adminUser.id,
      performedAt: new Date('2025-10-06'),
    },
  });

  console.log('✅ Created ops ticket and maintenance log');

  // ===================================
  // 16. INVENTORY
  // ===================================

  await prisma.inventory.createMany({
    data: [
      {
        model: 'Antminer S19 XP',
        availableUnits: 50,
        reservedUnits: 25,
        location: 'Texas DC-1',
      },
      {
        model: 'Antminer S21',
        availableUnits: 100,
        reservedUnits: 50,
        location: 'Wyoming DC-2',
      },
      {
        model: 'Whatsminer M60',
        availableUnits: 30,
        reservedUnits: 10,
        location: 'Texas DC-1',
      },
    ],
  });

  console.log('✅ Created inventory records');

  // ===================================
  // 17. WEBHOOKS & EVENT QUEUE
  // ===================================

  await prisma.webhook.create({
    data: {
      url: 'https://api.example.com/webhooks/crm',
      events: ['deal.created', 'deal.updated', 'invoice.paid'],
      secret: 'whsec_' + Math.random().toString(36).substring(2, 15),
      enabled: true,
    },
  });

  await prisma.eventQueue.createMany({
    data: [
      {
        eventType: 'lead.created',
        payloadJson: { leadId: allLeads[0].id, source: 'website' },
        status: EventQueueStatus.COMPLETED,
        processedAt: new Date(),
      },
      {
        eventType: 'deal.stage_changed',
        payloadJson: { dealId: deal1.id, oldStage: 'PROPOSAL', newStage: 'NEGOTIATION' },
        status: EventQueueStatus.PENDING,
      },
    ],
  });

  console.log('✅ Created webhooks and event queue');

  // ===================================
  // 18. AUDIT LOGS
  // ===================================

  await prisma.auditLog.createMany({
    data: [
      {
        userId: adminUser.id,
        action: 'CREATE',
        resource: 'account',
        details: { accountId: account1.id, name: account1.name },
        ip: '192.168.1.100',
      },
      {
        userId: salesUser.id,
        action: 'UPDATE',
        resource: 'deal',
        details: { dealId: deal1.id, field: 'stage', oldValue: 'PROPOSAL', newValue: 'NEGOTIATION' },
        ip: '192.168.1.101',
      },
      {
        userId: adminUser.id,
        action: 'CREATE',
        resource: 'contract',
        details: { contractId: contract1.id, contractNumber: contract1.contractNumber },
        ip: '192.168.1.100',
      },
    ],
  });

  console.log('✅ Created audit logs');

  // ===================================
  // 19. API KEYS
  // ===================================

  await prisma.apiKey.createMany({
    data: [
      {
        userId: adminUser.id,
        keyHash: 'sk_live_' + Math.random().toString(36).substring(2, 15),
        name: 'Production API Key',
        scopes: ['read', 'write', 'admin'],
        expiresAt: new Date('2026-12-31'),
      },
      {
        userId: salesUser.id,
        keyHash: 'sk_test_' + Math.random().toString(36).substring(2, 15),
        name: 'Sales Dashboard API',
        scopes: ['read'],
        expiresAt: new Date('2026-06-30'),
      },
    ],
  });

  console.log('✅ Created API keys');

  // ===================================
  // 20. BILLING CYCLES & REVENUE RECOGNITION
  // ===================================

  await prisma.billingCycle.create({
    data: {
      contractId: contract1.id,
      startDate: new Date('2025-10-01'),
      endDate: new Date('2025-10-31'),
      btcProduced: 0.15,
      powerConsumed: 360000,
      serviceFee: 50000,
    },
  });

  await prisma.revenueRecognition.create({
    data: {
      invoiceId: invoice1.id,
      period: '2025-10',
      amount: 50000,
      recognizedAt: new Date('2025-10-31'),
    },
  });

  console.log('✅ Created billing cycle and revenue recognition');

  console.log('\n🎉 Seed completed successfully!');
  console.log('\n📊 Summary:');
  console.log('  - 4 Roles (Admin, Sales, Operations, Finance)');
  console.log('  - 2 Users (admin@hashinsight.com, sales@hashinsight.com)');
  console.log('  - 5 Leads (various sources and statuses)');
  console.log('  - 3 Accounts');
  console.log('  - 2 Deals (different stages)');
  console.log('  - 10 Miner Assets');
  console.log('  - 3 Automation Rules');
  console.log('  - Complete related data (invoices, tickets, analytics, etc.)');
}

main()
  .catch((e) => {
    console.error('❌ Seed failed:', e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
