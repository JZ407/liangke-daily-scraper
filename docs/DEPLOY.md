# 量科网新闻抓取工作流 - 部署文档

## 系统要求

- Windows 10/11
- Python 3.11+（推荐 3.14）
- Microsoft Edge 浏览器（用于登录和 Cookie 提取）
- MySQL 8.0+（或 MariaDB 10.6+）

## 快速开始

```bash
# 1. 解压到任意目录，例如 D:\liangke_scraper\
# 2. 安装依赖并初始化
python setup.py

# 3. 启动 MySQL
start_mysql.bat

# 4. 创建数据库（MySQL 启动后执行）
python setup.py --db-only

# 5. 登录量科网 http://www.qtc.com.cn，然后更新 Cookie
update_cookie.bat

# 6. 运行每日抓取
run_daily.bat
```

## 详细安装步骤

### 1. 安装 Python 依赖

确保已安装 Python 3.11+，然后运行：

```bash
python setup.py
```

这会：
- 安装 `requirements.txt` 中的所有 Python 包
- 创建 `cookies/` 和 `mysql_data/` 目录
- 自动生成 `my.ini`（MySQL 配置文件）
- 初始化 MySQL 数据目录（如果尚未初始化）

### 2. 安装 MySQL（如果尚未安装）

如果没有安装 MySQL，可以通过以下方式安装：

**方式 A：winget（推荐）**
```bash
winget install Oracle.MySQL
```

**方式 B：MySQL Installer**
从 https://dev.mysql.com/downloads/installer/ 下载安装。

安装完成后，重新运行 `python setup.py` 以重新生成 `my.ini`。

### 3. 启动 MySQL

双击 `start_mysql.bat`，或在命令行运行：

```bash
start_mysql.bat
```

脚本会自动检测 MySQL 安装位置并启动服务。

### 4. 创建数据库和用户

MySQL 启动后，运行：

```bash
python setup.py --db-only
```

这会创建：
- 数据库 `liangke_scraper`
- 用户 `scraper` / 密码 `scraper123`

### 5. 配置 Cookie

1. 打开 Edge 浏览器，访问 http://www.qtc.com.cn
2. 登录你的账号
3. 双击 `update_cookie.bat`
4. 脚本会自动提取 Cookie 并保存到 `cookies/qtc_cookies.pkl`

Cookie 有效期约 1 周，过期后需重新运行 `update_cookie.bat`。

### 6. 运行抓取

双击 `run_daily.bat` 即可抓取当天新闻。

## 文件结构

```
liangke_scraper/
├── setup.py                    # 初始化脚本（依赖安装、目录创建、my.ini 生成）
├── requirements.txt            # Python 依赖
├── scrape_daily.py             # 每日抓取主程序（含自动标签）
├── db.py                       # SQLAlchemy ORM 数据库层
├── extract_original_date.py    # 参考链接原始日期提取
├── extract_cookie.py           # Edge CDP Cookie 提取
├── my.ini                      # MySQL 配置文件（自动生成）
├── start_mysql.bat             # 启动 MySQL
├── update_cookie.bat           # 更新 Cookie
├── run_daily.bat               # 一键运行每日抓取
├── quantum_keywords_v1.md      # 关键词词库
├── DEPLOY.md                   # 本文件
├── cookies/                    # Cookie 存储目录
└── mysql_data/                 # MySQL 数据目录
```

## 日常使用

| 场景 | 操作 |
|------|------|
| 首次部署 | 按上方 6 步执行 |
| 每日抓取 | 双击 `run_daily.bat` |
| Cookie 过期 | 登录量科网后运行 `update_cookie.bat` |
| 电脑重启后 | 先运行 `start_mysql.bat`，再运行 `run_daily.bat` |
| 设置定时任务 | 用 Windows 任务计划程序定时运行 `run_daily.bat` |

## 数据库连接信息

| 配置 | 值 |
|------|-----|
| 主机 | 127.0.0.1 |
| 端口 | 3306 |
| 数据库 | liangke_scraper |
| 用户 | scraper |
| 密码 | scraper123 |

可用任意 MySQL 客户端（如 DBeaver、Navicat、MySQL Workbench）连接查看数据。

## 导出数据

```bash
# 导出 Excel（标签展开格式）
python -c "import export_excel; export_excel.run()"

# 导出 SQL 备份
mysqldump -u scraper -pscanner123 liangke_scraper > backup.sql
```

## 常见问题

**Q: `setup.py` 提示找不到 MySQL**
A: 先安装 MySQL，然后重新运行 `python setup.py`。

**Q: `update_cookie.bat` 提示 Edge 未运行**
A: 确保 Edge 已打开并登录了量科网。脚本会尝试自动启动 Edge，但如果失败，请手动打开。

**Q: `scrape_daily.py` 提示 Cookie 文件不存在**
A: 先运行 `update_cookie.bat` 提取 Cookie。

**Q: MySQL 启动失败**
A: 检查 `my.ini` 中的 `basedir` 和 `datadir` 路径是否正确。可删除 `my.ini` 后重新运行 `python setup.py` 重新生成。

**Q: 数据库中文乱码**
A: 确保 `my.ini` 中包含 `character-set-server=utf8mb4`，且数据库创建时使用了 `utf8mb4` 字符集。

## 技术栈

- Python 3.14
- SQLAlchemy 2.x + PyMySQL
- BeautifulSoup4 + requests
- MySQL 8.4
- Chrome DevTools Protocol (CDP)
