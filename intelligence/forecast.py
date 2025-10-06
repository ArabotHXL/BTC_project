"""
BTC Price and Difficulty Forecasting Module
Uses ARIMA time series models for prediction with confidence intervals
"""

import logging
from datetime import datetime, timedelta, date
from typing import Dict, List, Tuple, Optional
import warnings

import pandas as pd
import numpy as np
from statsmodels.tsa.arima.model import ARIMA
from sklearn.metrics import mean_squared_error, mean_absolute_error
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

from app import db
from models import NetworkSnapshot, UserMiner, ForecastDaily, UserAccess

# Configure logging
logger = logging.getLogger(__name__)

# Suppress ARIMA convergence warnings
warnings.filterwarnings('ignore', category=UserWarning)
warnings.filterwarnings('ignore', category=FutureWarning)


def forecast_btc_price(days: int = 7) -> Dict:
    """
    Forecast BTC price using ARIMA model
    
    Args:
        days: Number of days to forecast (default 7)
        
    Returns:
        Dict containing:
            - predictions: List of {date, price, lower_bound, upper_bound}
            - rmse: Root Mean Squared Error
            - mae: Mean Absolute Error
            - model_params: ARIMA parameters used
    """
    try:
        logger.info(f"Starting BTC price forecast for {days} days")
        
        # Fetch historical BTC price data from network_snapshots
        cutoff_date = datetime.utcnow() - timedelta(days=90)  # Use last 90 days
        snapshots = NetworkSnapshot.query.filter(
            NetworkSnapshot.recorded_at >= cutoff_date,
            NetworkSnapshot.is_valid == True
        ).order_by(NetworkSnapshot.recorded_at.asc()).all()
        
        if len(snapshots) < 30:
            raise ValueError(f"Insufficient data: only {len(snapshots)} records found. Need at least 30.")
        
        # Prepare time series data
        df = pd.DataFrame([
            {
                'date': s.recorded_at.date(),
                'price': float(s.btc_price)
            }
            for s in snapshots
        ])
        
        # Group by date and take mean (in case of multiple records per day)
        df = df.groupby('date')['price'].mean().reset_index()
        df = df.sort_values('date')
        
        logger.info(f"Prepared {len(df)} daily price records for ARIMA model")
        
        # Split data for validation (80/20 split)
        split_idx = int(len(df) * 0.8)
        train_data = df['price'][:split_idx]
        test_data = df['price'][split_idx:]
        
        # Fit ARIMA model - using (1,1,1) as default, can be optimized
        # p=1 (autoregressive), d=1 (differencing), q=1 (moving average)
        model = ARIMA(train_data, order=(1, 1, 1))
        fitted_model = model.fit()
        
        logger.info(f"ARIMA model fitted with params: {fitted_model.params}")
        
        # Calculate RMSE and MAE on test set
        test_predictions = fitted_model.forecast(steps=len(test_data))
        rmse = np.sqrt(mean_squared_error(test_data, test_predictions))
        mae = mean_absolute_error(test_data, test_predictions)
        
        logger.info(f"Model metrics - RMSE: {rmse:.2f}, MAE: {mae:.2f}")
        
        # Refit on full dataset for final predictions
        full_model = ARIMA(df['price'], order=(1, 1, 1))
        full_fitted = full_model.fit()
        
        # Generate forecasts with confidence intervals
        forecast_result = full_fitted.forecast(steps=days, alpha=0.05)  # 95% confidence
        forecast_values = forecast_result
        
        # Get prediction intervals
        pred_int = full_fitted.get_forecast(steps=days).conf_int(alpha=0.05)
        
        # Build predictions list
        predictions = []
        last_date = df['date'].iloc[-1]
        
        for i in range(days):
            pred_date = last_date + timedelta(days=i+1)
            predictions.append({
                'date': pred_date,
                'price': float(forecast_values.iloc[i] if hasattr(forecast_values, 'iloc') else forecast_values[i]),
                'lower_bound': float(pred_int.iloc[i, 0]),
                'upper_bound': float(pred_int.iloc[i, 1])
            })
        
        result = {
            'predictions': predictions,
            'rmse': float(rmse),
            'mae': float(mae),
            'model_params': {
                'order': (1, 1, 1),
                'data_points': len(df)
            }
        }
        
        logger.info(f"BTC price forecast completed successfully. First prediction: ${predictions[0]['price']:.2f}")
        return result
        
    except Exception as e:
        logger.error(f"Error in BTC price forecasting: {str(e)}", exc_info=True)
        raise


