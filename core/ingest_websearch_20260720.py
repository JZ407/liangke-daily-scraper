"""
批量入库 WebSearch 投融资搜索结果 — 2026-07-20 批次
3 个新增 + 1 个日期修复
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import insert_or_update_article, article_exists, get_session, Article
from funding_tagger import tag_funding, merge_funding_tags
from urllib.parse import urlparse
from datetime import date

# ── 新增入库 ───────────────────────────────────────────────────────────
# 格式: (title, url, date, content_summary)

NEW_ARTICLES = [
    (
        "问天量子完成6亿元B轮融资，加速量子科技产业化布局",
        "https://www.chinaventure.com.cn/news/114-20260716-392305.html",
        date(2026, 7, 15),
        "安徽问天量子科技股份有限公司完成6亿元B轮融资。"
        "投资方包括中天汇富、合凡资产、延福基金、证通电子、金舵投资、海南晴澜、海南量启等。"
        "资金将用于核心技术规模化商用、量子随机数芯片量产扩能、量子AI融合产品研发。"
        "问天量子成立于2009年，总部位于安徽芜湖，是国家级专精特新小巨人企业，"
        "密标委量子密码标准制订工作组牵头单位，拥有量子保密通信领域200余项核心知识产权，"
        "搭建起量子安全、量子测量、量子芯片、后量子加密、量子科研教学五大核心板块的全栈式产品体系。"
    ),
    (
        "伏曦量子成立两月完成天使及天使+轮融资，宁德时代领投",
        "https://www.c114.com.cn/4app/3542/a1312591.html",
        date(2026, 6, 24),
        "上海伏曦量子科技有限公司成立于2026年4月，位于上海张江科学城，由赵琦博士领衔创立。"
        "公司定位为面向产业研发的量子应用算力平台。"
        "成立仅两个月，伏曦量子连续完成天使轮及天使+轮融资，"
        "领投方为宁德时代（持续加注），跟投方包括小苗朗程、五源资本、德迅投资、慕华科创、启盈同创等。"
        "赵琦博士此前任香港大学助理教授，是全球量子模拟算法领域代表性青年科学家，"
        "担任科技创新2030量子通信与量子计算机国家科技重大专项青年项目负责人，"
        "入选MIT Technology Review亚太区2024年度35岁以下科技创新35人。"
        "公司在Nature等顶级期刊发表论文58篇，累计引用超4400次。"
        "伏曦量子专注于纯软件算法平台，不绑定特定硬件架构，"
        "支持超导、离子阱与光量子三种主流硬件接口的统一编译。"
    ),
    (
        "中科量枢完成数千万元天使及天使+轮融资，打造量子计算操作系统",
        "https://www.163.com/dy/article/L29F9SMA05568W0A.html",
        date(2026, 7, 1),
        "中科量枢（北京）科技有限公司源自中科院计算所，成立于2026年3月。"
        "公司于成立4个月内完成天使轮及天使+轮融资，各数千万元。"
        "投资方包括中科创星、联想创投、百度风投等。"
        "公司打造面向超导、中性原子、离子阱等异构量子硬件的天枢操作系统，"
        "旨在解决量子计算硬件异构带来的编程和调度难题，"
        "提供统一的量子计算软件栈和编程框架。"
        "这是量子计算操作系统赛道的重要布局，标志着量子软件基础设施层获资本关注。"
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
            'search_tags': ['国内投融资', 'websearch']
        }

        # Auto-tag funding
        full_content = content + '\n\n🤖 本文由 AI 摘要生成，原文见链接'
        funding = tag_funding(title, full_content)
        if funding:
            tags = merge_funding_tags(tags, funding)

        try:
            insert_or_update_article(
                reference_url=url,
                liangke_url=url,
                title=title,
                content=full_content,
                original_date=article_date,
                liangke_date=article_date,
                source_domain=domain,
                reference_title=title,
                tags=tags,
                page_type='websearch'
            )
            print(f'OK: {title[:60]}')
            ingested += 1
        except Exception as e:
            print(f'ERROR: {title[:60]} -> {e}')

    print(f'\n=== 入库完成: {ingested} 新增, {skipped} 跳过 ===')
    session.close()

def fix_date():
    """修复太一量生 Pre-A (id=1372) 的 original_date=NULL"""
    session = get_session()
    article = session.query(Article).filter(Article.id == 1372).first()
    if article:
        if article.original_date is None:
            article.original_date = date(2026, 6, 17)
            article.liangke_date = date(2026, 6, 17)
            session.commit()
            print(f'FIXED: id=1372 original_date -> 2026-06-17')
        else:
            print(f'OK: id=1372 date already set ({article.original_date})')
    else:
        print(f'MISSING: id=1372 not found')
    session.close()

if __name__ == '__main__':
    ingest()
    print()
    fix_date()
