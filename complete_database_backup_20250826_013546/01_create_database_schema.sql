-- ========================================
-- BTC Mining Calculator Database Schema
-- Generated: 2025-08-26T01:35:49.729221
-- ========================================

-- 创建数据库表
-- ========================================

-- 表: activities
CREATE TABLE activities (    id SERIAL,
    customer_id INTEGER,
    lead_id INTEGER,
    deal_id INTEGER,
    type VARCHAR(50) NOT NULL DEFAULT '备注'::character varying,
    summary VARCHAR(200) NOT NULL,
    details TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by_id INTEGER,
    created_by VARCHAR(100),
    PRIMARY KEY (id)
);

-- 表: analysis_reports
CREATE TABLE analysis_reports (    id SERIAL,
    report_type VARCHAR(50) NOT NULL,
    generated_at TIMESTAMP NOT NULL,
    title VARCHAR(200) NOT NULL,
    summary TEXT,
    key_findings JSON,
    recommendations JSON,
    risk_assessment JSON,
    data_period_start TIMESTAMP,
    data_period_end TIMESTAMP,
    confidence_score NUMERIC(3,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id)
);

-- 表: api_usage
CREATE TABLE api_usage (    id SERIAL,
    user_id INTEGER NOT NULL,
    date TIMESTAMP NOT NULL,
    endpoint VARCHAR(200) NOT NULL,
    calls_count INTEGER,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    PRIMARY KEY (id)
);

-- 表: commission_edit_history
CREATE TABLE commission_edit_history (    id SERIAL,
    commission_record_id INTEGER NOT NULL,
    edited_at TIMESTAMP NOT NULL,
    edited_by_id INTEGER,
    edited_by_name VARCHAR(100),
    field_name VARCHAR(50) NOT NULL,
    old_value TEXT,
    new_value TEXT,
    change_reason VARCHAR(200),
    PRIMARY KEY (id)
);

-- 表: commission_records
CREATE TABLE commission_records (    id SERIAL,
    deal_id INTEGER NOT NULL,
    customer_id INTEGER NOT NULL,
    record_date TIMESTAMP NOT NULL,
    record_month VARCHAR(7) NOT NULL,
    client_monthly_profit DOUBLE PRECISION NOT NULL,
    client_btc_mined DOUBLE PRECISION,
    btc_price DOUBLE PRECISION,
    commission_type VARCHAR(20) NOT NULL,
    commission_rate DOUBLE PRECISION,
    commission_amount DOUBLE PRECISION NOT NULL,
    paid BOOLEAN NOT NULL,
    paid_date TIMESTAMP,
    notes TEXT,
    created_by_id INTEGER,
    PRIMARY KEY (id)
);

-- 表: crm_activities
CREATE TABLE crm_activities (    id SERIAL,
    customer_id INTEGER NOT NULL,
    lead_id INTEGER,
    deal_id INTEGER,
    type VARCHAR(50) NOT NULL,
    summary VARCHAR(200) NOT NULL,
    details TEXT,
    created_at TIMESTAMP NOT NULL,
    created_by VARCHAR(100),
    created_by_id INTEGER,
    PRIMARY KEY (id)
);

-- 表: crm_contacts
CREATE TABLE crm_contacts (    id SERIAL,
    customer_id INTEGER NOT NULL,
    name VARCHAR(100) NOT NULL,
    position VARCHAR(100),
    email VARCHAR(256),
    phone VARCHAR(50),
    primary BOOLEAN NOT NULL,
    created_at TIMESTAMP NOT NULL,
    notes TEXT,
    PRIMARY KEY (id)
);

-- 表: crm_customers
CREATE TABLE crm_customers (    id SERIAL,
    name VARCHAR(100) NOT NULL,
    company VARCHAR(200),
    email VARCHAR(256),
    phone VARCHAR(50),
    address VARCHAR(500),
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    tags VARCHAR(500),
    customer_type VARCHAR(50) NOT NULL,
    mining_capacity DOUBLE PRECISION,
    notes TEXT,
    created_by_id INTEGER,
    PRIMARY KEY (id)
);

