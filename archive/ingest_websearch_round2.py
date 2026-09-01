"""
批量入库 三轮深度搜索新发现投融资事件（2023-2025 补充批次）
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import insert_or_update_article, get_session, Article
from funding_tagger import tag_funding, merge_funding_tags
from urllib.parse import urlparse
from datetime import date, datetime


def extract_domain(url: str) -> str:
    try:
        return urlparse(url).netloc
    except Exception:
        return ''


# ── 新发现事件列表 ──────────────────────────────────────────────
# 每条: (title, url, date, content_summary)

NEW_ARTICLES = [
    # ── 2024 年 ──
    (
        "微观纪元完成数千万元Pre-A轮融资，合肥高投与昆仑资本联合领投",
        "https://stcn.com/article/detail/1221024.html",
        date(2024, 6, 3),
        "量子计算应用公司微观纪元完成数千万元Pre-A轮融资，"
        "由合肥高投与昆仑资本联合领投。微观纪元成立于2022年，"
        "总部位于合肥，专注于量子计算在生物医药、金融等领域的应用落地。"
    ),
    (
        "未磁科技完成超亿元A+轮融资，北京机器人产业基金领投",
        "https://www.chinaventure.com.cn/news/111-20240722-382119.html",
        date(2024, 7, 22),
        "量子精密测量企业未磁科技完成超亿元A+轮融资，由北京机器人产业基金领投，"
        "中科创星、朗玛峰创投等跟投。未磁科技专注于原子磁力计等量子传感技术。"
    ),
    (
        "华为哈勃投资国测量子，持股约4.38%",
        "https://www.stcn.com/article/detail/1311722.html",
        date(2024, 9, 1),
        "华为旗下深圳哈勃科技投资合伙企业入股国测量子科技（浙江）有限公司，"
        "持股约4.38%。国测量子是北京大学在量子精密测量领域唯一的产业化公司，"
        "核心产品为芯片原子钟，已实现全国产化。"
    ),
    (
        "星光股份以800万元增资收购天芯量子51%股权",
        "https://paper.cnstock.com/html/2024-05/22/content_1920950.htm",
        date(2024, 5, 22),
        "广东星光发展股份有限公司（002076.SZ）公告以800万元增资收购"
        "广州市天芯量子信息技术有限公司51%股权，切入量子保密通信与AI信息安全领域。"
        "交易含对赌条款，涉及6000万元营收目标。"
    ),

    # ── 2025 年 ──
    (
        "玻色量子获北京高精尖产业发展基金A+轮融资",
        "https://finance.eastmoney.com/a/202502143319626642.html",
        date(2025, 2, 14),
        "光量子计算公司玻色量子完成A+轮融资，由北京高精尖产业发展投资基金"
        "（规模20亿元的市级政府引导基金）领投。这是玻色量子成立以来的第6轮融资，"
        "累计融资额持续领跑光量子计算赛道。"
    ),
    (
        "图灵量子完成亿元级战略轮融资，盛世投资领投",
        "https://www.cnstock.com/commonDetail/474311",
        date(2025, 7, 21),
        "光量子芯片企业图灵量子完成亿元级战略轮融资，由盛世投资领投。"
        "图灵量子四年内完成五轮融资，2025年上半年订单额突破亿元。"
        "公司在光量子芯片和量子计算全栈解决方案方面保持国内领先地位。"
    ),
    (
        "中科酷原完成数千万元C轮融资，芯光量子基金与光谷天使基金投资",
        "https://www.cnstock.com/commonDetail/476109",
        date(2025, 7, 15),
        "中性原子量子计算企业中科酷原完成数千万元C轮融资，"
        "投资方包括芯光量子基金、光谷天使基金和彩讯股份。"
        "中科酷原总部位于武汉，2025年内已连续完成B轮、C轮和战略融资三轮。"
    ),
    (
        "中科酷原获近亿元战略融资，中国移动链长基金入局",
        "https://finance.eastmoney.com/news/1354,202601153620773128.html",
        date(2025, 12, 15),
        "中科酷原完成近亿元战略融资，由中国移动链长基金投资。"
        "这是中科酷原2025年内第三轮融资（继2月B轮/战略投资、7月C轮之后），"
        "中国移动通过链长基金布局中性原子量子计算路线。"
    ),
    (
        "逻辑比特科技完成天使轮融资，东方嘉富领投",
        "https://api3.cls.cn/share/article/1991713",
        date(2025, 3, 15),
        "超导量子计算公司杭州逻辑比特科技有限公司完成天使轮融资，"
        "由东方嘉富领投，浙江省科创母基金、西湖紫金创投、藕舫天使跟投。"
        "逻辑比特源自浙江大学，已实现100+量子比特芯片。"
    ),
    (
        "逻辑比特完成数千万元Pre-A轮融资，浙大联创领投",
        "https://www.pedaily.cn/first/135431.shtml",
        date(2025, 10, 14),
        "超导量子计算公司逻辑比特完成数千万元Pre-A轮融资，"
        "由浙大联创投资领投，东方嘉富、华夏恒天、西湖科创投等跟投。"
        "公司已推出'天目2号'100+量子比特超导芯片。"
    ),
    (
        "MatriQ原子矩阵完成种子轮融资，布局中性原子量子计算",
        "https://www.chinaventure.com.cn/news/114-20251107-388749.html",
        date(2025, 11, 7),
        "杭州原子矩阵计算有限公司（MatriQ）宣布完成种子轮融资，"
        "投资方包括L2F光源创业者基金、千乘资本和元禾原点。"
        "MatriQ由光源资本孵化，专注全栈中性原子量子计算方案。"
    ),
    (
        "量旋科技完成数亿元C轮融资，隆利科技等参投",
        "https://www.cls.cn/detail/xk/e413cfe017ed79712333b3130dbb46ef",
        date(2025, 12, 31),
        "量旋科技完成数亿元C轮融资，投资方包括隆利科技、晶凯资本、"
        "恒泰华盛、毅达资本、青岛瀚瑞、夏佐全等多家机构。"
        "距2025年7月B系列轮仅6个月，量旋科技实现B轮到C轮的快速资本推进。"
    ),
    (
        "矩阵时光获数千万元战略融资，南京未来产业天使基金首投",
        "https://njna.nanjing.gov.cn/tzxq/tzdt/202504/t20250418_5131185.html",
        date(2025, 3, 27),
        "矩阵时光数字科技有限公司获数千万元战略融资，"
        "由南京未来产业天使基金投资（该基金的首笔投资）。"
        "矩阵时光由南京大学陈增兵教授创办，专注于量子人工智能与量子安全技术。"
    ),
    (
        "频准激光科创板IPO获受理，拟募资14.1亿元",
        "https://news.qq.com/rain/a/20251210A06L3100",
        date(2025, 12, 10),
        "高端光纤激光器企业频准激光科创板IPO申请获受理，拟募资14.1亿元，"
        "保荐机构为中信建投证券，IPO前估值约43.5亿元。"
        "频准激光为量子计算和量子精密测量提供核心光源设备。"
    ),

    # ── 股权转让 / 二级市场 ──
    (
        "宏力达以1598万元受让本源量子0.2323%股份",
        "https://m.c114.com.cn/w3542-1296012.html",
        date(2025, 8, 15),
        "上市公司宏力达公告以1598万元受让本源量子0.2323%股份，"
        "对应本源量子整体估值约69亿元。同期嘉兴远帆以1665万元受让0.2420%股份。"
    ),

    # ── 政府引导基金 ──
    (
        "湖州南太湖新区设立首支量子科技天使基金",
        "http://taihu.huzhou.gov.cn/art/2025/3/17/art_1229210981_58910666.html",
        date(2025, 3, 17),
        "湖州南太湖新区设立首支量子科技天使基金，聚焦量子信息领域早期项目投资。"
        "湖州依托国测量子等本地量子企业打造量子科技产业集群。"
    ),
    (
        "四川省设立10亿元量子科技产业子基金",
        "https://wap.eastmoney.com/a/202604013692181849.html",
        date(2025, 3, 30),
        "四川省设立10亿元量子科技产业子基金，作为省级战略性新兴产业基金的重要组成部分。"
        "成都已集聚电子科技大学量子实验室、中科院光电所等量子科研力量。"
    ),
    (
        "国家创业投资引导基金设立，量子科技为重点方向",
        "https://finance.eastmoney.com/a/202512263602914675.html",
        date(2025, 12, 26),
        "国家创业投资引导基金正式设立，总规模达千亿级，量子科技与人工智能、"
        "生物技术并列为三大重点投资方向。该基金由国务院批准设立，"
        "旨在引导社会资本投向战略性新兴产业。"
    ),
]


def ingest():
    print(f"{'='*70}")
    print(f"WebSearch 补充批次入库 — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"待入库: {len(NEW_ARTICLES)} 篇")
    print(f"{'='*70}\n")

    inserted = 0
    updated = 0
    skipped = 0

    for i, (title, url, orig_date, content_detail) in enumerate(NEW_ARTICLES, 1):
        domain = extract_domain(url)
        full_content = content_detail + '\n\n🤖 本文由 AI 摘要生成，原文见链接'

        # Check duplicate by title
        session = get_session()
        try:
            existing = session.query(Article).filter(
                Article.title == title,
                Article.page_type == 'websearch'
            ).first()
        finally:
            session.close()

        if existing:
            print(f"[{i:2d}/{len(NEW_ARTICLES)}] SKIP (已存在)  {title[:60]}")
            skipped += 1
            continue

        # Tag funding
        funding = tag_funding(title, full_content)
        tags = {'weekly': ['资本运作'], 'search_tags': ['国内投融资', 'websearch']}
        tags = merge_funding_tags(tags, funding)

        if funding:
            c = funding.get('company', '?')
            r = funding.get('round', '?')
            a = funding.get('amount_text', '?')
            print(f"[{i:2d}/{len(NEW_ARTICLES)}] INSERT  {title[:60]}")
            print(f"         🏢 {c} | 💰 {r} | 📊 {a}")
        else:
            print(f"[{i:2d}/{len(NEW_ARTICLES)}] INSERT  {title[:60]}")
            print(f"         ⚠️ 未识别结构化字段")

        try:
            result = insert_or_update_article(
                reference_url=url,
                liangke_url=url,
                title=title,
                content=full_content,
                original_date=orig_date,
                liangke_date=orig_date,
                source_domain=domain,
                reference_title=title,
                tags=tags,
                page_type='websearch'
            )
            if result['action'] == 'inserted':
                inserted += 1
            else:
                updated += 1
        except Exception as e:
            print(f"         ❌ 入库失败: {e}")

    print(f"\n{'='*70}")
    print(f"入库完成: 新增 {inserted} | 更新 {updated} | 跳过 {skipped}")
    print(f"{'='*70}")


if __name__ == '__main__':
    ingest()
