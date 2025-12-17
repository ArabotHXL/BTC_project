import { HandlerRegistry } from './handlers';

const registry = new HandlerRegistry();
const eventTypes = registry.getAllEventTypes();

console.log('📋 Registered Event Types:');
console.log('─'.repeat(50));

const expectedEvents = [
  'lead.captured',
  'lead.converted',
  'deal.stage_changed',
  'deal.won',
  'contract.generated',
  'invoice.created',
  'invoice.paid',
  'payment.received',
  'payment.confirmed',
  'asset.status_changed',
  'asset.deployed',
  'asset.mining_started',
  'shipment.shipped',
  'shipment.delivered',
];

let allPresent = true;

for (const expected of expectedEvents) {
  const isPresent = eventTypes.includes(expected);
  const status = isPresent ? '✅' : '❌';
  console.log(`${status} ${expected}`);
  if (!isPresent) allPresent = false;
}

console.log('─'.repeat(50));
console.log(`Total: ${eventTypes.length} handlers registered`);
console.log(`Status: ${allPresent ? '✅ ALL REQUIRED EVENTS COVERED' : '❌ MISSING HANDLERS'}`);

if (!allPresent) {
  process.exit(1);
}
