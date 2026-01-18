-- Create safety_events table for edge device safety events
CREATE TABLE IF NOT EXISTS safety_events (
    id SERIAL PRIMARY KEY,
    edge_device_id INTEGER NOT NULL,
    site_id INTEGER NOT NULL,
    miner_id INTEGER,
    
    action VARCHAR(50) NOT NULL,
    reason VARCHAR(255) NOT NULL,
    
    temp_max FLOAT,
    
    ts TIMESTAMP NOT NULL,
    snapshot_json TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_safety_events_edge_device 
        FOREIGN KEY (edge_device_id) REFERENCES edge_devices(id) ON DELETE RESTRICT,
    CONSTRAINT fk_safety_events_site 
        FOREIGN KEY (site_id) REFERENCES hosting_sites(id) ON DELETE RESTRICT,
    CONSTRAINT fk_safety_events_miner 
        FOREIGN KEY (miner_id) REFERENCES hosted_miners(id) ON DELETE SET NULL
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS ix_safety_events_site_ts 
    ON safety_events(site_id, ts DESC);

CREATE INDEX IF NOT EXISTS ix_safety_events_edge_device 
    ON safety_events(edge_device_id);

CREATE INDEX IF NOT EXISTS ix_safety_events_action 
    ON safety_events(action);

CREATE INDEX IF NOT EXISTS ix_safety_events_created_at 
    ON safety_events(created_at DESC);

COMMENT ON TABLE safety_events IS 'Edge device safety events (thermal shutdown, emergency stop, etc.)';
COMMENT ON COLUMN safety_events.action IS 'Safety action type (e.g., THERMAL_SHUTDOWN, EMERGENCY_STOP)';
COMMENT ON COLUMN safety_events.reason IS 'Reason for the safety event';
COMMENT ON COLUMN safety_events.temp_max IS 'Maximum temperature recorded at time of event';
COMMENT ON COLUMN safety_events.ts IS 'Event timestamp from edge device';
COMMENT ON COLUMN safety_events.snapshot_json IS 'Full device state snapshot at time of event';
