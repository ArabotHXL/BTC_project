#!/usr/bin/env python3
"""
NFT元数据和SVG生成器
NFT Metadata and SVG Generator for SLA Proof Certificates

为SLA证明NFT生成专业的元数据和动态SVG图像
Generates professional metadata and dynamic SVG images for SLA Proof NFTs
"""

import logging
import json
import base64
from datetime import datetime, date
from typing import Dict, List, Optional, Any, Tuple
import hashlib
import math
import colorsys

# 数据库和模型导入
from models import SLAMetrics, SLACertificateRecord, SLAStatus

# 设置日志
logging.basicConfig(level=logging.INFO)
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
                'accent': '#ffa8a8',       # 粉红色
                'background': '#1a0808',   # 深红背景
                'text': '#ffffff',
                'gradient_start': '#ff8787',
                'gradient_end': '#ff6b6b'
            },
            'failed': {
                'primary': '#e03131',      # 红色
                'secondary': '#c92a2a',    # 深红色
                'accent': '#ff5757',       # 亮红色
                'background': '#2d0a0a',   # 深红背景
                'text': '#ffffff',
                'gradient_start': '#e03131',
                'gradient_end': '#c92a2a'
            }
        }
        
        logger.info("NFT Metadata Generator initialized")
    
    def generate_metadata(self, sla_metrics: SLAMetrics, month_year: int, 
                         recipient_address: str, certificate_id: str = None) -> Dict:
        """
        生成完整的NFT元数据
        
        Args:
            sla_metrics: SLA指标数据
            month_year: 月年份 (YYYYMM格式)
            recipient_address: 接收者地址
            certificate_id: 证书ID
            
        Returns:
            完整的NFT元数据字典
        """
        try:
            # 解析月份和年份
            year = month_year // 100
            month = month_year % 100
            month_name = self._get_month_name(month)
            
            # 确定等级颜色主题
            status_key = sla_metrics.sla_status.name.lower()
            
            # 生成SVG图像
            svg_image = self._generate_svg_certificate(sla_metrics, month_year, recipient_address)
            
            # 生成基础元数据
            metadata = {
                "name": f"BTC Mining SLA Certificate - {month_name} {year}",
                "description": f"Service Level Agreement proof certificate for {month_name} {year}. "
                             f"This Soulbound NFT certifies {float(sla_metrics.composite_sla_score):.2f}% SLA compliance "
                             f"for Bitcoin mining calculator services with {sla_metrics.sla_status.value} rating.",
                "image": f"data:image/svg+xml;base64,{base64.b64encode(svg_image.encode()).decode()}",
                
                # OpenSea标准属性
                "external_url": f"https://calc.hashinsight.net/sla/certificate/{certificate_id or 'unknown'}",
                "background_color": self.color_schemes[status_key]['background'].replace('#', ''),
                
                # NFT特性属性
                "attributes": [
                    {
                        "trait_type": "Certificate Type",
                        "value": "SLA Proof Certificate"
                    },
                    {
                        "trait_type": "Month",
                        "value": f"{month_name} {year}"
                    },
                    {
                        "trait_type": "SLA Score",
                        "value": float(sla_metrics.composite_sla_score),
                        "display_type": "number",
                        "max_value": 100
                    },
                    {
                        "trait_type": "SLA Status",
                        "value": sla_metrics.sla_status.value
                    },
                    {
                        "trait_type": "Uptime Percentage",
                        "value": float(sla_metrics.uptime_percentage),
                        "display_type": "number",
                        "max_value": 100
                    },
                    {
                        "trait_type": "Availability Percentage", 
                        "value": float(sla_metrics.availability_percentage),
                        "display_type": "number",
                        "max_value": 100
                    },
                    {
                        "trait_type": "Average Response Time",
                        "value": sla_metrics.avg_response_time_ms,
                        "display_type": "number"
                    },
                    {
                        "trait_type": "Data Accuracy",
                        "value": float(sla_metrics.data_accuracy_percentage),
                        "display_type": "number",
                        "max_value": 100
                    },
                    {
                        "trait_type": "API Success Rate",
                        "value": float(sla_metrics.api_success_rate),
                        "display_type": "number", 
                        "max_value": 100
                    },
                    {
                        "trait_type": "Transparency Score",
                        "value": float(sla_metrics.transparency_score),
                        "display_type": "number",
                        "max_value": 100
                    },
                    {
                        "trait_type": "Blockchain Verifications",
                        "value": sla_metrics.blockchain_verifications,
                        "display_type": "number"
                    },
                    {
                        "trait_type": "IPFS Uploads",
                        "value": sla_metrics.ipfs_uploads,
                        "display_type": "number"
                    },
                    {
                        "trait_type": "Total Errors",
                        "value": sla_metrics.error_count,
                        "display_type": "number"
                    },
                    {
                        "trait_type": "Downtime Minutes",
                        "value": sla_metrics.downtime_minutes,
                        "display_type": "number"
                    },
                    {
                        "trait_type": "Certificate Generation",
                        "value": datetime.utcnow().strftime("%Y-%m-%d"),
                        "display_type": "date"
                    },
                    {
                        "trait_type": "Rarity",
                        "value": self._calculate_rarity(sla_metrics)
                    }
                ],
                
                # 自定义扩展属性
                "sla_metrics": {
                    "composite_score": float(sla_metrics.composite_sla_score),
                    "uptime": float(sla_metrics.uptime_percentage),
                    "availability": float(sla_metrics.availability_percentage),
                    "response_time": {
                        "average": sla_metrics.avg_response_time_ms,
                        "maximum": sla_metrics.max_response_time_ms,
                        "minimum": sla_metrics.min_response_time_ms
                    },
                    "accuracy": float(sla_metrics.data_accuracy_percentage),
                    "api_success_rate": float(sla_metrics.api_success_rate),
                    "transparency": float(sla_metrics.transparency_score),
                    "blockchain_stats": {
                        "verifications": sla_metrics.blockchain_verifications,
                        "ipfs_uploads": sla_metrics.ipfs_uploads
                    },
                    "error_stats": {
                        "total_errors": sla_metrics.error_count,
                        "critical_errors": sla_metrics.critical_error_count,
                        "downtime_minutes": sla_metrics.downtime_minutes
                    }
                },
                
                # 平台和合规信息
                "platform": {
                    "name": "HashInsight BTC Mining Calculator",
                    "version": "2.0.0",
                    "blockchain": "Base L2",
                    "standard": "ERC-721 Soulbound"
                },
                
                # 验证和审计信息
                "verification": {
                    "data_source": sla_metrics.data_source or "system_monitor",
                    "verified_by_blockchain": sla_metrics.verified_by_blockchain,
                    "ipfs_hash": sla_metrics.ipfs_hash,
                    "recorded_at": sla_metrics.recorded_at.isoformat() if sla_metrics.recorded_at else None
                }
            }
            
            # 添加特殊徽章属性
            badges = self._generate_achievement_badges(sla_metrics)
            if badges:
                metadata["attributes"].extend([
                    {
                        "trait_type": "Achievement Badges",
                        "value": ", ".join(badges)
                    }
                ])
            
            logger.info(f"Generated NFT metadata for {month_name} {year}: {sla_metrics.composite_sla_score}% SLA")
            
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to generate NFT metadata: {e}")
            return self._generate_fallback_metadata(month_year, recipient_address)
    
    def _generate_svg_certificate(self, sla_metrics: SLAMetrics, month_year: int, 
                                recipient_address: str) -> str:
        """生成动态SVG证书图像"""
        try:
            year = month_year // 100
            month = month_year % 100
            month_name = self._get_month_name(month)
            
            status_key = sla_metrics.sla_status.name.lower()
            colors = self.color_schemes[status_key]
            
            # 计算径向进度条参数
            score = float(sla_metrics.composite_sla_score)
            progress_angle = (score / 100) * 360
            
            # 生成SVG
            svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg width="{self.svg_width}" height="{self.svg_height}" viewBox="0 0 {self.svg_width} {self.svg_height}" 
     xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
  
  <!-- 定义渐变和滤镜 -->
  <defs>
    {self._generate_svg_definitions(colors)}
  </defs>
  
  <!-- 背景 -->
  <rect width="{self.svg_width}" height="{self.svg_height}" fill="{colors['background']}" />
  
  <!-- 背景图案 -->
  {self._generate_background_pattern(colors)}
  
  <!-- 主要内容区域 -->
  <g transform="translate(50, 50)">
    
    <!-- 顶部标题区域 -->
    {self._generate_header_section(month_name, year, colors)}
    
    <!-- 中心评分圆环 -->
    {self._generate_score_circle(score, colors, progress_angle)}
    
    <!-- 性能指标网格 -->
    {self._generate_metrics_grid(sla_metrics, colors)}
    
    <!-- 底部信息区域 -->
    {self._generate_footer_section(recipient_address, colors)}
    
    <!-- 装饰元素 -->
    {self._generate_decorative_elements(colors)}
    
  </g>
  
  <!-- 边框和特效 -->
  {self._generate_border_effects(colors)}
  
