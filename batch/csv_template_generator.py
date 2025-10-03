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
    
    # 模板字段定义
    TEMPLATE_FIELDS_EN = {
        'miner_number': {'header': 'Miner Number', 'example': 'M001', 'required': False, 'description': 'Unique identifier for the miner'},
        'model_name': {'header': 'Model Name', 'example': 'Antminer S19 Pro', 'required': False, 'description': 'Auto-detect if left blank'},
        'hashrate': {'header': 'Hashrate (TH/s)', 'example': '110', 'required': True, 'description': 'Mining hashrate in TH/s'},
        'power': {'header': 'Power (W)', 'example': '3250', 'required': True, 'description': 'Power consumption in Watts'},
        'electricity_cost': {'header': 'Electricity Cost ($/kWh)', 'example': '0.08', 'required': True, 'description': 'Cost per kilowatt-hour'},
        'machine_price': {'header': 'Machine Price ($)', 'example': '2500', 'required': False, 'description': 'Purchase price of the miner'},
        'quantity': {'header': 'Quantity', 'example': '1', 'required': False, 'description': 'Number of identical miners'},
        'custom_name': {'header': 'Custom Name', 'example': 'Farm A - Rack 1', 'required': False, 'description': 'Custom identifier'},
        'notes': {'header': 'Notes', 'example': 'Purchased 2024-01', 'required': False, 'description': 'Additional notes'}
    }
    
    TEMPLATE_FIELDS_ZH = {
        'miner_number': {'header': '矿机编号', 'example': 'M001', 'required': False, 'description': '矿机唯一标识'},
        'model_name': {'header': '矿机型号', 'example': 'Antminer S19 Pro', 'required': False, 'description': '留空自动识别'},
        'hashrate': {'header': '算力(TH/s)', 'example': '110', 'required': True, 'description': '挖矿算力'},
        'power': {'header': '功耗(W)', 'example': '3250', 'required': True, 'description': '功率消耗'},
        'electricity_cost': {'header': '电费($/kWh)', 'example': '0.08', 'required': True, 'description': '每千瓦时电费'},
        'machine_price': {'header': '矿机价格($)', 'example': '2500', 'required': False, 'description': '购买价格'},
        'quantity': {'header': '数量', 'example': '1', 'required': False, 'description': '相同矿机数量'},
        'custom_name': {'header': '自定义名称', 'example': '矿场A-机架1', 'required': False, 'description': '自定义标识'},
        'notes': {'header': '备注', 'example': '2024-01购买', 'required': False, 'description': '附加备注'}
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
        
        # 提取字段顺序
        field_order = ['miner_number', 'model_name', 'hashrate', 'power', 'electricity_cost', 
                      'machine_price', 'quantity', 'custom_name', 'notes']
        
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
                    f'M{str(i+1).zfill(3)}',  # miner_number
                    model['name'],             # model_name
                    str(model['hashrate']),    # hashrate
                    str(model['power']),       # power
                    '0.08',                    # electricity_cost
                    str(model['price']),       # machine_price
                    '1',                       # quantity
                    f'Farm A - Rack {i+1}' if language == 'en' else f'矿场A-机架{i+1}',  # custom_name
                    ''                         # notes
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
            
            # 添加特定字段的验证规则
            if key == 'hashrate':
                rules[key]['type'] = 'float'
                rules[key]['min'] = 0
                rules[key]['max'] = 1000
            elif key == 'power':
                rules[key]['type'] = 'int'
                rules[key]['min'] = 0
                rules[key]['max'] = 20000
            elif key == 'electricity_cost':
                rules[key]['type'] = 'float'
                rules[key]['min'] = 0
                rules[key]['max'] = 1
            elif key == 'machine_price':
                rules[key]['type'] = 'float'
                rules[key]['min'] = 0
            elif key == 'quantity':
                rules[key]['type'] = 'int'
                rules[key]['min'] = 1
                rules[key]['max'] = 10000
        
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
        field_order = ['miner_number', 'model_name', 'hashrate', 'power', 'electricity_cost', 
                      'machine_price', 'quantity', 'custom_name', 'notes']
        
        headers = [fields[f]['header'] for f in field_order]
        writer = csv.writer(output)
        writer.writerow(headers)
        
        # 获取模型数据
        popular_models = cls._get_popular_models()
        
        # 生成大量数据
        for i in range(count):
            model = popular_models[i % len(popular_models)]
            row = [
                f'M{str(i+1).zfill(5)}',
                model['name'],
                str(model['hashrate']),
                str(model['power']),
                '0.08',
                str(model['price']),
                '1',
                f'Batch-{i // 100 + 1}-{i % 100 + 1}',
                ''
            ]
            writer.writerow(row)
        
        return output.getvalue()
