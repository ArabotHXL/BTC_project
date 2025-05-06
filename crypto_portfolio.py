"""
加密货币投资组合管理模块
提供与加密货币投资组合相关的功能
"""

import json
import logging
import requests
from datetime import datetime, timedelta
from flask import jsonify, request, session
from sqlalchemy.exc import SQLAlchemyError

from db import db
from models import CryptoAsset, Portfolio, UserAccess

# 加密货币API基本URL
COINGECKO_API_BASE = "https://api.coingecko.com/api/v3"

def get_crypto_list():
    """获取支持的加密货币列表"""
    try:
        url = f"{COINGECKO_API_BASE}/coins/markets"
        params = {
            'vs_currency': 'usd',
            'order': 'market_cap_desc',
            'per_page': 100,
            'page': 1,
            'sparkline': False
        }
        response = requests.get(url, params=params)
        if response.status_code == 200:
            crypto_list = response.json()
            result = []
            for crypto in crypto_list:
                result.append({
                    'id': crypto.get('id'),
                    'symbol': crypto.get('symbol').upper(),
                    'name': crypto.get('name'),
                    'image': crypto.get('image'),
                    'current_price': crypto.get('current_price'),
                    'market_cap': crypto.get('market_cap'),
                    'market_cap_rank': crypto.get('market_cap_rank'),
                    'price_change_percentage_24h': crypto.get('price_change_percentage_24h')
                })
            return {'success': True, 'data': result}
        else:
            logging.error(f"获取加密货币列表失败: HTTP {response.status_code}")
            return {'success': False, 'error': f"API错误: {response.status_code}"}
    except Exception as e:
        logging.error(f"获取加密货币列表时发生异常: {str(e)}")
        return {'success': False, 'error': f"获取加密货币列表失败: {str(e)}"}

def get_crypto_price(crypto_id):
    """获取特定加密货币的当前价格"""
    try:
        url = f"{COINGECKO_API_BASE}/simple/price"
        params = {
            'ids': crypto_id,
            'vs_currencies': 'usd',
            'include_24hr_change': 'true'
        }
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            if crypto_id in data:
                return {
                    'success': True, 
                    'price': data[crypto_id].get('usd'),
                    'change_24h': data[crypto_id].get('usd_24h_change')
                }
            else:
                return {'success': False, 'error': '未找到该加密货币的数据'}
        else:
            logging.error(f"获取加密货币价格失败: HTTP {response.status_code}")
            return {'success': False, 'error': f"API错误: {response.status_code}"}
    except Exception as e:
        logging.error(f"获取加密货币价格时发生异常: {str(e)}")
        return {'success': False, 'error': f"获取价格失败: {str(e)}"}

def get_historical_prices(crypto_id, days=30):
    """获取加密货币的历史价格数据"""
    try:
        url = f"{COINGECKO_API_BASE}/coins/{crypto_id}/market_chart"
        params = {
            'vs_currency': 'usd',
            'days': days,
            'interval': 'daily'
        }
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            prices = []
            if 'prices' in data:
                for price_data in data['prices']:
                    # 价格数据格式为 [timestamp, price]
                    timestamp = price_data[0]
                    price = price_data[1]
                    date = datetime.fromtimestamp(timestamp / 1000).strftime('%Y-%m-%d')
                    prices.append({'date': date, 'price': price})
                return {'success': True, 'data': prices}
            else:
                return {'success': False, 'error': '未找到价格历史数据'}
        else:
            logging.error(f"获取历史价格失败: HTTP {response.status_code}")
            return {'success': False, 'error': f"API错误: {response.status_code}"}
    except Exception as e:
        logging.error(f"获取历史价格时发生异常: {str(e)}")
        return {'success': False, 'error': f"获取历史价格失败: {str(e)}"}