-- 表: crm_deals
CREATE TABLE crm_deals (    id SERIAL,
    customer_id INTEGER NOT NULL,
    lead_id INTEGER,
    title VARCHAR(200) NOT NULL,
    status USER-DEFINED NOT NULL,
    value DOUBLE PRECISION NOT NULL,
    currency VARCHAR(10) NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    expected_close_date TIMESTAMP,
    closed_date TIMESTAMP,
    assigned_to VARCHAR(100),
    description TEXT,
    mining_capacity DOUBLE PRECISION,
    electricity_cost DOUBLE PRECISION,
    contract_term INTEGER,
    created_by_id INTEGER,
    assigned_to_id INTEGER,
    commission_type VARCHAR(20) DEFAULT 'percentage'::character varying,
    commission_rate DOUBLE PRECISION,
    commission_amount DOUBLE PRECISION,
    mining_farm_name VARCHAR(200),
    mining_farm_location VARCHAR(200),
    client_investment DOUBLE PRECISION,
    monthly_profit_estimate DOUBLE PRECISION,
    PRIMARY KEY (id)
);

-- 表: crm_leads
CREATE TABLE crm_leads (    id SERIAL,
    customer_id INTEGER NOT NULL,
    title VARCHAR(200) NOT NULL,
    status USER-DEFINED NOT NULL,
    source VARCHAR(100),
    estimated_value DOUBLE PRECISION NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    assigned_to VARCHAR(100),
    description TEXT,
    next_follow_up TIMESTAMP,
    created_by_id INTEGER,
    assigned_to_id INTEGER,
    PRIMARY KEY (id)
);

-- 表: customers
CREATE TABLE customers (    id SERIAL,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(50),
    company VARCHAR(255),
    status VARCHAR(50) DEFAULT 'active'::character varying,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id)
);

-- 表: historical_prices
CREATE TABLE historical_prices (    id SERIAL,
    price_date DATE NOT NULL,
    btc_price NUMERIC(12,2) NOT NULL,
    volume_24h NUMERIC(15,2) DEFAULT 0,
    market_cap NUMERIC(20,2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id)
);

-- 表: leads
CREATE TABLE leads (    id SERIAL,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(50),
    company VARCHAR(255),
    source VARCHAR(100),
    status VARCHAR(50) DEFAULT 'new'::character varying,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id)
);

-- 表: login_records
CREATE TABLE login_records (    id SERIAL,
    email VARCHAR(256) NOT NULL,
    login_time TIMESTAMP NOT NULL,
    successful BOOLEAN NOT NULL,
    ip_address VARCHAR(50),
    login_location VARCHAR(512),
    PRIMARY KEY (id)
);

-- 表: market_analytics
CREATE TABLE market_analytics (    id SERIAL,
    recorded_at TIMESTAMP NOT NULL,
    btc_price NUMERIC(15,2) NOT NULL,
    btc_market_cap BIGINT,
    btc_volume_24h BIGINT,
    network_hashrate NUMERIC(10,2) NOT NULL,
    network_difficulty NUMERIC(20,2) NOT NULL,
    block_reward NUMERIC(10,8),
    fear_greed_index INTEGER,
    price_change_1h NUMERIC(8,4),
    price_change_24h NUMERIC(8,4),
    price_change_7d NUMERIC(8,4),
    source VARCHAR(50) DEFAULT 'multiple'::character varying,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    current_block_height INTEGER,
    median_time INTEGER,
    total_work TEXT,
    sync_progress NUMERIC(5,2),
    blocks_until_adjustment INTEGER,
    PRIMARY KEY (id)
);

-- 表: market_analytics_enhanced
CREATE TABLE market_analytics_enhanced (    id SERIAL,
    recorded_at TIMESTAMP NOT NULL,
    total_spot_volume BIGINT,
    total_futures_volume BIGINT,
    total_options_volume BIGINT,
    weighted_avg_price NUMERIC(12,2),
    avg_funding_rate NUMERIC(8,6),
    data_completeness NUMERIC(5,2),
    exchange_count INTEGER,
    source_detail JSONB,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now(),
    PRIMARY KEY (id)
);