</svg>"""

            return svg
            
        except Exception as e:
            logger.error(f"Failed to generate SVG certificate: {e}")
            return self._generate_fallback_svg(month_year, recipient_address)
    
    def _generate_svg_definitions(self, colors: Dict) -> str:
        """生成SVG定义部分"""
        return f"""
    <linearGradient id="primaryGradient" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{colors['gradient_start']};stop-opacity:1" />
      <stop offset="100%" style="stop-color:{colors['gradient_end']};stop-opacity:1" />
    </linearGradient>
    
    <radialGradient id="scoreGradient" cx="50%" cy="50%" r="50%">
      <stop offset="0%" style="stop-color:{colors['primary']};stop-opacity:0.8" />
      <stop offset="70%" style="stop-color:{colors['secondary']};stop-opacity:0.6" />
      <stop offset="100%" style="stop-color:{colors['background']};stop-opacity:0.4" />
    </radialGradient>
    
    <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="4" result="coloredBlur"/>
      <feMerge> 
        <feMergeNode in="coloredBlur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
    
    <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="3" dy="3" stdDeviation="2" flood-color="{colors['primary']}" flood-opacity="0.3"/>
    </filter>
    
    <pattern id="hexPattern" patternUnits="userSpaceOnUse" width="60" height="52">
      <polygon points="30,2 52,15 52,37 30,50 8,37 8,15" 
               fill="none" stroke="{colors['primary']}" stroke-width="0.5" opacity="0.1"/>
    </pattern>
    """
    
    def _generate_background_pattern(self, colors: Dict) -> str:
        """生成背景图案"""
        return f"""
  <!-- 背景六边形图案 -->
  <rect width="100%" height="100%" fill="url(#hexPattern)" opacity="0.3"/>
  
  <!-- 光效 -->
  <circle cx="500" cy="200" r="300" fill="url(#scoreGradient)" opacity="0.1"/>
  <circle cx="200" cy="800" r="200" fill="{colors['primary']}" opacity="0.05"/>
  <circle cx="800" cy="800" r="250" fill="{colors['secondary']}" opacity="0.05"/>
  """
    
    def _generate_header_section(self, month_name: str, year: int, colors: Dict) -> str:
        """生成标题部分"""
        return f"""
    <!-- 标题区域 -->
    <g transform="translate(400, 80)">
      <text x="0" y="0" text-anchor="middle" font-family="Arial, sans-serif" 
            font-size="28" font-weight="bold" fill="{colors['text']}" filter="url(#glow)">
        SLA PROOF CERTIFICATE
      </text>
      <text x="0" y="35" text-anchor="middle" font-family="Arial, sans-serif" 
            font-size="20" fill="{colors['accent']}">
        {month_name} {year}
      </text>
      <text x="0" y="60" text-anchor="middle" font-family="Arial, sans-serif" 
            font-size="14" fill="{colors['text']}" opacity="0.8">
        HashInsight BTC Mining Calculator Services
      </text>
    </g>
    
    <!-- 装饰线条 -->
    <line x1="200" y1="120" x2="700" y2="120" stroke="url(#primaryGradient)" stroke-width="2" opacity="0.6"/>
    """
    
    def _generate_score_circle(self, score: float, colors: Dict, progress_angle: float) -> str:
        """生成中心评分圆环"""
        # 计算进度弧路径
        center_x, center_y = 450, 400
        radius = 120
        
        # 将角度转换为弧度
        start_angle = -90  # 从顶部开始
        end_angle = start_angle + progress_angle
        
        start_x = center_x + radius * math.cos(math.radians(start_angle))
        start_y = center_y + radius * math.sin(math.radians(start_angle))
        
        end_x = center_x + radius * math.cos(math.radians(end_angle))
        end_y = center_y + radius * math.sin(math.radians(end_angle))
        
        large_arc = 1 if progress_angle > 180 else 0
        
        return f"""
    <!-- 评分圆环 -->
    <g transform="translate(0, 50)">
      
      <!-- 背景圆环 -->
      <circle cx="{center_x}" cy="{center_y}" r="{radius}" 
              fill="none" stroke="{colors['background']}" stroke-width="12" opacity="0.3"/>
      
      <!-- 进度圆环 -->
      <path d="M {start_x} {start_y} A {radius} {radius} 0 {large_arc} 1 {end_x} {end_y}" 
            fill="none" stroke="url(#primaryGradient)" stroke-width="12" 
            stroke-linecap="round" filter="url(#glow)"/>
      
      <!-- 中心分数显示 -->
      <text x="{center_x}" y="{center_y - 15}" text-anchor="middle" 
            font-family="Arial, sans-serif" font-size="48" font-weight="bold" 
            fill="{colors['primary']}" filter="url(#glow)">
        {score:.1f}
      </text>
      <text x="{center_x}" y="{center_y + 15}" text-anchor="middle" 
            font-family="Arial, sans-serif" font-size="16" 
            fill="{colors['text']}" opacity="0.8">
        SLA SCORE
      </text>
      
      <!-- 状态标签 -->
      <rect x="{center_x - 40}" y="{center_y + 40}" width="80" height="25" 
            rx="12" fill="url(#primaryGradient)" filter="url(#shadow)"/>
      <text x="{center_x}" y="{center_y + 56}" text-anchor="middle" 
            font-family="Arial, sans-serif" font-size="12" font-weight="bold" 
            fill="{colors['background']}">
        {self._get_status_text(score)}
      </text>
      
    </g>
    """
    
    def _generate_metrics_grid(self, sla_metrics: SLAMetrics, colors: Dict) -> str:
        """生成性能指标网格"""
        metrics_data = [
            ("UPTIME", f"{float(sla_metrics.uptime_percentage):.1f}%", "Runtime availability"),
            ("RESPONSE", f"{sla_metrics.avg_response_time_ms}ms", "Average response time"),
            ("ACCURACY", f"{float(sla_metrics.data_accuracy_percentage):.1f}%", "Data accuracy rate"),
            ("API SUCCESS", f"{float(sla_metrics.api_success_rate):.1f}%", "API call success rate"),
            ("TRANSPARENCY", f"{float(sla_metrics.transparency_score):.1f}%", "Transparency audit score"),
            ("BLOCKCHAIN", f"{sla_metrics.blockchain_verifications}", "Blockchain verifications")
        ]
        
        grid_html = []
        
        for i, (label, value, description) in enumerate(metrics_data):
            row = i // 3
            col = i % 3
            x = 50 + col * 280
            y = 650 + row * 120
            
            grid_html.append(f"""
      <!-- 指标卡片 {i} -->
      <g transform="translate({x}, {y})">
        <rect x="0" y="0" width="250" height="90" rx="8" 
              fill="{colors['background']}" stroke="{colors['primary']}" 
              stroke-width="1" opacity="0.6" filter="url(#shadow)"/>
        
        <text x="125" y="25" text-anchor="middle" 
              font-family="Arial, sans-serif" font-size="10" 
              fill="{colors['accent']}" font-weight="bold">
          {label}
        </text>
        
        <text x="125" y="50" text-anchor="middle" 
              font-family="Arial, sans-serif" font-size="20" font-weight="bold" 
              fill="{colors['primary']}">
          {value}
        </text>
        
        <text x="125" y="70" text-anchor="middle" 
              font-family="Arial, sans-serif" font-size="8" 
              fill="{colors['text']}" opacity="0.6">
          {description}
        </text>
      </g>
      """)
        
        return '\n'.join(grid_html)
    
    def _generate_footer_section(self, recipient_address: str, colors: Dict) -> str:
        """生成底部信息区域"""
        # 缩短地址显示
        short_address = f"{recipient_address[:6]}...{recipient_address[-4:]}"
        
        return f"""
    <!-- 底部信息 -->
    <g transform="translate(0, 850)">
      
      <!-- 分隔线 -->
      <line x1="100" y1="0" x2="800" y2="0" stroke="url(#primaryGradient)" 
            stroke-width="1" opacity="0.4"/>
      
      <!-- 接收者地址 -->
      <text x="450" y="25" text-anchor="middle" font-family="monospace" 
            font-size="12" fill="{colors['text']}" opacity="0.7">
        Issued to: {short_address}
      </text>
      
      <!-- 时间戳 -->
      <text x="450" y="45" text-anchor="middle" font-family="Arial, sans-serif" 
            font-size="10" fill="{colors['accent']}" opacity="0.6">
        Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
      </text>
      
      <!-- 区块链标识 -->
      <text x="450" y="65" text-anchor="middle" font-family="Arial, sans-serif" 
            font-size="10" fill="{colors['text']}" opacity="0.5">
        Base L2 • Soulbound NFT • ERC-721
      </text>
      
    </g>
    """
    
    def _generate_decorative_elements(self, colors: Dict) -> str:
        """生成装饰元素"""
        return f"""
    <!-- 装饰元素 -->
    
    <!-- 左上角装饰 -->
    <g transform="translate(50, 50)" opacity="0.4">
      <polygon points="0,0 40,0 40,40 20,60 0,40" fill="{colors['primary']}" opacity="0.3"/>
      <polygon points="0,0 40,0 20,20" fill="{colors['accent']}" opacity="0.5"/>
    </g>
    
    <!-- 右上角装饰 -->
    <g transform="translate(810, 50) scale(-1, 1)" opacity="0.4">
      <polygon points="0,0 40,0 40,40 20,60 0,40" fill="{colors['primary']}" opacity="0.3"/>
      <polygon points="0,0 40,0 20,20" fill="{colors['accent']}" opacity="0.5"/>
    </g>
    
    <!-- 星星装饰 -->
    <g opacity="0.3">
      <polygon points="150,200 155,210 165,210 157,218 160,228 150,223 140,228 143,218 135,210 145,210" 
               fill="{colors['accent']}"/>
      <polygon points="750,250 755,260 765,260 757,268 760,278 750,273 740,278 743,268 735,260 745,260" 
               fill="{colors['accent']}"/>
      <polygon points="100,700 105,710 115,710 107,718 110,728 100,723 90,728 93,718 85,710 95,710" 
               fill="{colors['accent']}"/>
    </g>
    """
    
    def _generate_border_effects(self, colors: Dict) -> str:
        """生成边框特效"""
        return f"""
  <!-- 边框特效 -->
  <rect x="10" y="10" width="{self.svg_width - 20}" height="{self.svg_height - 20}" 
        rx="20" fill="none" stroke="url(#primaryGradient)" stroke-width="3" 
        opacity="0.6" filter="url(#glow)"/>
  
  <!-- 角落装饰 -->
  <g stroke="{colors['primary']}" stroke-width="2" fill="none" opacity="0.8">
    <path d="M 30 30 L 60 30 L 60 60" />
    <path d="M {self.svg_width - 30} 30 L {self.svg_width - 60} 30 L {self.svg_width - 60} 60" />
    <path d="M 30 {self.svg_height - 30} L 60 {self.svg_height - 30} L 60 {self.svg_height - 60}" />
    <path d="M {self.svg_width - 30} {self.svg_height - 30} L {self.svg_width - 60} {self.svg_height - 30} L {self.svg_width - 60} {self.svg_height - 60}" />
  </g>
  """
    
    def _get_month_name(self, month: int) -> str:
        """获取月份名称"""
        month_names = {
            1: "January", 2: "February", 3: "March", 4: "April",
            5: "May", 6: "June", 7: "July", 8: "August",
            9: "September", 10: "October", 11: "November", 12: "December"
        }
        return month_names.get(month, "Unknown")
    
    def _get_status_text(self, score: float) -> str:
        """根据分数获取状态文本"""
        if score >= 95:
            return "EXCELLENT"
        elif score >= 90:
            return "GOOD"
        elif score >= 85:
            return "ACCEPTABLE"
        elif score >= 80:
            return "POOR"
        else:
            return "FAILED"
    
    def _calculate_rarity(self, sla_metrics: SLAMetrics) -> str:
        """计算证书稀有度"""
        score = float(sla_metrics.composite_sla_score)
        
        if score >= 99.5:
            return "Legendary"
        elif score >= 98:
            return "Epic"
        elif score >= 95:
            return "Rare"
        elif score >= 90:
            return "Uncommon"
        else:
            return "Common"
    
    def _generate_achievement_badges(self, sla_metrics: SLAMetrics) -> List[str]:
        """生成成就徽章"""
        badges = []
        
        # 基于各项指标生成徽章
        if float(sla_metrics.uptime_percentage) >= 99.9:
            badges.append("99.9% Uptime Champion")
        
        if sla_metrics.avg_response_time_ms <= 100:
            badges.append("Lightning Fast")
        
        if float(sla_metrics.data_accuracy_percentage) >= 99:
            badges.append("Data Precision Master")
        
        if float(sla_metrics.api_success_rate) >= 99.5:
            badges.append("API Reliability Expert")
        
        if sla_metrics.blockchain_verifications >= 100:
            badges.append("Blockchain Transparency Pioneer")
        
        if sla_metrics.error_count == 0:
            badges.append("Zero Error Achievement")
        
        if float(sla_metrics.composite_sla_score) >= 99:
            badges.append("Excellence Certified")
        
        return badges
    
    def _generate_fallback_metadata(self, month_year: int, recipient_address: str) -> Dict:
        """生成备用元数据（错误时使用）"""
        year = month_year // 100
        month = month_year % 100
        month_name = self._get_month_name(month)
        
        return {
            "name": f"BTC Mining SLA Certificate - {month_name} {year}",
            "description": f"Service Level Agreement proof certificate for {month_name} {year}.",
            "image": "data:image/svg+xml;base64," + base64.b64encode(
                self._generate_fallback_svg(month_year, recipient_address).encode()
            ).decode(),
            "attributes": [
                {
                    "trait_type": "Certificate Type",
                    "value": "SLA Proof Certificate"
                },
                {
                    "trait_type": "Month",
                    "value": f"{month_name} {year}"
                },
                {
                    "trait_type": "Status",
                    "value": "Error - Regeneration Required"
                }
            ]
        }
    
    def _generate_fallback_svg(self, month_year: int, recipient_address: str) -> str:
        """生成备用SVG（错误时使用）"""
        year = month_year // 100
        month = month_year % 100
        month_name = self._get_month_name(month)
        
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg width="1000" height="1000" viewBox="0 0 1000 1000" xmlns="http://www.w3.org/2000/svg">
  <rect width="1000" height="1000" fill="#1a1a1a"/>
  <text x="500" y="400" text-anchor="middle" font-family="Arial" font-size="24" fill="#ffffff">
    SLA Certificate
  </text>
  <text x="500" y="450" text-anchor="middle" font-family="Arial" font-size="18" fill="#cccccc">
    {month_name} {year}
  </text>
  <text x="500" y="550" text-anchor="middle" font-family="Arial" font-size="12" fill="#999999">
    Error occurred during generation
  </text>
</svg>"""

