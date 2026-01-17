import requests
from bs4 import BeautifulSoup
import csv
from datetime import datetime

def main():
    # 1. 伪装头（保持不变）
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    # 2. 我们换成【必应搜索】，它比百度稍微友好一点
    # 搜索关键词：AI 运营 招聘
    url = "https://cn.bing.com/search?q=AI%E8%BF%90%E8%90%A5+%E6%8B%9B%E8%81%98"
    
    print("正在切换目标，尝试从 Bing 抓取数据...")
    
    try:
        # 3. 发送请求
        resp = requests.get(url, headers=headers, timeout=10)
        resp.encoding = 'utf-8'
        
        # 4. 解析网页
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # 5. 提取标题和对应的链接
        # Bing 的 h2 通常结构为 <h2><a href="...">标题...</a></h2>
        records = []
        titles = soup.find_all('h2')
        
        if not titles:
            print("Bing 也识别出咱们是爬虫了。别灰心，这是常态！")
            print("网页返回内容预览：", resp.text[:200])
        else:
            print(f"--- 成功抓到 {len(titles)} 个结果 ---")
            for i, h2 in enumerate(titles, 1):
                a_tag = h2.find('a')
                if a_tag and a_tag.get('href'):
                    title_text = a_tag.get_text().strip()
                    href = a_tag.get('href').strip()
                    records.append([title_text, href])
                    print(f"{i}. {title_text}\n   链接: {href}")
                else:
                    # 如果没有a标签，忽略该结果
                    continue
            
            # 6. 保存到 CSV 文件
            now = datetime.now()
            csv_filename = f"bing_data_{now.strftime('%Y-%m-%d_%H-%M')}.csv"
            with open(csv_filename, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(['标题', '链接'])
                writer.writerows(records)
            print(f"\n文件已保存：{csv_filename}")
                
    except Exception as e:
        print(f"出错了: {e}")

if __name__ == "__main__":
    main()