def forecast_difficulty(days: int = 7) -> Dict:
    """
    Forecast network difficulty using ARIMA model
    
    Args:
        days: Number of days to forecast (default 7)
        
    Returns:
        Dict containing:
            - predictions: List of {date, difficulty, lower_bound, upper_bound}
            - rmse: Root Mean Squared Error
            - mae: Mean Absolute Error
            - model_params: ARIMA parameters used
    """
    try:
        logger.info(f"Starting difficulty forecast for {days} days")
        
        # Fetch historical difficulty data from network_snapshots
        cutoff_date = datetime.utcnow() - timedelta(days=90)  # Use last 90 days
        snapshots = NetworkSnapshot.query.filter(
            NetworkSnapshot.recorded_at >= cutoff_date,
            NetworkSnapshot.is_valid == True
        ).order_by(NetworkSnapshot.recorded_at.asc()).all()
        
        if len(snapshots) < 30:
            raise ValueError(f"Insufficient data: only {len(snapshots)} records found. Need at least 30.")
        
        # Prepare time series data
        df = pd.DataFrame([
            {
                'date': s.recorded_at.date(),
                'difficulty': float(s.network_difficulty)
            }
            for s in snapshots
        ])
        
        # Group by date and take mean
        df = df.groupby('date')['difficulty'].mean().reset_index()
        df = df.sort_values('date')
        
        logger.info(f"Prepared {len(df)} daily difficulty records for ARIMA model")
        
        # Split data for validation (80/20 split)
        split_idx = int(len(df) * 0.8)
        train_data = df['difficulty'][:split_idx]
        test_data = df['difficulty'][split_idx:]
        
        # Fit ARIMA model - using (1,1,1) for difficulty
        model = ARIMA(train_data, order=(1, 1, 1))
        fitted_model = model.fit()
        
        logger.info(f"ARIMA model fitted for difficulty")
        
        # Calculate RMSE and MAE on test set
        test_predictions = fitted_model.forecast(steps=len(test_data))
        rmse = np.sqrt(mean_squared_error(test_data, test_predictions))
        mae = mean_absolute_error(test_data, test_predictions)
        
        logger.info(f"Model metrics - RMSE: {rmse:.2f}, MAE: {mae:.2f}")
        
        # Refit on full dataset for final predictions
        full_model = ARIMA(df['difficulty'], order=(1, 1, 1))
        full_fitted = full_model.fit()
        
        # Generate forecasts with confidence intervals
        forecast_result = full_fitted.forecast(steps=days, alpha=0.05)
        forecast_values = forecast_result
        
        # Get prediction intervals
        pred_int = full_fitted.get_forecast(steps=days).conf_int(alpha=0.05)
        
        # Build predictions list
        predictions = []
        last_date = df['date'].iloc[-1]
        
        for i in range(days):
            pred_date = last_date + timedelta(days=i+1)
            predictions.append({
                'date': pred_date,
                'difficulty': float(forecast_values.iloc[i] if hasattr(forecast_values, 'iloc') else forecast_values[i]),
                'lower_bound': float(pred_int.iloc[i, 0]),
                'upper_bound': float(pred_int.iloc[i, 1])
            })
        
        result = {
            'predictions': predictions,
            'rmse': float(rmse),
            'mae': float(mae),
            'model_params': {
                'order': (1, 1, 1),
                'data_points': len(df)
            }
        }
        
        logger.info(f"Difficulty forecast completed successfully. First prediction: {predictions[0]['difficulty']:.2f}")
        return result
        
    except Exception as e:
        logger.error(f"Error in difficulty forecasting: {str(e)}", exc_info=True)
        raise