# 全局生成器实例
metadata_generator = None

def get_nft_generator() -> NFTMetadataGenerator:
    """获取NFT元数据生成器实例"""
    global metadata_generator
    if metadata_generator is None:
        metadata_generator = NFTMetadataGenerator()
        logger.info("Global NFT metadata generator initialized")
    return metadata_generator

def generate_certificate_metadata(sla_metrics: SLAMetrics, month_year: int, 
                                recipient_address: str, certificate_id: str = None) -> Dict:
    """
    便捷函数：生成SLA证书NFT元数据
    
    Args:
        sla_metrics: SLA指标数据
        month_year: 月年份 (YYYYMM格式)
        recipient_address: 接收者地址
        certificate_id: 证书ID
        
    Returns:
        完整的NFT元数据字典
    """
    generator = get_nft_generator()
    return generator.generate_metadata(sla_metrics, month_year, recipient_address, certificate_id)

if __name__ == "__main__":
    # 测试生成器
    from datetime import datetime
    from models import SLAStatus
    
    # 创建测试SLA数据
    class MockSLAMetrics:
        def __init__(self):
            self.composite_sla_score = 96.5
            self.sla_status = SLAStatus.EXCELLENT
            self.uptime_percentage = 99.8
            self.availability_percentage = 99.5
            self.avg_response_time_ms = 150
            self.max_response_time_ms = 800
            self.min_response_time_ms = 50
            self.data_accuracy_percentage = 99.2
            self.api_success_rate = 98.8
            self.transparency_score = 95.0
            self.blockchain_verifications = 45
            self.ipfs_uploads = 12
            self.error_count = 2
            self.critical_error_count = 0
            self.downtime_minutes = 5
            self.data_source = "system_monitor"
            self.verified_by_blockchain = True
            self.ipfs_hash = "QmTest123"
            self.recorded_at = datetime.utcnow()
    
    # 测试生成
    test_metrics = MockSLAMetrics()
    generator = NFTMetadataGenerator()
    
    metadata = generator.generate_metadata(
        test_metrics,
        202509,
        "0x1234567890123456789012345678901234567890",
        "test-cert-001"
    )
    
    print("Generated NFT Metadata:")
    print(json.dumps(metadata, indent=2, default=str))