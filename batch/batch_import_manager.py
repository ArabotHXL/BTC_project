"""
HashInsight Enterprise - Batch Import Manager
批量导入管理器

功能特性：
- 5000台矿机CSV批量导入（流式处理）
- 自动型号识别（基于功耗/算力特征匹配）
- WebSocket实时进度推送
- 分片处理（每批500台）
- 失败重试机制（exponential backoff）
- 详细错误报告（行号、错误类型、建议修复）
"""

import csv
import io
import logging
import time
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import pandas as pd
from sqlalchemy import text
from db import db
from models import UserMiner, MinerModel

logger = logging.getLogger(__name__)


class BatchImportError(Exception):
    """批量导入异常"""
    def __init__(self, row_number: int, error_type: str, message: str, suggestion: str = None):
        self.row_number = row_number
        self.error_type = error_type
        self.message = message
        self.suggestion = suggestion
        super().__init__(f"Row {row_number}: {error_type} - {message}")


class BatchImportManager:
    """批量导入管理器"""
    
    # 每批处理数量
    BATCH_SIZE = 500
    
    # 最大重试次数
    MAX_RETRIES = 3
    
    # 重试延迟（秒）- exponential backoff
    RETRY_BASE_DELAY = 1
    
    # 自动识别阈值
    HASHRATE_TOLERANCE = 0.15  # 算力误差容忍度 ±15%
    POWER_TOLERANCE = 0.20     # 功耗误差容忍度 ±20%
    
    def __init__(self, user_id: int, websocket_callback=None):
        """
        初始化批量导入管理器
        
        Args:
            user_id: 用户ID
            websocket_callback: WebSocket推送回调函数
        """
        self.user_id = user_id
        self.websocket_callback = websocket_callback
        self.miner_models_cache = {}  # 型号缓存
        self._load_miner_models()
    
    def _load_miner_models(self):
        """预加载所有矿机型号到缓存"""
        try:
            models = MinerModel.query.filter_by(is_active=True).all()
            for model in models:
                self.miner_models_cache[model.id] = {
                    'id': model.id,
                    'model_name': model.model_name,
                    'manufacturer': model.manufacturer,
                    'reference_hashrate': float(model.reference_hashrate),
                    'reference_power': int(model.reference_power),
                    'reference_price': float(model.reference_price or 0),
                    'reference_efficiency': float(model.reference_efficiency or 0)
                }
            logger.info(f"Loaded {len(self.miner_models_cache)} miner models to cache")
        except Exception as e:
            logger.error(f"Failed to load miner models: {e}")
            raise
    
    def _send_progress(self, progress: float, message: str, data: Dict = None):
        """发送进度更新"""
        if self.websocket_callback:
            try:
                self.websocket_callback({
                    'type': 'progress',
                    'progress': round(progress, 2),
                    'message': message,
                    'timestamp': datetime.utcnow().isoformat(),
                    'data': data or {}
                })
            except Exception as e:
                logger.error(f"Failed to send progress update: {e}")
    
    def auto_identify_model(self, hashrate: float, power: int) -> Optional[Dict]:
        """
        自动识别矿机型号（基于功耗/算力特征匹配）
        
        Args:
            hashrate: 算力 (TH/s)
            power: 功耗 (W)
            
        Returns:
            匹配的矿机型号字典，如果未找到返回None
        """
        best_match = None
        min_score = float('inf')
        
        for model_id, model in self.miner_models_cache.items():
            # 计算算力偏差
            hashrate_diff = abs(hashrate - model['reference_hashrate']) / model['reference_hashrate']
            
            # 计算功耗偏差
            power_diff = abs(power - model['reference_power']) / model['reference_power']
            
            # 如果两个参数都在容忍范围内
            if hashrate_diff <= self.HASHRATE_TOLERANCE and power_diff <= self.POWER_TOLERANCE:
                # 计算综合评分（偏差越小越好）
                score = hashrate_diff * 0.6 + power_diff * 0.4
                
                if score < min_score:
                    min_score = score
                    best_match = model
        
        if best_match:
            logger.info(f"Auto-identified model: {best_match['model_name']} "
                       f"(hashrate: {hashrate}TH/s, power: {power}W, score: {min_score:.3f})")
        else:
            logger.warning(f"No model match found for hashrate: {hashrate}TH/s, power: {power}W")
        
        return best_match
    
    def validate_row(self, row: Dict, row_number: int) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        验证单行数据
        
        Returns:
            (is_valid, error_type, error_message)
        """
        # 必填字段检查
        required_fields = ['hashrate', 'power', 'electricity_cost']
        for field in required_fields:
            if field not in row or not row[field]:
                return False, 'missing_field', f"Missing required field: {field}", \
                       f"Please provide {field} value"
        
        # 数据类型验证
        try:
            hashrate = float(row['hashrate'])
            power = int(row['power'])
            electricity_cost = float(row['electricity_cost'])
            quantity = int(row.get('quantity', 1))
            machine_price = float(row.get('machine_price', 0))
        except (ValueError, TypeError) as e:
            return False, 'invalid_type', f"Invalid data type: {str(e)}", \
                   "Ensure hashrate, power, electricity_cost are numbers"
        
        # 范围验证
        if hashrate <= 0 or hashrate > 1000:
            return False, 'invalid_range', f"Hashrate {hashrate} out of valid range (0-1000 TH/s)", \
                   "Provide a realistic hashrate value"
        
        if power <= 0 or power > 20000:
            return False, 'invalid_range', f"Power {power} out of valid range (0-20000 W)", \
                   "Provide a realistic power consumption value"
        
        if electricity_cost < 0 or electricity_cost > 1:
            return False, 'invalid_range', f"Electricity cost {electricity_cost} out of valid range (0-1 $/kWh)", \
                   "Provide a realistic electricity cost"
        
        if quantity <= 0 or quantity > 10000:
            return False, 'invalid_range', f"Quantity {quantity} out of valid range (1-10000)", \
                   "Provide a valid quantity"
        
        return True, None, None, None
    
    def process_batch(self, batch: List[Dict], batch_number: int) -> Tuple[List[Dict], List[Dict]]:
        """
        处理单个批次
        
        Returns:
            (success_list, error_list)
        """
        success_records = []
        error_records = []
        
        for idx, row in enumerate(batch):
            row_number = batch_number * self.BATCH_SIZE + idx + 1
            
            try:
                # 验证数据
                is_valid, error_type, error_msg, suggestion = self.validate_row(row, row_number)
                if not is_valid:
                    error_records.append({
                        'row': row_number,
                        'error_type': error_type,
                        'error': error_msg,
                        'suggestion': suggestion,
                        'data': row
                    })
                    continue
                
                # 提取数据
                hashrate = float(row['hashrate'])
                power = int(row['power'])
                electricity_cost = float(row['electricity_cost'])
                quantity = int(row.get('quantity', 1))
                machine_price = float(row.get('machine_price', 0))
                custom_name = row.get('custom_name', '')
                notes = row.get('notes', '')
                
                # 自动识别型号
                model = None
                if 'model_name' in row and row['model_name']:
                    # 如果提供了型号名称，直接查找
                    for m_id, m in self.miner_models_cache.items():
                        if m['model_name'].lower() == row['model_name'].lower():
                            model = m
                            break
                    
                    if not model:
                        error_records.append({
                            'row': row_number,
                            'error_type': 'model_not_found',
                            'error': f"Model '{row['model_name']}' not found",
                            'suggestion': 'Use auto-identification or provide a valid model name',
                            'data': row
                        })
                        continue
                else:
                    # 自动识别型号
                    model = self.auto_identify_model(hashrate, power)
                    
                    if not model:
                        error_records.append({
                            'row': row_number,
                            'error_type': 'no_model_match',
                            'error': f"No matching model found for hashrate={hashrate}TH/s, power={power}W",
                            'suggestion': 'Provide model_name explicitly or adjust hashrate/power values',
                            'data': row
                        })
                        continue
                
                # 准备插入数据
                success_records.append({
                    'user_id': self.user_id,
                    'miner_model_id': model['id'],
                    'actual_hashrate': hashrate,
                    'actual_power': power,
                    'actual_price': machine_price,
                    'electricity_cost': electricity_cost,
                    'quantity': quantity,
                    'custom_name': custom_name,
                    'notes': notes,
                    'original_hashrate': hashrate,
                    'status': 'active'
                })
                
            except Exception as e:
                logger.error(f"Error processing row {row_number}: {e}")
                error_records.append({
                    'row': row_number,
                    'error_type': 'processing_error',
                    'error': str(e),
                    'suggestion': 'Check data format and values',
                    'data': row
                })
        
        return success_records, error_records
    
    def bulk_insert_with_retry(self, records: List[Dict], retry_count: int = 0) -> bool:
        """
        批量插入数据（带重试机制）
        
        Args:
            records: 要插入的记录列表
            retry_count: 当前重试次数
            
        Returns:
            是否成功
        """
        try:
            # 使用SQLAlchemy bulk insert
            db.session.bulk_insert_mappings(UserMiner, records)
            db.session.commit()
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Bulk insert failed (attempt {retry_count + 1}): {e}")
            
            if retry_count < self.MAX_RETRIES:
                # Exponential backoff
                delay = self.RETRY_BASE_DELAY * (2 ** retry_count)
                logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
                
                return self.bulk_insert_with_retry(records, retry_count + 1)
            else:
                logger.error(f"Max retries reached. Failed to insert {len(records)} records")
                return False
    
    def import_csv(self, csv_content: str, filename: str = None) -> Dict:
        """
        导入CSV文件（主入口）
        
        Args:
            csv_content: CSV文件内容（字符串或二进制）
            filename: 文件名
            
        Returns:
            导入结果字典
        """
        start_time = time.time()
        
        try:
            # 解析CSV
            self._send_progress(5, "Parsing CSV file...")
            
            # 使用pandas读取CSV（支持更多格式）
            if isinstance(csv_content, bytes):
                csv_content = csv_content.decode('utf-8')
            
            df = pd.read_csv(io.StringIO(csv_content))
            total_rows = len(df)
            
            logger.info(f"Starting batch import: {total_rows} rows from {filename}")
            self._send_progress(10, f"Parsed {total_rows} rows")
            
            # 转换为字典列表
            rows = df.to_dict('records')
            
            # 分批处理
            total_batches = (total_rows + self.BATCH_SIZE - 1) // self.BATCH_SIZE
            all_success = []
            all_errors = []
            
            for batch_num in range(total_batches):
                start_idx = batch_num * self.BATCH_SIZE
                end_idx = min(start_idx + self.BATCH_SIZE, total_rows)
                batch = rows[start_idx:end_idx]
                
                # 处理批次
                self._send_progress(
                    10 + (batch_num / total_batches) * 70,
                    f"Processing batch {batch_num + 1}/{total_batches} ({start_idx + 1}-{end_idx})"
                )
                
                success_records, error_records = self.process_batch(batch, batch_num)
                
                # 批量插入成功记录
                if success_records:
                    insert_success = self.bulk_insert_with_retry(success_records)
                    if insert_success:
                        all_success.extend(success_records)
                    else:
                        # 插入失败，标记为错误
                        for record in success_records:
                            all_errors.append({
                                'row': batch_num * self.BATCH_SIZE + len(all_errors) + 1,
                                'error_type': 'database_insert_failed',
                                'error': 'Failed to insert into database after retries',
                                'suggestion': 'Check database connection and try again',
                                'data': record
                            })
                
                all_errors.extend(error_records)
            
            # 完成
            elapsed_time = time.time() - start_time
            success_count = len(all_success)
            error_count = len(all_errors)
            
            self._send_progress(
                100,
                f"Import completed: {success_count} success, {error_count} errors",
                {
                    'success_count': success_count,
                    'error_count': error_count,
                    'elapsed_time': round(elapsed_time, 2)
                }
            )
            
            result = {
                'success': True,
                'total_rows': total_rows,
                'success_count': success_count,
                'error_count': error_count,
                'elapsed_time': round(elapsed_time, 2),
                'errors': all_errors[:100] if all_errors else [],  # 限制返回前100个错误
                'performance': {
                    'rows_per_second': round(total_rows / elapsed_time, 2),
                    'batches_processed': total_batches
                }
            }
            
            logger.info(f"Batch import completed: {success_count}/{total_rows} success in {elapsed_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"Batch import failed: {e}", exc_info=True)
            self._send_progress(0, f"Import failed: {str(e)}")
            
            return {
                'success': False,
                'error': str(e),
                'error_type': 'system_error',
                'suggestion': 'Check CSV format and try again'
            }
    
    def generate_error_report(self, errors: List[Dict]) -> str:
        """
        生成详细错误报告
        
        Returns:
            错误报告（CSV格式）
        """
        if not errors:
            return ""
        
        output = io.StringIO()
        fieldnames = ['row_number', 'error_type', 'error_message', 'suggestion', 'original_data']
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        
        writer.writeheader()
        for error in errors:
            writer.writerow({
                'row_number': error.get('row', 'N/A'),
                'error_type': error.get('error_type', 'unknown'),
                'error_message': error.get('error', 'N/A'),
                'suggestion': error.get('suggestion', 'N/A'),
                'original_data': str(error.get('data', {}))
            })
        
        return output.getvalue()
