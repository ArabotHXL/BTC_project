import { BaseEventHandler } from './BaseHandler';
import { EventPayload } from '../publisher';

export class AssetStatusChangedHandler extends BaseEventHandler {
  eventType = 'asset.status_changed';

  async handle(event: EventPayload): Promise<void> {
    console.log(`🔄 Asset status changed: ${event.data.serialNumber}`, {
      from: event.data.oldStatus,
      to: event.data.newStatus,
    });
  }
}

export class AssetDeployedHandler extends BaseEventHandler {
  eventType = 'asset.deployed';

  async handle(event: EventPayload): Promise<void> {
    console.log(`🚀 Asset deployed: ${event.data.serialNumber}`, {
      location: event.data.location,
    });
  }
}

export class AssetMiningStartedHandler extends BaseEventHandler {
  eventType = 'asset.mining_started';

  async handle(event: EventPayload): Promise<void> {
    console.log(`⛏️ Asset mining started: ${event.data.serialNumber}`);
  }
}
