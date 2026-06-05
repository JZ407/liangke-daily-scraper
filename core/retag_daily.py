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
    """Build the classification prompt — v2.0 with strict priority, channel rules, funding split."""
    return f"""将以下量子科技新闻分类到五大类别之一。

==== 判定优先级（严格按此顺序，多标签冲突时唯一归类）====
资本运作 > 科技前沿 > 产品动态 > 企业资讯 > 宏观态势

==== 分类定义 ====

1. 资本运作 —— 钱和所有权的流动
   【属于】企业融资（A/B/C轮、IPO等）、收购并购、财报营收估值、政府资助/拨款/补贴给具体企业、企业重大资本支出（建厂、百亿投资，且资金是标题核心信息）
   【不属于】政府面向全行业的资助计划→宏观态势 | 政府资助大学/研究机构→宏观态势或科技前沿 | 资金只是背景信息的技术/产品/合作新闻→按内容本质归类

2. 科技前沿 —— 知识层面的推进，不涉及商业产品
   【属于】学术论文（Nature/Science/PRL/arXiv预印本）、实验突破/新物理现象、新算法/新理论、学术会议成果、学术渠道发布的开源工具
   【不属于】商业产品→产品动态 | 行业白皮书→宏观态势 | 注意：公司新闻稿包装的研究成果，如果本质是学术预印本/论文，仍归科技前沿

3. 产品动态 —— 能买能用能部署的东西
   【属于】新芯片/整机/软件/云服务正式发布可用、通过商业渠道宣布的性能突破（产品发布会、公司新闻稿、官网博客）、商用落地/量产/客户部署/云平台上线、产品认证获批、公司具体产品路线图（含时间节点/性能目标）
   【不属于】论文中报告的性能指标→科技前沿 | 实验室原型机未开放→科技前沿 | 纯理论算法→科技前沿 | 通过arXiv/Nature等学术渠道发布的成果→科技前沿

4. 企业资讯 —— 公司组织层面的变化
   【属于】高管任命（CEO/CTO/VP等，一律归此）、战略合作签约/MoU/联盟加入（无具体成果产出）、办公室/研发中心扩建裁员、公司战略愿景品牌重塑、企业回应辟谣公关声明法律诉讼
   【不属于】合作研究成果发表→科技前沿 | 合作推出产品→产品动态 | 获投资→资本运作

5. 宏观态势 —— 影响整个行业，而非单个公司
   【属于】国家量子战略/政策法规/出口管制、行业路线图（政府/联盟发布）、市场研究报告/竞争格局、人才教育（大学专业/学院）、国际科技合作格局、政府资助给大学/研究机构用于平台建设或产业布局、科普/行业综述
   【不属于】某公司获政府资助→资本运作 | 某公司产品路线图→产品动态 | 单个学术成果→科技前沿

==== 关键边界规则 ====
- 资金核心原则：只有资金数额/融资轮次/估值/所有权变更是新闻核心时才归资本运作，否则按内容本质归类
- 政府资助分流：给企业→资本运作；给大学/研究机构→宏观态势（强调产业布局）或科技前沿（强调具体科研）
- 人事变动：无论技术还是管理岗位，一律企业资讯
- 发布渠道优先：arXiv/Nature/Science等学术渠道→科技前沿；PR/公司新闻室→产品动态
- 常规声明不转移：论文末尾的"有望应用于量子计算"等不改变科技前沿属性
- 合作区分：签合作协议/MoU（无成果产出）→企业资讯；合作发表论文/研发成功→科技前沿

==== 速查对照 ====
企业获融资 → 资本运作 | 企业发新芯片（含型号） → 产品动态 | 企业任命CTO → 企业资讯
Nature论文 → 科技前沿 | 国家量子五年规划 → 宏观态势 | 政府拨款IBM建厂 → 资本运作
政府拨款大学建实验室 → 宏观态势 | 公司大学签MoU → 企业资讯 | 公司大学联合发表论文 → 科技前沿
arXiv论文 → 科技前沿 | 企业回应辟谣 → 企业资讯 | 公司产品路线图（含时间/指标） → 产品动态

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