def get_user_assets(user_email):
    """获取用户的所有加密货币资产"""
    try:
        assets = CryptoAsset.query.filter_by(user_email=user_email).all()
        result = []
        
        for asset in assets:
            # 获取最新价格
            price_info = get_crypto_price(asset.crypto_id)
            current_price = price_info.get('price', 0) if price_info.get('success') else 0
            price_change = price_info.get('change_24h', 0) if price_info.get('success') else 0
            
            # 计算当前价值
            current_value = current_price * asset.amount if current_price else 0
            
            # 计算收益率
            profit_percentage = 0
            if asset.purchase_price and asset.purchase_price > 0 and current_price > 0:
                profit_percentage = ((current_price - asset.purchase_price) / asset.purchase_price) * 100
            
            asset_data = {
                'id': asset.id,
                'crypto_id': asset.crypto_id,
                'symbol': asset.crypto_symbol,
                'name': asset.crypto_name,
                'amount': asset.amount,
                'purchase_price': asset.purchase_price,
                'purchase_date': asset.purchase_date.strftime('%Y-%m-%d') if asset.purchase_date else None,
                'current_price': current_price,
                'current_value': current_value,
                'price_change_24h': price_change,
                'profit_loss_percentage': profit_percentage,
                'notes': asset.notes
            }
            result.append(asset_data)
        
        return {'success': True, 'data': result}
    except SQLAlchemyError as e:
        db.session.rollback()
        logging.error(f"数据库错误获取用户资产: {str(e)}")
        return {'success': False, 'error': f"数据库错误: {str(e)}"}
    except Exception as e:
        logging.error(f"获取用户资产时发生异常: {str(e)}")
        return {'success': False, 'error': f"获取资产失败: {str(e)}"}

def add_crypto_asset(user_email, crypto_data):
    """添加加密货币资产到用户投资组合"""
    try:
        # 验证用户是否存在
        user = UserAccess.query.filter_by(email=user_email).first()
        if not user:
            return {'success': False, 'error': '用户不存在'}
        
        # 验证加密货币ID是否有效
        price_info = get_crypto_price(crypto_data.get('crypto_id'))
        if not price_info.get('success'):
            return {'success': False, 'error': '无效的加密货币ID'}
        
        # 解析日期
        purchase_date = None
        if crypto_data.get('purchase_date'):
            try:
                purchase_date = datetime.strptime(crypto_data.get('purchase_date'), '%Y-%m-%d')
            except ValueError:
                return {'success': False, 'error': '无效的购买日期格式，请使用YYYY-MM-DD格式'}
        
        # 创建新资产
        new_asset = CryptoAsset(
            user_email=user_email,
            crypto_id=crypto_data.get('crypto_id'),
            crypto_symbol=crypto_data.get('crypto_symbol'),
            crypto_name=crypto_data.get('crypto_name'),
            amount=float(crypto_data.get('amount')),
            purchase_price=float(crypto_data.get('purchase_price')) if crypto_data.get('purchase_price') else None,
            purchase_date=purchase_date,
            notes=crypto_data.get('notes')
        )
        
        # 获取历史价格数据并设置
        if purchase_date:
            days_since_purchase = (datetime.now() - purchase_date).days
            history_data = get_historical_prices(crypto_data.get('crypto_id'), days=max(30, days_since_purchase))
            if history_data.get('success'):
                new_asset.set_price_history(history_data.get('data'))
        
        # 保存到数据库
        db.session.add(new_asset)
        
        # 确保用户有一个投资组合，如果没有则创建
        portfolio = Portfolio.query.filter_by(user_email=user_email).first()
        if not portfolio:
            portfolio = Portfolio(user_email=user_email)
            db.session.add(portfolio)
        
        db.session.commit()
        
        # 更新投资组合风险指标
        update_portfolio_metrics(user_email)
        
        return {'success': True, 'message': '资产添加成功', 'asset_id': new_asset.id}
    except ValueError as e:
        db.session.rollback()
        logging.error(f"资产数据类型错误: {str(e)}")
        return {'success': False, 'error': f"数据格式错误: {str(e)}"}
    except SQLAlchemyError as e:
        db.session.rollback()
        logging.error(f"数据库错误添加资产: {str(e)}")
        return {'success': False, 'error': f"数据库错误: {str(e)}"}
    except Exception as e:
        db.session.rollback()
        logging.error(f"添加资产时发生异常: {str(e)}")
        return {'success': False, 'error': f"添加资产失败: {str(e)}"}

