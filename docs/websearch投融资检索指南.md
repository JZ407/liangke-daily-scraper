# WebSearch 量子投融资检索入库指南

## 一、目标

用 WebSearch 发现中国大陆量子公司的具体投融资事件，去重后入库到 MySQL `articles` 表，`page_type='websearch'`，打上 `tags.funding` 结构化标签。

---

## 二、搜索策略

### 2.1 域名白名单（28 个）

优先用核心财经域（前 11 个），地域政府域作为补充：

```
核心：eastmoney.com, stcn.com, finance.sina.com.cn, news.qq.com,
      chinaventure.com.cn, pedaily.cn, cls.cn, 163.com, 10jqka.com.cn,
      people.com.cn, xinhuanet.com

地域：ah.gov.cn, beijing.gov.cn, shanghai.gov.cn, gd.gov.cn,
      hubei.gov.cn, zj.gov.cn, jiangsu.gov.cn, sc.gov.cn,
      hefei.gov.cn, wuhan.gov.cn, haidian.gov.cn, shenzhen.gov.cn,
      hangzhou.gov.cn, chengdu.gov.cn, suzhou.gov.cn, nanjing.gov.cn, wuxi.gov.cn,
      szxc.gov.cn, pudong.gov.cn, jiangning.gov.cn, binhu.gov.cn
```

### 2.2 地域政府域（基金监控重点）

量子产业基金通常由地方政府首发，官网公告是最快的信息源：

| 域名 | 典型产出 |
|------|---------|
| `ah.gov.cn`, `hefei.gov.cn` | 合肥量子基金、安徽省级基金 |
| `beijing.gov.cn`, `haidian.gov.cn` | 北京量子基金、海淀区配套 |
| `shanghai.gov.cn` | 上海未来产业基金动态 |
| `sc.gov.cn`, `chengdu.gov.cn` | 四川振兴量子基金 |
| `hubei.gov.cn`, `wuhan.gov.cn` | 湖北/武汉量子基金 |
| `gd.gov.cn`, `shenzhen.gov.cn` | 广东/深圳量子基金 |
| `zj.gov.cn`, `hangzhou.gov.cn` | 浙江/杭州量子基金 |

⚠️ 政府域的文章标题通常不含"融资"关键词，搜索时用 `量子 基金` 比 `量子 融资` 命中率更高。

### 2.3 Query 设计

**早期方案（21 组，token 消耗大）**：轮次 9 组 + 技术路线 3 组 + IPO/基金/收购 4 组 + 地域 5 组。

**优化后（6-8 组，推荐）**：合并同类词，每组覆盖更广：

| # | Query | 覆盖 |
|---|-------|------|
| 1 | `量子 天使轮 Pre-A A轮 融资 亿元 2026` | 早期轮次 |
| 2 | `量子 B轮 C轮 D轮 Pre-IPO 战略融资 亿元 2026` | 中后期轮次 |
| 3 | `量子 超导 离子阱 中性原子 光量子 融资 2026` | 技术路线 |
| 4 | `量子 测量 传感 IPO 科创板 上市 2026` | 测量/IPO |
| 5 | `量子 基金 收购 并购 2026` | 基金/并购 |
| 6 | `合肥 北京 深圳 上海 武汉 量子 融资 2026` | 地域 |

⚠️ **加年份 `2026`** 可以减少旧闻噪音。

### 2.3 补充搜索

当搜索结果摘要里出现新公司名但没有对应链接时，单独搜公司名：

```
"无量量子" 融资 A轮
```

不加 `allowed_domains` 限制，先找到 URL 再判断域名是否在白名单内。

---

## 三、入库规则（铁律）

### 3.1 URL 必须真实

**禁止自己编造 URL。** 每条入库记录的 `reference_url` 必须来自 WebSearch 返回的链接列表。找不到合法 URL 的，跳过。

### 3.2 收录标准

- ✅ 中国大陆量子公司具体投融资事件（天使→Pre-IPO 全轮次）
- ✅ IPO 过会/注册通过
- ✅ 收购/并购（上市公司收量子公司）
- ✅ 量子产业基金设立（地方政府/央企/国资发起的专项基金）
- ❌ 海外公司融资
- ❌ 宏观/汇总/盘点/趋势类文章（如"2026年量子融资全景"）
- ❌ 政府拨款/资助/合同类（非 VC 轮次）
- ❌ 海外公司融资

