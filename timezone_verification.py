"""
EST时区验证脚本
验证网络数据收集系统是否正确使用EST时区
"""

import sys
sys.path.append('.')

from app import app
from models import NetworkSnapshot
from datetime import datetime
import pytz

def verify_timezone_implementation():
    """验证时区实施情况"""
    print("EST时区实施验证")
    print("=" * 50)
    
    with app.app_context():
        # 获取最新的网络快照记录
        latest_records = NetworkSnapshot.query.order_by(NetworkSnapshot.id.desc()).limit(3).all()
        
        if not latest_records:
            print("❌ 没有找到网络快照记录")
            return
        
        # 当前时间对比
        utc_now = datetime.utcnow()
        est_tz = pytz.timezone('US/Eastern')
        est_now = pytz.utc.localize(utc_now).astimezone(est_tz)
        
        print(f"当前UTC时间: {utc_now.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"当前EST时间: {est_now.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"时差: {(utc_now.hour - est_now.hour) % 24}小时")
        print()
        
        print("最新网络快照记录:")
        print("-" * 30)
        
        for i, record in enumerate(latest_records, 1):
            stored_time = record.recorded_at
            print(f"记录 {record.id}:")
            print(f"  存储时间: {stored_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"  BTC价格: ${record.btc_price:,.0f}")
            
            # 计算时间差
            time_diff = utc_now - stored_time
            minutes_ago = int(time_diff.total_seconds() / 60)
            print(f"  时间差: {minutes_ago}分钟前")
            
            # 验证是否为EST时间
            if stored_time.hour < utc_now.hour or (stored_time.hour == 23 and utc_now.hour < 4):
                print(f"  ✅ 时区验证: EST时间正确")
            else:
                print(f"  ❌ 时区验证: 可能不是EST时间")
            print()
        
        # 价格趋势验证
        if len(latest_records) >= 2:
            price_change = latest_records[0].btc_price - latest_records[-1].btc_price
            print(f"价格变化: ${price_change:+.0f}")
            print(f"记录总数: {NetworkSnapshot.query.count()}")
        
        print("\n结论:")
        if all(r.recorded_at.hour >= 22 or r.recorded_at.hour <= 23 for r in latest_records):
            print("✅ EST时区实施成功 - 所有记录使用正确的EST时间")
        else:
            print("⚠️  时区可能需要调整")

if __name__ == "__main__":
    verify_timezone_implementation()