"""
Subscription entitlement decorators for route-level access control.
"""
from functools import wraps
from flask import jsonify, session, request
from models_subscription import Plan, Subscription


def get_user_plan(user_id: int) -> Plan:
    """Get the current plan for a user."""
    if not user_id:
        return Plan.query.get("free")
    
    subscription = Subscription.query.filter_by(
        user_id=user_id, 
        status="active"
    ).first()
    
    if not subscription:
        return Plan.query.get("free")
    
    return subscription.plan or Plan.query.get("free")


def get_user_subscription(user_id: int) -> Subscription:
    """Get the current subscription for a user."""
    return Subscription.query.filter_by(
        user_id=user_id, 
        status="active"
    ).first()


def require_plan(required_plan_ids):
    """Decorator to require specific plan levels."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            user_id = session.get('user_id')
            if not user_id:
                return jsonify({'error': 'Authentication required', 'upgrade_required': True}), 401
            
            user_plan = get_user_plan(user_id)
            if not user_plan or user_plan.id not in required_plan_ids:
                return jsonify({
                    'error': 'Plan upgrade required',
                    'current_plan': user_plan.id if user_plan else 'free',
                    'required_plans': required_plan_ids,
                    'upgrade_required': True
                }), 402
            
            return f(*args, **kwargs)
        return wrapper
    return decorator


def require_feature(feature_check):
    """Decorator to require specific feature access."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            user_id = session.get('user_id')
            if not user_id:
                return jsonify({'error': 'Authentication required', 'upgrade_required': True}), 401
            
            user_plan = get_user_plan(user_id)
            if not user_plan or not feature_check(user_plan):
                return jsonify({
                    'error': 'Feature requires plan upgrade',
                    'current_plan': user_plan.id if user_plan else 'free',
                    'upgrade_required': True
                }), 402
            
            return f(*args, **kwargs)
        return wrapper
    return decorator


# Common feature checks
def allow_api_access(plan: Plan) -> bool:
    return plan.allow_api if plan else False


def allow_scenarios(plan: Plan) -> bool:
    return plan.allow_scenarios if plan else False


def allow_advanced_analytics(plan: Plan) -> bool:
    return plan.allow_advanced_analytics if plan else False


def check_miners_limit(plan: Plan, requested_miners: int) -> bool:
    return requested_miners <= plan.max_miners if plan else False


def check_history_limit(plan: Plan, requested_days: int) -> bool:
    return requested_days <= plan.history_days if plan else False