### 3.3 去重

入库前用 Python 查 MySQL：

```python
from db import get_session, Article
session = get_session()
existing = session.query(Article).filter(
    Article.title == candidate_title,
    Article.page_type == 'websearch'
).first()
# 存在则跳过
```

标题相同就跳过。不用模糊匹配（容易误杀）。

### 3.4 入库参数

```python
insert_or_update_article(
    reference_url=url,       # 必须来自搜索结果
    liangke_url=url,         # websearch 没有量科网链接，和 reference_url 相同
    title=title,
    content=content + '\n\n🤖 本文由 AI 摘要生成，原文见链接',
    original_date=date,
    liangke_date=date,
    source_domain='163.com', # 从 URL 提取
    reference_title='原标题',
    tags={
        'weekly': ['资本运作'],
        'search_tags': ['国内投融资', 'websearch']
    },
    page_type='websearch'
)
```

### 3.5 自动打 funding 标签

入库后立即调用 tagger：

```python
from funding_tagger import tag_funding, merge_funding_tags

funding = tag_funding(title, content)
if funding:
    tags = merge_funding_tags(tags, funding)
```

这会在 `tags.funding` 里自动填入 company / investors / round / amount，面板就能读到。

---

## 四、常见陷阱

### 4.1 AI 摘要里有，链接里没有

搜索结果顶部的 AI 摘要会整合多家信息，但摘要里提到的事件不一定有对应链接。**必须去链接列表里找 URL，找不到就跳过。**

案例：无量量子 A 轮只在摘要里出现，6 组搜索的链接都没覆盖。需要额外搜 `"无量量子" 融资` 才找到 163.com 的链接。

### 4.2 同名公司混淆

"幺正量子" 和 "正则量子" 字形相近，"量坤科技" 和 "量旋科技" 也容易搞混。比对时看全称。

### 4.3 同一公司多轮融资

华翊量子有 Pre-A、A、A+ 三轮，每条都是独立事件。去重只看标题，不看公司名。

### 4.4 金额提取的坑

- "数千万元" = 3 千万，不是 3 亿
- "1800 万欧元" 要换算（×7.8），不是当人民币
- "亿元级" 是模糊表述，按 1.5 亿估算
- IPO 募资金额和估值金额不要混淆

### 4.5 轮次分类

- `Pre-A` 必须在 `A轮` 之前匹配，否则会被 A 轮吞掉
- `Pre-IPO` 同理，必须在 `IPO` 之前
- "天使轮"和"基金"的区分：标题里"上海未来产业基金"是投资方名称，不是融资轮次

---

## 五、效率经验

| 经验 | 说明 |
|------|------|
| 6-8 组合并搜索 | 21 组 → 6 组，token 消耗从 ~50K 降到 ~15K |
| 先查库再搜 | 看已有 37 条覆盖了哪些公司/轮次，心里有数 |
| 间隔 3-5 天搜一次 | 量子融资不是每天都有，高频搜索回报递减 |
| funding 标签自动打 | 入库即打标，省去后续跑 extractor |

---

## 六、演进历史

| 阶段 | 日期 | 入库 | 搜索组数 | 关键改进 |
|------|------|------|---------|---------|
| v1 | 06/14 | 5 条 | 21 组 | 初始版本，逐条搜 |
| v2 | 06/15 | 1 条 | 8 组 | 合并 query，token 优化 |
| v3 | 06/16 | 0 条 | 6 组 | +funding 自动打标 |
| v4 | 06/16 | 1 条 | 6+1 | 补充搜索绕过 AI 摘要漏检 |

---

## 七、一句话总结

> 用 6-8 组合并 query 在 28 个白名单域搜 → 政府域单独搜 `量子 基金` 抓产业基金 → 从链接列表（不是摘要）找 URL → 查 MySQL 去重 → 入库 + 自动打 funding 标签 → 面板自动刷新。
