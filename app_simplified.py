"""简化后的主应用文件"""
import logging
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash, g

# 本地模块导入
from config import Config
from db import db
from auth import verify_email, login_required
from models import LoginRecord, UserAccess
from translations import get_translation
from utils.helpers import get_user_role, has_role, get_client_ip
from utils.api_client import APIClient
from mining_calculator import MINER_DATA, calculate_mining_profitability
from crm_routes import init_crm_routes

# 初始化Flask应用
app = Flask(__name__)
app.config.from_object(Config)

# 设置日志
logging.basicConfig(level=getattr(logging, Config.LOG_LEVEL))

# 初始化数据库
db.init_app(app)

# 初始化API客户端
api_client = APIClient()

# 注册CRM路由
init_crm_routes(app)

# 添加模板过滤器
@app.template_filter('nl2br')
def nl2br_filter(s):
    """将文本中的换行符转换为HTML的<br>标签"""
    if s is None:
        return ""
    return s.replace('\n', '<br>\n')

@app.before_request
def before_request():
    """请求前处理"""
    g.language = session.get('language', 'zh')

@app.context_processor
def inject_translator():
    def translate(text):
        return get_translation(text, g.language)
    return dict(translate=translate)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """用户登录"""
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        
        if verify_email(email):
            # 登录成功
            session['email'] = email
            session['role'] = get_user_role(email)
            session['user_id'] = None  # 可以从数据库获取
            
            # 记录登录
            try:
                login_record = LoginRecord(
                    email=email,
                    successful=True,
                    ip_address=get_client_ip()
                )
                db.session.add(login_record)
                db.session.commit()
            except Exception as e:
                logging.error(f"记录登录失败: {str(e)}")
            
            return redirect(url_for('index'))
        else:
            flash('邮箱未授权，请联系管理员', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """用户登出"""
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    """主页 - 挖矿计算器"""
    return render_template('index.html', miners=MINER_DATA)

@app.route('/calculate', methods=['POST'])
@login_required
def calculate():
    """计算挖矿收益"""
    try:
        # 获取表单数据
        data = request.get_json() or request.form
        
        miner_model = data.get('miner_model')
        miner_count = int(data.get('miner_count', 1))
        electricity_cost = float(data.get('electricity_cost', 0.05))
        use_real_time = data.get('use_real_time_data') == 'true'
        
        # 获取网络数据
        if use_real_time:
            network_stats = api_client.get_all_network_stats()
        else:
            network_stats = {
                'btc_price': float(data.get('btc_price', Config.DEFAULT_BTC_PRICE)),
                'difficulty': float(data.get('difficulty', Config.DEFAULT_DIFFICULTY)),
                'hashrate': Config.DEFAULT_HASHRATE_EH,
                'block_reward': Config.DEFAULT_BLOCK_REWARD
            }
        
        # 计算收益
        if miner_model and miner_model in MINER_DATA:
            miner_info = MINER_DATA[miner_model]
            result = calculate_mining_profitability(
                hashrate=miner_info['hashrate'],
                power_consumption=miner_info['power'],
                electricity_cost=electricity_cost,
                btc_price=network_stats['btc_price'],
                difficulty=network_stats['difficulty'],
                block_reward=network_stats['block_reward'],
                miner_count=miner_count,
                use_real_time_data=False  # 已经获取了数据
            )
            
            return jsonify({
                'success': True,
                'result': result,
                'network_stats': network_stats
            })
        else:
            return jsonify({
                'success': False,
                'error': '无效的矿机型号'
            }), 400
            
    except Exception as e:
        logging.error(f"计算错误: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'计算出错: {str(e)}'
        }), 500

@app.route('/get_network_stats')
@login_required
def get_network_stats():
    """获取网络统计数据"""
    try:
        stats = api_client.get_all_network_stats()
        return jsonify(stats)
    except Exception as e:
        logging.error(f"获取网络数据失败: {str(e)}")
        return jsonify({
            'error': f'获取网络数据失败: {str(e)}'
        }), 500

@app.route('/get_miners')
@login_required  
def get_miners():
    """获取矿机列表"""
    return jsonify(MINER_DATA)

# 管理员功能
@app.route('/user-access')
@login_required
def user_access():
    """用户访问管理"""
    if not has_role(['owner', 'admin']):
        flash('权限不足', 'danger')
        return redirect(url_for('index'))
    
    users = UserAccess.query.order_by(UserAccess.created_at.desc()).all()
    return render_template('user_access.html', users=users)

# 创建数据库表
with app.app_context():
    db.create_all()
    logging.info("数据库表初始化完成")

if __name__ == '__main__':
    app.run(debug=True)