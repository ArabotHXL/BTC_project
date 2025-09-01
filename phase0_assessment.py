
#!/usr/bin/env python3
"""
Phase 0: 现状评估 - Bitcoin Calculator 托管平台集成准备
评估现有系统架构，为托管功能集成做准备
"""

import os
import sys
import logging
import json
from datetime import datetime
import psycopg2
from sqlalchemy import inspect, text
import importlib.util

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Phase0Assessment:
    def __init__(self):
        self.assessment_results = {
            "timestamp": datetime.now().isoformat(),
            "phase": "Phase 0 - 现状评估",
            "system_name": "Bitcoin Calculator (calc.hashinsight.net)",
            "assessment_status": "in_progress",
            "findings": {},
            "recommendations": {},
            "readiness_score": 0
        }
        
    def check_environment(self):
        """检查环境变量配置"""
        logger.info("🔍 检查环境变量配置...")
        
        required_vars = [
            'DATABASE_URL',
            'SESSION_SECRET'
        ]
        
        optional_vars = [
            'SKIP_DATABASE_HEALTH_CHECK',
            'FLASK_ENV',
            'DEBUG'
        ]
        
        env_status = {
            "required": {},
            "optional": {},
            "missing_required": [],
            "status": "unknown"
        }
        
        # 检查必需变量
        for var in required_vars:
            value = os.environ.get(var)
            if value:
                env_status["required"][var] = "✅ 已配置"
            else:
                env_status["required"][var] = "❌ 缺失"
                env_status["missing_required"].append(var)
        
        # 检查可选变量
        for var in optional_vars:
            value = os.environ.get(var)
            env_status["optional"][var] = "✅ " + str(value) if value else "⚪ 未设置"
        
        # 设置状态
        if not env_status["missing_required"]:
            env_status["status"] = "ready"
            logger.info("✅ 环境变量配置完整")
        else:
            env_status["status"] = "needs_attention"
            logger.warning(f"⚠️ 缺失必需环境变量: {env_status['missing_required']}")
        
        self.assessment_results["findings"]["environment"] = env_status
        return env_status["status"] == "ready"

    def check_database_schema(self):
        """检查数据库架构"""
        logger.info("🗄️ 检查数据库架构...")
        
        db_status = {
            "connection": "unknown",
            "tables": {},
            "key_tables_present": [],
            "missing_tables": [],
            "hosting_ready_tables": [],
            "schema_analysis": {}
        }
        
        try:
            # 尝试连接数据库
            database_url = os.environ.get('DATABASE_URL')
            if not database_url:
                db_status["connection"] = "no_url"
                logger.error("❌ DATABASE_URL 未配置")
                self.assessment_results["findings"]["database"] = db_status
                return False
            
            # 使用 psycopg2 连接
            conn = psycopg2.connect(database_url)
            cursor = conn.cursor()
            
            # 获取所有表
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """)
            
            tables = [row[0] for row in cursor.fetchall()]
            db_status["connection"] = "success"
            
            # 分析关键表
            key_tables = [
                "users", "miner_models", "market_analytics", 
                "user_subscriptions", "subscription_plans",
                "crm_customers", "crm_deals", "technical_indicators"
            ]
            
            hosting_tables = [
                "mining_sites", "hosting_contracts", "sla_records",
                "billing_records", "maintenance_logs"
            ]
            
            for table in tables:
                if table in key_tables:
                    db_status["key_tables_present"].append(table)
                elif table in hosting_tables:
                    db_status["hosting_ready_tables"].append(table)
                
                # 获取表结构
                cursor.execute(f"""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns
                    WHERE table_name = '{table}'
                    ORDER BY ordinal_position;
                """)
                
                columns = cursor.fetchall()
                db_status["tables"][table] = {
                    "columns": len(columns),
                    "structure": [{"name": col[0], "type": col[1], "nullable": col[2]} for col in columns]
                }
            
            # 检查缺失的关键表
            for table in key_tables:
                if table not in tables:
                    db_status["missing_tables"].append(table)
            
            # 分析现有架构的托管就绪程度
            readiness_analysis = self._analyze_hosting_readiness(db_status)
            db_status["schema_analysis"] = readiness_analysis
            
            cursor.close()
            conn.close()
            
            logger.info(f"✅ 数据库连接成功，发现 {len(tables)} 个表")
            logger.info(f"📊 关键表: {len(db_status['key_tables_present'])}/{len(key_tables)}")
            
        except Exception as e:
            db_status["connection"] = "failed"
            db_status["error"] = str(e)
            logger.error(f"❌ 数据库连接失败: {e}")
        
        self.assessment_results["findings"]["database"] = db_status
        return db_status["connection"] == "success"

    def _analyze_hosting_readiness(self, db_status):
        """分析托管功能就绪程度"""
        analysis = {
            "user_management": "ready" if "users" in db_status["key_tables_present"] else "missing",
            "subscription_system": "ready" if "user_subscriptions" in db_status["key_tables_present"] else "missing",
            "crm_foundation": "ready" if "crm_customers" in db_status["key_tables_present"] else "missing",
            "miner_data": "ready" if "miner_models" in db_status["key_tables_present"] else "missing",
            "market_analytics": "ready" if "market_analytics" in db_status["key_tables_present"] else "missing",
            "hosting_specific": "needs_creation" if not db_status["hosting_ready_tables"] else "partial",
            "overall_readiness": 0
        }
        
        ready_count = sum(1 for v in analysis.values() if v == "ready")
        total_checks = len(analysis) - 1  # 排除 overall_readiness
        analysis["overall_readiness"] = (ready_count / total_checks) * 100
        
        return analysis

    def check_application_architecture(self):
        """检查应用架构"""
        logger.info("🏗️ 检查应用架构...")
        
        arch_status = {
            "main_files": {},
            "module_structure": {},
            "route_analysis": {},
            "template_structure": {},
            "static_assets": {},
            "modularity_score": 0
        }
        
        # 检查主要文件
        main_files = ["main.py", "app.py", "config.py", "models.py"]
        for file in main_files:
            if os.path.exists(file):
                arch_status["main_files"][file] = "✅ 存在"
                # 分析文件大小和复杂度
                try:
                    with open(file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        arch_status["main_files"][f"{file}_lines"] = len(lines)
                except:
                    pass
            else:
                arch_status["main_files"][file] = "❌ 缺失"
        
        # 检查模块结构
        if os.path.exists("modules"):
            arch_status["module_structure"]["modules_dir"] = "✅ 存在"
            modules = os.listdir("modules")
            arch_status["module_structure"]["available_modules"] = modules
        else:
            arch_status["module_structure"]["modules_dir"] = "❌ 缺失"
        
        # 检查模板结构
        if os.path.exists("templates"):
            templates = []
            for root, dirs, files in os.walk("templates"):
                for file in files:
                    if file.endswith('.html'):
                        templates.append(os.path.join(root, file))
            arch_status["template_structure"]["count"] = len(templates)
            arch_status["template_structure"]["organized"] = len([t for t in templates if '/' in t]) > 0
        
        # 检查静态资源
        if os.path.exists("static"):
            static_files = []
            for root, dirs, files in os.walk("static"):
                static_files.extend(files)
            arch_status["static_assets"]["count"] = len(static_files)
            arch_status["static_assets"]["has_css"] = any(f.endswith('.css') for f in static_files)
            arch_status["static_assets"]["has_js"] = any(f.endswith('.js') for f in static_files)
        
        # 计算模块化分数
        modularity_factors = [
            arch_status["main_files"].get("config.py") == "✅ 存在",
            arch_status["main_files"].get("models.py") == "✅ 存在",
            arch_status["module_structure"].get("modules_dir") == "✅ 存在",
            arch_status["template_structure"].get("organized", False),
            len(arch_status["static_assets"]) > 0
        ]
        
        arch_status["modularity_score"] = (sum(modularity_factors) / len(modularity_factors)) * 100
        
        logger.info(f"✅ 架构分析完成，模块化分数: {arch_status['modularity_score']:.1f}%")
        
        self.assessment_results["findings"]["architecture"] = arch_status
        return arch_status["modularity_score"] > 60

    def check_existing_features(self):
        """检查现有功能"""
        logger.info("⚙️ 检查现有功能...")
        
        features = {
            "mining_calculator": self._check_file_exists("mining_calculator.py"),
            "batch_calculator": self._check_file_exists("batch_calculator_routes.py"),
            "analytics_engine": self._check_file_exists("analytics_engine.py"),
            "crm_system": self._check_file_exists("crm_routes.py"),
            "user_management": self._check_file_exists("auth.py"),
            "billing_system": self._check_file_exists("billing_routes.py"),
            "performance_monitor": self._check_file_exists("performance_monitor.py"),
            "api_endpoints": self._check_api_routes(),
            "real_time_data": self._check_file_exists("bitcoin_rpc_client.py"),
            "advanced_algorithms": self._check_file_exists("advanced_algorithm_engine.py")
        }
        
        feature_score = (sum(1 for v in features.values() if v) / len(features)) * 100
        
        logger.info(f"✅ 功能检查完成，功能完整度: {feature_score:.1f}%")
        
        self.assessment_results["findings"]["features"] = {
            "available_features": features,
            "completeness_score": feature_score,
            "hosting_ready_features": self._identify_hosting_ready_features(features)
        }
        
        return feature_score > 70

    def _check_file_exists(self, filename):
        """检查文件是否存在"""
        return os.path.exists(filename)

    def _check_api_routes(self):
        """检查API路由"""
        try:
            if os.path.exists("app.py"):
                with open("app.py", 'r', encoding='utf-8') as f:
                    content = f.read()
                    return "/api/" in content
        except:
            pass
        return False

    def _identify_hosting_ready_features(self, features):
        """识别可用于托管功能的现有特性"""
        hosting_ready = {}
        
        if features["user_management"]:
            hosting_ready["user_roles"] = "可扩展支持托管商/客户角色"
        
        if features["crm_system"]:
            hosting_ready["customer_management"] = "可用于托管客户管理"
        
        if features["billing_system"]:
            hosting_ready["billing_foundation"] = "可扩展支持托管计费"
        
        if features["performance_monitor"]:
            hosting_ready["sla_monitoring"] = "可用于SLA监控"
        
        if features["analytics_engine"]:
            hosting_ready["data_collection"] = "可用于对账数据收集"
        
        return hosting_ready

    def generate_recommendations(self):
        """生成建议"""
        logger.info("📋 生成实施建议...")
        
        findings = self.assessment_results["findings"]
        recommendations = {
            "immediate_actions": [],
            "phase1_requirements": [],
            "technical_debt": [],
            "hosting_readiness": "unknown"
        }
        
        # 环境配置建议
        if findings.get("environment", {}).get("status") != "ready":
            recommendations["immediate_actions"].append({
                "action": "配置缺失的环境变量",
                "priority": "high",
                "details": findings["environment"]["missing_required"]
            })
        
        # 数据库建议
        db_findings = findings.get("database", {})
        if db_findings.get("connection") != "success":
            recommendations["immediate_actions"].append({
                "action": "修复数据库连接",
                "priority": "critical",
                "details": "无法连接到数据库"
            })
        elif db_findings.get("missing_tables"):
            recommendations["phase1_requirements"].append({
                "action": "创建托管相关数据表",
                "priority": "medium",
                "details": "需要添加托管站点、合同、SLA等表"
            })
        
        # 架构建议
        arch_findings = findings.get("architecture", {})
        if arch_findings.get("modularity_score", 0) < 70:
            recommendations["technical_debt"].append({
                "action": "改进代码模块化",
                "priority": "medium",
                "details": "当前模块化程度不足，建议重构"
            })
        
        # 功能建议
        feature_findings = findings.get("features", {})
        if feature_findings.get("completeness_score", 0) > 80:
            recommendations["phase1_requirements"].append({
                "action": "扩展现有功能支持托管",
                "priority": "low",
                "details": "现有功能完整度高，可直接扩展"
            })
        
        # 托管就绪评估
        if (findings.get("environment", {}).get("status") == "ready" and
            db_findings.get("connection") == "success" and
            feature_findings.get("completeness_score", 0) > 70):
            recommendations["hosting_readiness"] = "ready_for_integration"
        elif db_findings.get("connection") == "success":
            recommendations["hosting_readiness"] = "needs_preparation"
        else:
            recommendations["hosting_readiness"] = "requires_fixes"
        
        self.assessment_results["recommendations"] = recommendations
        return recommendations

    def calculate_readiness_score(self):
        """计算整体就绪分数"""
        findings = self.assessment_results["findings"]
        
        scores = {
            "environment": 100 if findings.get("environment", {}).get("status") == "ready" else 0,
            "database": 100 if findings.get("database", {}).get("connection") == "success" else 0,
            "architecture": findings.get("architecture", {}).get("modularity_score", 0),
            "features": findings.get("features", {}).get("completeness_score", 0)
        }
        
        # 加权平均
        weights = {"environment": 0.2, "database": 0.3, "architecture": 0.2, "features": 0.3}
        total_score = sum(scores[key] * weights[key] for key in scores)
        
        self.assessment_results["readiness_score"] = round(total_score, 2)
        return total_score

    def run_assessment(self):
        """运行完整评估"""
        logger.info("🚀 开始 Phase 0 现状评估...")
        logger.info("=" * 60)
        
        # 执行各项检查
        checks = [
            ("环境配置", self.check_environment),
            ("数据库架构", self.check_database_schema),
            ("应用架构", self.check_application_architecture),
            ("现有功能", self.check_existing_features)
        ]
        
        for check_name, check_func in checks:
            try:
                logger.info(f"\n📋 正在检查: {check_name}")
                result = check_func()
                status = "✅ 通过" if result else "⚠️ 需要注意"
                logger.info(f"{check_name}: {status}")
            except Exception as e:
                logger.error(f"❌ {check_name} 检查失败: {e}")
        
        # 生成建议和分数
        self.generate_recommendations()
        total_score = self.calculate_readiness_score()
        
        # 更新最终状态
        self.assessment_results["assessment_status"] = "completed"
        
        # 输出总结
        self._print_summary()
        
        return self.assessment_results

    def _print_summary(self):
        """打印评估总结"""
        logger.info("\n" + "=" * 60)
        logger.info("📊 Phase 0 现状评估总结")
        logger.info("=" * 60)
        
        score = self.assessment_results["readiness_score"]
        recommendations = self.assessment_results["recommendations"]
        
        # 显示就绪分数
        if score >= 80:
            status_emoji = "🟢"
            status_text = "优秀 - 可以直接进入 Phase 1"
        elif score >= 60:
            status_emoji = "🟡"
            status_text = "良好 - 需要少量准备后可进入 Phase 1"
        else:
            status_emoji = "🔴"
            status_text = "需要改进 - 建议先解决关键问题"
        
        logger.info(f"\n{status_emoji} 总体就绪分数: {score:.1f}/100")
        logger.info(f"📈 评估结果: {status_text}")
        
        # 显示托管就绪状态
        hosting_readiness = recommendations.get("hosting_readiness", "unknown")
        readiness_map = {
            "ready_for_integration": "🚀 准备就绪，可开始托管功能集成",
            "needs_preparation": "⚙️ 需要准备工作，然后可集成托管功能",
            "requires_fixes": "🔧 需要修复关键问题才能继续"
        }
        
        logger.info(f"🏠 托管功能就绪度: {readiness_map.get(hosting_readiness, '未知')}")
        
        # 显示关键建议
        if recommendations.get("immediate_actions"):
            logger.info(f"\n⚡ 立即需要处理的问题 ({len(recommendations['immediate_actions'])} 项):")
            for i, action in enumerate(recommendations["immediate_actions"], 1):
                logger.info(f"   {i}. {action['action']} (优先级: {action['priority']})")
        
        if recommendations.get("phase1_requirements"):
            logger.info(f"\n📋 Phase 1 需要的工作 ({len(recommendations['phase1_requirements'])} 项):")
            for i, req in enumerate(recommendations["phase1_requirements"], 1):
                logger.info(f"   {i}. {req['action']}")
        
        logger.info(f"\n📄 详细报告已保存到评估结果中")
        logger.info("=" * 60)

    def save_report(self, filename="phase0_assessment_report.json"):
        """保存评估报告"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.assessment_results, f, indent=2, ensure_ascii=False)
            logger.info(f"✅ 评估报告已保存到: {filename}")
        except Exception as e:
            logger.error(f"❌ 保存报告失败: {e}")

def main():
    """主函数"""
    logger.info("🎯 Bitcoin Calculator 托管平台集成 - Phase 0 现状评估")
    logger.info("📅 评估时间: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    # 创建评估实例并运行
    assessment = Phase0Assessment()
    results = assessment.run_assessment()
    
    # 保存报告
    assessment.save_report()
    
    # 返回结果
    return results

if __name__ == "__main__":
    try:
        results = main()
        
        # 根据结果决定退出码
        score = results.get("readiness_score", 0)
        if score >= 60:
            sys.exit(0)  # 成功
        else:
            sys.exit(1)  # 需要改进
            
    except KeyboardInterrupt:
        logger.info("\n⚠️ 评估被用户中断")
        sys.exit(2)
    except Exception as e:
        logger.error(f"❌ 评估过程中发生错误: {e}")
        sys.exit(3)
