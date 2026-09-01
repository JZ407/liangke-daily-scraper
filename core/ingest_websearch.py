"""WebSearch 投融资事件批量入库（参数化正典脚本，替代 5 个历史日期变体）。

用法:
  C:/Python314/python.exe -X utf8 ingest_websearch.py --input batch_20260901.json

输入 JSON 格式（按 liangke_daily/docs/websearch投融资检索指南.md 入库规则）:
[
  {"title": "幺正量子完成数亿元A轮融资", "url": "https://...", "date": "2026-08-03", "content": "..."}
]

入库逻辑: 按 title+page_type='websearch' 去重 → funding_tagger 打标（三分字典）
→ insert_or_update_article 入库。
"""
import argparse
import json
import os
import sys
from datetime import date
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import insert_or_update_article, get_session, Article
from funding_tagger import tag_funding, merge_funding_tags


def extract_domain(url):
    return urlparse(url).netloc.replace('www.', '')


def load_articles(input_path):
    """从 JSON 文件加载待入库文章列表，返回 [(title, url, date, content), ...]"""
    with open(input_path, 'r', encoding='utf-8') as f:
        raw = json.load(f)
    articles = []
    for item in raw:
        title = (item.get('title') or '').strip()
        url = (item.get('url') or '').strip()
        date_str = (item.get('date') or '').strip()
        content = (item.get('content') or '').strip()
        if not (title and url and content):
            print(f'[WARN] 跳过缺字段条目: {item}')
            continue
        try:
            orig_date = date.fromisoformat(date_str)
        except ValueError:
            print(f'[WARN] 跳过日期格式错误条目: {title[:40]}（{date_str}）')
            continue
        articles.append((title, url, orig_date, content))
    return articles


def main():
    parser = argparse.ArgumentParser(description='WebSearch 投融资事件批量入库')
    parser.add_argument('--input', required=True, help='待入库文章 JSON 文件路径')
    args = parser.parse_args()

    articles = load_articles(args.input)
    if not articles:
        print('[FAIL] 没有可入库的文章')
        sys.exit(1)
    print(f'[INFO] 加载 {len(articles)} 条文章')

    inserted = updated = skipped = funding_tagged = 0
    for i, (title, url, orig_date, content_detail) in enumerate(articles, 1):
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
            print(f"[{i}/{len(articles)}] SKIP (已存在)  {title[:50]}")
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
            print(f"[{i}/{len(articles)}] INSERT  {title[:50]}")
            print(f"         🏢 {funding.get('company','?')} | 💰 {funding.get('round','?')} | 📊 {funding.get('amount_text','?')}")
            invs = funding.get('investors', [])
            if invs:
                print(f"         👥 投资方: {', '.join(sorted(invs))}")
        else:
            print(f"[{i}/{len(articles)}] INSERT  {title[:50]}")
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