-- 表: miner_models
CREATE TABLE miner_models (    id SERIAL,
    model_name VARCHAR(100) NOT NULL,
    manufacturer VARCHAR(50) NOT NULL,
    reference_hashrate DOUBLE PRECISION NOT NULL,
    reference_power INTEGER NOT NULL,
    reference_efficiency DOUBLE PRECISION,
    release_date DATE,
    reference_price DOUBLE PRECISION,
    is_active BOOLEAN,
    is_liquid_cooled BOOLEAN,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    chip_type VARCHAR(50),
    fan_count INTEGER,
    operating_temp_min INTEGER,
    operating_temp_max INTEGER,
    noise_level INTEGER,
    length_mm DOUBLE PRECISION,
    width_mm DOUBLE PRECISION,
    height_mm DOUBLE PRECISION,
    weight_kg DOUBLE PRECISION,
    PRIMARY KEY (id)
);

-- 表: miner_specs
CREATE TABLE miner_specs (    id SERIAL,
    model VARCHAR(100) NOT NULL,
    hashrate DOUBLE PRECISION NOT NULL,
    power_consumption DOUBLE PRECISION NOT NULL,
    price DOUBLE PRECISION,
    release_date DATE,
    efficiency DOUBLE PRECISION,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id)
);

-- 表: mining_metrics
CREATE TABLE mining_metrics (    id SERIAL,
    recorded_at TIMESTAMP NOT NULL,
    hashrate_change_24h NUMERIC(5,2),
    difficulty_adjustment NUMERIC(5,2),
    next_difficulty_estimate NUMERIC(20,2),
    mempool_size INTEGER,
    avg_block_time NUMERIC(6,2),
    mining_revenue_per_th NUMERIC(10,6),
    network_value_to_transactions NUMERIC(8,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id)
);

-- 表: network_snapshots
CREATE TABLE network_snapshots (    id SERIAL,
    recorded_at TIMESTAMP NOT NULL,
    btc_price DOUBLE PRECISION NOT NULL,
    network_difficulty DOUBLE PRECISION NOT NULL,
    network_hashrate DOUBLE PRECISION NOT NULL,
    block_reward DOUBLE PRECISION NOT NULL,
    price_source VARCHAR(50),
    data_source VARCHAR(50),
    is_valid BOOLEAN,
    api_response_time DOUBLE PRECISION,
    PRIMARY KEY (id)
);

-- 表: payments
CREATE TABLE payments (    id SERIAL,
    subscription_id INTEGER NOT NULL,
    amount DOUBLE PRECISION NOT NULL,
    currency VARCHAR(3) NOT NULL,
    status USER-DEFINED NOT NULL,
    stripe_payment_intent_id VARCHAR(255),
    stripe_charge_id VARCHAR(255),
    invoice_number VARCHAR(100),
    invoice_url VARCHAR(500),
    payment_date TIMESTAMP,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    PRIMARY KEY (id)
);

-- 表: plans
CREATE TABLE plans (    id VARCHAR NOT NULL,
    name VARCHAR NOT NULL,
    price INTEGER,
    max_miners INTEGER,
    coins TEXT,
    history_days INTEGER,
    allow_api BOOLEAN,
    allow_scenarios BOOLEAN,
    allow_advanced_analytics BOOLEAN,
    created_at TIMESTAMP,
    PRIMARY KEY (id)
);

-- 表: portfolio_history
CREATE TABLE portfolio_history (    id SERIAL,
    portfolio_id INTEGER NOT NULL,
    snapshot_date TIMESTAMP NOT NULL,
    btc_inventory NUMERIC(12,8) NOT NULL,
    btc_price_usd NUMERIC(12,2) NOT NULL,
    inventory_value_usd NUMERIC(15,2) NOT NULL,
    unrealized_pl_percent NUMERIC(8,4) NOT NULL,
    cash_reserves NUMERIC(15,2) NOT NULL,
    total_portfolio_value NUMERIC(15,2) NOT NULL,
    PRIMARY KEY (id)
);

