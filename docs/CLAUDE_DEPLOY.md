# 量科网抓取工作流 - Claude Code 自动部署指令

> **用途**：将此文档交给 Claude Code，它将自动完成除浏览器登录外的所有部署步骤。

---

## 项目概述

这是一个量科网（http://www.qtc.com.cn）每日新闻自动抓取系统，包含：
- 首页新闻抓取
- 参考链接原始日期提取
- MySQL 数据库存储与去重
- 自动标签分类
- Excel 导出

---

## 前置依赖检查

Claude 请先执行环境检查，根据结果决定后续步骤：

```bash
# 检查 Python
python --version

# 检查 MySQL（尝试多种路径）
ls -la "/c/Program Files/MySQL/MySQL Server 8.4/bin/mysqld.exe" 2>/dev/null || \
ls -la "/c/Program Files/MySQL/MySQL Server 8.0/bin/mysqld.exe" 2>/dev/null || \
echo "MySQL_NOT_FOUND"

# 检查 Edge
ls -la "/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" 2>/dev/null || \
ls -la "/c/Program Files/Microsoft/Edge/Application/msedge.exe" 2>/dev/null || \
echo "EDGE_NOT_FOUND"
```

**判断逻辑**：
- 如果 `MySQL_NOT_FOUND`：先安装 MySQL（见下方安装步骤），再重新运行本部署流程。
- 如果 `EDGE_NOT_FOUND`：提示用户安装 Edge 浏览器（但通常 Windows 自带，极少缺失）。

---

## 步骤 1：安装 MySQL（如未安装）

如果检测到 MySQL 未安装，Claude 请执行：

```bash
winget install Oracle.MySQL
```

安装完成后，**重新启动终端**并重新运行本流程。

> 如果 winget 不可用，Claude 请提示用户手动下载安装：
> https://dev.mysql.com/downloads/installer/
> 选择 "Server only" 安装模式即可。

---

## 步骤 2：初始化项目环境

Claude 请确保当前工作目录是项目根目录（包含 setup.py），然后执行：

```bash
# 1. 安装 Python 依赖
pip install -r requirements.txt

# 2. 运行初始化脚本（创建目录、生成 my.ini、初始化 MySQL 数据目录）
python setup.py
```

**setup.py 会完成**：
- 安装 `requests`, `beautifulsoup4`, `SQLAlchemy`, `PyMySQL`, `cryptography`, `websocket-client`, `openpyxl`
- 创建 `cookies/` 和 `mysql_data/` 子目录
- 根据检测到的 MySQL 路径自动生成 `my.ini`
- 初始化 MySQL 数据目录（仅首次）

---

## 步骤 3：启动 MySQL 并创建数据库

Claude 请执行：

```bash
# 启动 MySQL（后台运行）
start_mysql.bat

# 等待 MySQL 就绪（轮询端口）
for i in {1..30}; do
  netstat -an | grep -q "127.0.0.1:3306" && echo "MySQL ready" && break
  sleep 1
done
```

MySQL 启动后，创建数据库和用户：

```bash
python setup.py --db-only
```

**验证数据库连接**：

```bash
python -c "from db import get_article_count; print('DB OK, total:', get_article_count())"
```

如果输出 `DB OK, total: 0` 或已有数据，说明数据库连接正常。

---

## 步骤 4：人工介入 - 浏览器登录

**Claude 无法自动完成此步骤，必须提示用户操作：**

> 请用户在 Edge 浏览器中完成以下操作：
> 1. 打开 http://www.qtc.com.cn
> 2. 点击右上角登录，输入账号密码
> 3. 保持浏览器窗口打开（不要关闭 Edge）
> 4. 告诉 Claude "已登录"

---

## 步骤 5：提取 Cookie

用户确认登录后，Claude 执行：

```bash
update_cookie.bat
```

这会通过 Edge CDP 协议自动提取量科网的登录 Cookie，保存到 `cookies/qtc_cookies.pkl`。

**验证**：检查 Cookie 文件是否存在且非空。

```bash
ls -la cookies/qtc_cookies.pkl
```

---

## 步骤 6：首次运行抓取验证

Claude 执行完整抓取流程：

```bash
run_daily.bat
```

或直接运行 Python：

```bash
python scrape_daily.py
```

**期望输出**：
- "Found XX candidate news items on homepage"
- 显示今日新闻的抓取过程
- "INSERTED" 或 "UPDATED" 状态
- 最终统计报告（New articles / Updated articles / Errors）

**错误处理**：
- 如果报错 "Cookie file not found"：重新执行步骤 5
- 如果报错数据库连接失败：检查 MySQL 是否运行（`netstat -an | grep 3306`）

---

## 步骤 7：验证数据完整性

Claude 执行验证脚本：

```bash
python -c "
from db import get_session, Article
session = get_session()
total = session.query(Article).count()
empty_content = session.query(Article).filter((Article.content == '') | (Article.content == None)).count()
refs = session.query(Article).filter(Article.liangke_url.like('%/reference/%')).count()
print(f'Total articles: {total}')
print(f'Empty content: {empty_content}')
print(f'Reference articles: {refs}')
print('Status: OK' if empty_content == 0 else 'Status: WARNING - some articles missing content')
"
```

---

## 步骤 8：导出示例 Excel（可选）

Claude 可以帮用户导出一份 Excel 确认数据格式：

```bash
python export_excel.py
```

---

## 日常使用指令（给用户备忘）

部署完成后，用户每天只需要：

1. **电脑重启后**：先双击 `start_mysql.bat`
2. **每日抓取**：双击 `run_daily.bat`
3. **Cookie 过期**（约 1 周）：先登录量科网，再运行 `update_cookie.bat`
4. **导出 Excel**：运行 `python export_excel.py`

---

## 故障排查速查

| 现象 | Claude 处理方案 |
|------|----------------|
| `Cookie file not found` | 重新运行 `update_cookie.bat`，确保 Edge 已登录 |
| `Access denied for user 'scraper'` | 重新运行 `python setup.py --db-only` |
| MySQL 启动失败 | 检查 `my.ini` 中的 `basedir` 是否正确；删除 `mysql_data` 后重新 `python setup.py` |
| 抓取成功但数据库为空 | 检查日期过滤逻辑；可能是量科网当天无更新 |
| 标签全为空 | 检查 `scrape_daily.py` 中的 `auto_tag` 函数是否被调用 |

---

## 项目文件清单

Claude 部署前请确认以下文件齐全：

```
scrape_daily.py         [必需] 主抓取程序
db.py                    [必需] 数据库 ORM
extract_cookie.py        [必需] Cookie 提取
extract_original_date.py [必需] 原始日期提取
export_excel.py          [可选] Excel 导出
setup.py                 [必需] 初始化脚本
requirements.txt         [必需] Python 依赖
my.ini                   [自动生成] MySQL 配置
start_mysql.bat          [必需] 启动 MySQL
run_daily.bat            [必需] 一键抓取
update_cookie.bat        [必需] 更新 Cookie
DEPLOY.md                [可选] 人类阅读版部署文档
quantum_keywords_v1.md   [可选] 关键词词库
```

---

## 部署完成标志

当 Claude 完成以上所有步骤，且验证输出显示：
- MySQL 运行正常
- Cookie 提取成功
- `python scrape_daily.py` 执行无报错
- 数据库中有今日新闻数据

即视为部署成功。请向用户报告总文章数和今日新增数。
