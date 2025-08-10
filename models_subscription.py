"""
Subscription & Plan models for Stripe integration.
"""
from datetime import datetime
from models import db


class Plan(db.Model):
    __tablename__ = "plans"
    id = db.Column(db.String, primary_key=True)  # free/basic/pro
    name = db.Column(db.String, nullable=False)
    price = db.Column(db.Integer, default=0)  # price in cents
    max_miners = db.Column(db.Integer, default=3)
    coins = db.Column(db.Text)  # comma-separated list
    history_days = db.Column(db.Integer, default=7)
    allow_api = db.Column(db.Boolean, default=False)
    allow_scenarios = db.Column(db.Boolean, default=False)
    allow_advanced_analytics = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Subscription(db.Model):
    __tablename__ = "subscriptions"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user_access.id"))
    plan_id = db.Column(db.String, db.ForeignKey("plans.id"), default="free")
    stripe_customer_id = db.Column(db.String)
    stripe_subscription_id = db.Column(db.String)
    stripe_price_id = db.Column(db.String)
    status = db.Column(db.String, default="free")  # free/active/trialing/past_due/canceled
    current_period_start = db.Column(db.DateTime)
    current_period_end = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    plan = db.relationship("Plan", backref="subscriptions")
    user = db.relationship("UserAccess", backref="subscriptions")

# 为了测试兼容性，添加别名
SubscriptionPlan = Plan
UserSubscription = Subscription