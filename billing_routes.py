"""
Stripe billing and subscription routes.
"""
import os
import stripe
import logging
from flask import Blueprint, request, jsonify, redirect, url_for, session, render_template
from datetime import datetime
from models_subscription import Plan, Subscription
from models import UserAccess
from decorators import get_user_plan, get_user_subscription
from db import db


# Stripe configuration
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')
STRIPE_PRICE_BASIC = os.environ.get('STRIPE_PRICE_BASIC', 'price_basic_id')  # $29/month
STRIPE_PRICE_PRO = os.environ.get('STRIPE_PRICE_PRO', 'price_pro_id')      # $99/month
STRIPE_ENDPOINT_SECRET = os.environ.get('STRIPE_ENDPOINT_SECRET')

if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY
else:
    logging.warning("STRIPE_SECRET_KEY not found in environment variables")

billing_bp = Blueprint("billing", __name__)


def get_current_user():
    """Get current user from session."""
    user_id = session.get('user_id')
    email = session.get('email')
    
    if user_id:
        return UserAccess.query.get(user_id)
    elif email:
        return UserAccess.query.filter_by(email=email).first()
    return None


@billing_bp.route('/plans')
def show_plans():
    """Display subscription plans."""
    user = get_current_user()
    current_plan = get_user_plan(user.id if user else None)
    plans = Plan.query.all()
    
    return render_template('billing/plans.html', 
                         plans=plans, 
                         current_plan=current_plan,
                         user=user)


