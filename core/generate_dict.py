"""Generate category_dict.yaml from existing articles using LLM.

Strategy:
1. Collect representative articles per category
2. For each category, ask LLM to suggest keywords with weights
3. Also ask for negative keywords (misleading words that look like this category)
4. Assemble into unified YAML dictionary
"""
import sys, os, re, json, yaml
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.db import get_session, Article

# Load LLM client (fixed version)
sys.path.insert(0, 'D:/Claude_code/rag_system/rag_system')
from llm_client import LLMClient

cfg = yaml.safe_load(open('D:/Claude_code/rag_system/config.yaml', encoding='utf-8'))
llm_cfg = cfg['llm']
client = LLMClient(provider='openai', api_key=llm_cfg['api_key'],
                   api_base=llm_cfg['api_base'], model=llm_cfg['model'],
                   max_tokens=4096, timeout=180)

CATEGORIES = ['资本运作', '科技前沿', '产品动态', '企业资讯', '宏观态势']

def collect_samples(session, samples_per_cat=25):
    """Collect representative titles per category."""
    samples = {cat: [] for cat in CATEGORIES}
    for cat in CATEGORIES:
        # Get articles where weekly tag = cat, preferring newer ones
        rows = session.query(Article).filter(Article.tags != None).order_by(Article.id.desc()).all()
        for r in rows:
            if len(samples[cat]) >= samples_per_cat:
                break
            tags = r.tags if isinstance(r.tags, dict) else (json.loads(r.tags) if r.tags else {})
            weekly = tags.get('weekly', [])
            if weekly and weekly[0] == cat:
                content_snippet = ((r.content or '').replace('\n', ' ')[:200]).strip()
                samples[cat].append(f"{r.title} | {content_snippet}")
    return samples


def generate_category_dict(samples):
    """Ask LLM to generate keywords per category, one category at a time."""
    all_results = {}

    for cat in CATEGORIES:
        print(f"\n{'='*50}")
        print(f"Processing: {cat} ({len(samples[cat])} samples)")
        print(f"{'='*50}")

        sample_text = '\n'.join(f"{i+1}. {s[:150]}" for i, s in enumerate(samples[cat]))

        prompt = f"""分析以下{len(samples[cat])}条量子科技新闻标题（它们都被归类为"{cat}"）。

请提取关键词并给出权重建议。输出格式严格为 YAML：

```yaml
{cat}:
  strong_signals:          # 这些模式命中标题→直接判定为该类，不需要打分
    - pattern: "正则1"
    - pattern: "正则2"
  positives:               # 正向关键词 [词: 权重(1-5)]
    关键词1: 5              # 5=一锤定音, 4=强信号, 3=中等, 2=弱信号, 1=辅助
    关键词2: 3
  negatives:               # 负向词 [词: 扣分(1-5)]
    误导词1: -3             # 看起来像{cat}但其实不是，扣分
    误导词2: -2
```

要求：
1. strong_signals 是正则模式，命中后直接判定，不需要打分。控制在3-5条高置信度的
2. positives 选10-15个最有区分力的关键词，权重1-5（5=仅凭这个词就能判定）
3. negatives 选3-5个误导词——看标题像{cat}但其实属于其他类别的，标注扣分值和应归属的类别

样本标题：
{sample_text}

请只输出YAML，不要加任何解释。"""

        try:
            response = client.chat([{'role': 'user', 'content': prompt}])
            # Extract YAML block
            yaml_match = re.search(r'```(?:yaml)?\s*\n(.*?)```', response, re.DOTALL)
            if yaml_match:
                yaml_text = yaml_match.group(1)
            else:
                yaml_text = response
            # Clean up
            yaml_text = yaml_text.strip()
            if yaml_text.startswith('yaml\n'):
                yaml_text = yaml_text[5:]
            cat_data = yaml.safe_load(yaml_text)
            if cat_data:
                all_results.update(cat_data)
                print(f"  → Got {len(cat_data.get(cat, {}).get('positives', {}))} positive keywords")
        except Exception as e:
            print(f"  ERROR: {e}")
            all_results[cat] = {'strong_signals': [], 'positives': {}, 'negatives': {}}

    return all_results


def main():
    session = get_session()
    samples = collect_samples(session, samples_per_cat=25)

    for cat in CATEGORIES:
        print(f"{cat}: {len(samples[cat])} samples")

    print("\n--- Asking LLM to generate dictionary ---")
    cat_dict = generate_category_dict(samples)

    # Add priority metadata
    final = {'categories': {}}
    for i, cat in enumerate(CATEGORIES):
        entry = cat_dict.get(cat, {'strong_signals': [], 'positives': {}, 'negatives': {}})
        entry['priority'] = i + 1
        final['categories'][cat] = entry

    # Write
    output_path = os.path.join(os.path.dirname(__file__), 'category_dict.yaml')
    with open(output_path, 'w', encoding='utf-8') as f:
        yaml.dump(final, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    print(f"\nDictionary saved to: {output_path}")
    session.close()


if __name__ == '__main__':
    main()
