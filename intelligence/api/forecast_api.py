"""
Intelligence Layer - Forecast API
==================================

Flask blueprint for BTC price and difficulty forecasting endpoints.

Endpoints:
- GET /api/intelligence/forecast/<user_id> - Get user's forecast data
- POST /api/intelligence/forecast/<user_id>/refresh - Trigger forecast refresh
"""

import logging
from datetime import datetime, date
from flask import Blueprint, request, jsonify, g
from sqlalchemy.exc import SQLAlchemyError

from db import db
from models import ForecastDaily, UserAccess
from api_auth_middleware import require_api_auth
from intelligence.forecast import forecast_btc_price, forecast_difficulty
from common.rbac import require_permission, Permission

logger = logging.getLogger(__name__)

forecast_bp = Blueprint('forecast_api', __name__, url_prefix='/api/intelligence/forecast')


@forecast_bp.route('/<int:user_id>', methods=['GET'])
@require_api_auth(required_permissions=['read'], allow_session_auth=True)
@require_permission([Permission.INTEL_READ, Permission.INTEL_FORECAST], require_all=True)
def get_user_forecast(user_id):
    """
    Get user's forecast data
    
    Query Parameters:
    - days: Number of forecast days (default: 7)
    - include_history: Include historical forecasts (default: false)
    
    Returns:
        JSON with forecast data including BTC price and difficulty predictions
    """
    try:
        days = request.args.get('days', 7, type=int)
        include_history = request.args.get('include_history', 'false').lower() == 'true'
        
        if days < 1 or days > 30:
            return jsonify({
                'status': 'error',
                'message': 'Days parameter must be between 1 and 30'
            }), 400
        
        user = UserAccess.query.get(user_id)
        if not user:
            return jsonify({
                'status': 'error',
                'message': f'User {user_id} not found'
            }), 404
        
        query = ForecastDaily.query.filter_by(user_id=user_id)
        
        if not include_history:
            query = query.filter(ForecastDaily.forecast_date >= date.today())
        
        forecasts = query.order_by(ForecastDaily.forecast_date.asc()).limit(days).all()
        
        forecast_data = []
        for fc in forecasts:
            forecast_data.append({
                'date': fc.forecast_date.isoformat(),
                'btc_price': {
                    'predicted': float(fc.predicted_btc_price),
                    'lower_bound': float(fc.price_lower_bound) if fc.price_lower_bound else None,
                    'upper_bound': float(fc.price_upper_bound) if fc.price_upper_bound else None
                },
                'difficulty': {
                    'predicted': float(fc.predicted_difficulty),
                    'lower_bound': float(fc.difficulty_lower_bound) if fc.difficulty_lower_bound else None,
                    'upper_bound': float(fc.difficulty_upper_bound) if fc.difficulty_upper_bound else None
                },
                'revenue': {
                    'predicted': float(fc.predicted_daily_revenue) if fc.predicted_daily_revenue else None
                },
                'model_accuracy': {
                    'price_rmse': float(fc.price_rmse) if fc.price_rmse else None,
                    'difficulty_rmse': float(fc.difficulty_rmse) if fc.difficulty_rmse else None
                },
                'created_at': fc.created_at.isoformat() if fc.created_at else None
            })
        
        logger.info(f"Retrieved {len(forecast_data)} forecast records for user {user_id}")
        
        return jsonify({
            'status': 'success',
            'user_id': user_id,
            'forecast_days': days,
            'forecasts': forecast_data,
            'count': len(forecast_data)
        }), 200
        
    except SQLAlchemyError as e:
        logger.error(f"Database error retrieving forecast for user {user_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Database error occurred',
            'error': str(e)
        }), 500
        
    except Exception as e:
        logger.error(f"Error retrieving forecast for user {user_id}: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Internal server error',
            'error': str(e)
        }), 500


@forecast_bp.route('/<int:user_id>/refresh', methods=['POST'])
@require_api_auth(required_permissions=['write'], allow_session_auth=True)
@require_permission([Permission.INTEL_READ, Permission.INTEL_FORECAST], require_all=True)
def refresh_user_forecast(user_id):
    """
    Trigger forecast refresh for a user
    
    Request Body:
    - days: Number of days to forecast (default: 7)
    - force: Force recalculation even if recent forecast exists (default: false)
    
    Returns:
        JSON with newly generated forecast data
    """
    try:
        data = request.get_json() or {}
        days = data.get('days', 7)
        force = data.get('force', False)
        
        if days < 1 or days > 30:
            return jsonify({
                'status': 'error',
                'message': 'Days parameter must be between 1 and 30'
            }), 400
        
        user = UserAccess.query.get(user_id)
        if not user:
            return jsonify({
                'status': 'error',
                'message': f'User {user_id} not found'
            }), 404
        
        if not force:
            recent_forecast = ForecastDaily.query.filter_by(user_id=user_id).filter(
                ForecastDaily.created_at >= datetime.utcnow().replace(hour=0, minute=0, second=0)
            ).first()
            
            if recent_forecast:
                return jsonify({
                    'status': 'success',
                    'message': 'Recent forecast already exists. Use force=true to recalculate.',
                    'user_id': user_id,
                    'last_forecast': recent_forecast.created_at.isoformat()
                }), 200
        
        logger.info(f"Generating new {days}-day forecast for user {user_id}")
        
        price_forecast = forecast_btc_price(days=days)
        difficulty_forecast = forecast_difficulty(days=days)
        
        new_forecasts = []
        for i in range(days):
            price_pred = price_forecast['predictions'][i]
            diff_pred = difficulty_forecast['predictions'][i]
            
            forecast = ForecastDaily(
                user_id=user_id,
                forecast_date=price_pred['date'],
                forecast_horizon=days,
                predicted_btc_price=price_pred['price'],
                price_lower_bound=price_pred['lower_bound'],
                price_upper_bound=price_pred['upper_bound'],
                predicted_difficulty=diff_pred['difficulty'],
                difficulty_lower_bound=diff_pred['lower_bound'],
                difficulty_upper_bound=diff_pred['upper_bound'],
                price_rmse=price_forecast['rmse'],
                difficulty_rmse=difficulty_forecast['rmse'],
                created_at=datetime.utcnow()
            )
            
            db.session.add(forecast)
            new_forecasts.append(forecast)
        
        db.session.commit()
        
        logger.info(f"Successfully created {len(new_forecasts)} forecast records for user {user_id}")
        
        return jsonify({
            'status': 'success',
            'message': f'Generated {days}-day forecast',
            'user_id': user_id,
            'forecast_count': len(new_forecasts),
            'model_metrics': {
                'price_rmse': price_forecast['rmse'],
                'price_mae': price_forecast['mae'],
                'difficulty_rmse': difficulty_forecast['rmse'],
                'difficulty_mae': difficulty_forecast['mae']
            },
            'created_at': datetime.utcnow().isoformat()
        }), 201
        
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error refreshing forecast for user {user_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Database error occurred',
            'error': str(e)
        }), 500
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error refreshing forecast for user {user_id}: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': 'Internal server error',
            'error': str(e)
        }), 500
