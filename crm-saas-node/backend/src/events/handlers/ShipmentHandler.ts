import { BaseEventHandler } from './BaseHandler';
import { EventPayload } from '../publisher';

export class ShipmentShippedHandler extends BaseEventHandler {
  eventType = 'shipment.shipped';

  async handle(event: EventPayload): Promise<void> {
    console.log(`📦 Shipment shipped: ${event.data.trackingNumber}`, {
      carrier: event.data.carrier,
    });
  }
}

export class ShipmentDeliveredHandler extends BaseEventHandler {
  eventType = 'shipment.delivered';

  async handle(event: EventPayload): Promise<void> {
    console.log(`✅ Shipment delivered: ${event.data.trackingNumber}`, {
      location: event.data.location,
    });
  }
}
