import pandas as pd
import matplotlib.pyplot as plt
import glob # 专门用来查找文件名的库
import os

# ================= 1. 批量读取 =================
print("📂 正在批量读取实验数据...")

# 找到 data_lab 文件夹下所有的 .xlsx 文件
file_list = glob.glob("data_lab/*.xlsx")
print(f"ℹ️ 共发现 {len(file_list)} 个实验批次文件。")

all_data = [] # 创建一个空列表，用来装所有的表格

for file in file_list:
    # 读取每一个 Excel
    df = pd.read_excel(file)
    all_data.append(df)

# 把 20 个表格拼成一个超级大表格 (纵向堆叠)
# 这一步相当于把所有人的实验数据合在了一起
big_df = pd.concat(all_data, ignore_index=True)

print(f"✅ 数据合并完成！总共处理了 {len(big_df)} 行数据。")

# ================= 2. 数据分析 =================
print("🧮 正在进行统计分析 (计算平均值与标准差)...")

# 核心魔法：按“时间”分组，计算 pH 值的“平均值(mean)”和“标准差(std)”
# groupby 是 pandas 最强大的功能
summary = big_df.groupby("时间 (h)")["pH值"].agg(["mean", "std"])

print("📊 分析结果前 5 行：")
print(summary.head())

# ================= 3. 科研绘图 =================
print("🎨 正在绘制科研图表...")

# 设置中文字体 (防止乱码)
plt.rcParams['font.sans-serif'] = ['SimHei'] # 用黑体显示中文
plt.rcParams['axes.unicode_minus'] = False   # 正常显示负号

plt.figure(figsize=(10, 6)) # 设置画布大小

# 画线：平均值
plt.plot(summary.index, summary["mean"], color="red", label="pH 平均值", linewidth=2)

# 画阴影：标准差 (Mean + Std 到 Mean - Std 之间的区域)
# 这种图在论文里叫 "Error Band"，非常显专业
plt.fill_between(summary.index, 
                 summary["mean"] - summary["std"], 
                 summary["mean"] + summary["std"], 
                 color="red", alpha=0.2, label="实验误差范围 (±SD)")

# 装饰图表
plt.title("20批次酸奶发酵过程 pH 变化趋势", fontsize=16)
plt.xlabel("发酵时间 (h)", fontsize=12)
plt.ylabel("pH 值", fontsize=12)
plt.grid(True, linestyle='--', alpha=0.6) # 加网格线
plt.legend() # 显示图例

# 保存并展示
output_img = "result_chart.png"
plt.savefig(output_img, dpi=300) # 300 dpi 是打印级清晰度
print(f"🎉 图表已保存为: {output_img}")

plt.show() # 弹窗显示