def update_crypto_asset(asset_id, user_email, update_data):
    """更新用户的加密货币资产信息"""
    try:
        # 查找资产并验证所有权
        asset = CryptoAsset.query.filter_by(id=asset_id, user_email=user_email).first()
        if not asset:
            return {'success': False, 'error': '资产不存在或您无权修改'}
        
        # 更新资产信息
        if 'amount' in update_data:
            asset.amount = float(update_data.get('amount'))
        
        if 'purchase_price' in update_data and update_data.get('purchase_price'):
            asset.purchase_price = float(update_data.get('purchase_price'))
        
        if 'purchase_date' in update_data and update_data.get('purchase_date'):
            try:
                asset.purchase_date = datetime.strptime(update_data.get('purchase_date'), '%Y-%m-%d')
            except ValueError:
                return {'success': False, 'error': '无效的购买日期格式，请使用YYYY-MM-DD格式'}
        
        if 'notes' in update_data:
            asset.notes = update_data.get('notes')
        
        # 更新时间戳
        asset.updated_at = datetime.utcnow()
        
        # 保存更改
        db.session.commit()
        
        # 更新投资组合风险指标
        update_portfolio_metrics(user_email)
        
        return {'success': True, 'message': '资产更新成功'}
    except ValueError as e:
        db.session.rollback()
        logging.error(f"资产数据类型错误: {str(e)}")
        return {'success': False, 'error': f"数据格式错误: {str(e)}"}
    except SQLAlchemyError as e:
        db.session.rollback()
        logging.error(f"数据库错误更新资产: {str(e)}")
        return {'success': False, 'error': f"数据库错误: {str(e)}"}
    except Exception as e:
        db.session.rollback()
        logging.error(f"更新资产时发生异常: {str(e)}")
        return {'success': False, 'error': f"更新资产失败: {str(e)}"}

def delete_crypto_asset(asset_id, user_email):
    """删除用户的加密货币资产"""
    try:
        # 查找资产并验证所有权
        asset = CryptoAsset.query.filter_by(id=asset_id, user_email=user_email).first()
        if not asset:
            return {'success': False, 'error': '资产不存在或您无权删除'}
        
        # 删除资产
        db.session.delete(asset)
        db.session.commit()
        
        # 更新投资组合风险指标
        update_portfolio_metrics(user_email)
        
        return {'success': True, 'message': '资产删除成功'}
    except SQLAlchemyError as e:
        db.session.rollback()
        logging.error(f"数据库错误删除资产: {str(e)}")
        return {'success': False, 'error': f"数据库错误: {str(e)}"}
    except Exception as e:
        db.session.rollback()
        logging.error(f"删除资产时发生异常: {str(e)}")
        return {'success': False, 'error': f"删除资产失败: {str(e)}"}