-- 表: subscription_plans
CREATE TABLE subscription_plans (    id VARCHAR(50) NOT NULL,
    name VARCHAR(100) NOT NULL,
    price DOUBLE PRECISION,
    currency VARCHAR(10),
    max_miners INTEGER,
    max_historical_days INTEGER,
    allow_batch_calculator BOOLEAN,
    allow_crm_system BOOLEAN,
    allow_advanced_analytics BOOLEAN,
    allow_api_access BOOLEAN,
    allow_custom_scenarios BOOLEAN,
    allow_professional_reports BOOLEAN,
    allow_user_management BOOLEAN,
    allow_priority_support BOOLEAN,
    available_miner_models INTEGER,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    PRIMARY KEY (id)
);

-- 表: subscriptions
CREATE TABLE subscriptions (    id SERIAL,
    user_id INTEGER,
    plan_id VARCHAR,
    stripe_customer_id VARCHAR,
    stripe_subscription_id VARCHAR,
    stripe_price_id VARCHAR,
    status VARCHAR,
    current_period_start TIMESTAMP,
    current_period_end TIMESTAMP,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    PRIMARY KEY (id)
);

-- 表: technical_indicators
CREATE TABLE technical_indicators (    id SERIAL,
    recorded_at TIMESTAMP NOT NULL,
    sma_20 NUMERIC(12,2),
    sma_50 NUMERIC(12,2),
    ema_12 NUMERIC(12,2),
    ema_26 NUMERIC(12,2),
    rsi_14 NUMERIC(5,2),
    macd NUMERIC(8,4),
    bollinger_upper NUMERIC(12,2),
    bollinger_lower NUMERIC(12,2),
    volatility_30d NUMERIC(5,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    volatility REAL DEFAULT 0.05,
    PRIMARY KEY (id)
);

-- 表: user_access
CREATE TABLE user_access (    id SERIAL,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(256) NOT NULL,
    company VARCHAR(200),
    position VARCHAR(100),
    created_at TIMESTAMP NOT NULL,
    access_days INTEGER NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    notes TEXT,
    last_login TIMESTAMP,
    role VARCHAR(20) NOT NULL DEFAULT 'customer'::character varying,
    created_by_id INTEGER,
    username VARCHAR(50),
    password_hash VARCHAR(512),
    is_email_verified BOOLEAN DEFAULT false,
    email_verification_token VARCHAR(100),
    subscription_plan VARCHAR(20) NOT NULL DEFAULT 'free'::character varying,
    PRIMARY KEY (id)
);

-- 表: user_miners
CREATE TABLE user_miners (    id SERIAL,
    user_id INTEGER NOT NULL,
    miner_model_id INTEGER NOT NULL,
    custom_name VARCHAR(100),
    quantity INTEGER NOT NULL DEFAULT 1,
    actual_hashrate DOUBLE PRECISION NOT NULL,
    actual_power INTEGER NOT NULL,
    actual_price DOUBLE PRECISION NOT NULL,
    electricity_cost DOUBLE PRECISION NOT NULL,
    decay_rate_monthly DOUBLE PRECISION NOT NULL DEFAULT 0.5,
    status VARCHAR(20) NOT NULL DEFAULT 'active'::character varying,
    location VARCHAR(200),
    purchase_date DATE,
    notes TEXT,
    original_hashrate DOUBLE PRECISION,
    last_maintenance_date DATE,
    maintenance_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP NOT NULL DEFAULT now(),
    PRIMARY KEY (id)
);

-- 表: user_portfolios
CREATE TABLE user_portfolios (    id SERIAL,
    user_id INTEGER NOT NULL,
    btc_inventory NUMERIC(12,8) NOT NULL DEFAULT 0,
    avg_cost_basis NUMERIC(12,2) NOT NULL DEFAULT 0,
    cash_reserves NUMERIC(15,2) NOT NULL DEFAULT 0,
    monthly_opex NUMERIC(12,2) NOT NULL DEFAULT 0,
    electricity_cost_kwh NUMERIC(6,4) NOT NULL DEFAULT 0.05,
    facility_capacity_mw NUMERIC(8,3) NOT NULL DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    is_active BOOLEAN DEFAULT true,
    PRIMARY KEY (id)
);

-- 表: user_subscriptions
CREATE TABLE user_subscriptions (    id SERIAL,
    user_id INTEGER NOT NULL,
    plan_id VARCHAR(50) NOT NULL,
    status VARCHAR(20),
    started_at TIMESTAMP,
    expires_at TIMESTAMP,
    cancelled_at TIMESTAMP,
    stripe_subscription_id VARCHAR(100),
    stripe_customer_id VARCHAR(100),
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    PRIMARY KEY (id)
);

-- 表: users
CREATE TABLE users (    id SERIAL,
    email VARCHAR(120) NOT NULL,
    username VARCHAR(80),
    password_hash VARCHAR(256) NOT NULL,
    is_active BOOLEAN,
    is_verified BOOLEAN,
    created_at TIMESTAMP,
    last_login TIMESTAMP,
    role VARCHAR(20),
    PRIMARY KEY (id)
);

-- 外键约束
-- ========================================

ALTER TABLE activities ADD CONSTRAINT fk_activities_customer_id FOREIGN KEY (customer_id) REFERENCES crm_customers(id);
ALTER TABLE activities ADD CONSTRAINT fk_activities_lead_id FOREIGN KEY (lead_id) REFERENCES crm_leads(id);
ALTER TABLE activities ADD CONSTRAINT fk_activities_deal_id FOREIGN KEY (deal_id) REFERENCES crm_deals(id);
ALTER TABLE activities ADD CONSTRAINT fk_activities_created_by_id FOREIGN KEY (created_by_id) REFERENCES user_access(id);
ALTER TABLE api_usage ADD CONSTRAINT fk_api_usage_user_id FOREIGN KEY (user_id) REFERENCES users(id);
ALTER TABLE commission_edit_history ADD CONSTRAINT fk_commission_edit_history_commission_record_id FOREIGN KEY (commission_record_id) REFERENCES commission_records(id);
ALTER TABLE commission_edit_history ADD CONSTRAINT fk_commission_edit_history_edited_by_id FOREIGN KEY (edited_by_id) REFERENCES user_access(id);
ALTER TABLE commission_records ADD CONSTRAINT fk_commission_records_deal_id FOREIGN KEY (deal_id) REFERENCES crm_deals(id);
ALTER TABLE commission_records ADD CONSTRAINT fk_commission_records_customer_id FOREIGN KEY (customer_id) REFERENCES crm_customers(id);
ALTER TABLE commission_records ADD CONSTRAINT fk_commission_records_created_by_id FOREIGN KEY (created_by_id) REFERENCES user_access(id);
ALTER TABLE crm_activities ADD CONSTRAINT fk_crm_activities_customer_id FOREIGN KEY (customer_id) REFERENCES crm_customers(id);
ALTER TABLE crm_activities ADD CONSTRAINT fk_crm_activities_lead_id FOREIGN KEY (lead_id) REFERENCES crm_leads(id);
ALTER TABLE crm_activities ADD CONSTRAINT fk_crm_activities_deal_id FOREIGN KEY (deal_id) REFERENCES crm_deals(id);
ALTER TABLE crm_activities ADD CONSTRAINT fk_crm_activities_created_by_id FOREIGN KEY (created_by_id) REFERENCES user_access(id);
ALTER TABLE crm_contacts ADD CONSTRAINT fk_crm_contacts_customer_id FOREIGN KEY (customer_id) REFERENCES crm_customers(id);
ALTER TABLE crm_customers ADD CONSTRAINT fk_crm_customers_created_by_id FOREIGN KEY (created_by_id) REFERENCES user_access(id);
ALTER TABLE crm_deals ADD CONSTRAINT fk_crm_deals_customer_id FOREIGN KEY (customer_id) REFERENCES crm_customers(id);
ALTER TABLE crm_deals ADD CONSTRAINT fk_crm_deals_lead_id FOREIGN KEY (lead_id) REFERENCES crm_leads(id);
ALTER TABLE crm_deals ADD CONSTRAINT fk_crm_deals_created_by_id FOREIGN KEY (created_by_id) REFERENCES user_access(id);
ALTER TABLE crm_deals ADD CONSTRAINT fk_crm_deals_assigned_to_id FOREIGN KEY (assigned_to_id) REFERENCES user_access(id);
ALTER TABLE crm_leads ADD CONSTRAINT fk_crm_leads_customer_id FOREIGN KEY (customer_id) REFERENCES crm_customers(id);
ALTER TABLE crm_leads ADD CONSTRAINT fk_crm_leads_created_by_id FOREIGN KEY (created_by_id) REFERENCES user_access(id);
ALTER TABLE crm_leads ADD CONSTRAINT fk_crm_leads_assigned_to_id FOREIGN KEY (assigned_to_id) REFERENCES user_access(id);
ALTER TABLE payments ADD CONSTRAINT fk_payments_subscription_id FOREIGN KEY (subscription_id) REFERENCES user_subscriptions(id);
ALTER TABLE portfolio_history ADD CONSTRAINT fk_portfolio_history_portfolio_id FOREIGN KEY (portfolio_id) REFERENCES user_portfolios(id);
ALTER TABLE subscriptions ADD CONSTRAINT fk_subscriptions_user_id FOREIGN KEY (user_id) REFERENCES user_access(id);
ALTER TABLE subscriptions ADD CONSTRAINT fk_subscriptions_plan_id FOREIGN KEY (plan_id) REFERENCES plans(id);
ALTER TABLE user_access ADD CONSTRAINT fk_user_access_created_by_id FOREIGN KEY (created_by_id) REFERENCES user_access(id);
ALTER TABLE user_miners ADD CONSTRAINT fk_user_miners_user_id FOREIGN KEY (user_id) REFERENCES user_access(id);
ALTER TABLE user_miners ADD CONSTRAINT fk_user_miners_miner_model_id FOREIGN KEY (miner_model_id) REFERENCES miner_models(id);
ALTER TABLE user_portfolios ADD CONSTRAINT fk_user_portfolios_user_id FOREIGN KEY (user_id) REFERENCES user_access(id);
ALTER TABLE user_subscriptions ADD CONSTRAINT fk_user_subscriptions_user_id FOREIGN KEY (user_id) REFERENCES users(id);
ALTER TABLE user_subscriptions ADD CONSTRAINT fk_user_subscriptions_plan_id FOREIGN KEY (plan_id) REFERENCES subscription_plans(id);

-- 索引
-- ========================================

CREATE INDEX idx_reports_type_date ON analysis_reports (report_type, generated_at);
CREATE UNIQUE INDEX customers_email_key ON customers (email);
CREATE UNIQUE INDEX historical_prices_price_date_key ON historical_prices (price_date);
CREATE INDEX idx_historical_prices_date ON historical_prices (price_date);
CREATE INDEX idx_market_analytics_created_at ON market_analytics (created_at);
CREATE INDEX idx_market_analytics_price ON market_analytics (btc_price);
CREATE INDEX idx_market_analytics_recorded_at ON market_analytics (recorded_at);
CREATE INDEX idx_market_recorded_at ON market_analytics (recorded_at);
CREATE INDEX idx_enhanced_recorded_at ON market_analytics_enhanced (recorded_at);
CREATE UNIQUE INDEX ix_miner_models_model_name ON miner_models (model_name);
CREATE UNIQUE INDEX miner_specs_model_key ON miner_specs (model);
CREATE INDEX idx_mining_recorded_at ON mining_metrics (recorded_at);
CREATE INDEX ix_network_snapshots_recorded_at ON network_snapshots (recorded_at);
CREATE INDEX idx_history_portfolio_date ON portfolio_history (portfolio_id, snapshot_date);
CREATE INDEX idx_technical_recorded_at ON technical_indicators (recorded_at);
CREATE UNIQUE INDEX user_access_email_key ON user_access (email);
CREATE UNIQUE INDEX user_access_username_unique ON user_access (username);
CREATE INDEX idx_user_miners_model_id ON user_miners (miner_model_id);
CREATE INDEX idx_user_miners_status ON user_miners (status);
CREATE INDEX idx_user_miners_user_id ON user_miners (user_id);
CREATE INDEX idx_portfolios_active ON user_portfolios (is_active);
CREATE INDEX idx_portfolios_user_id ON user_portfolios (user_id);
CREATE UNIQUE INDEX user_portfolios_user_id_key ON user_portfolios (user_id);
CREATE UNIQUE INDEX ix_users_email ON users (email);
CREATE UNIQUE INDEX users_username_key ON users (username);
