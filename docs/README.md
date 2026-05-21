# 量科网每日新闻抓取工作流（MySQL 版）

## 功能特性

- **每日自动抓取**：只抓取当天更新的新闻
- **参考链接原始日期**：深入原始来源提取真实发布日期（非量科网转载时间）
- **MySQL 数据库存储**：科学结构化存储，支持查询/统计/导出
- **跨天去重**：同一篇原始新闻只存一条，重复抓取时更新计数
- **Cookie 自动提取**：从 Edge 浏览器提取登录态，无需明文密码

## 文件结构

```
D:\Claude_code\
├── my.ini                      # MySQL 配置文件
├── db.py                       # SQLAlchemy ORM 层
├── extract_cookie.py           # Edge Cookie 提取（CDP）
├── extract_original_date.py    # 参考链接原始日期提取
├── scrape_daily.py             # 每日抓取主程序（集成数据库+去重+原始日期）
├── start_mysql.bat             # 启动 MySQL 服务
├── update_cookie.bat           # 更新 Cookie（登录后运行）
├── run_daily.bat               # 一键运行每日抓取
└── README.md                   # 本文档
```

## 快速开始

### 1. 启动 MySQL（首次或重启后）

双击 `start_mysql.bat`

MySQL 数据目录位于 `C:\Users\zhouj\mysql_data`，端口 3306。

### 2. 更新 Cookie（每周一次）

1. 在 Edge 浏览器登录 http://www.qtc.com.cn
2. 双击 `update_cookie.bat`
3. Cookie 自动提取并保存到桌面 `qtc_cookies.pkl`

### 3. 运行每日抓取

双击 `run_daily.bat`

脚本会自动：
1. 检查并启动 MySQL
2. 提取最新 Cookie
3. 抓取当天新闻 → 提取参考链接原始日期 → 去重入库
4. 输出统计报告

### 4. 设置定时任务（可选）

`Win + R` → `taskschd.msc` → 创建基本任务 → 每天定时运行 `run_daily.bat`

## 数据库连接信息

| 配置 | 值 |
|------|-----|
| 主机 | 127.0.0.1 |
| 端口 | 3306 |
| 数据库 | liangke_scraper |
| 用户 | scraper |
| 密码 | scraper123 |
| root 密码 | root123 |

## 表结构

```sql
CREATE TABLE articles (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    reference_url   VARCHAR(1000),      -- 原始来源链接（去重键）
    liangke_url     VARCHAR(1000),      -- 量科网链接
    title           VARCHAR(500),       -- 标题
    content         LONGTEXT,           -- 正文
    original_date   DATE,               -- 原始发布日期（来自参考链接）
    liangke_date    DATE,               -- 量科网显示日期
    source_domain   VARCHAR(200),       -- 原始来源域名
    reference_title VARCHAR(200),       -- 参考链接锚文本
    tags            JSON,               -- 标签
    first_seen_at   DATETIME,           -- 首次入库时间
    last_seen_at    DATETIME,           -- 最后更新时间
    fetch_count     INT DEFAULT 1,      -- 被抓取次数
    UNIQUE KEY uk_reference_url (reference_url(255))
);
```

## 常用查询

```sql
-- 查看今天的文章
SELECT title, original_date, source_domain 
FROM articles 
WHERE liangke_date = CURDATE() 
ORDER BY original_date DESC;

-- 查看抓取统计
SELECT 
    COUNT(*) as total_articles,
    COUNT(DISTINCT source_domain) as sources,
    MIN(original_date) as earliest,
    MAX(original_date) as latest
FROM articles;

-- 查看重复被抓取的文章
SELECT title, fetch_count 
FROM articles 
WHERE fetch_count > 1 
ORDER BY fetch_count DESC;

-- 按来源域名统计
SELECT source_domain, COUNT(*) as count 
FROM articles 
GROUP BY source_domain 
ORDER BY count DESC;
```

## 原始日期提取策略

按优先级依次尝试：
1. `meta[property="article:published_time"]`
2. `meta[property="og:updated_time"]`
3. `meta[name="date"]` / `meta[name="pubdate"]`
4. `<time datetime="...">` 标签
5. JSON-LD (`datePublished`)
6. URL 路径中的日期模式（如 `/2026/05/18/`）
7. 全部失败时回退到量科网日期

## 去重机制

- **去重键**：`reference_url`（原始来源链接）
- **逻辑**：抓取前 SELECT 检查 → 不存在则 INSERT → 存在则 UPDATE（fetch_count++）
- **跨天**：同一篇新闻无论哪天出现，只会有一条记录，fetch_count 累加

## 注意事项

1. **Cookie 有效期**：约 1 周，过期后需重新运行 `update_cookie.bat`
2. **MySQL 启动**：电脑重启后需先运行 `start_mysql.bat`
3. **原始日期提取**：部分网站可能反爬导致提取失败，此时回退到量科网日期
4. **串行请求**：访问参考链接时 1.5 秒间隔，避免被封

## 技术栈

- Python 3.14
- SQLAlchemy 2.x + PyMySQL
- BeautifulSoup4
- MySQL 8.4.9
- Chrome DevTools Protocol (CDP)
