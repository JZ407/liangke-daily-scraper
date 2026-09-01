"""
批量入库 WebSearch 投融资搜索结果（2023-2025）
按 liangke_daily/docs/websearch投融资检索指南.md 入库规则执行
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import insert_or_update_article, article_exists, get_session, Article
from funding_tagger import tag_funding, merge_funding_tags
from urllib.parse import urlparse
from datetime import date, datetime

# ── 待入库文章列表 ───────────────────────────────────────────────────
# (title, url, date, content_summary)
ARTICLES_2023 = [
    (
        "图灵量子完成数亿元A轮融资，中网投领投",
        "https://36kr.com/p/2092178289885571",
        date(2023, 1, 18),
        "光量子芯片公司图灵量子完成数亿元A轮融资，由中国互联网投资基金（中网投）领投，"
        "华控基金、联想创投、东证创新跟投。图灵量子由上海交通大学金贤敏教授创立，"
        "专注于光量子芯片和量子计算全栈解决方案。"
    ),
    (
        "联想、东方证券等入股图灵量子",
        "https://company.cnstock.com/company/scp_gsxw/202309/5125675.htm",
        date(2023, 9, 1),
        "工商变更显示，联想集团、东方证券等机构新增为图灵量子股东。"
        "图灵量子此前于2023年1月完成数亿元A轮融资。"
    ),
    (
        "玻色量子完成新一轮亿元级融资，中移基金领投",
        "https://www.pedaily.cn/first/88979.shtml",
        date(2023, 3, 8),
        "光量子计算公司玻色量子完成新一轮亿元级融资，由北京中移数字新经济产业基金（中国移动旗下）"
        "和华控基金领投，盈富泰克、朝科创等跟投。这是玻色量子成立两年内的第四轮融资，"
        "公司总部位于北京，专注相干光量子计算。"
    ),
    (
        "硅臻量子完成1500万元新一轮融资，国芯科技投资",
        "http://stock.stockstar.com/IG2023042000028111.shtml",
        date(2023, 4, 20),
        "光量子集成芯片企业硅臻量子完成1500万元新一轮融资，投资方为国芯科技。"
        "硅臻量子专注于光量子集成芯片设计。"
    ),
    (
        "幺正量子获顺为资本、科大讯飞战略入股",
        "https://36kr.com/newsflashes/2566976435725958",
        date(2023, 12, 18),
        "合肥幺正量子科技有限公司获顺为资本（小米系）和科大讯飞战略入股。"
        "幺正量子专注于离子阱量子计算技术路线，总部位于合肥。"
    ),
    (
        "武汉国科量子拟增资并吸收合并湖北国科量子",
        "https://www.c114.com.cn/quantum/5341/a1244372.html",
        date(2023, 6, 1),
        "武汉国科量子通信网络有限公司拟通过增资方式吸收合并湖北国科量子通信网络有限公司，"
        "实现量子通信网络业务的整合。"
    ),
    (
        "湖北省设立20亿元量子科技产业投资基金",
        "http://www.hubei.gov.cn/zwgk/hbyw/hbywqb/202311/t20231116_4947889.shtml",
        date(2023, 11, 16),
        "湖北省人民政府宣布设立20亿元省级量子科技产业投资基金，"
        "重点支持量子计算、量子通信、量子精密测量等领域的技术研发和产业化。"
        "这是国内规模最大的省级量子专项基金之一。"
    ),
]

ARTICLES_2024 = [
    (
        "华翊量子完成近亿元战略轮融资，中移资本独家投资",
        "https://www.cei.cn/defaultsite/s/article/2024/01/24/4b4ff606-8c51eaba-018d-38ff969e-0e35_2024.html",
        date(2024, 1, 24),
        "离子阱量子计算公司华翊量子完成近亿元战略轮融资，由中国移动旗下中移资本独家投资。"
        "华翊量子（华翊博奥）总部位于北京，专注离子阱量子计算技术。"
    ),
    (
        "华翊量子完成过亿元Pre-A轮融资",
        "https://www.chinastarmarket.cn/detail/1702198",
        date(2024, 5, 15),
        "华翊量子完成过亿元Pre-A轮融资，由央视融媒体基金领投，百度风投、联想创投、三七互娱跟投。"
        "这是华翊量子2024年内完成的第二轮融资（继1月战略轮之后）。"
    ),
    (
        "国盾量子再融资获注册批复，中电信量子集团17.75亿元全额认购",
        "https://cs.com.cn/qs/202411/t20241122_6456039.html",
        date(2024, 11, 22),
        "国盾量子向特定对象发行A股股票项目获注册批复，中电信量子集团以17.75亿元全额认购。"
        "本次定增完成后，中电信量子集团将成为国盾量子控股股东，"
        "标志着中国电信正式控股量子通信龙头企业。"
    ),
    (
        "禾信仪器拟收购量羲技术控制权，跨界量子硬件领域",
        "https://www.chnfund.com/article/AR3bf7448b-c537-c3d1-bd28-3a15c726b393",
        date(2024, 10, 15),
        "上市公司禾信仪器公告拟通过发行股份及支付现金方式购买上海量羲技术控制权。"
        "量羲技术为量子计算提供上游核心硬件设备。本次交易构成重大资产重组。"
    ),
    (
        "国仪量子启动科创板IPO辅导",
        "https://www.chinastarmarket.cn/detail/1813428",
        date(2024, 9, 29),
        "国仪量子技术（合肥）股份有限公司启动科创板IPO辅导，辅导机构为华泰联合证券。"
        "国仪量子由中科大少年班校友贺羽创立，布局量子计算与量子精密测量技术，"
        "股东包括高瓴资本、IDG资本、中科院资本等。"
    ),
    (
        "湖北首支量子产业基金设立，首期规模1亿元",
        "https://www.chinastarmarket.cn/detail/1533654",
        date(2024, 6, 11),
        "在武汉量子论坛2024上，湖北省首支量子产业基金——武汉光谷芯光量子科技投资基金正式发布，"
        "首期规模1亿元，重点投资量子通信、量子精密测量等方向，投资周期10-15年。"
    ),
    (
        "中国银行设立300亿科创母基金，量子技术为重点方向",
        "https://guandian.hk/article/20240826/431736.html",
        date(2024, 8, 26),
        "中国银行宣布设立300亿元人民币科创母基金，量子技术与AI、生物技术并列为三大重点投资方向，"
        "覆盖合肥、深圳、武汉等多座城市。"
    ),
]

ARTICLES_2025 = [
    (
        "森一量子连续完成天使轮及Pre-A轮融资",
        "https://36kr.com/newsflashes/3201478088588672",
        date(2025, 3, 11),
        "森一量子连续完成天使轮及Pre-A轮融资，累计数千万元。"
        "公司专注于光通信核心材料领域，产品可应用于量子通信产业链上游。"
    ),
    (
        "量旋科技完成数亿元B系列轮融资",
        "http://www.ce.cn/xwzx/kj/202507/t20250721_2414864.shtml",
        date(2025, 7, 21),
        "量旋科技完成数亿元B系列轮融资，用于加速技术升级与全球化扩张。"
        "量旋科技是超导和核磁共振量子计算路线的代表企业，"
        "此前曾获比亚迪、联想创投等产业资本投资。"
    ),
    (
        "岭澜基金与千里马资本受让本源量子股份，整体估值120亿元",
        "https://www.chinastarmarket.cn/detail/2213558",
        date(2025, 11, 28),
        "岭澜基金（6100万元）与千里马资本（1970万元）合计8070余万元受让本源量子股份，"
        "交易对应本源量子整体估值120亿元。本源量子是中国首家量子计算公司，总部位于合肥。"
    ),
    (
        "天阳科技拟3000万元参投创投基金，间接布局本源量子",
        "https://finance.eastmoney.com/a/202512153591708563.html",
        date(2025, 12, 15),
        "金融科技公司天阳科技公告拟以3000万元认缴青岛红马金鑫创投基金47.54%份额，"
        "该基金将间接投资本源量子，天阳科技借此切入量子计算赛道。"
    ),
    (
        "国富量子更名并收购量旋科技4.27%股权，与夸密量子战略合作",
        "https://stock.10jqka.com.cn/20250317/c666749338.shtml",
        date(2025, 3, 17),
        "港股公司国富创新更名为国富量子，此前以3950万港元收购量旋科技4.27%股权。"
        "同时宣布与夸密量子达成战略合作，全面转型量子科技赛道。"
    ),
    (
        "国仪量子科创板IPO获受理，拟募资11.69亿元",
        "https://fxxh.cis.org.cn/news/6454.html",
        date(2025, 12, 10),
        "国仪量子技术（合肥）股份有限公司科创板IPO申请获上交所受理，"
        "拟募资11.69亿元，IPO前估值超96亿元。公司主营量子精密测量仪器和量子计算产品，"
        "由中科大少年班校友贺羽（90后）掌舵。"
    ),
    (
        "本源量子启动IPO辅导，最新估值69亿元",
        "https://m.mydrivers.com/newsview/1074904.html",
        date(2025, 9, 15),
        "中国首家量子计算公司本源量子启动IPO辅导，辅导机构为中信建投证券，"
        "最新估值约69亿元。本源量子专注超导量子计算整机研发，总部位于合肥。"
    ),
    (
        "北京未来开源量子创业投资基金发布，规模5亿元",
        "http://bj.people.com.cn/n2/2025/1214/c14540-41441945.html",
        date(2025, 12, 14),
        "北京未来开源量子创业投资基金正式发布，规模5亿元，由北京市与海淀区联合设立，"
        "国融工发与中科创星担任双GP，投资量子信息领域初创及成长企业。"
    ),
    (
        "武汉设立量子概念验证基金，首期约1000万元",
        "http://tctest.wuhan.gov.cn/tzwh/tzzx/202511/t20251126_2683083.shtml",
        date(2025, 11, 26),
        "武汉市东湖高新区设立湖北省首支以量子命名的概念验证基金，规模约1000万元，"
        "由光谷天使基金与创新平台按1:1出资，用于量子技术早期验证和孵化。"
    ),
    (
        "中国电信发起设立首支央企量子产业创投基金",
        "https://m.cnstock.com/commonDetail/591840",
        date(2025, 11, 20),
        "在2025量子科技和产业大会上，中国电信宣布发起设立首支央企量子产业创业投资基金，"
        "聚焦量子通信、量子计算、量子精密测量等领域的早期投资。"
    ),
    (
        "500亿中银科创母基金启动，覆盖量子等八大领域",
        "https://www.chinastarmarket.cn/detail/1972332",
        date(2025, 3, 15),
        "中国银行旗下中银科创母基金启动，总规模500亿元，覆盖合肥、深圳、武汉等8个城市，"
        "量子技术与AI、生物技术并列为三大核心投资方向。"
    ),
]

ALL_ARTICLES = ARTICLES_2023 + ARTICLES_2024 + ARTICLES_2025


def extract_domain(url: str) -> str:
    """Extract domain from URL."""
    try:
        return urlparse(url).netloc
    except Exception:
        return ''


def ingest():
    print(f"{'='*70}")
    print(f"WebSearch 投融资入库开始 — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"待入库: {len(ALL_ARTICLES)} 篇 ({len(ARTICLES_2023)} 篇2023 + {len(ARTICLES_2024)} 篇2024 + {len(ARTICLES_2025)} 篇2025)")
    print(f"{'='*70}\n")

    skipped = 0
    inserted = 0
    updated = 0
    funding_tagged = 0

    for i, (title, url, orig_date, content_detail) in enumerate(ALL_ARTICLES, 1):
        domain = extract_domain(url)

        # Build full content with AI summary marker
        full_content = content_detail + '\n\n🤖 本文由 AI 摘要生成，原文见链接'

        # Check if already exists by title (per guide: exact title match)
        session = get_session()
        try:
            existing = session.query(Article).filter(
                Article.title == title,
                Article.page_type == 'websearch'
            ).first()
        finally:
            session.close()

        if existing:
            print(f"[{i:2d}/{len(ALL_ARTICLES)}] SKIP (已存在)  {title[:50]}...")
            skipped += 1
            continue

        # Tag funding
        funding = tag_funding(title, full_content)

        # Base tags
        tags = {
            'weekly': ['资本运作'],
            'search_tags': ['国内投融资', 'websearch']
        }

        # Merge funding tags
        tags = merge_funding_tags(tags, funding)
        if funding:
            funding_tagged += 1
            company = funding.get('company', '?')
            round_ = funding.get('round', '?')
            amount_text = funding.get('amount_text', '?')
            print(f"[{i:2d}/{len(ALL_ARTICLES)}] INSERT  {title[:50]}...")
            print(f"         🏢 {company} | 💰 {round_} | 📊 {amount_text}")
        else:
            print(f"[{i:2d}/{len(ALL_ARTICLES)}] INSERT  {title[:50]}...")
            print(f"         ⚠️ funding tagger 未识别到结构化字段")

        # Insert
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
    print(f"入库完成:")
    print(f"  新增: {inserted}  更新: {updated}  跳过: {skipped}")
    print(f"  结构化打标成功: {funding_tagged}/{inserted}")
    print(f"{'='*70}")


if __name__ == '__main__':
    ingest()
