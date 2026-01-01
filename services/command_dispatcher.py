"""
Command Dispatcher Service
命令调度器 - 将 RemoteCommand 拆分为多个 MinerCommand

功能:
1. 解析 RemoteCommand 的 target_ids，拆分为单矿机命令
2. 命令类型映射 (REBOOT → restart, POWER_MODE → set_frequency 等)
3. miner_id 归属校验 (确保属于指定 site_id)
4. TTL/过期校验
5. 结果聚合 (MinerCommand 结果 → RemoteCommandResult → RemoteCommand)
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple

from db import db
from models import HostingMiner, HostingSite

logger = logging.getLogger(__name__)

COMMAND_TYPE_MAPPING = {
    'REBOOT': 'restart',
    'RESTART': 'restart',
    'POWER_MODE': 'set_frequency',
    'SET_FREQUENCY': 'set_frequency',
    'CHANGE_POOL': 'set_pool',
    'SET_POOL': 'set_pool',
    'STOP': 'disable',
    'DISABLE': 'disable',
    'START': 'enable',
    'ENABLE': 'enable',
    'SET_FAN': 'set_fan',
}

REVERSE_COMMAND_MAPPING = {v: k for k, v in COMMAND_TYPE_MAPPING.items()}

DEFAULT_COMMAND_TTL_HOURS = 24
DEFAULT_PRIORITY = 5


class CommandDispatchError(Exception):
    """命令调度错误"""
    pass


class MinerNotFoundError(CommandDispatchError):
    """矿机不存在"""
    pass


class MinerOwnershipError(CommandDispatchError):
    """矿机不属于指定站点"""
    pass


def validate_miner_ownership(site_id: int, miner_id: str) -> Optional[HostingMiner]:
    """
    验证 miner_id 是否属于指定的 site_id
    
    Args:
        site_id: 站点ID
        miner_id: 矿机标识 (serial_number)
    
    Returns:
        HostingMiner 对象，如果验证通过
    
    Raises:
        MinerNotFoundError: 矿机不存在
        MinerOwnershipError: 矿机不属于指定站点
    """
    miner = HostingMiner.query.filter_by(serial_number=str(miner_id)).first()
    
    if not miner:
        raise MinerNotFoundError(f"Miner not found: {miner_id}")
    
    if miner.site_id != site_id:
        raise MinerOwnershipError(
            f"Miner {miner_id} belongs to site {miner.site_id}, not {site_id}"
        )
    
    return miner


def map_command_type(remote_command_type: str) -> str:
    """
    将 RemoteCommand 命令类型映射到 MinerCommand 类型
    
    Args:
        remote_command_type: RemoteCommand 的命令类型 (如 REBOOT, POWER_MODE)
    
    Returns:
        MinerCommand 的命令类型 (如 restart, set_frequency)
    """
    upper_type = remote_command_type.upper()
    return COMMAND_TYPE_MAPPING.get(upper_type, remote_command_type.lower())


def dispatch_remote_command(
    remote_command_id: str,
    site_id: int,
    target_ids: List[str],
    command_type: str,
    parameters: Dict[str, Any],
    operator_id: Optional[int] = None,
    expires_at: Optional[datetime] = None,
    priority: int = DEFAULT_PRIORITY,
    validate_ownership: bool = True
) -> Tuple[List[Dict], List[Dict]]:
    """
    将 RemoteCommand 拆分为多个 MinerCommand
    
    Args:
        remote_command_id: RemoteCommand ID
        site_id: 站点ID
        target_ids: 目标矿机ID列表
        command_type: 命令类型 (RemoteCommand 格式)
        parameters: 命令参数
        operator_id: 操作者用户ID
        expires_at: 过期时间
        priority: 优先级
        validate_ownership: 是否验证矿机归属
    
    Returns:
        (success_list, error_list): 成功创建的命令列表和错误列表
    """
    from api.collector_api import MinerCommand
    from models_remote_control import RemoteCommand, RemoteCommandResult
    
    if expires_at is None:
        expires_at = datetime.utcnow() + timedelta(hours=DEFAULT_COMMAND_TTL_HOURS)
    
    mapped_command_type = map_command_type(command_type)
    
    success_list = []
    error_list = []
    
    for miner_id in target_ids:
        miner_id_str = str(miner_id)
        
        if validate_ownership:
            try:
                validate_miner_ownership(site_id, miner_id_str)
            except MinerNotFoundError as e:
                error_list.append({
                    'miner_id': miner_id_str,
                    'error': 'MINER_NOT_FOUND',
                    'message': str(e)
                })
                result = RemoteCommandResult.query.filter_by(
                    command_id=remote_command_id,
                    miner_id=miner_id_str
                ).first()
                if result:
                    result.result_status = 'SKIPPED'
                    result.result_message = str(e)
                    result.finished_at = datetime.utcnow()
                continue
            except MinerOwnershipError as e:
                error_list.append({
                    'miner_id': miner_id_str,
                    'error': 'OWNERSHIP_ERROR',
                    'message': str(e)
                })
                result = RemoteCommandResult.query.filter_by(
                    command_id=remote_command_id,
                    miner_id=miner_id_str
                ).first()
                if result:
                    result.result_status = 'SKIPPED'
                    result.result_message = str(e)
                    result.finished_at = datetime.utcnow()
                continue
        
        command = MinerCommand(
            miner_id=miner_id_str,
            site_id=site_id,
            remote_command_id=remote_command_id,
            command_type=mapped_command_type,
            parameters=parameters,
            status='pending',
            priority=priority,
            expires_at=expires_at,
            operator_id=operator_id
        )
        
        db.session.add(command)
        success_list.append({
            'miner_id': miner_id_str,
            'command_type': mapped_command_type
        })
    
    try:
        if not success_list and error_list:
            remote_cmd = RemoteCommand.query.get(remote_command_id)
            if remote_cmd:
                remote_cmd.status = 'FAILED'
                remote_cmd.updated_at = datetime.utcnow()
                logger.warning(
                    f"RemoteCommand {remote_command_id[:8]} failed: "
                    f"all {len(error_list)} targets rejected"
                )
        
        db.session.commit()
        
        if success_list:
            logger.info(
                f"Dispatched RemoteCommand {remote_command_id[:8]}: "
                f"{len(success_list)} commands created, {len(error_list)} errors"
            )
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to dispatch commands: {e}")
        raise CommandDispatchError(f"Database error: {e}")
    
    return success_list, error_list


def aggregate_command_results(remote_command_id: str) -> Dict[str, Any]:
    """
    聚合 MinerCommand 结果到 RemoteCommand
    
    当所有 MinerCommand 完成后，更新 RemoteCommand 的总状态
    
    Args:
        remote_command_id: RemoteCommand ID
    
    Returns:
        聚合结果统计
    """
    from api.collector_api import MinerCommand
    from models_remote_control import RemoteCommand, RemoteCommandResult
    
    remote_command = RemoteCommand.query.get(remote_command_id)
    if not remote_command:
        logger.warning(f"RemoteCommand not found: {remote_command_id}")
        return {'error': 'RemoteCommand not found'}
    
    miner_commands = MinerCommand.query.filter_by(
        remote_command_id=remote_command_id
    ).all()
    
    if not miner_commands:
        return {'total': 0, 'pending': 0, 'completed': 0, 'failed': 0}
    
    stats = {
        'total': len(miner_commands),
        'pending': 0,
        'sent': 0,
        'executing': 0,
        'completed': 0,
        'failed': 0,
        'expired': 0,
        'cancelled': 0
    }
    
    now = datetime.utcnow()
    
    for cmd in miner_commands:
        stats[cmd.status] = stats.get(cmd.status, 0) + 1
        
        result = RemoteCommandResult.query.filter_by(
            command_id=remote_command_id,
            miner_id=cmd.miner_id
        ).first()
        
        if result and cmd.status in ('completed', 'failed'):
            if cmd.status == 'completed':
                result.result_status = 'SUCCEEDED'
            else:
                result.result_status = 'FAILED'
            
            result.result_message = cmd.result_message
            result.finished_at = cmd.executed_at or now
            
            if cmd.execution_time_ms:
                result.metrics_json = result.metrics_json or {}
                result.metrics_json['execution_time_ms'] = cmd.execution_time_ms
            
            if cmd.edge_device_id:
                result.metrics_json = result.metrics_json or {}
                result.metrics_json['edge_device_id'] = cmd.edge_device_id
    
    finished = stats['completed'] + stats['failed'] + stats['expired'] + stats['cancelled']
    
    if finished >= stats['total']:
        if stats['failed'] == 0 and stats['expired'] == 0:
            remote_command.status = 'SUCCEEDED'
        elif stats['completed'] > 0:
            remote_command.status = 'PARTIAL'
        else:
            remote_command.status = 'FAILED'
        
        remote_command.updated_at = now
        logger.info(
            f"RemoteCommand {remote_command_id[:8]} completed: "
            f"status={remote_command.status}, completed={stats['completed']}, failed={stats['failed']}"
        )
    
    db.session.commit()
    
    return stats


def update_miner_command_result(
    command_id: int,
    status: str,
    result_code: Optional[int] = None,
    result_message: Optional[str] = None,
    execution_time_ms: Optional[int] = None,
    edge_device_id: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    更新 MinerCommand 结果并触发聚合
    
    Args:
        command_id: MinerCommand ID
        status: 执行状态 (completed/failed)
        result_code: 结果代码
        result_message: 结果消息
        execution_time_ms: 执行耗时(毫秒)
        edge_device_id: 执行设备ID
    
    Returns:
        更新后的命令信息
    """
    from api.collector_api import MinerCommand
    
    command = MinerCommand.query.get(command_id)
    if not command:
        logger.warning(f"MinerCommand not found: {command_id}")
        return None
    
    now = datetime.utcnow()
    
    command.status = status
    command.executed_at = now
    command.result_code = result_code
    command.result_message = result_message
    
    if execution_time_ms:
        command.execution_time_ms = execution_time_ms
    
    if edge_device_id:
        command.edge_device_id = edge_device_id
    
    db.session.commit()
    
    if command.remote_command_id:
        aggregate_command_results(command.remote_command_id)
    
    return command.to_dict()


def get_pending_commands_for_site(site_id: int, limit: int = 50) -> List[Dict]:
    """
    获取站点的待执行命令 (供 Edge Collector 轮询)
    
    Args:
        site_id: 站点ID
        limit: 最大返回数量
    
    Returns:
        命令列表 (不包含IP地址)
    """
    from api.collector_api import MinerCommand
    
    now = datetime.utcnow()
    
    MinerCommand.query.filter(
        MinerCommand.site_id == site_id,
        MinerCommand.status == 'pending',
        MinerCommand.expires_at < now
    ).update({'status': 'expired'}, synchronize_session=False)
    
    commands = MinerCommand.query.filter(
        MinerCommand.site_id == site_id,
        MinerCommand.status == 'pending',
        MinerCommand.expires_at >= now
    ).order_by(
        MinerCommand.priority.desc(),
        MinerCommand.created_at.asc()
    ).limit(limit).all()
    
    result = []
    for cmd in commands:
        cmd.status = 'sent'
        cmd.sent_at = now
        result.append(cmd.to_command_payload())
    
    if result:
        db.session.commit()
        logger.info(f"Sent {len(result)} commands to site {site_id}")
    
    return result
