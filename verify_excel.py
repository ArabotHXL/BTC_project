#!/usr/bin/env python3
import pandas as pd
import sys

filename = "attached_assets/mining_batch_results_1755401937575_1755401956792.xlsx"

try:
    df = pd.read_excel(filename, sheet_name=0)
    print("Excel文件读取成功!")
    print(f"行数: {len(df)}")
    print(f"列数: {len(df.columns)}")
    print("列名:", list(df.columns))
    print("\n前3行数据:")
    print(df.head(3).to_string())
    print("\n汇总统计:")
    if 'Daily Profit' in df.columns:
        print(f"总日收益: ${df['Daily Profit'].sum():,.2f}")
    if 'Quantity' in df.columns:
        print(f"总矿机数: {df['Quantity'].sum():,}")
except Exception as e:
    print(f"读取Excel文件时出错: {e}")