"""Fetch Baidu homepage and report connectivity with title."""
import re

import requests


def main() -> None:
    url = "https://www.baidu.com"
    try:
        resp = requests.get(url, timeout=10)
        resp.encoding = 'utf-8'
    except Exception as exc:  # noqa: BLE001
        print(f"访问失败，错误信息: {exc}")
        return

    if resp.status_code == 200:
        print("网络连接正常，随时可以开始抓取数据！")
        title_match = re.search(r"<title>(.*?)</title>", resp.text, re.IGNORECASE | re.DOTALL)
        title = title_match.group(1).strip() if title_match else "未找到标题"
        print(f"网页标题: {title}")
    else:
        print("访问失败")


if __name__ == "__main__":
    main()