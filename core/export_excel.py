"""
一键导出量科网新闻到 Excel（标签展开格式）
用法: python export_excel.py
"""
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill
from db import get_session, Article
from datetime import date
import os


def run(output_path=None):
    session = get_session()
    articles = session.query(Article).order_by(Article.id).all()
    if not articles:
        print("No articles found in database.")
        return

    max_tags = max((len(a.tags) if isinstance(a.tags, list) else 0) for a in articles)

    wb = Workbook()
    ws = wb.active
    ws.title = '量科网新闻'

    base_headers = ['ID', '标题', '量科网链接', '参考链接', '原始日期', '量科网日期', '来源域名', '正文', '抓取次数']
    # Flatten tags dict into columns
    tag_key_headers = ['周报标签', '检索标签', '投融资标签', '图谱-机构', '图谱-技术']
    headers = base_headers + tag_key_headers + [f'标签{i+1}' for i in range(max_tags)]
    ws.append(headers)

    header_fill = PatternFill(start_color='366092', end_color='366092', fill_type='solid')
    header_font = Font(color='FFFFFF', bold=True)
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)

    for a in articles:
        ref_url = a.reference_url if a.reference_url != a.liangke_url else ''
        row = [
            a.id,
            a.title,
            a.liangke_url,
            ref_url,
            a.original_date.strftime('%Y-%m-%d') if a.original_date else '',
            a.liangke_date.strftime('%Y-%m-%d') if a.liangke_date else '',
            a.source_domain or '',
            a.content or '',
            a.fetch_count,
        ]
        tags = a.tags or {}
        if isinstance(tags, list):
            # Old format: list of strings
            flat_tags = tags
            weekly_str = ''
            search_str = ''
            fund_str = ''
            kg_inst = ''
            kg_tech = ''
        elif isinstance(tags, dict):
            # New format: dict with namespaces
            flat_tags = []
            weekly_str = '、'.join(tags.get('weekly', []))
            search_str = '、'.join(tags.get('search_tags', []))
            # Funding — single summary column
            funding = tags.get('funding', {})
            if isinstance(funding, dict) and funding.get('is_funding'):
                parts = []
                if funding.get('round'): parts.append(funding['round'])
                if funding.get('company'): parts.append(funding['company'])
                if funding.get('amount_text'): parts.append(funding['amount_text'])
                invs = funding.get('investors', [])
                if invs: parts.append('、'.join(invs[:5]))
                fund_str = ' | '.join(parts)
            else:
                fund_str = ''
            # Knowledge Graph
            kg = tags.get('knowledge_graph', {})
            if isinstance(kg, dict):
                kg_inst = '、'.join(kg.get('institutions', []) or [])
                kg_tech = '、'.join(kg.get('technologies', []) or [])
            else:
                kg_inst = kg_tech = ''
        else:
            flat_tags = []
            weekly_str = search_str = fund_str = kg_inst = kg_tech = ''

        row = [
            a.id,
            a.title,
            a.liangke_url,
            ref_url,
            a.original_date.strftime('%Y-%m-%d') if a.original_date else '',
            a.liangke_date.strftime('%Y-%m-%d') if a.liangke_date else '',
            a.source_domain or '',
            a.content or '',
            a.fetch_count,
            weekly_str,
            search_str,
            fund_str,
            kg_inst,
            kg_tech,
        ]
        row.extend(flat_tags)
        tag_count = len(tags) if isinstance(tags, list) else 0
        row.extend([''] * (max_tags - tag_count))
        ws.append(row)

    ws.column_dimensions['A'].width = 6
    ws.column_dimensions['B'].width = 50
    ws.column_dimensions['C'].width = 40
    ws.column_dimensions['D'].width = 40
    ws.column_dimensions['E'].width = 12
    ws.column_dimensions['F'].width = 12
    ws.column_dimensions['G'].width = 20
    ws.column_dimensions['H'].width = 60
    ws.column_dimensions['I'].width = 10
    # Tag key columns (J-Q)
    key_col_widths = [10, 18, 30, 18, 18]
    for i, w in enumerate(key_col_widths):
        col = chr(ord('J') + i)
        ws.column_dimensions[col].width = w
    # Legacy flat tag columns
    for i in range(max_tags):
        col_idx = 9 + len(tag_key_headers) + i  # J=9, plus key cols
        if col_idx < 26:
            col = chr(ord('A') + col_idx)
        else:
            col = chr(ord('A') + (col_idx // 26) - 1) + chr(ord('A') + (col_idx % 26))
        ws.column_dimensions[col].width = 15

    ws.freeze_panes = 'A2'
    ws.auto_filter.ref = ws.dimensions

    if output_path is None:
        output_path = f'量科网新闻_标签展开_{date.today().strftime("%Y%m%d")}.xlsx'

    wb.save(output_path)
    print(f'Exported {len(articles)} articles to: {output_path}')


if __name__ == '__main__':
    run()