def forecast_user_revenue(user_id: int, days: int = 7) -> Dict:
    """
    Forecast user's daily mining revenue based on their hashrate
    
    Args:
        user_id: User ID from user_access table
        days: Number of days to forecast (default 7)
        
    Returns:
        Dict containing:
            - user_id: User ID
            - total_hashrate: User's total hashrate in TH/s
            - predictions: List of {date, revenue, lower_bound, upper_bound}
            - saved_records: Number of records saved to database
    """
    try:
        logger.info(f"Starting revenue forecast for user {user_id}, {days} days")
        
        # Get user's total hashrate from active miners
        user_miners = UserMiner.query.filter(
            UserMiner.user_id == user_id,
            UserMiner.status == 'active'
        ).all()
        
        if not user_miners:
            logger.warning(f"No active miners found for user {user_id}")
            return {
                'user_id': user_id,
                'total_hashrate': 0,
                'predictions': [],
                'saved_records': 0,
                'message': 'No active miners found'
            }
        
        # Calculate total hashrate
        total_hashrate = sum(m.actual_hashrate * m.quantity for m in user_miners)
        logger.info(f"User {user_id} total hashrate: {total_hashrate:.2f} TH/s")
        
        # Get price and difficulty forecasts
        price_forecast = forecast_btc_price(days)
        difficulty_forecast = forecast_difficulty(days)
        
        # Calculate revenue for each day
        # Revenue = (hashrate_TH/s * 1e12 * 86400 * block_reward) / (difficulty * 2^32) * btc_price
        block_reward = 3.125  # Current BTC block reward
        predictions = []
        
        for i in range(days):
            price_data = price_forecast['predictions'][i]
            diff_data = difficulty_forecast['predictions'][i]
            
            # Calculate revenue (simplified formula)
            hashrate_h_s = total_hashrate * 1e12  # Convert TH/s to H/s
            daily_blocks = 144  # Approximately 144 blocks per day
            
            # Daily BTC mined = (hashrate / network_hashrate) * daily_blocks * block_reward
            # Using difficulty as proxy for network hashrate
            # difficulty * 2^32 / 600 = network hashrate in H/s
            network_hashrate = diff_data['difficulty'] * (2**32) / 600
            
            daily_btc = (hashrate_h_s / network_hashrate) * daily_blocks * block_reward
            revenue = daily_btc * price_data['price']
            
            # Calculate bounds using price and difficulty bounds
            revenue_lower = (hashrate_h_s / (diff_data['upper_bound'] * (2**32) / 600)) * daily_blocks * block_reward * price_data['lower_bound']
            revenue_upper = (hashrate_h_s / (diff_data['lower_bound'] * (2**32) / 600)) * daily_blocks * block_reward * price_data['upper_bound']
            
            predictions.append({
                'date': price_data['date'],
                'revenue': float(revenue),
                'lower_bound': float(revenue_lower),
                'upper_bound': float(revenue_upper),
                'btc_price': price_data['price'],
                'difficulty': diff_data['difficulty']
            })
        
        # Save results to ForecastDaily model
        saved_count = 0
        for pred in predictions:
            try:
                # Check if forecast already exists for this user, date, and horizon
                existing = ForecastDaily.query.filter_by(
                    user_id=user_id,
                    forecast_date=pred['date'],
                    forecast_horizon=days
                ).first()
                
                if existing:
                    # Update existing record
                    existing.predicted_btc_price = pred['btc_price']
                    existing.price_lower_bound = price_forecast['predictions'][predictions.index(pred)]['lower_bound']
                    existing.price_upper_bound = price_forecast['predictions'][predictions.index(pred)]['upper_bound']
                    existing.predicted_difficulty = pred['difficulty']
                    existing.difficulty_lower_bound = difficulty_forecast['predictions'][predictions.index(pred)]['lower_bound']
                    existing.difficulty_upper_bound = difficulty_forecast['predictions'][predictions.index(pred)]['upper_bound']
                    existing.predicted_daily_revenue = pred['revenue']
                    existing.revenue_lower_bound = pred['lower_bound']
                    existing.revenue_upper_bound = pred['upper_bound']
                    existing.rmse = (price_forecast['rmse'] + difficulty_forecast['rmse']) / 2
                    existing.mae = (price_forecast['mae'] + difficulty_forecast['mae']) / 2
                    existing.updated_at = datetime.utcnow()
                else:
                    # Create new record
                    forecast_record = ForecastDaily(
                        user_id=user_id,
                        forecast_date=pred['date'],
                        forecast_horizon=days,
                        predicted_btc_price=pred['btc_price'],
                        price_lower_bound=price_forecast['predictions'][predictions.index(pred)]['lower_bound'],
                        price_upper_bound=price_forecast['predictions'][predictions.index(pred)]['upper_bound'],
                        predicted_difficulty=pred['difficulty'],
                        difficulty_lower_bound=difficulty_forecast['predictions'][predictions.index(pred)]['lower_bound'],
                        difficulty_upper_bound=difficulty_forecast['predictions'][predictions.index(pred)]['upper_bound'],
                        predicted_daily_revenue=pred['revenue'],
                        revenue_lower_bound=pred['lower_bound'],
                        revenue_upper_bound=pred['upper_bound'],
                        model_name='ARIMA',
                        rmse=(price_forecast['rmse'] + difficulty_forecast['rmse']) / 2,
                        mae=(price_forecast['mae'] + difficulty_forecast['mae']) / 2
                    )
                    db.session.add(forecast_record)
                
                saved_count += 1
                
            except SQLAlchemyError as e:
                logger.error(f"Error saving forecast for date {pred['date']}: {str(e)}")
                continue
        
        # Commit all changes
        db.session.commit()
        logger.info(f"Saved {saved_count} forecast records for user {user_id}")
        
        result = {
            'user_id': user_id,
            'total_hashrate': float(total_hashrate),
            'predictions': predictions,
            'saved_records': saved_count,
            'price_metrics': {
                'rmse': price_forecast['rmse'],
                'mae': price_forecast['mae']
            },
            'difficulty_metrics': {
                'rmse': difficulty_forecast['rmse'],
                'mae': difficulty_forecast['mae']
            }
        }
        
        logger.info(f"Revenue forecast completed for user {user_id}. Average daily revenue: ${np.mean([p['revenue'] for p in predictions]):.2f}")
        return result
        
    except Exception as e:
        logger.error(f"Error in user revenue forecasting: {str(e)}", exc_info=True)
        db.session.rollback()
        raise