def get_portfolio_summary(user_email):
    """获取用户投资组合的摘要信息"""
    try:
        # 获取用户所有资产
        assets_result = get_user_assets(user_email)
        if not assets_result.get('success'):
            return assets_result
        
        assets = assets_result.get('data', [])
        
        # 计算总价值
        total_value = sum(asset.get('current_value', 0) for asset in assets)
        
        # 计算总成本（如果有购买价数据）
        total_cost = 0
        for asset in assets:
            if asset.get('purchase_price') and asset.get('amount'):
                total_cost += asset.get('purchase_price') * asset.get('amount')
        
        # 计算总收益率
        total_profit_percentage = 0
        if total_cost > 0:
            total_profit_percentage = ((total_value - total_cost) / total_cost) * 100
        
        # 计算资产分配比例
        for asset in assets:
            if total_value > 0:
                asset['allocation_percentage'] = (asset.get('current_value', 0) / total_value) * 100
            else:
                asset['allocation_percentage'] = 0
        
        # 获取投资组合对象
        portfolio = Portfolio.query.filter_by(user_email=user_email).first()
        
        # 准备摘要
        summary = {
            'total_value': total_value,
            'total_cost': total_cost,
            'total_profit_percentage': total_profit_percentage,
            'asset_count': len(assets),
            'assets': assets
        }
        
        # 添加风险评估
        if portfolio:
            risk_metrics = portfolio.get_risk_metrics()
            summary['risk_metrics'] = risk_metrics
            
            # 添加表现历史
            performance_history = portfolio.get_performance_history()
            summary['performance_history'] = performance_history
            
            # 添加优化建议
            optimization_suggestions = portfolio.get_optimization_suggestions()
            summary['optimization_suggestions'] = optimization_suggestions
            
        return {'success': True, 'data': summary}
    except Exception as e:
        logging.error(f"获取投资组合摘要时发生异常: {str(e)}")
        return {'success': False, 'error': f"获取投资组合摘要失败: {str(e)}"}

def update_portfolio_metrics(user_email):
    """更新用户投资组合的风险指标和优化建议"""
    try:
        # 获取用户所有资产
        assets_result = get_user_assets(user_email)
        if not assets_result.get('success'):
            return assets_result
        
        assets = assets_result.get('data', [])
        
        # 获取或创建投资组合
        portfolio = Portfolio.query.filter_by(user_email=user_email).first()
        if not portfolio:
            portfolio = Portfolio(user_email=user_email)
            db.session.add(portfolio)
        
        # 计算风险指标
        metrics = calculate_risk_metrics(assets)
        portfolio.set_risk_metrics(metrics)
        
        # 生成优化建议
        suggestions = generate_optimization_suggestions(assets, metrics)
        portfolio.set_optimization_suggestions(suggestions)
        
        # 更新历史表现数据
        update_performance_history(portfolio, assets)
        
        # 保存更改
        db.session.commit()
        
        return {'success': True, 'message': '投资组合指标更新成功'}
    except SQLAlchemyError as e:
        db.session.rollback()
        logging.error(f"数据库错误更新投资组合指标: {str(e)}")
        return {'success': False, 'error': f"数据库错误: {str(e)}"}
    except Exception as e:
        db.session.rollback()
        logging.error(f"更新投资组合指标时发生异常: {str(e)}")
        return {'success': False, 'error': f"更新投资组合指标失败: {str(e)}"}

def calculate_risk_metrics(assets):
    """计算投资组合风险指标"""
    # 资产数量
    asset_count = len(assets)
    
    # 计算总价值
    total_value = sum(asset.get('current_value', 0) for asset in assets)
    
    # 默认指标
    metrics = {
        'diversification_score': 0,
        'volatility_score': 5,
        'risk_score': 5,
        'asset_count': asset_count,
        'total_value': total_value
    }
    
    # 如果没有资产，直接返回默认指标
    if asset_count == 0:
        return metrics
    
    # 多样化得分 (基于资产数量和集中度)
    # 0-3 个资产: 低多样化
    # 4-7 个资产: 中等多样化
    # 8+ 个资产: 高多样化
    if asset_count < 4:
        diversification_score = min(3, asset_count) * 2
    elif asset_count < 8:
        diversification_score = 6 + (asset_count - 3)
    else:
        diversification_score = 10
    
    # 检查集中度 - 如果单一资产占比超过50%，降低多样化得分
    for asset in assets:
        allocation = asset.get('allocation_percentage', 0)
        if allocation > 50:
            diversification_score = max(1, diversification_score - 4)
            break
        elif allocation > 30:
            diversification_score = max(1, diversification_score - 2)
            break
    
    # 波动性得分 (基于24小时价格变化的振幅)
    # 计算24小时价格变化的平均绝对值
    price_changes = [abs(asset.get('price_change_24h', 0)) for asset in assets if asset.get('price_change_24h') is not None]
    avg_price_change = sum(price_changes) / len(price_changes) if price_changes else 0
    
    # 波动性评分
    if avg_price_change < 1:
        volatility_score = 1  # 非常低波动性
    elif avg_price_change < 3:
        volatility_score = 3  # 低波动性
    elif avg_price_change < 5:
        volatility_score = 5  # 中等波动性
    elif avg_price_change < 8:
        volatility_score = 7  # 高波动性
    else:
        volatility_score = 10  # 非常高波动性
    
    # 整体风险评分 (多样化和波动性的加权平均)
    risk_score = (volatility_score * 0.7) - (diversification_score * 0.3)
    risk_score = max(1, min(10, round(risk_score)))
    
    metrics.update({
        'diversification_score': diversification_score,
        'volatility_score': volatility_score,
        'risk_score': risk_score
    })
    
    return metrics

