"""Category scorer using unified dictionary with positive/negative weighting.

Usage:
    scorer = CategoryScorer('category_dict.yaml')
    result = scorer.classify(title, content)
    # result: '资本运作' | '科技前沿' | ... | None (low confidence → LLM)
"""
import re
import yaml
import os
from typing import Dict, Optional
import jieba

# Load dictionary relative to this file
DICT_PATH = os.path.join(os.path.dirname(__file__), 'category_dict.yaml')

# Minimum score difference required to make a decision
# If top score - second score < MIN_GAP, return None (ambiguous → LLM)
MIN_GAP = 2
# If top score < MIN_CONFIDENCE, return None (too weak → LLM)
MIN_CONFIDENCE = 3


class CategoryScorer:
    def __init__(self, dict_path: str = None):
        dict_path = dict_path or DICT_PATH
        with open(dict_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        self.categories = self.config['categories']
        # Sort by priority for tie-breaking
        self._cat_order = sorted(self.categories.keys(),
                                 key=lambda c: self.categories[c].get('priority', 99))

    def classify(self, title: str, content: str = '', reference_url: str = '') -> Optional[str]:
        """Classify an article. Returns category name or None if uncertain."""
        title = title or ''
        content = content or ''
        title_lower = title.lower()
        text_lower = title_lower + ' ' + (content[:500] or '').lower()

        # Phase 0: arXiv URL → force 科技前沿
        if reference_url and 'arxiv.org' in reference_url.lower():
            return '科技前沿'

        # Phase 1: Strong signals (short-circuit)
        for cat, cfg in self.categories.items():
            for sig in cfg.get('strong_signals', []):
                pattern = sig.get('pattern', '')
                scope = sig.get('scope', 'any')
                search_in = title_lower if scope == 'title' else text_lower
                try:
                    if re.search(pattern, search_in, re.IGNORECASE):
                        return cat
                except re.error:
                    continue

        # Phase 2: Positive scoring
        scores = {cat: 0.0 for cat in self.categories}
        for cat, cfg in self.categories.items():
            for kw, weight in cfg.get('positives', {}).items():
                if _tokenized_match(kw, text_lower):
                    scores[cat] += float(weight)

        # Phase 3: Negative scoring (penalties)
        for cat, cfg in self.categories.items():
            for kw, penalty in cfg.get('negatives', {}).items():
                if _tokenized_match(kw, text_lower):
                    # penalty is stored as negative number already
                    scores[cat] += float(penalty)

        # Phase 4: Decision
        sorted_cats = sorted(scores.keys(), key=lambda c: scores[c], reverse=True)
        top_score = scores[sorted_cats[0]]
        second_score = scores[sorted_cats[1]]

        # Too weak to decide
        if top_score < MIN_CONFIDENCE:
            return None

        # Too close to call
        if top_score - second_score < MIN_GAP:
            return None

        return sorted_cats[0]

    def score_all(self, title: str, content: str = '') -> Dict[str, float]:
        """Return all category scores for debugging/auditing."""
        title = title or ''
        content = content or ''
        title_lower = title.lower()
        text_lower = title_lower + ' ' + (content[:500] or '').lower()

        scores = {cat: 0.0 for cat in self.categories}
        for cat, cfg in self.categories.items():
            for kw, weight in cfg.get('positives', {}).items():
                if _tokenized_match(kw, text_lower):
                    scores[cat] += float(weight)
            for kw, penalty in cfg.get('negatives', {}).items():
                if _tokenized_match(kw, text_lower):
                    scores[cat] += float(penalty)
        return scores

    def matched_keywords(self, title: str, content: str = '') -> Dict[str, list]:
        """Return which keywords matched for each category (for debugging)."""
        title = title or ''
        content = content or ''
        title_lower = title.lower()
        text_lower = title_lower + ' ' + (content[:500] or '').lower()

        matches = {}
        for cat, cfg in self.categories.items():
            pos = [(kw, w) for kw, w in cfg.get('positives', {}).items()
                   if kw.lower() in text_lower]
            neg = [(kw, w) for kw, w in cfg.get('negatives', {}).items()
                   if kw.lower() in text_lower]
            matches[cat] = {'positives': pos, 'negatives': neg}
        return matches


def _tokenized_match(keyword: str, text: str) -> bool:
    """Check if keyword appears as a word in text (jieba boundary-aware).

    Avoids substring false matches like '合作' matching inside '光合作用'.
    For English keywords: uses case-insensitive word-boundary regex.
    For Chinese keywords: tokenizes text with jieba, then checks if keyword
    appears as a complete token or as a substring bounded by non-CJK characters.
    """
    if not keyword or not text:
        return False
    kw_lower = keyword.lower()
    text_lower = text.lower()

    # English/numeric keywords: use regex word boundaries
    if re.match(r'^[a-zA-Z0-9\s\-\.\+\$]+$', kw_lower):
        try:
            return bool(re.search(r'\b' + re.escape(kw_lower) + r'\b', text_lower))
        except re.error:
            return kw_lower in text_lower

    # Chinese/mixed: use jieba tokenization
    tokens = set(jieba.lcut(text_lower))
    # Check as whole token
    if kw_lower in tokens:
        return True
    # Check as substring bounded by non-CJK chars
    # This catches multi-word phrases where jieba might split differently
    idx = text_lower.find(kw_lower)
    while idx >= 0:
        before_ok = idx == 0 or not _is_cjk(text_lower[idx - 1])
        after_ok = idx + len(kw_lower) >= len(text_lower) or not _is_cjk(text_lower[idx + len(kw_lower)])
        if before_ok and after_ok:
            return True
        idx = text_lower.find(kw_lower, idx + 1)
    return False


def _is_cjk(ch: str) -> bool:
    """Check if character is a CJK unified ideograph."""
    cp = ord(ch)
    return (0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF or
            0x20000 <= cp <= 0x2A6DF or 0xF900 <= cp <= 0xFAFF)


# Singleton
_scorer = None

def get_scorer() -> CategoryScorer:
    global _scorer
    if _scorer is None:
        _scorer = CategoryScorer()
    return _scorer


if __name__ == '__main__':
    scorer = CategoryScorer()

    # Quick test on a few cases
    tests = [
        ('OQC完成2.6亿英镑C轮融资', ''),
        ('Quobly完成1.15亿欧元A轮融资，加速商业化', ''),
        ('IBM任命新CEO Arvind Krishna', ''),
        ('Nature发表量子纠错里程碑论文', ''),
        ('本源量子发布新一代超导量子处理器', ''),
        ('中国量子计算五年发展规划发布', ''),
    ]

    for title, content in tests:
        result = scorer.classify(title, content)
        scores = scorer.score_all(title, content)
        top_two = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:2]
        print(f'{"="*60}')
        print(f'Title: {title[:80]}')
        print(f'Result: {result}')
        print(f'Scores: {top_two[0][0]}={top_two[0][1]}, {top_two[1][0]}={top_two[1][1]}')
