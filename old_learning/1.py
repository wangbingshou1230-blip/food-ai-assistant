from __future__ import annotations

import sys
from datetime import datetime


def main() -> None:
    # 获取本机当前时间（本地时区），并以 ISO 8601 形式输出（包含毫秒与时区偏移）
    now_local = datetime.now().astimezone()
    print(f"当前电脑精确时间：{now_local.isoformat(timespec='milliseconds')}")

    py_ver = sys.version.split()[0]
    print(f"主人，您的 AIGC 自动化系统已就绪，当前 Python 版本运行正常。（Python {py_ver}）")


if __name__ == "__main__":
    main()