def generate_optimization_suggestions(assets, metrics):
    """生成投资组合优化建议"""
    suggestions = []
    
    # 如果没有资产，建议添加主流加密货币
    if not assets:
        suggestions.append({
            'type': 'add_assets',
            'severity': 'high',
            'message': '您的投资组合目前没有资产。建议添加一些主流加密货币如比特币(BTC)和以太坊(ETH)作为基础。'
        })
        return suggestions
    
    # 检查多样化程度
    if metrics.get('diversification_score', 0) < 5:
        suggestions.append({
            'type': 'diversification',
            'severity': 'medium',
            'message': '您的投资组合多样化程度较低。考虑增加不同类型的加密货币以降低风险。'
        })
    
    # 检查资产集中度
    high_concentration_assets = []
    for asset in assets:
        if asset.get('allocation_percentage', 0) > 40:
            high_concentration_assets.append(asset.get('name'))
    
    if high_concentration_assets:
        suggestions.append({
            'type': 'concentration',
            'severity': 'medium',
            'message': f"您的投资组合过于集中在 {', '.join(high_concentration_assets)} 上。考虑重新平衡以降低特定资产风险。",
            'assets': high_concentration_assets
        })
    
    # 检查波动性
    if metrics.get('volatility_score', 0) > 7:
        suggestions.append({
            'type': 'volatility',
            'severity': 'medium',
            'message': '您的投资组合波动性较高。考虑增加一些稳定币或波动性较低的资产来平衡风险。'
        })
    
    # 检查是否有稳定币
    has_stablecoin = any(asset.get('symbol') in ['USDT', 'USDC', 'DAI', 'BUSD'] for asset in assets)
    if not has_stablecoin and len(assets) >= 3:
        suggestions.append({
            'type': 'stablecoin',
            'severity': 'low',
            'message': '您的投资组合中没有稳定币。考虑添加一些稳定币以应对市场波动。'
        })
    
    # 根据投资组合规模生成更多建议
    if len(assets) > 10:
        suggestions.append({
            'type': 'consolidation',
            'severity': 'low',
            'message': '您的投资组合包含很多小型持仓。考虑合并一些较小的持仓以简化管理。'
        })
    
    return suggestions

def update_performance_history(portfolio, assets):
    """更新投资组合的历史表现数据"""
    # 获取当前性能历史
    history = portfolio.get_performance_history()
    
    # 计算当前总价值
    total_value = sum(asset.get('current_value', 0) for asset in assets)
    
    # 当前日期
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 添加今天的数据点
    if today not in history:
        history[today] = {
            'total_value': total_value,
            'asset_count': len(assets),
            'assets': []
        }
        
        # 添加各资产贡献
        for asset in assets:
            history[today]['assets'].append({
                'symbol': asset.get('symbol'),
                'name': asset.get('name'),
                'value': asset.get('current_value', 0),
                'price': asset.get('current_price', 0),
                'amount': asset.get('amount', 0)
            })
    
    # 限制历史数据量
    # 如果历史记录过多，只保留最近60天
    dates = sorted(history.keys())
    if len(dates) > 60:
        for old_date in dates[:-60]:
            if old_date in history:
                del history[old_date]
    
    # 更新历史数据
    portfolio.set_performance_history(history)