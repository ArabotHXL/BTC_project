"""
HashInsight Enterprise - Batch Import Integration Tests
批量导入集成测试
"""

import pytest
import csv
import io
from batch.batch_import_manager import BatchImportManager
from batch.csv_template_generator import CSVTemplateGenerator


class TestBatchImport:
    """批量导入集成测试"""
    
    def setup_method(self):
        """测试初始化"""
        self.user_id = 1
        self.manager = BatchImportManager(self.user_id)
    
    def test_template_generation(self):
        """测试CSV模板生成"""
        template = CSVTemplateGenerator.generate_template('en', include_examples=True)
        
        assert len(template) > 0
        assert 'Hashrate' in template
        assert 'Power' in template
        assert 'Electricity Cost' in template
    
    def test_small_batch_import(self):
        """测试小批量导入（< 500台）"""
        csv_data = """Hashrate (TH/s),Power (W),Electricity Cost ($/kWh),Machine Price ($),Quantity
110,3250,0.08,2500,1
200,3550,0.08,3200,1
"""
        
        result = self.manager.import_csv(csv_data, 'test.csv')
        
        assert result['success'] is True
        assert result['success_count'] == 2
        assert result['error_count'] == 0
    
    def test_auto_model_identification(self):
        """测试自动型号识别"""
        # S19 Pro规格
        model = self.manager.auto_identify_model(110, 3250)
        
        assert model is not None
        assert model['reference_hashrate'] > 0
        assert model['reference_power'] > 0
    
    def test_validation_errors(self):
        """测试数据验证错误"""
        csv_data = """Hashrate (TH/s),Power (W),Electricity Cost ($/kWh)
-10,3250,0.08
110,50000,0.08
110,3250,5.0
"""
        
        result = self.manager.import_csv(csv_data, 'invalid.csv')
        
        assert result['error_count'] > 0
    
    @pytest.mark.slow
    def test_large_batch_import(self):
        """测试大批量导入（5000台）"""
        # 生成5000行CSV
        csv_data = CSVTemplateGenerator.generate_bulk_template(count=5000)
        
        result = self.manager.import_csv(csv_data, 'bulk_5000.csv')
        
        assert result['success'] is True
        assert result['total_rows'] == 5000
        assert result['elapsed_time'] < 30  # 应在30秒内完成
        assert result['performance']['rows_per_second'] > 150


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-m', 'not slow'])
