import pandas as pd
import numpy as np
import os
import random

# 1. 创建存放数据的文件夹
folder_name = "data_lab"
if not os.path.exists(folder_name):
    os.makedirs(folder_name)
    print(f"📂 文件夹已创建：{folder_name}")

print("🧪 正在模拟生成 20 份酸奶发酵实验数据...")

# 2. 循环生成 20 个 Excel 文件
for i in range(1, 21):
    # 模拟数据：时间(0-24小时)，pH值(从6.8下降到4.5左右)，酸度(上升)
    hours = list(range(25)) # 0到24小时
    
    # 制造一点随机波动，模拟真实的实验误差
    ph_values = [6.8 - (x * 0.1) + random.uniform(-0.05, 0.05) for x in hours]
    acidity_values = [70 + (x * 2) + random.uniform(-1, 1) for x in hours]
    
    # 确保数据不离谱 (修剪一下)
    ph_values = [max(4.0, val) for val in ph_values] # pH 不会低于 4.0
    
    # 创建 DataFrame (相当于 Excel 的一张表)
    df = pd.DataFrame({
        "时间 (h)": hours,
        "pH值": ph_values,
        "总酸度 (°T)": acidity_values
    })
    
    # 保存为 Excel
    file_name = f"{folder_name}/batch_{20260101 + i}.xlsx"
    df.to_excel(file_name, index=False)
    print(f"✅ 已生成: {file_name}")

print("\n🎉 数据准备完毕！请去 data_lab 文件夹看看。")