/**
 * Event Logger - JSONL format event logging system
 * Logs all system events to daily JSONL files under events/YYYY-MM-DD/
 */

import * as fs from 'fs';
import * as path from 'path';
import { Event, EventType, EventSource, EventStatus } from './types';

export class EventLogger {
  private eventsDir: string;

  constructor(eventsBaseDir: string = './events') {
    this.eventsDir = eventsBaseDir;
    this.ensureEventsDirectory();
  }

  /**
   * Append an event to today's JSONL file
   */
  public appendEvent(event: Partial<Event>): void {
    try {
      const fullEvent: Event = {
        ts: new Date().toISOString(),
        type: event.type!,
        source: event.source!,
        key: event.key!,
        status: event.status!,
        latency_ms: event.latency_ms,
        details: event.details,
        actor: event.actor || 'system'
      };

      const today = this.getTodayString();
      const dailyDir = path.join(this.eventsDir, today);
      
      // Ensure daily directory exists
      if (!fs.existsSync(dailyDir)) {
        fs.mkdirSync(dailyDir, { recursive: true });
      }

      const logFile = path.join(dailyDir, `events.jsonl`);
      const logLine = JSON.stringify(fullEvent) + '\n';

      fs.appendFileSync(logFile, logLine, 'utf8');
    } catch (error) {
      console.error('Failed to append event:', error);
    }
  }

  /**
   * Helper: Record a data fetch event
   */
  public recordDataFetch(
    source: EventSource,
    key: string,
    status: EventStatus,
    latency_ms: number,
    details?: Record<string, any>
  ): void {
    this.appendEvent({
      type: 'datahub.fetch',
      source,
      key,
      status,
      latency_ms,
      details
    });
  }

  /**
   * Helper: Record an alert event
   */
  public recordAlert(
    minerId: string,
    ruleId: string,
    status: EventStatus,
    details: Record<string, any>
  ): void {
    this.appendEvent({
      type: 'monitor.alert',
      source: 'system',
      key: `${minerId}:${ruleId}`,
      status,
      details
    });
  }

  /**
   * Helper: Record a control command
   */
  public recordCommand(
    minerId: string,
    command: string,
    actor: string,
    status: EventStatus,
    details?: Record<string, any>
  ): void {
    this.appendEvent({
      type: 'monitor.command',
      source: 'ui',
      key: `${minerId}:${command}`,
      status,
      actor,
      details
    });
  }

  /**
   * Helper: Record an email notification
   */
  public recordEmail(
    to: string,
    subject: string,
    status: EventStatus,
    details?: Record<string, any>
  ): void {
    this.appendEvent({
      type: 'email.sent',
      source: 'system',
      key: to,
      status,
      details: { subject, ...details }
    });
  }

  /**
   * Read events from a specific date
   */
  public readEvents(date: string): Event[] {
    const dailyDir = path.join(this.eventsDir, date);
    const logFile = path.join(dailyDir, 'events.jsonl');

    if (!fs.existsSync(logFile)) {
      return [];
    }

    const content = fs.readFileSync(logFile, 'utf8');
    const lines = content.split('\n').filter(line => line.trim());
    
    return lines.map(line => JSON.parse(line) as Event);
  }

  /**
   * Export events to CSV format
   */
  public exportToCSV(events: Event[]): string {
    const headers = ['timestamp', 'type', 'source', 'key', 'status', 'latency_ms', 'actor', 'details'];
    const rows = events.map(e => [
      e.ts,
      e.type,
      e.source,
      e.key,
      e.status,
      e.latency_ms || '',
      e.actor || '',
      JSON.stringify(e.details || {})
    ]);

    return [
      headers.join(','),
      ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
    ].join('\n');
  }

  private getTodayString(): string {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }

  private ensureEventsDirectory(): void {
    if (!fs.existsSync(this.eventsDir)) {
      fs.mkdirSync(this.eventsDir, { recursive: true });
    }
  }
}

// Export singleton instance
export const eventLogger = new EventLogger();
