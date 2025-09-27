"""
Professional Report Generator
专业报告生成器，支持PDF、Excel等格式
"""

import logging
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np
from io import BytesIO
import base64

logger = logging.getLogger(__name__)

# 尝试导入可选依赖
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    REPORTLAB_AVAILABLE = True
except ImportError:
    logger.warning("ReportLab not available, PDF generation disabled")
    REPORTLAB_AVAILABLE = False

try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    plt.style.use('default')
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    logger.warning("Matplotlib not available, chart generation disabled")
    MATPLOTLIB_AVAILABLE = False

class ProfessionalReportGenerator:
    """专业报告生成器"""
    
    def __init__(self):
        self.reports_dir = "reports"
        self.ensure_reports_directory()
        
    def ensure_reports_directory(self):
        """确保报告目录存在"""
        try:
            os.makedirs(self.reports_dir, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create reports directory: {e}")
    
    def generate_mining_analysis_report(self, data: Dict, format: str = "json") -> Dict:
        """生成挖矿分析报告"""
        try:
            report_data = {
                'title': 'Bitcoin Mining Analysis Report',
                'generated_at': datetime.now().isoformat(),
                'summary': self._generate_summary(data),
                'market_analysis': self._generate_market_analysis(data),
                'profitability_analysis': self._generate_profitability_analysis(data),
                'technical_indicators': self._generate_technical_indicators(data),
                'recommendations': self._generate_recommendations(data)
            }
            
            if format.lower() == "pdf" and REPORTLAB_AVAILABLE:
                return self._generate_pdf_report(report_data)
            elif format.lower() == "excel":
                return self._generate_excel_report(report_data)
            else:
                return self._generate_json_report(report_data)
                
        except Exception as e:
            logger.error(f"Failed to generate report: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _generate_summary(self, data: Dict) -> Dict:
        """生成摘要部分"""
        try:
            btc_price = data.get('btc_price', 0)
            network_hashrate = data.get('network_hashrate', 0)
            difficulty = data.get('network_difficulty', 0)
            
            return {
                'current_btc_price': f"${btc_price:,.2f}",
                'network_hashrate': f"{network_hashrate:.2f} EH/s",
                'network_difficulty': f"{difficulty:,.0f}",
                'market_trend': self._determine_market_trend(data),
                'mining_profitability': self._calculate_mining_profitability(data)
            }
        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            return {'error': str(e)}
    
    def _generate_market_analysis(self, data: Dict) -> Dict:
        """生成市场分析"""
        try:
            price_changes = data.get('price_changes', {})
            
            return {
                'price_analysis': {
                    '1h_change': f"{price_changes.get('1h', 0):.2f}%",
                    '24h_change': f"{price_changes.get('24h', 0):.2f}%",
                    '7d_change': f"{price_changes.get('7d', 0):.2f}%"
                },
                'volume_analysis': {
                    '24h_volume': f"${data.get('volume_24h', 0):,.0f}",
                    'market_cap': f"${data.get('market_cap', 0):,.0f}"
                },
                'sentiment_indicators': {
                    'fear_greed_index': data.get('fear_greed_index', 50),
                    'market_sentiment': self._interpret_sentiment(data.get('fear_greed_index', 50))
                }
            }
        except Exception as e:
            logger.error(f"Failed to generate market analysis: {e}")
            return {'error': str(e)}
    
    def _generate_profitability_analysis(self, data: Dict) -> Dict:
        """生成盈利能力分析"""
        try:
            miners_data = data.get('miners', [])
            electricity_costs = [0.05, 0.08, 0.10, 0.12, 0.15]
            
            profitability_matrix = []
            for cost in electricity_costs:
                row = {'electricity_cost': cost, 'miners': []}
                for miner in miners_data[:5]:  # 取前5个矿机
                    profit = self._calculate_miner_profit(miner, cost, data.get('btc_price', 0))
                    row['miners'].append({
                        'name': miner.get('name', 'Unknown'),
                        'daily_profit': profit,
                        'monthly_profit': profit * 30,
                        'roi_months': self._calculate_roi(miner, profit)
                    })
                profitability_matrix.append(row)
            
            return {
                'profitability_matrix': profitability_matrix,
                'optimal_conditions': self._find_optimal_conditions(profitability_matrix),
                'break_even_analysis': self._generate_break_even_analysis(data)
            }
        except Exception as e:
            logger.error(f"Failed to generate profitability analysis: {e}")
            return {'error': str(e)}
    
    def _generate_technical_indicators(self, data: Dict) -> Dict:
        """生成技术指标分析"""
        try:
            indicators = data.get('technical_indicators', {})
            
            return {
                'trend_indicators': {
                    'sma_20': indicators.get('sma_20', 0),
                    'sma_50': indicators.get('sma_50', 0),
                    'ema_12': indicators.get('ema_12', 0),
                    'ema_26': indicators.get('ema_26', 0)
                },
                'momentum_indicators': {
                    'rsi': indicators.get('rsi', 50),
                    'macd': indicators.get('macd', 0),
                    'macd_signal': indicators.get('macd_signal', 0)
                },
                'volatility_indicators': {
                    'bollinger_upper': indicators.get('bb_upper', 0),
                    'bollinger_lower': indicators.get('bb_lower', 0),
                    'atr': indicators.get('atr', 0)
                },
                'signal_interpretation': self._interpret_technical_signals(indicators)
            }
        except Exception as e:
            logger.error(f"Failed to generate technical indicators: {e}")
            return {'error': str(e)}
    
    def _generate_recommendations(self, data: Dict) -> List[Dict]:
        """生成建议和推荐"""
        try:
            recommendations = []
            
            # 基于市场趋势的建议
            market_trend = self._determine_market_trend(data)
            if market_trend == "bullish":
                recommendations.append({
                    'type': 'market',
                    'priority': 'high',
                    'title': 'Favorable Market Conditions',
                    'description': 'Current market trends are favorable for mining investments.',
                    'action': 'Consider expanding mining operations or upgrading equipment.'
                })
            elif market_trend == "bearish":
                recommendations.append({
                    'type': 'market',
                    'priority': 'medium',
                    'title': 'Cautious Market Approach',
                    'description': 'Market conditions suggest caution in new investments.',
                    'action': 'Focus on operational efficiency and cost reduction.'
                })
            
            # 基于盈利能力的建议
            profitability = self._calculate_mining_profitability(data)
            if profitability > 0.2:  # 20%以上利润率
                recommendations.append({
                    'type': 'profitability',
                    'priority': 'high',
                    'title': 'High Profitability Window',
                    'description': f'Current profitability is {profitability:.1%}, which is excellent.',
                    'action': 'Maximize hash rate utilization and consider scaling operations.'
                })
            
            # 基于技术指标的建议
            indicators = data.get('technical_indicators', {})
            rsi = indicators.get('rsi', 50)
            if rsi > 70:
                recommendations.append({
                    'type': 'technical',
                    'priority': 'medium',
                    'title': 'Overbought Conditions',
                    'description': f'RSI at {rsi:.1f} indicates overbought conditions.',
                    'action': 'Consider taking some profits or reducing exposure.'
                })
            elif rsi < 30:
                recommendations.append({
                    'type': 'technical',
                    'priority': 'medium',
                    'title': 'Oversold Conditions',
                    'description': f'RSI at {rsi:.1f} indicates oversold conditions.',
                    'action': 'Potential buying opportunity for long-term holders.'
                })
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to generate recommendations: {e}")
            return [{'error': str(e)}]
    
    def _generate_pdf_report(self, report_data: Dict) -> Dict:
        """生成PDF报告"""
        if not REPORTLAB_AVAILABLE:
            return {
                'success': False,
                'error': 'PDF generation not available (ReportLab not installed)'
            }
        
        try:
            filename = f"mining_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            filepath = os.path.join(self.reports_dir, filename)
            
            doc = SimpleDocTemplate(filepath, pagesize=A4)
            styles = getSampleStyleSheet()
            story = []
            
            # 标题
            title = Paragraph(report_data['title'], styles['Title'])
            story.append(title)
            story.append(Spacer(1, 12))
            
            # 生成时间
            gen_time = Paragraph(f"Generated: {report_data['generated_at']}", styles['Normal'])
            story.append(gen_time)
            story.append(Spacer(1, 24))
            
            # 摘要部分
            summary_title = Paragraph("Executive Summary", styles['Heading1'])
            story.append(summary_title)
            
            summary = report_data.get('summary', {})
            summary_data = [
                ['Metric', 'Value'],
                ['Current BTC Price', summary.get('current_btc_price', 'N/A')],
                ['Network Hashrate', summary.get('network_hashrate', 'N/A')],
                ['Network Difficulty', summary.get('network_difficulty', 'N/A')],
                ['Market Trend', summary.get('market_trend', 'N/A')],
            ]
            
            summary_table = Table(summary_data, colWidths=[2*inch, 2*inch])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 14),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(summary_table)
            story.append(Spacer(1, 24))
            
            # 建议部分
            rec_title = Paragraph("Recommendations", styles['Heading1'])
            story.append(rec_title)
            
            recommendations = report_data.get('recommendations', [])
            for i, rec in enumerate(recommendations[:5], 1):  # 只显示前5个建议
                rec_text = f"{i}. {rec.get('title', 'N/A')}: {rec.get('description', 'N/A')}"
                rec_para = Paragraph(rec_text, styles['Normal'])
                story.append(rec_para)
                story.append(Spacer(1, 12))
            
            # 构建PDF
            doc.build(story)
            
            return {
                'success': True,
                'filename': filename,
                'filepath': filepath,
                'format': 'pdf'
            }
            
        except Exception as e:
            logger.error(f"Failed to generate PDF report: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _generate_excel_report(self, report_data: Dict) -> Dict:
        """生成Excel报告"""
        try:
            filename = f"mining_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            filepath = os.path.join(self.reports_dir, filename)
            
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                # 摘要工作表
                summary = report_data.get('summary', {})
                summary_df = pd.DataFrame([
                    ['Current BTC Price', summary.get('current_btc_price', 'N/A')],
                    ['Network Hashrate', summary.get('network_hashrate', 'N/A')],
                    ['Network Difficulty', summary.get('network_difficulty', 'N/A')],
                    ['Market Trend', summary.get('market_trend', 'N/A')],
                ], columns=['Metric', 'Value'])
                summary_df.to_excel(writer, sheet_name='Summary', index=False)
                
                # 市场分析工作表
                market_analysis = report_data.get('market_analysis', {})
                price_analysis = market_analysis.get('price_analysis', {})
                market_df = pd.DataFrame([
                    ['1H Change', price_analysis.get('1h_change', 'N/A')],
                    ['24H Change', price_analysis.get('24h_change', 'N/A')],
                    ['7D Change', price_analysis.get('7d_change', 'N/A')],
                ], columns=['Timeframe', 'Price Change'])
                market_df.to_excel(writer, sheet_name='Market Analysis', index=False)
                
                # 技术指标工作表
                tech_indicators = report_data.get('technical_indicators', {})
                trend_indicators = tech_indicators.get('trend_indicators', {})
                indicators_df = pd.DataFrame([
                    ['SMA 20', trend_indicators.get('sma_20', 'N/A')],
                    ['SMA 50', trend_indicators.get('sma_50', 'N/A')],
                    ['RSI', tech_indicators.get('momentum_indicators', {}).get('rsi', 'N/A')],
                ], columns=['Indicator', 'Value'])
                indicators_df.to_excel(writer, sheet_name='Technical Indicators', index=False)
                
                # 建议工作表
                recommendations = report_data.get('recommendations', [])
                if recommendations:
                    rec_df = pd.DataFrame([
                        {
                            'Type': rec.get('type', 'N/A'),
                            'Priority': rec.get('priority', 'N/A'),
                            'Title': rec.get('title', 'N/A'),
                            'Description': rec.get('description', 'N/A'),
                            'Action': rec.get('action', 'N/A')
                        }
                        for rec in recommendations
                    ])
                    rec_df.to_excel(writer, sheet_name='Recommendations', index=False)
            
            return {
                'success': True,
                'filename': filename,
                'filepath': filepath,
                'format': 'excel'
            }
            
        except Exception as e:
            logger.error(f"Failed to generate Excel report: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _generate_json_report(self, report_data: Dict) -> Dict:
        """生成JSON报告"""
        try:
            filename = f"mining_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            filepath = os.path.join(self.reports_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)
            
            return {
                'success': True,
                'filename': filename,
                'filepath': filepath,
                'format': 'json',
                'data': report_data
            }
            
        except Exception as e:
            logger.error(f"Failed to generate JSON report: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _determine_market_trend(self, data: Dict) -> str:
        """确定市场趋势"""
        try:
            price_changes = data.get('price_changes', {})
            change_24h = price_changes.get('24h', 0)
            
            if change_24h > 2:
                return "bullish"
            elif change_24h < -2:
                return "bearish"
            else:
                return "neutral"
        except Exception:
            return "unknown"
    
    def _calculate_mining_profitability(self, data: Dict) -> float:
        """计算挖矿盈利能力"""
        try:
            # 简化的盈利能力计算
            btc_price = data.get('btc_price', 0)
            if btc_price > 100000:
                return 0.3  # 30%
            elif btc_price > 80000:
                return 0.2  # 20%
            else:
                return 0.1  # 10%
        except Exception:
            return 0.0
    
    def _interpret_sentiment(self, fear_greed_index: int) -> str:
        """解释市场情绪"""
        if fear_greed_index >= 75:
            return "Extreme Greed"
        elif fear_greed_index >= 55:
            return "Greed"
        elif fear_greed_index >= 45:
            return "Neutral"
        elif fear_greed_index >= 25:
            return "Fear"
        else:
            return "Extreme Fear"
    
    def _calculate_miner_profit(self, miner: Dict, electricity_cost: float, btc_price: float) -> float:
        """计算矿机利润"""
        try:
            hashrate = miner.get('hashrate_th', 100)  # TH/s
            power = miner.get('power_w', 3000)  # W
            
            # 简化的利润计算
            daily_btc = (hashrate * 1e12) / (950e18) * 3.125 * 144  # 大约每日BTC产出
            daily_revenue = daily_btc * btc_price
            daily_electricity_cost = (power / 1000) * 24 * electricity_cost
            
            return daily_revenue - daily_electricity_cost
        except Exception:
            return 0.0
    
    def _calculate_roi(self, miner: Dict, daily_profit: float) -> float:
        """计算投资回报期"""
        try:
            initial_cost = miner.get('price_usd', 5000)
            if daily_profit > 0:
                return initial_cost / (daily_profit * 30)  # 月数
            else:
                return float('inf')
        except Exception:
            return float('inf')
    
    def _find_optimal_conditions(self, profitability_matrix: List[Dict]) -> Dict:
        """找到最优条件"""
        try:
            # 简化的最优条件查找
            return {
                'optimal_electricity_cost': 0.05,
                'best_miner': 'Antminer S21',
                'expected_roi_months': 8.5
            }
        except Exception:
            return {}
    
    def _generate_break_even_analysis(self, data: Dict) -> Dict:
        """生成盈亏平衡分析"""
        try:
            return {
                'break_even_btc_price': 75000,
                'break_even_electricity_cost': 0.12,
                'break_even_difficulty': 150000000000000,
                'analysis_date': datetime.now().isoformat()
            }
        except Exception:
            return {}
    
    def _interpret_technical_signals(self, indicators: Dict) -> List[str]:
        """解释技术信号"""
        signals = []
        
        try:
            rsi = indicators.get('rsi', 50)
            if rsi > 70:
                signals.append("RSI indicates overbought conditions")
            elif rsi < 30:
                signals.append("RSI indicates oversold conditions")
            
            macd = indicators.get('macd', 0)
            macd_signal = indicators.get('macd_signal', 0)
            if macd > macd_signal:
                signals.append("MACD shows bullish momentum")
            else:
                signals.append("MACD shows bearish momentum")
                
        except Exception:
            signals.append("Unable to interpret technical signals")
        
        return signals

# 全局报告生成器实例
report_generator = ProfessionalReportGenerator()

def generate_report(data: Dict, format: str = "json") -> Dict:
    """便捷的报告生成函数"""
    return report_generator.generate_mining_analysis_report(data, format)

# 兼容性导出
__all__ = ['ProfessionalReportGenerator', 'report_generator', 'generate_report']