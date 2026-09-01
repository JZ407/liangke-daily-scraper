"""
批量入库 WebSearch 投融资搜索结果 — 2026-08-05 批次
2 个新增事件
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import insert_or_update_article, get_session, Article
from funding_tagger import tag_funding, merge_funding_tags
from urllib.parse import urlparse
from datetime import date

# ── 新增入库 ───────────────────────────────────────────────────────────
# 格式: (title, url, date, content_summary)

NEW_ARTICLES = [
    (
        "幻码跃迁完成数千万元种子轮融资，打造量子×AI融合创新的量子计算基础设施",
        "https://www.chinaventure.com.cn/news/114-20260714-392270.html",
        date(2026, 7, 14),
        "上海幻码跃迁量子科技有限公司宣布完成数千万元种子轮融资。"
        "本轮由L2F光源创业者基金领投，云启资本、小苗朗程共同参与，光源资本同时担任孵化方。"
        "资金将用于核心人才团队建设、量子计算全栈软件研发、量子AI技术研发和跨平台量子计算产业生态建设。"
        "公司聚焦量子计算与AI融合创新，定位为国产量子计算系统级软件与应用解决方案提供商，"
        "通过"底层软件栈+上层算法应用+AI驱动研发工具"的全栈路径，将异构量子硬件能力转化为产业侧可调用的新型计算能力。"
        "团队核心成员来自QuEra、百度、哈佛大学、香港科技大学等头部企业与高校，"
        "覆盖超导、中性原子、离子阱、光量子等主流硬件路线。"
        "CEO幺宏顺曾参与百度PaddleQuantum核心模块研发；首席科学家王鑫曾任百度量子计算研究所Tech Leader；"
        "首席科学家刘金国为哈佛大学Lukin组博士后、QuEra全职顾问。"
        "公司已与多家量子硬件厂商展开合作，在金融优化、生物医药等高价值领域推进场景验证。"
    ),
    (
        "逻辑比特科技发布超导量子计算云平台，官宣数亿元A轮融资",
        "https://www.stcn.com/article/detail/4008738.html",
        date(2026, 7, 9),
        "逻辑比特科技（杭州）于2026年7月9日正式发布超导量子计算云平台，并同步官宣完成数亿元A轮融资。"
        "本轮由康君资本、混沌投资（葛卫东旗下）联合领投。"
        "资金将用于下一代超导量子芯片研发、自动化产线建设、云平台能力扩展及国际化人才引进。"
        "逻辑比特科技成立于2022年，是国内超导量子计算赛道的新锐力量，成立以来已完成6轮融资。"
        "公司聚焦超导量子芯片与整机系统开发，已构建从芯片设计、制备到系统集成的全栈能力。"
        "值得注意的是，知名投资人葛卫东通过混沌投资参与此轮融资，"
        "其此前在商品期货领域的量化投资经验与量子计算的契合点受到市场关注。"
    ),
]

def extract_domain(url):
    return urlparse(url).netloc.replace('www.', '')

def ingest():
    session = get_session()
    ingested = 0
    skipped = 0

    for title, url, article_date, content in NEW_ARTICLES:
        # Dedup by title
        existing = session.query(Article).filter(
            Article.title == title,
            Article.page_type == 'websearch'
        ).first()
        if existing:
            print(f'SKIP (exists): {title[:60]}')
            skipped += 1
            continue

        domain = extract_domain(url)
        tags = {
            'weekly': ['资本运作'],
            'search_tags': ['国内投融资', 'websearch'],
            'funding': {},
        }

        # Insert
        article = Article(
            title=title,
            content=content,
            content_edited=content,
            liangke_date=article_date.isoformat(),
            original_date=article_date.isoformat(),
            page_type='websearch',
            source_domain=domain,
            reference_url=url,
            liangke_url=url,
            tags=tags,
        )
        session.add(article)
        session.flush()

        # Apply funding tagger
        try:
            tag_funding(article, commit=False)
            merge_funding_tags(article, commit=False)
            session.flush()
            session.refresh(article)
        except Exception as e:
            print(f'WARN: funding tagger failed for {title[:40]}: {e}')

        session.commit()
        print(f'OK: {title[:60]}')
        ingested += 1

    print(f'\nDone: {ingested} new, {skipped} skipped')

if __name__ == '__main__':
    ingest()
