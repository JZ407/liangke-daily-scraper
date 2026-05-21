# 量科网每日新闻抓取

量科网 (qtc.com.cn) 每日新闻抓取与日报生成工具。

## 目录结构

```
liangke_daily/
├── core/               # 核心抓取脚本
│   ├── scrape_daily.py         # 每日首页抓取
│   ├── extract_cookie.py       # Edge Cookie 提取
│   ├── extract_original_date.py # 参考链接原始日期提取
│   ├── generate_daily_report.py # 日报生成
│   ├── export_excel.py         # Excel 导出
│   ├── db.py                   # MySQL ORM 模型
│   └── setup.py                # 初始化脚本
├── config/             # 配置文件与启动脚本
│   ├── my.ini                  # MySQL 配置
│   ├── run_daily.bat           # 一键运行日报抓取
│   ├── start_mysql.bat         # 启动 MySQL
│   └── update_cookie.bat       # 更新 Cookie
├── data/               # 数据目录
│   └── cookies/                # Cookie 存储
├── docs/               # 文档
└── requirements.txt
```

## 快速开始

1. 安装依赖：`pip install -r requirements.txt`
2. 初始化 MySQL：`python core/setup.py`
3. 登录 http://www.qtc.com.cn 后运行 `config/update_cookie.bat`
4. 运行 `config/run_daily.bat` 开始抓取

## 更新日志

- 2026-05-21: 修复 `extract_original_date` 优先级，移除 fallback 到量科网日期的逻辑
- 2026-05-21: 新增 `export_daily.py`，支持 MySQL 数据库导出 Excel
- 2026-05-21: 完成 2026-05-21 当日抓取（5 条新入库，11 条更新，45 条跳过）
- 2026-05-21: 导出当日数据库为 `daily_export.xlsx`（69 条记录）
