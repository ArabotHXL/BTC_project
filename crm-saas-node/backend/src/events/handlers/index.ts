import { BaseEventHandler } from './BaseHandler';
import { LeadCapturedHandler, LeadConvertedHandler } from './LeadHandler';
import { DealStageChangedHandler, DealWonHandler } from './DealHandler';
import { InvoiceCreatedHandler, InvoiceIssuedHandler, InvoicePaidHandler } from './InvoiceHandler';
import { ContractGeneratedHandler, ContractSignedHandler } from './ContractHandler';
import { PaymentReceivedHandler, PaymentConfirmedHandler } from './PaymentHandler';
import { AssetStatusChangedHandler, AssetDeployedHandler, AssetMiningStartedHandler } from './AssetHandler';
import { ShipmentShippedHandler, ShipmentDeliveredHandler } from './ShipmentHandler';

export class HandlerRegistry {
  private handlers: Map<string, BaseEventHandler[]> = new Map();

  constructor() {
    this.registerHandlers();
  }

  private registerHandlers(): void {
    // Lead handlers (2)
    this.register(new LeadCapturedHandler());
    this.register(new LeadConvertedHandler());

    // Deal handlers (2)
    this.register(new DealStageChangedHandler());
    this.register(new DealWonHandler());

    // Contract handlers (2)
    this.register(new ContractGeneratedHandler());
    this.register(new ContractSignedHandler());

    // Invoice handlers (3)
    this.register(new InvoiceCreatedHandler());
    this.register(new InvoiceIssuedHandler());
    this.register(new InvoicePaidHandler());

    // Payment handlers (2)
    this.register(new PaymentReceivedHandler());
    this.register(new PaymentConfirmedHandler());

    // Asset handlers (3)
    this.register(new AssetStatusChangedHandler());
    this.register(new AssetDeployedHandler());
    this.register(new AssetMiningStartedHandler());

    // Shipment handlers (2)
    this.register(new ShipmentShippedHandler());
    this.register(new ShipmentDeliveredHandler());

    console.log(`✅ Registered ${this.getAllEventTypes().length} event handlers`);
  }

  register(handler: BaseEventHandler): void {
    const eventType = handler.eventType;
    if (!this.handlers.has(eventType)) {
      this.handlers.set(eventType, []);
    }
    this.handlers.get(eventType)!.push(handler);
  }

  getHandlers(eventType: string): BaseEventHandler[] {
    return this.handlers.get(eventType) || [];
  }

  getAllEventTypes(): string[] {
    return Array.from(this.handlers.keys());
  }
}

export * from './BaseHandler';
