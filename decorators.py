"""
Subscription and feature access decorators.
"""
from functools import wraps
from flask import session, jsonify, redirect, url_for, current_app
from models_subscription import Subscription, Plan
from models import db


def get_user_plan(user_id):
    """Get user's current plan or default to free."""
    if not user_id:
        # Default free plan for unauthenticated users
        return Plan.query.filter_by(id='free').first()
    
    subscription = Subscription.query.filter_by(user_id=user_id).first()
    if subscription and subscription.plan:
        return subscription.plan
    
    # Default to free plan
    return Plan.query.filter_by(id='free').first()


def require_entitlement(check_func):
    """
    Decorator to check if user has required entitlement.
    Usage: @require_entitlement(lambda p: p.allow_scenarios)
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = session.get('user_id')
            plan = get_user_plan(user_id)
            
            if not plan:
                return jsonify({
                    'success': False, 
                    'error': 'upgrade_required',
                    'message': 'Plan not found. Please contact support.'
                }), 402
            
            # Check if user has required entitlement
            if not check_func(plan):
                upgrade_url = url_for('billing_routes.plans')
                return jsonify({
                    'success': False,
                    'error': 'upgrade_required', 
                    'message': f'This feature requires {plan.name} plan or higher.',
                    'current_plan': plan.name,
                    'upgrade_url': upgrade_url
                }), 402
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def check_miner_limit(miner_count):
    """
    Check if user can process the specified number of miners.
    Returns (allowed: bool, plan: Plan, message: str)
    """
    user_id = session.get('user_id')
    plan = get_user_plan(user_id)
    
    if not plan:
        return False, None, "Plan not found"
    
    if miner_count > plan.max_miners:
        return False, plan, f"Current plan allows up to {plan.max_miners} miners. You're trying to process {miner_count} miners."
    
    return True, plan, "OK"


def get_user_subscription(user_id):
    """Get user's current subscription."""
    if not user_id:
        return None
    return Subscription.query.filter_by(user_id=user_id).first()


def require_plan(plan_id):
    """Decorator to require a specific plan."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = session.get('user_id')
            plan = get_user_plan(user_id)
            
            if not plan or plan.id != plan_id:
                return redirect(url_for('billing_routes.plans'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_feature(feature_name):
    """Decorator to require a specific feature."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = session.get('user_id')
            plan = get_user_plan(user_id)
            
            if not plan:
                return redirect(url_for('billing_routes.plans'))
            
            # Check feature based on plan
            if feature_name == 'advanced_analytics' and not plan.allow_advanced_analytics:
                return redirect(url_for('billing_routes.plans'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def allow_advanced_analytics(user_id):
    """Check if user has access to advanced analytics."""
    plan = get_user_plan(user_id)
    return plan and plan.allow_advanced_analytics


class UpgradeRequired(Exception):
    """Exception raised when user needs to upgrade their plan."""
    def __init__(self, message, current_plan=None, required_feature=None):
        self.message = message
        self.current_plan = current_plan
        self.required_feature = required_feature
        super().__init__(self.message)