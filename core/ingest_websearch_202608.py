"""
批量入库 WebSearch 投融资搜索结果(2026-08-18 增量批次)
按 liangke_daily/docs/websearch投融资检索指南.md 入库规则执行
6 条事件全部经原文验证(投中网/证券时报/中国国新/C114/商道创投网)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import insert_or_update_article, get_session, Article
from funding_tagger import tag_funding, merge_funding_tags
from urllib.parse import urlparse
from datetime import date

ALL_ARTICLES = [
    (
        "幺正量子完成数亿元A轮融资，深创投领投，社保湾区基金联合出资",
        "https://www.chinaventure.com.cn/news/114-20260803-392572.html",
        date(2026, 8, 3),
        "合肥幺正量子科技有限公司宣布完成数亿元A轮融资。本轮由深创投领投，"
        "社保基金湾区科技创新股权投资基金（深圳）与深圳市创新资本投资有限公司联合出资，"
        "广发信德、京铭资本、普华资本、启赋资本、兴泰资本、达晨财智、华控基金、"
        "首程控股、协鑫能科、灏浚投资、凯联资本、芯能创投、众为中国等多家机构跟投，"
        "云岫资本担任长期财务顾问。资金将用于加速研发攻关，瞄准量子优越性与量子纠错目标，"
        "持续强化公司QCCD（量子电荷耦合器件）技术路线的全栈能力。"
        "本轮距上一轮融资落地不足四个月。公司孵化自中国科大郭光灿院士团队，"
        "是国内QCCD离子阱量子计算领军企业。（来源：投中网 2026-08-03）"
    ),
    (
        "问天量子完成6亿元B轮融资，加速量子科技产业化布局",
        "https://www.chinaventure.com.cn/news/114-20260716-392305.html",
        date(2026, 7, 16),
        "安徽问天量子科技股份有限公司完成B轮融资，获得6亿元资金注入，"
        "新进投资方包括中天汇富、合凡资产、延福基金等多家机构。"
        "资金主要用于核心技术的规模化商用、量子随机数芯片的量产扩能，"
        "以及面向人工智能时代的量子AI融合产品研发。"
        "问天量子成立于2009年，是我国首批从事量子信息技术产业化的国家级高新技术企业、"
        "国家级专精特新重点小巨人企业，也是密标委指定的量子密码标准制订工作组牵头单位，"
        "拥有量子保密通信领域200余项核心知识产权，是地方后备上市企业之一。（来源：投中网 2026-07-16）"
    ),
    (
        "不筹量子完成数亿元A轮融资，国泰海通、金鼎资本、中芯聚源等联合投资",
        "https://shangdaovc.icoc.me/h-nd-14465.html",
        date(2026, 8, 15),
        "上海不筹量子科技有限公司完成数亿元A轮融资，由国泰海通、金鼎资本、中芯聚源、"
        "上海科创集团、头部产投方、中信旗下基金、TCL创投、金浦智能、道禾长期投资、"
        "元禾控股、杨浦梦航、上海产业知识产权基金、川创投等机构及产业方联合投资，"
        "高鹄资本担任本轮长期融资财务顾问。"
        "公司2025年在上海成立，脱胎于复旦大学中性原子量子计算实验室，"
        "主攻中性原子量子计算整机研发与落地转化，布局物理层、纠错层、算法层全栈研发体系，"
        "覆盖冷原子调控、光镊阵列、量子测控、软件栈等关键环节，"
        "已完成万级光镊阵列关键技术验证，推出量筹一号原子量子人工智能基座。"
        "创始人兼CEO为李晓鹏教授。（来源：商道创投网 2026-08-15）"
    ),
    (
        "国盛量子完成数千万元战略融资，国家电网旗下国网创投基金投资",
        "https://www.stcn.com/article/detail/4078901.html",
        date(2026, 8, 16),
        "安徽省国盛量子科技有限公司完成数千万元战略融资，"
        "投资机构为国家电网旗下的国网创投基金。"
        "国盛量子是国内首家专注量子工业测量的科技企业，"
        "本轮融资将用于金刚石NV（氮-空位）色心量子测量技术迭代、"
        "量子传感产品矩阵扩容与产能建设，并加速技术在工业场景的产业化落地。"
        "这是央企资本在量子科技赛道的又一布局，与此前国网信通助建的皖电量子计算云实验平台等形成呼应。"
        "（来源：证券时报 2026-08-16）"
    ),
    (
        "国仪量子科创板IPO上市（688828.SH），量子精密测量第一股登陆A股",
        "https://www.crhc.cn/rmzx/xwzx/ssqydt/2026/8/fad9261f06624ade8b44c02cdef21315.htm",
        date(2026, 8, 11),
        "8月11日，国仪量子技术（合肥）股份有限公司在上海证券交易所科创板上市，"
        "股票代码688828.SH，成为A股市场量子精密测量领域第一股。"
        "国仪量子成立于2016年，是我国领先的高端科学仪器企业，专注研发高端科学仪器，"
        "聚焦量子科技、材料科学、化学化工、生物医药、先进制造等领域，"
        "提供高端科学仪器装备和以增强型量子传感器为代表的核心关键器件及解决方案。"
        "国新基金旗下国风投基金、国风投生物基金自2021年起投资国仪量子，并于2025年追加投入，"
        "国新基金将持续发挥投资生态圈与产业资源优势，助力国仪量子加强自主创新和产业化能力。"
        "（来源：中国国新 2026-08-11）"
    ),
    (
        "伏曦量子完成天使轮及天使+轮融资，宁德时代领投",
        "https://www.c114.com.cn/quantum/5285/a1312590.html",
        date(2026, 6, 24),
        "量子算法初创公司上海伏曦量子科技有限公司宣布连续完成天使及天使+轮融资。"
        "领投方为全球动力电池龙头宁德时代，小苗朗程、五源资本、德迅投资、慕华科创、启盈同创跟投。"
        "伏曦量子成立于2026年4月，位于上海张江，定位为面向产业研发的量子应用算力平台，"
        "目标是打通产业问题、量子建模、算法求解、硬件执行、结果验证的完整链路，"
        "让量子计算从科研成果和硬件指标展示真正进入企业研发流程。"
        "公司由赵琦博士领衔创立，赵琦曾任香港大学助理教授，"
        "是全球量子模拟算法领域的代表性青年科学家。（来源：C114通信网 2026-06-24）"
    ),
]


def extract_domain(url):
    return urlparse(url).netloc.replace('www.', '')


def main():
    inserted = updated = skipped = funding_tagged = 0

    for i, (title, url, orig_date, content_detail) in enumerate(ALL_ARTICLES, 1):
        domain = extract_domain(url)
        full_content = content_detail + '\n\n🤖 本文由 AI 摘要生成，原文见链接'

        session = get_session()
        try:
            existing = session.query(Article).filter(
                Article.title == title,
                Article.page_type == 'websearch'
            ).first()
        finally:
            session.close()

        if existing:
            print(f"[{i}/{len(ALL_ARTICLES)}] SKIP (已存在)  {title[:50]}")
            skipped += 1
            continue

        funding = tag_funding(title, full_content)
        tags = {
            'weekly': ['资本运作'],
            'search_tags': ['国内投融资', 'websearch']
        }
        tags = merge_funding_tags(tags, funding)

        if funding:
            funding_tagged += 1
            print(f"[{i}/{len(ALL_ARTICLES)}] INSERT  {title[:50]}")
            print(f"         🏢 {funding.get('company','?')} | 💰 {funding.get('round','?')} | 📊 {funding.get('amount_text','?')}")
            invs = funding.get('investors', [])
            if invs:
                print(f"         👥 投资方: {', '.join(sorted(invs))}")
        else:
            print(f"[{i}/{len(ALL_ARTICLES)}] INSERT  {title[:50]}")
            print(f"         ⚠️ funding tagger 未识别到结构化字段")

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
    print(f"入库完成: 新增 {inserted}  更新 {updated}  跳过 {skipped}  funding打标 {funding_tagged}")


if __name__ == '__main__':
    main()
