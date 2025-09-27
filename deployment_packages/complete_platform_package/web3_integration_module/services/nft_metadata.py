"""
NFT元数据和SVG生成器
为SLA证明NFT生成专业的元数据和动态SVG图像
"""

import logging
import json
import base64
from datetime import datetime, date
from typing import Dict, List, Optional, Any, Tuple
import hashlib
import math
import colorsys

logger = logging.getLogger(__name__)

class NFTMetadataGenerator:
    """NFT元数据和SVG生成器主类"""
    
    def __init__(self):
        """初始化生成器"""
        self.svg_width = 1000
        self.svg_height = 1000
        self.color_schemes = {
            'excellent': {
                'primary': '#00ff88',      # 翠绿色
                'secondary': '#00cc6a',    # 深绿色
                'accent': '#66ffaa',       # 浅绿色
                'background': '#0a1a0f',   # 深绿背景
                'text': '#ffffff',         # 白色文字
                'gradient_start': '#00ff88',
                'gradient_end': '#00cc6a'
            },
            'good': {
                'primary': '#4dabf7',      # 蓝色
                'secondary': '#339af0',    # 深蓝色
                'accent': '#74c0fc',       # 浅蓝色
                'background': '#0c1618',   # 深蓝背景
                'text': '#ffffff',
                'gradient_start': '#4dabf7',
                'gradient_end': '#339af0'
            },
            'acceptable': {
                'primary': '#ffd43b',      # 金黄色
                'secondary': '#fab005',    # 橙黄色
                'accent': '#ffe066',       # 浅黄色
                'background': '#1a1508',   # 深黄背景
                'text': '#000000',
                'gradient_start': '#ffd43b',
                'gradient_end': '#fab005'
            },
            'poor': {
                'primary': '#ff8787',      # 浅红色
                'secondary': '#ff6b6b',    # 中红色
                'accent': '#ffa8a8',       # 很浅红色
                'background': '#1a0b0b',   # 深红背景
                'text': '#ffffff',
                'gradient_start': '#ff8787',
                'gradient_end': '#ff6b6b'
            },
            'failed': {
                'primary': '#6c757d',      # 灰色
                'secondary': '#495057',    # 深灰色
                'accent': '#868e96',       # 浅灰色
                'background': '#121416',   # 很深灰背景
                'text': '#ffffff',
                'gradient_start': '#6c757d',
                'gradient_end': '#495057'
            }
        }
        
        logger.info("NFTMetadataGenerator initialized")
    
    def generate_sla_certificate_metadata(self, certificate_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成SLA证书NFT元数据
        
        Args:
            certificate_data: 证书数据
            
        Returns:
            NFT元数据
        """
        try:
            # 提取关键信息
            month_year = certificate_data.get('month_year')
            sla_score = certificate_data.get('sla_score', 0)
            user_info = certificate_data.get('user_info', {})
            metrics = certificate_data.get('metrics', {})
            
            # 确定SLA等级和颜色方案
            sla_grade = self._determine_sla_grade(sla_score)
            color_scheme = self.color_schemes[sla_grade]
            
            # 生成SVG图像
            svg_image = self._generate_sla_certificate_svg(
                certificate_data, sla_grade, color_scheme
            )
            
            # 转换为base64 data URL
            svg_base64 = base64.b64encode(svg_image.encode()).decode()
            image_data_url = f"data:image/svg+xml;base64,{svg_base64}"
            
            # 构建元数据
            metadata = {
                "name": f"SLA Certificate - {self._format_month_year(month_year)}",
                "description": self._generate_certificate_description(certificate_data, sla_grade),
                "image": image_data_url,
                "external_url": f"https://your-domain.com/certificates/{certificate_data.get('id')}",
                "attributes": self._generate_attributes(certificate_data, sla_grade),
                "properties": {
                    "category": "SLA Certificate",
                    "type": "Soulbound",
                    "version": "1.0.0",
                    "generated_at": datetime.utcnow().isoformat(),
                    "month_year": month_year,
                    "sla_score": sla_score,
                    "sla_grade": sla_grade.title(),
                    "recipient": user_info.get('wallet_address', ''),
                    "certificate_id": certificate_data.get('id'),
                    "blockchain_verified": True
                },
                "background_color": color_scheme['background'].replace('#', ''),
                "animation_url": None,  # 可以添加动画版本
                "youtube_url": None
            }
            
            logger.info(f"生成NFT元数据成功: 证书ID {certificate_data.get('id')}")
            return metadata
            
        except Exception as e:
            logger.error(f"生成NFT元数据失败: {e}")
            raise
    
    def _generate_sla_certificate_svg(self, certificate_data: Dict[str, Any], 
                                    sla_grade: str, color_scheme: Dict[str, str]) -> str:
        """生成SLA证书SVG"""
        try:
            month_year = certificate_data.get('month_year')
            sla_score = certificate_data.get('sla_score', 0)
            metrics = certificate_data.get('metrics', {})
            user_info = certificate_data.get('user_info', {})
            
            # SVG模板
            svg = f'''<svg width="{self.svg_width}" height="{self.svg_height}" 
                        xmlns="http://www.w3.org/2000/svg">
                
                <!-- 背景渐变 -->
                <defs>
                    <radialGradient id="backgroundGradient" cx="50%" cy="50%" r="70%">
                        <stop offset="0%" style="stop-color:{color_scheme['gradient_start']};stop-opacity:0.1"/>
                        <stop offset="100%" style="stop-color:{color_scheme['background']};stop-opacity:1"/>
                    </radialGradient>
                    
                    <linearGradient id="headerGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                        <stop offset="0%" style="stop-color:{color_scheme['primary']}"/>
                        <stop offset="100%" style="stop-color:{color_scheme['secondary']}"/>
                    </linearGradient>
                    
                    <!-- 光效滤镜 -->
                    <filter id="glow">
                        <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
                        <feMerge> 
                            <feMergeNode in="coloredBlur"/>
                            <feMergeNode in="SourceGraphic"/>
                        </feMerge>
                    </filter>
                </defs>
                
                <!-- 背景 -->
                <rect width="100%" height="100%" fill="url(#backgroundGradient)"/>
                
                <!-- 边框装饰 -->
                {self._generate_border_decorations(color_scheme)}
                
                <!-- 头部区域 -->
                <rect x="50" y="50" width="900" height="150" rx="15" fill="url(#headerGradient)" opacity="0.9"/>
                
                <!-- 标题 -->
                <text x="500" y="110" text-anchor="middle" font-family="Arial, sans-serif" 
                      font-size="48" font-weight="bold" fill="{color_scheme['text']}" filter="url(#glow)">
                    SLA CERTIFICATE
                </text>
                
                <text x="500" y="150" text-anchor="middle" font-family="Arial, sans-serif" 
                      font-size="24" fill="{color_scheme['text']}" opacity="0.8">
                    Service Level Agreement Proof
                </text>
                
                <!-- 月份年份 -->
                <text x="500" y="250" text-anchor="middle" font-family="Arial, sans-serif" 
                      font-size="36" font-weight="bold" fill="{color_scheme['primary']}">
                    {self._format_month_year(month_year)}
                </text>
                
                <!-- SLA分数圆环 -->
                {self._generate_sla_score_circle(500, 400, sla_score, color_scheme)}
                
                <!-- 指标面板 -->
                {self._generate_metrics_panel(metrics, color_scheme)}
                
                <!-- 等级标识 -->
                <rect x="350" y="750" width="300" height="80" rx="40" 
                      fill="{color_scheme['primary']}" opacity="0.2" stroke="{color_scheme['primary']}" stroke-width="2"/>
                <text x="500" y="800" text-anchor="middle" font-family="Arial, sans-serif" 
                      font-size="32" font-weight="bold" fill="{color_scheme['primary']}">
                    {sla_grade.upper()}
                </text>
                
                <!-- 底部信息 -->
                <text x="500" y="900" text-anchor="middle" font-family="Arial, sans-serif" 
                      font-size="16" fill="{color_scheme['text']}" opacity="0.7">
                    Blockchain Verified • Soulbound NFT
                </text>
                
                <text x="500" y="930" text-anchor="middle" font-family="Arial, sans-serif" 
                      font-size="14" fill="{color_scheme['text']}" opacity="0.5">
                    Generated on {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
                </text>
                
                <!-- 装饰性几何图案 -->
                {self._generate_geometric_patterns(color_scheme)}
                
            </svg>'''
            
            return svg
            
        except Exception as e:
            logger.error(f"生成SVG失败: {e}")
            raise
    
    def _generate_sla_score_circle(self, cx: int, cy: int, score: float, 
                                 color_scheme: Dict[str, str]) -> str:
        """生成SLA分数圆环"""
        try:
            radius = 80
            stroke_width = 12
            circumference = 2 * math.pi * radius
            progress = (score / 100) * circumference
            
            return f'''
                <!-- 背景圆环 -->
                <circle cx="{cx}" cy="{cy}" r="{radius}" fill="none" 
                        stroke="{color_scheme['background']}" stroke-width="{stroke_width}" opacity="0.3"/>
                
                <!-- 进度圆环 -->
                <circle cx="{cx}" cy="{cy}" r="{radius}" fill="none" 
                        stroke="{color_scheme['primary']}" stroke-width="{stroke_width}"
                        stroke-dasharray="{progress} {circumference}"
                        stroke-dashoffset="0" stroke-linecap="round"
                        transform="rotate(-90 {cx} {cy})" filter="url(#glow)"/>
                
                <!-- 分数文本 -->
                <text x="{cx}" y="{cy - 10}" text-anchor="middle" font-family="Arial, sans-serif" 
                      font-size="42" font-weight="bold" fill="{color_scheme['primary']}">
                    {score:.1f}%
                </text>
                
                <text x="{cx}" y="{cy + 25}" text-anchor="middle" font-family="Arial, sans-serif" 
                      font-size="18" fill="{color_scheme['text']}" opacity="0.7">
                    SLA Score
                </text>
            '''
            
        except Exception as e:
            logger.error(f"生成分数圆环失败: {e}")
            return ""
    
    def _generate_metrics_panel(self, metrics: Dict[str, Any], 
                              color_scheme: Dict[str, str]) -> str:
        """生成指标面板"""
        try:
            panel_y = 520
            metrics_data = [
                ("Uptime", f"{metrics.get('uptime_percentage', 0):.2f}%"),
                ("Response Time", f"{metrics.get('response_time_avg', 0):.1f}ms"),
                ("Accuracy", f"{metrics.get('accuracy_percentage', 0):.2f}%"),
                ("Transparency", f"{metrics.get('transparency_score', 0):.1f}")
            ]
            
            panel_svg = f'''
                <!-- 指标面板背景 -->
                <rect x="150" y="{panel_y}" width="700" height="180" rx="10" 
                      fill="{color_scheme['background']}" opacity="0.6" 
                      stroke="{color_scheme['primary']}" stroke-width="1"/>
            '''
            
            # 生成指标项
            for i, (label, value) in enumerate(metrics_data):
                x_pos = 200 + (i % 2) * 300
                y_pos = panel_y + 60 + (i // 2) * 60
                
                panel_svg += f'''
                    <text x="{x_pos}" y="{y_pos}" font-family="Arial, sans-serif" 
                          font-size="16" fill="{color_scheme['text']}" opacity="0.8">
                        {label}
                    </text>
                    <text x="{x_pos}" y="{y_pos + 25}" font-family="Arial, sans-serif" 
                          font-size="20" font-weight="bold" fill="{color_scheme['primary']}">
                        {value}
                    </text>
                '''
            
            return panel_svg
            
        except Exception as e:
            logger.error(f"生成指标面板失败: {e}")
            return ""
    
    def _generate_border_decorations(self, color_scheme: Dict[str, str]) -> str:
        """生成边框装饰"""
        return f'''
            <!-- 外边框 -->
            <rect x="10" y="10" width="980" height="980" rx="20" fill="none" 
                  stroke="{color_scheme['primary']}" stroke-width="2" opacity="0.3"/>
            
            <!-- 内边框 -->
            <rect x="25" y="25" width="950" height="950" rx="15" fill="none" 
                  stroke="{color_scheme['accent']}" stroke-width="1" opacity="0.5"/>
            
            <!-- 角落装饰 -->
            <circle cx="50" cy="50" r="5" fill="{color_scheme['primary']}" opacity="0.7"/>
            <circle cx="950" cy="50" r="5" fill="{color_scheme['primary']}" opacity="0.7"/>
            <circle cx="50" cy="950" r="5" fill="{color_scheme['primary']}" opacity="0.7"/>
            <circle cx="950" cy="950" r="5" fill="{color_scheme['primary']}" opacity="0.7"/>
        '''
    
    def _generate_geometric_patterns(self, color_scheme: Dict[str, str]) -> str:
        """生成装饰性几何图案"""
        return f'''
            <!-- 左侧装饰 -->
            <polygon points="100,300 120,280 140,300 120,320" 
                     fill="{color_scheme['accent']}" opacity="0.3"/>
            <polygon points="100,350 120,330 140,350 120,370" 
                     fill="{color_scheme['accent']}" opacity="0.2"/>
            
            <!-- 右侧装饰 -->
            <polygon points="860,300 880,280 900,300 880,320" 
                     fill="{color_scheme['accent']}" opacity="0.3"/>
            <polygon points="860,350 880,330 900,350 880,370" 
                     fill="{color_scheme['accent']}" opacity="0.2"/>
        '''
    
    def _determine_sla_grade(self, sla_score: float) -> str:
        """确定SLA等级"""
        if sla_score >= 95:
            return 'excellent'
        elif sla_score >= 90:
            return 'good'
        elif sla_score >= 85:
            return 'acceptable'
        elif sla_score >= 80:
            return 'poor'
        else:
            return 'failed'
    
    def _format_month_year(self, month_year: int) -> str:
        """格式化月份年份显示"""
        try:
            year = month_year // 100
            month = month_year % 100
            
            month_names = [
                "January", "February", "March", "April", "May", "June",
                "July", "August", "September", "October", "November", "December"
            ]
            
            return f"{month_names[month - 1]} {year}"
            
        except Exception as e:
            logger.error(f"格式化月份年份失败: {e}")
            return str(month_year)
    
    def _generate_certificate_description(self, certificate_data: Dict[str, Any], 
                                        sla_grade: str) -> str:
        """生成证书描述"""
        month_year = certificate_data.get('month_year')
        sla_score = certificate_data.get('sla_score', 0)
        
        return (
            f"This Soulbound NFT certificate verifies the Service Level Agreement "
            f"performance for {self._format_month_year(month_year)}. "
            f"Achieved SLA score: {sla_score:.1f}% ({sla_grade.title()} grade). "
            f"This certificate is permanently recorded on the blockchain and "
            f"cannot be transferred, ensuring the integrity and authenticity "
            f"of the SLA proof."
        )
    
    def _generate_attributes(self, certificate_data: Dict[str, Any], 
                           sla_grade: str) -> List[Dict[str, Any]]:
        """生成NFT属性"""
        month_year = certificate_data.get('month_year')
        sla_score = certificate_data.get('sla_score', 0)
        metrics = certificate_data.get('metrics', {})
        
        attributes = [
            {
                "trait_type": "Certificate Type",
                "value": "SLA Proof"
            },
            {
                "trait_type": "Month Year",
                "value": self._format_month_year(month_year)
            },
            {
                "trait_type": "SLA Grade",
                "value": sla_grade.title()
            },
            {
                "trait_type": "SLA Score",
                "value": sla_score,
                "display_type": "number"
            },
            {
                "trait_type": "Uptime Percentage",
                "value": metrics.get('uptime_percentage', 0),
                "display_type": "number"
            },
            {
                "trait_type": "Response Time (ms)",
                "value": metrics.get('response_time_avg', 0),
                "display_type": "number"
            },
            {
                "trait_type": "Accuracy Percentage",
                "value": metrics.get('accuracy_percentage', 0),
                "display_type": "number"
            },
            {
                "trait_type": "Transparency Score",
                "value": metrics.get('transparency_score', 0),
                "display_type": "number"
            },
            {
                "trait_type": "Blockchain Verified",
                "value": "Yes"
            },
            {
                "trait_type": "Transferable",
                "value": "No (Soulbound)"
            }
        ]
        
        return attributes
    
    def generate_batch_metadata(self, certificates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """批量生成元数据"""
        try:
            metadata_list = []
            
            for certificate in certificates:
                try:
                    metadata = self.generate_sla_certificate_metadata(certificate)
                    metadata_list.append(metadata)
                except Exception as e:
                    logger.error(f"生成证书 {certificate.get('id')} 元数据失败: {e}")
                    continue
            
            logger.info(f"批量生成元数据完成: {len(metadata_list)}/{len(certificates)}")
            return metadata_list
            
        except Exception as e:
            logger.error(f"批量生成元数据失败: {e}")
            return []

# 全局实例
nft_metadata_generator = NFTMetadataGenerator()

# 导出
__all__ = ['NFTMetadataGenerator', 'nft_metadata_generator']