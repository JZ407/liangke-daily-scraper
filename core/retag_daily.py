"""Re-tag all daily articles using the new 5-category LLM prompt.

Uses the same prompt template from scrape_daily.py's _llm_classify_batch.
"""
import sys, os, re, json, time
from datetime import datetime
import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db import get_session, Article

BATCH_SIZE = 10
DELAY = 1  # seconds between batches

CATEGORIES = ['资本运作', '产品动态', '企业资讯', '科技前沿', '宏观态势']


def _build_prompt(text_list: str) -> str:
    """Build the classification prompt — same logic as scrape_daily._llm_classify_batch."""
    return f"""将以下量子科技新闻分类到五大类别之一。

优先级规则：资本运作 > 企业资讯 > 产品动态 > 科技前沿 > 宏观态势。

==== 分类定义（含正例和反例）====

1. 资本运作 —— 钱和所有权的流动
   【属于】融资（A轮/B轮/种子轮）、收购并购、IPO上市、财报营收估值、政府资助/拨款给具体企业
   【不属于】公司发新产品→产品动态 | 公司跟大学合作研究→企业资讯 | 政府发布行业政策→宏观态势
   示例：IQM获芬兰Ilmarinen投资 ✓ | 英国发布量子战略 ✗（→宏观态势）

2. 产品动态 —— 能买能用能部署的东西
   【属于】新芯片/计算机/软件/云服务发布、性能指标突破（量子体积/保真度/量子比特数）、商用落地/量产/客户部署
   【不属于】论文里提了新算法→科技前沿 | 公司说"计划推出"但无实物→企业资讯
   示例：微软发布Majorana 2芯片 ✓ | 论文报道高保真度实验→科技前沿

3. 企业资讯 —— 公司组织层面的变化
   【属于】合作签约/战略联盟、CEO/CTO/高管任命、办公室扩建/裁员、公司战略/愿景宣布
   【不属于】合作研究成果发表→科技前沿 | 获投资→资本运作 | 发布产品→产品动态
   示例：深圳市委调研中科酷原 ✓ | 两家公司联合发表Nature论文 ✗（→科技前沿）

4. 科技前沿 —— 知识层面的推进，不涉及商业产品
   【属于】学术论文（Nature/Science/PRL/arXiv预印本）、实验突破/新物理现象、新算法/新理论方法
   【不属于】量子计算机量产→产品动态 | 行业白皮书→宏观态势 | 某公司实验室成果宣称"可用于产品"→产品动态

5. 宏观态势 —— 影响整个行业，而非单个公司
   【属于】国家量子战略/政策法规、行业路线图、市场研究报告、国际竞争格局、人才教育、行业标准发布
   【不属于】某公司获政府资助→资本运作 | 某公司产品路线图→产品动态 | 某公司白皮书→企业资讯

==== 关键边界规则 ====
- 政府给钱：给具体公司=资本运作，发布行业政策=宏观态势
- 论文研究：学术发表=科技前沿，为产品造势=产品动态
- 合作联合：签合作协议=企业资讯，发表联合论文=科技前沿
- arXiv预印本：一律归科技前沿

每条新闻标题后附有正文前400字（| 分隔）。每篇只输出一个类别。输出格式：编号:类别

{text_list}

输出："""


def get_llm_client():
    import yaml
    sys.path.insert(0, 'D:/Claude_code/rag_system/rag_system')
    cfg = yaml.safe_load(open('D:/Claude_code/rag_system/config.yaml', encoding='utf-8'))
    llm_cfg = cfg['llm']
    from llm_client import LLMClient
    return LLMClient(provider='openai', api_key=llm_cfg['api_key'],
                     api_base=llm_cfg['api_base'], model=llm_cfg['model'],
                     max_tokens=2048, timeout=180)


def classify_batch(client, articles):
    """Send a batch to LLM, return dict of {index: category}."""
    lines = []
    for i, a in enumerate(articles):
        content_preview = ((a.content or '').replace('\n', ' ')[:300]).strip()
        lines.append(f"{i+1}. {a.title[:120]} | {content_preview}")

    text_list = '\n'.join(lines)
    prompt = _build_prompt(text_list)

    try:
        response = client.chat([{'role': 'user', 'content': prompt}])
        results = {}
        for line in response.strip().split('\n'):
            m = re.match(r'(\d+)[：:]\s*(\S+)', line.strip())
            if m:
                idx = int(m.group(1)) - 1
                cat = m.group(2).strip()
                if cat in CATEGORIES:
                    results[idx] = cat
        return results
    except Exception as e:
        print(f"  LLM error: {e}")
        return {}


def main():
    client = get_llm_client()
    session = get_session()

    # Get all articles
    articles = session.query(Article).order_by(Article.id).all()
    total = len(articles)
    print(f"Total articles: {total}")

    changed = 0
    unchanged = 0
    errors = 0

    for batch_start in range(0, total, BATCH_SIZE):
        batch = articles[batch_start:batch_start + BATCH_SIZE]
        batch_end = min(batch_start + BATCH_SIZE, total)
        print(f"\nBatch {batch_start+1}-{batch_end}/{total}")

        results = classify_batch(client, batch)
        if not results:
            errors += len(batch)
            print("  All failed, skipping batch")
            time.sleep(DELAY)
            continue

        for idx, cat in results.items():
            if idx >= len(batch):
                continue
            art = batch[idx]

            # Get current tags
            tags = art.tags
            if isinstance(tags, str):
                try:
                    tags = json.loads(tags)
                except Exception:
                    tags = {}

            if not isinstance(tags, dict):
                tags = {}

            old_weekly = tags.get('weekly', [])
            old_cat = old_weekly[0] if old_weekly else '?'
            if old_cat == cat:
                unchanged += 1
            else:
                print(f"  [{art.id}] {old_cat} -> {cat} | {art.title[:60].encode('gbk', errors='replace').decode('gbk', errors='replace')}")
                tags['weekly'] = [cat]
                art.tags = tags
                changed += 1

        try:
            session.commit()
        except Exception as e:
            print(f"  Commit error: {e}")
            session.rollback()
            errors += len(batch)

        print(f"  Progress: {changed} changed, {unchanged} unchanged, {errors} errors")
        time.sleep(DELAY)

    session.close()
    print(f"\n{'='*50}")
    print(f"Re-tagging complete:")
    print(f"  Changed:   {changed}")
    print(f"  Unchanged: {unchanged}")
    print(f"  Errors:    {errors}")
    print(f"  Total:     {total}")
    print(f"{'='*50}")


if __name__ == '__main__':
    main()
