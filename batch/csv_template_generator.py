"""
HashInsight Enterprise - CSV Template Generator
CSV模板生成器

功能特性：
- CSV模板自动生成
- 支持中英文列名
- 内置数据验证规则
- 示例数据自动填充
"""

import csv
import io
from typing import List, Dict
from models import MinerModel


class CSVTemplateGenerator:
    """CSV模板生成器"""
    
    # 模板字段定义 - 托管服务版本
    TEMPLATE_FIELDS_EN = {
        'site_name': {'header': 'Site', 'example': 'Texas DC-01', 'required': True, 'description': 'Hosting site name (must exist in system)'},
        'client_email': {'header': 'Client Email', 'example': 'client@example.com', 'required': True, 'description': 'Customer email address (must be registered)'},
        'serial_number': {'header': 'Serial Number', 'example': 'SN20240001', 'required': True, 'description': 'Unique device serial number'},
        'model_name': {'header': 'Model Name', 'example': 'Antminer S19 Pro', 'required': False, 'description': 'Auto-detect if left blank'},
        'hashrate': {'header': 'Hashrate (TH/s)', 'example': '110', 'required': True, 'description': 'Mining hashrate in TH/s'},
        'power': {'header': 'Power (W)', 'example': '3250', 'required': True, 'description': 'Power consumption in Watts'},
        'hosting_fee': {'header': 'Hosting Fee ($/month)', 'example': '150', 'required': False, 'description': 'Monthly hosting fee'},
        'rack_position': {'header': 'Rack Position', 'example': 'A1-R3-U12', 'required': False, 'description': 'Physical rack location'},
        'ip_address': {'header': 'IP Address', 'example': '192.168.1.100', 'required': False, 'description': 'Miner IP address'},
        'notes': {'header': 'Notes', 'example': 'VIP customer', 'required': False, 'description': 'Additional notes'}
    }
    
    TEMPLATE_FIELDS_ZH = {
        'site_name': {'header': '站点', 'example': '德州数据中心-01', 'required': True, 'description': '托管站点名称（必须在系统中存在）'},
        'client_email': {'header': '客户邮箱', 'example': 'client@example.com', 'required': True, 'description': '客户邮箱地址（必须已注册）'},
        'serial_number': {'header': '序列号', 'example': 'SN20240001', 'required': True, 'description': '设备唯一序列号'},
        'model_name': {'header': '矿机型号', 'example': 'Antminer S19 Pro', 'required': False, 'description': '留空自动识别'},
        'hashrate': {'header': '算力(TH/s)', 'example': '110', 'required': True, 'description': '挖矿算力'},
        'power': {'header': '功耗(W)', 'example': '3250', 'required': True, 'description': '功率消耗'},
        'hosting_fee': {'header': '托管费($/月)', 'example': '150', 'required': False, 'description': '月度托管费用'},
        'rack_position': {'header': '机架位置', 'example': 'A1-R3-U12', 'required': False, 'description': '物理机架位置'},
        'ip_address': {'header': 'IP地址', 'example': '192.168.1.100', 'required': False, 'description': '矿机IP地址'},
        'notes': {'header': '备注', 'example': 'VIP客户', 'required': False, 'description': '附加备注'}
    }
    
    @classmethod
    def generate_template(cls, language: str = 'en', include_examples: bool = True, 
                         example_count: int = 3) -> str:
        """
        生成CSV模板
        
        Args:
            language: 语言 ('en' 或 'zh')
            include_examples: 是否包含示例数据
            example_count: 示例数据行数
            
        Returns:
            CSV模板内容（字符串）
        """
        fields = cls.TEMPLATE_FIELDS_ZH if language == 'zh' else cls.TEMPLATE_FIELDS_EN
        
        output = io.StringIO()
        
        # 提取字段顺序 - 托管服务版本
        field_order = ['site_name', 'client_email', 'serial_number', 'model_name', 'hashrate', 
                      'power', 'hosting_fee', 'rack_position', 'ip_address', 'notes']
        
        # 写入表头
        headers = [fields[f]['header'] for f in field_order]
        writer = csv.writer(output)
        writer.writerow(headers)
        
        # 写入示例数据
        if include_examples:
            # 获取真实的矿机型号数据
            try:
                popular_models = cls._get_popular_models()
            except:
                popular_models = [
                    {'name': 'Antminer S19 Pro', 'hashrate': 110, 'power': 3250, 'price': 2500},
                    {'name': 'Antminer S21', 'hashrate': 200, 'power': 3550, 'price': 3200},
                    {'name': 'WhatsMiner M53S', 'hashrate': 226, 'power': 6554, 'price': 4500}
                ]
            
            for i in range(min(example_count, len(popular_models))):
                model = popular_models[i]
                example_row = [
                    'Texas DC-01' if language == 'en' else '德州数据中心-01',  # site_name
                    f'client{i+1}@example.com',  # client_email
                    f'SN{str(2024000 + i + 1)}',  # serial_number
                    model['name'],  # model_name
                    str(model['hashrate']),  # hashrate
                    str(model['power']),  # power
                    '150',  # hosting_fee
                    f'A1-R{i+1}-U12' if language == 'en' else f'A1-机架{i+1}-U12',  # rack_position
                    f'192.168.1.{100 + i}',  # ip_address
                    ''  # notes
                ]
                writer.writerow(example_row)
        
        return output.getvalue()
    
    @classmethod
    def _get_popular_models(cls) -> List[Dict]:
        """获取热门矿机型号"""
        try:
            models = MinerModel.query.filter_by(is_active=True)\
                .order_by(MinerModel.reference_hashrate.desc())\
                .limit(10).all()
            
            return [
                {
                    'name': m.model_name,
                    'hashrate': m.reference_hashrate,
                    'power': m.reference_power,
                    'price': m.reference_price or 0
                }
                for m in models
            ]
        except Exception as e:
            # Fallback to hardcoded data
            return [
                {'name': 'Antminer S19 Pro', 'hashrate': 110, 'power': 3250, 'price': 2500},
                {'name': 'Antminer S21', 'hashrate': 200, 'power': 3550, 'price': 3200},
                {'name': 'WhatsMiner M53S', 'hashrate': 226, 'power': 6554, 'price': 4500}
            ]
    
    @classmethod
    def generate_validation_rules(cls, language: str = 'en') -> Dict:
        """
        生成数据验证规则
        
        Returns:
            验证规则字典
        """
        fields = cls.TEMPLATE_FIELDS_ZH if language == 'zh' else cls.TEMPLATE_FIELDS_EN
        
        rules = {}
        for key, config in fields.items():
            rules[key] = {
                'required': config['required'],
                'description': config['description'],
                'example': config['example']
            }
            
            # 添加特定字段的验证规则 - 托管服务版本
            if key == 'hashrate':
                rules[key]['type'] = 'float'
                rules[key]['min'] = 0
                rules[key]['max'] = 1000
            elif key == 'power':
                rules[key]['type'] = 'int'
                rules[key]['min'] = 0
                rules[key]['max'] = 20000
            elif key == 'hosting_fee':
                rules[key]['type'] = 'float'
                rules[key]['min'] = 0
                rules[key]['max'] = 10000
            elif key == 'site_name':
                rules[key]['type'] = 'str'
                rules[key]['note'] = 'Must exist in hosting_sites table'
            elif key == 'client_email':
                rules[key]['type'] = 'email'
                rules[key]['note'] = 'Must be registered customer email'
            elif key == 'serial_number':
                rules[key]['type'] = 'str'
                rules[key]['note'] = 'Must be unique device identifier'
        
        return rules
    
    @classmethod
    def generate_bulk_template(cls, count: int = 5000, language: str = 'en') -> str:
        """
        生成大批量导入模板（用于性能测试）
        
        Args:
            count: 生成行数
            language: 语言
            
        Returns:
            CSV内容
        """
        fields = cls.TEMPLATE_FIELDS_ZH if language == 'zh' else cls.TEMPLATE_FIELDS_EN
        
        output = io.StringIO()
        field_order = ['site_name', 'client_email', 'serial_number', 'model_name', 'hashrate', 
                      'power', 'hosting_fee', 'rack_position', 'ip_address', 'notes']
        
        headers = [fields[f]['header'] for f in field_order]
        writer = csv.writer(output)
        writer.writerow(headers)
        
        # 获取模型数据
        popular_models = cls._get_popular_models()
        
        # 生成大量数据
        for i in range(count):
            model = popular_models[i % len(popular_models)]
            row = [
                'Texas DC-01' if language == 'en' else '德州数据中心-01',
                f'client{(i % 100) + 1}@example.com',
                f'SN{str(2024000 + i + 1).zfill(8)}',
                model['name'],
                str(model['hashrate']),
                str(model['power']),
                '150',
                f'A{(i // 1000) + 1}-R{(i // 100) % 10 + 1}-U{(i % 100) + 1}',
                f'192.168.{(i // 256) + 1}.{i % 256}',
                ''
            ]
            writer.writerow(row)
        
        return output.getvalue()