@billing_bp.route('/checkout', methods=['POST'])
def create_checkout():
    """Create Stripe checkout session."""
    if not STRIPE_SECRET_KEY:
        return jsonify({'error': 'Stripe not configured'}), 500
    
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Authentication required'}), 401

    data = request.get_json()
    plan_id = data.get('plan', 'basic')
    
    # Get price ID based on plan
    price_id = STRIPE_PRICE_BASIC if plan_id == 'basic' else STRIPE_PRICE_PRO
    
    try:
        # Create Stripe checkout session
        checkout_session = stripe.checkout.Session.create(
            mode='subscription',
            customer_email=user.email,
            line_items=[{
                'price': price_id,
                'quantity': 1,
            }],
            success_url=url_for('billing.success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('billing.cancel', _external=True),
            metadata={
                'user_id': str(user.id),
                'plan_id': plan_id
            }
        )
        
        return jsonify({'checkout_url': checkout_session.url})
        
    except Exception as e:
        logging.error(f"Stripe checkout error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@billing_bp.route('/success')
def success():
    """Checkout success page."""
    session_id = request.args.get('session_id')
    if session_id and STRIPE_SECRET_KEY:
        try:
            session_obj = stripe.checkout.Session.retrieve(session_id)
            return render_template('billing/success.html', session=session_obj)
        except Exception as e:
            logging.error(f"Error retrieving session: {str(e)}")
    
    return render_template('billing/success.html')


@billing_bp.route('/cancel')
def cancel():
    """Checkout cancelled page."""
    return render_template('billing/cancel.html')


@billing_bp.route('/portal')
def customer_portal():
    """Redirect to Stripe customer portal."""
    if not STRIPE_SECRET_KEY:
        return jsonify({'error': 'Stripe not configured'}), 500
    
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Authentication required'}), 401
    
    subscription = get_user_subscription(user.id)
    if not subscription or not subscription.stripe_customer_id:
        return jsonify({'error': 'No active subscription found'}), 404
    
    try:
        portal_session = stripe.billing_portal.Session.create(
            customer=subscription.stripe_customer_id,
            return_url=url_for('billing.show_plans', _external=True),
        )
        return redirect(portal_session.url)
    except Exception as e:
        logging.error(f"Customer portal error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@billing_bp.route('/webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhook events."""
    if not STRIPE_SECRET_KEY or not STRIPE_ENDPOINT_SECRET:
        return jsonify({'error': 'Stripe not configured'}), 500
    
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_ENDPOINT_SECRET
        )
    except ValueError as e:
        logging.error(f"Invalid payload: {e}")
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError as e:
        logging.error(f"Invalid signature: {e}")
        return jsonify({'error': 'Invalid signature'}), 400

    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session_obj = event['data']['object']
        handle_checkout_completed(session_obj)
        
    elif event['type'] == 'customer.subscription.updated':
        subscription_obj = event['data']['object']
        handle_subscription_updated(subscription_obj)
        
    elif event['type'] == 'customer.subscription.deleted':
        subscription_obj = event['data']['object']
        handle_subscription_deleted(subscription_obj)
        
    elif event['type'] == 'invoice.payment_failed':
        invoice_obj = event['data']['object']
        handle_payment_failed(invoice_obj)

    return jsonify({'received': True})


def handle_checkout_completed(session_obj):
    """Handle successful checkout completion."""
    try:
        user_id = int(session_obj['metadata'].get('user_id'))
        plan_id = session_obj['metadata'].get('plan_id')
        stripe_customer_id = session_obj['customer']
        stripe_subscription_id = session_obj['subscription']
        
        user = UserAccess.query.get(user_id)
        if not user:
            logging.error(f"User {user_id} not found for checkout completion")
            return
        
        # Create or update subscription
        subscription = Subscription.query.filter_by(user_id=user_id).first()
        if not subscription:
            subscription = Subscription(user_id=user_id)
            db.session.add(subscription)
        
        subscription.plan_id = plan_id
        subscription.stripe_customer_id = stripe_customer_id
        subscription.stripe_subscription_id = stripe_subscription_id
        subscription.status = 'active'
        subscription.updated_at = datetime.utcnow()
        
        db.session.commit()
        logging.info(f"Subscription activated for user {user_id}, plan {plan_id}")
        
    except Exception as e:
        logging.error(f"Error handling checkout completion: {str(e)}")
        db.session.rollback()


def handle_subscription_updated(subscription_obj):
    """Handle subscription updates."""
    try:
        stripe_subscription_id = subscription_obj['id']
        status = subscription_obj['status']
        current_period_start = datetime.fromtimestamp(subscription_obj['current_period_start'])
        current_period_end = datetime.fromtimestamp(subscription_obj['current_period_end'])
        
        subscription = Subscription.query.filter_by(
            stripe_subscription_id=stripe_subscription_id
        ).first()
        
        if subscription:
            subscription.status = status
            subscription.current_period_start = current_period_start
            subscription.current_period_end = current_period_end
            subscription.updated_at = datetime.utcnow()
            db.session.commit()
            logging.info(f"Subscription {stripe_subscription_id} updated to status {status}")
            
    except Exception as e:
        logging.error(f"Error handling subscription update: {str(e)}")
        db.session.rollback()


def handle_subscription_deleted(subscription_obj):
    """Handle subscription cancellation."""
    try:
        stripe_subscription_id = subscription_obj['id']
        
        subscription = Subscription.query.filter_by(
            stripe_subscription_id=stripe_subscription_id
        ).first()
        
        if subscription:
            subscription.status = 'canceled'
            subscription.plan_id = 'free'
            subscription.updated_at = datetime.utcnow()
            db.session.commit()
            logging.info(f"Subscription {stripe_subscription_id} canceled")
            
    except Exception as e:
        logging.error(f"Error handling subscription deletion: {str(e)}")
        db.session.rollback()


def handle_payment_failed(invoice_obj):
    """Handle failed payment."""
    try:
        stripe_subscription_id = invoice_obj['subscription']
        
        subscription = Subscription.query.filter_by(
            stripe_subscription_id=stripe_subscription_id
        ).first()
        
        if subscription:
            subscription.status = 'past_due'
            subscription.updated_at = datetime.utcnow()
            db.session.commit()
            logging.info(f"Subscription {stripe_subscription_id} marked as past due")
            
    except Exception as e:
        logging.error(f"Error handling payment failure: {str(e)}")
        db.session.rollback()


@billing_bp.route('/api/current-plan')
def api_current_plan():
    """API endpoint to get current user's plan."""
    user = get_current_user()
    if not user:
        return jsonify({'plan': 'free', 'authenticated': False})
    
    plan = get_user_plan(user.id)
    subscription = get_user_subscription(user.id)
    
    plan_data = {
        'id': plan.id,
        'name': plan.name,
        'max_miners': plan.max_miners,
        'history_days': plan.history_days,
        'allow_api': plan.allow_api,
        'allow_scenarios': plan.allow_scenarios,
        'allow_advanced_analytics': plan.allow_advanced_analytics,
        'authenticated': True
    }
    
    if subscription:
        plan_data['subscription'] = {
            'status': subscription.status,
            'current_period_end': subscription.current_period_end.isoformat() if subscription.current_period_end else None
        }
    
    return jsonify(plan_data)