def refresh_all_forecasts(days: int = 7) -> Dict:
    """
    Refresh forecasts for all active users
    Used by background workers to update predictions
    
    Args:
        days: Number of days to forecast (default 7)
        
    Returns:
        Dict containing:
            - total_users: Total number of users processed
            - successful: Number of successful forecasts
            - failed: Number of failed forecasts
            - details: List of results per user
    """
    try:
        logger.info("Starting forecast refresh for all active users")
        
        # Get all active users who have miners
        users_with_miners = db.session.query(UserMiner.user_id).filter(
            UserMiner.status == 'active'
        ).distinct().all()
        
        user_ids = [u[0] for u in users_with_miners]
        logger.info(f"Found {len(user_ids)} users with active miners")
        
        results = {
            'total_users': len(user_ids),
            'successful': 0,
            'failed': 0,
            'details': []
        }
        
        for user_id in user_ids:
            try:
                logger.info(f"Processing forecasts for user {user_id}")
                
                user_result = forecast_user_revenue(user_id, days)
                
                results['successful'] += 1
                results['details'].append({
                    'user_id': user_id,
                    'status': 'success',
                    'hashrate': user_result['total_hashrate'],
                    'records_saved': user_result['saved_records']
                })
                
                logger.info(f"Successfully updated forecasts for user {user_id}")
                
            except Exception as e:
                logger.error(f"Failed to update forecasts for user {user_id}: {str(e)}")
                results['failed'] += 1
                results['details'].append({
                    'user_id': user_id,
                    'status': 'failed',
                    'error': str(e)
                })
        
        logger.info(f"Forecast refresh completed. Success: {results['successful']}, Failed: {results['failed']}")
        return results
        
    except Exception as e:
        logger.error(f"Error in refresh_all_forecasts: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    # Test the forecasting functions
    logging.basicConfig(level=logging.INFO)
    
    print("Testing BTC Price Forecast...")
    price_result = forecast_btc_price(7)
    print(f"Price predictions: {len(price_result['predictions'])} days")
    print(f"RMSE: {price_result['rmse']:.2f}, MAE: {price_result['mae']:.2f}")
    
    print("\nTesting Difficulty Forecast...")
    diff_result = forecast_difficulty(7)
    print(f"Difficulty predictions: {len(diff_result['predictions'])} days")
    print(f"RMSE: {diff_result['rmse']:.2f}, MAE: {diff_result['mae']:.2f}")
