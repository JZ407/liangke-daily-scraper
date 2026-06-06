"""
量科网每日新闻抓取脚本 (MySQL + 去重 + 原始日期提取)
"""
import sys
import requests
from category_scorer import get_scorer  # unified dictionary-based classifier
from bs4 import BeautifulSoup
import pickle
import time
import random
import os
import re
from datetime import datetime, timedelta
from urllib.parse import urlparse

from extract_original_date import get_original_date
from db import insert_or_update_article, article_exists, get_article_count

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15',
]
HEADERS = {'User-Agent': _USER_AGENTS[0]}

def _rotate_ua():
    """Rotate User-Agent header for anti-scraping."""
    HEADERS['User-Agent'] = random.choice(_USER_AGENTS)

COOKIE_PATH = os.path.join(BASE_DIR, '..', 'data', 'cookies', 'qtc_cookies.pkl')
BASE_URL = 'http://www.qtc.com.cn'

# 原有技术标签关键词库
KEYWORDS = {
    '量子计算': ['量子计算', '量子比特', 'qubit', '量子门', '量子电路', '量子算法', '量子优势', '量子霸权', '量子纠错', '逻辑量子比特', '物理量子比特', '量子体积', '量子模拟', '量子机器学习', '变分量子算法', 'vqa', 'vqe', '量子退火', '量子编译', 'nisq', 'ftqc', '容错量子计算', '量子噪声', '量子相干'],
    '量子通信': ['量子通信', '量子密钥分发', 'qkd', '量子隐形传态', '量子纠缠', '量子中继器', '量子网络', '量子互联网', '量子卫星', '自由空间量子通信', '光纤量子通信', '设备无关', 'di-qkd', 'mdi-qkd', '连续变量', 'cv-qkd'],
    '后量子密码': ['后量子密码', 'pqc', '抗量子密码', '格密码', '哈希密码', '编码密码', '多元密码', '同态加密', '零知识证明', '数字签名', '密钥封装', 'kem', 'nist后量子', '密码敏捷性', 'tls', 'ssl', 'pki', '后量子迁移', 'post-quantum'],
    '量子传感': ['量子传感', '量子计量', '量子精密测量', '原子钟', '量子陀螺仪', '量子磁力计', '量子雷达', '重力仪', '干涉仪', '压缩态'],
    '硬件平台': ['超导量子比特', 'transmon', '离子阱', 'ion trap', '光量子', '光子量子', '硅自旋', '中性原子', '拓扑量子比特', '马约拉纳', 'nv色心', 'nv中心', '里德伯', '量子点', '单光子探测器', 'snspd', '超导纳米线', '约瑟夫森结', '稀释制冷机', '光子集成电路'],
    '量子物理': ['量子力学', '量子叠加', '量子态', '波函数', '量子涨落', '退相干', '量子混沌', '贝尔不等式', '量子场论', '多体物理', '凝聚态物理', '冷原子', '腔量子电动力学', '腔qed'],
    '行业应用': ['量子化学', '药物发现', '材料科学', '组合优化', '供应链优化', '金融建模', '密码分析', '量子安全', '量子成像', '量子导航', 'qcaas', '量子计算即服务', '混合量子-经典'],
    '政策标准': ['量子战略', '国家量子计划', '量子技术标准化', '出口管制', '网络安全法规', '量子人才', '产学研合作'],
    '企业与机构': ['ibm', 'google', '谷歌', '英伟达', 'nvidia', '英特尔', 'intel', '微软', 'microsoft', '亚马逊', 'amazon', 'ionq', 'rigetti', 'xanadu', 'pasqal', 'd-wave', 'quera', 'quantinuum', '国盾量子', '本源量子', 'nist', '欧盟量子旗舰', 'arxiv'],
    '融资商业': ['量子投资', '风险投资', 'ipo', '战略合作', '政府资助', '量子初创', '量子生态', '商业化', '营收增长', '市场份额', '融资', '估值', '亿美元', '万美元'],
}

SPECIFIC_TAGS = {
    'QKD': ['qkd', '量子密钥分发'],
    'PQC': ['pqc', '后量子密码'],
    '超导': ['超导', 'transmon', 'snspd', '约瑟夫森'],
    '离子阱': ['离子阱', 'ion trap'],
    '光量子': ['光量子', '光子量子', '单光子'],
    'NIST': ['nist'],
    'arXiv': ['arxiv'],
    '融资': ['融资', '估值', '万美元', '亿美元'],
    '量子计算': ['量子计算', '量子比特', 'qubit'],
    '量子通信': ['量子通信', '量子网络', '量子互联网'],
    '量子纠错': ['量子纠错', '逻辑量子比特'],
    '后量子迁移': ['后量子迁移', '密码迁移'],
    '半导体': ['半导体', '硅自旋', '量子点'],
    'AI/ML': ['机器学习', '人工智能', 'ai', 'ml-'],
}

# 五大分类标签关键词库（每篇文章必须有且仅有一个）
# 优先级：资本运作 > 产品动态 > 企业资讯 > 科技前沿 > 宏观态势
CATEGORY_KEYWORDS = {
    '资本运作': [
        '融资', '投资', '风投', 'vc ', 'pe ', 'ipo', '上市', '招股',
        '估值', '亿美元', '万美元', '人民币', '千万', '百万', '亿元',
        '收购', '并购', '合并', '分拆', '剥离', '整合',
        '资助', '拨款', '补贴', '基金', '预算', '经费',
        '营收', '收入', '利润', '亏损', '财报', '业绩', '增长',
        '股权', '股东', '控股', '参股', '注资', '增资', '扩股',
        'a轮', 'b轮', 'c轮', 'd轮', '种子轮', '天使轮', '战略融资',
        'raise', 'raised', 'raises', 'raising', 'funding', 'fund', 'funds',
        'series', 'equity', 'offering', 'pricing of', 'closes',
        'completes acquisition', 'completes sale', 'acquires',
        'stock', 'shares', 'shareholder', 'market cap', 'market capital',
        'capital', 'backed by', 'led by', 'investor', 'venture',
        'grant', 'awarded', 'contract award', 'million dollar',
        'billion dollar', 'm deal', 'mn deal', 'loan', 'bond',
        'debt', 'credit', 'capital raise', 'capital raising',
    ],
    '产品动态': [
        '产品', '发布', '推出', '新品上市', '产品上市', '芯片', '处理器', '计算机',
        '量子计算机', '量子芯片', '量子处理器', '原型机', '样机',
        '系统', '平台', '软件', '工具', 'sdk', 'api', '云服务',
        '升级', '迭代', '性能', '指标', '保真度', '相干时间',
        '低温', '制冷机', '测控', '封装', '互联', '模块化',
        '量产', '商用', '部署', '交付', '生产线', '制造',
    ],
    '企业资讯': [
        'ibm', 'google', '谷歌', '微软', 'microsoft', '亚马逊', 'amazon',
        '英伟达', 'nvidia', '英特尔', 'intel', '苹果', 'apple',
        'ionq', 'rigetti', 'xanadu', 'pasqal', 'd-wave', 'quera', 'quantinuum',
        '国盾量子', '本源量子', '国仪量子', '国创中心', '中电科', '华为',
        '合作', '协议', '签约', '伙伴', '联盟', '成员',
        '任命', '高管', 'ceo', 'cto', '总裁', '创始人', '团队', '离职',
        '扩建', '新厂', '研发中心', '总部', '分部', '办事处',
    ],
    '科技前沿': [
        '论文', '研究', '突破', '实验', '发现', '理论', '算法', '模型',
        '量子比特', '量子门', '量子电路', '量子纠缠', '量子叠加',
        '量子纠错', '逻辑量子比特', '物理量子比特', '量子体积',
        '超导', '离子阱', '光量子', '中性原子', '硅自旋', '拓扑',
        '量子模拟', '量子机器学习', '变分量子', 'vqa', 'vqe',
        'arxiv', 'nature', 'science', '物理评论', 'prl',
        '预印本', '实验验证', '原理验证', '科学', '学术', '期刊',
    ],
    '宏观态势': [
        '政策', '战略', '规划', '法规', '标准', '出口管制', '制裁', '法案',
        '人才', '教育', '培训', '科研', '产学研',
        '市场', '产业', '生态', '趋势', '报告', '预测', '全球', '国际',
        '国家量子', '量子计划', '路线图', '白皮书', '指南', '倡议',
        '竞争', '领先', '差距', '挑战', '机遇', '风险',
    ],
}

CATEGORY_PRIORITY = ['资本运作', '产品动态', '企业资讯', '科技前沿', '宏观态势']


def _match_category(text_lower: str) -> str:
    """匹配五大分类标签（关键词兜底），返回唯一分类。"""
    scores = {}
    for tag, words in CATEGORY_KEYWORDS.items():
        score = 0
        for word in words:
            if word.lower() in text_lower:
                score += 1
        scores[tag] = score

    if max(scores.values()) == 0:
        return '宏观态势'

    # Higher score wins; on tie, lower priority index (higher priority) wins
    best_tag = max(CATEGORY_PRIORITY, key=lambda t: (scores[t], -CATEGORY_PRIORITY.index(t)))
    return best_tag


def _hard_classify(title: str, content: str = '') -> str | None:
    """确定性规则分类。明确案例直接返回类别，歧义案例返回 None 交给 LLM。

    设计原则：宁可漏过（返回 None）也不误判。只拦截极高置信度的模式。
    检查顺序：标题人事 > 标题融资 > 其他 > 正文融资 > 正文人事
    标题级优先于正文级，避免正文背景信息（如"担任财务顾问"）干扰标题核心判断。
    """
    text = (title or '') + ' ' + ((content or '')[:200])

    # ═══════════════════════════════════════════════════════════
    # Step 1: 标题级检查（高置信度，标题体现核心新闻）
    # ═══════════════════════════════════════════════════════════

    # 1a. 人事任命（标题）
    if re.search(r'(任命|出任|担任|加盟|加入|晋升|擢升|提升|擢升为).{0,10}'
                 r'(CEO|CTO|CFO|COO|总裁|首席|总经理|董事长|副总裁|总监|合伙人)', title):
        return '企业资讯'
    if re.search(r'(离职|辞任|卸任|退休|离开).{0,10}'
                 r'(CEO|CTO|总裁|首席|创始人)', title):
        return '企业资讯'

    # 1b. 融资轮次（标题）: "完成C轮融资" / "获天使轮融资" / "A轮/B轮/种子轮"
    if re.search(r'(完成|获|获得|宣布|签署|达成).{0,15}'
                 r'(轮融资|元融资|美元融资|欧元融资)', title):
        return '资本运作'
    if re.search(r'(天使轮|种子轮|A轮|B轮|C轮|D轮|Pre-IPO)', title):
        return '资本运作'
    if re.search(r'(完成|获|获得|宣布|签署|达成).{0,10}融资', title):
        return '资本运作'

    # 1c. IPO/SPAC（标题）: "拟借壳上市" / "提交上市申请"
    if re.search(r'(拟|计划|已|正式|宣布|完成|提交).{0,10}'
                 r'(借壳上市|IPO上市|SPAC|上市申请)', title):
        return '资本运作'

    # 1d. 收购并购（标题）
    if re.search(r'(收购|并购|合并|控股|注资|参股).{0,10}'
                 r'(公司|企业|正式|完成|宣布|交易|旗下)', title):
        return '资本运作'

    # ═══════════════════════════════════════════════════════════
    # Step 2: 正文级检查（标题不明确时从正文补充）
    # ═══════════════════════════════════════════════════════════

    # 2a. 融资轮次（正文）: SPAC / 战略融资/投资（需动作词） / 政府拨款 / 估值
    if re.search(r'SPAC', text, re.IGNORECASE) and \
       re.search(r'(公司|企业|关注|合并|收购|上市)', text):
        return '资本运作'
    if re.search(r'(拟|计划|已|正式|宣布|完成|提交|受到).{0,10}'
                 r'(借壳上市|IPO上市|SPAC|上市申请)', text):
        return '资本运作'
    if re.search(r'(完成|获|获得|宣布|签署|达成|进行|新一轮).{0,10}'
                 r'(战略融资|战略投资)', text):
        return '资本运作'
    # 收购并购（正文）
    if re.search(r'(收购|并购|合并|控股|注资|参股).{0,10}'
                 r'(公司|企业|正式|完成|宣布|交易|旗下)', text):
        return '资本运作'
    # 估值
    if re.search(r'(估值|市值).{0,10}(亿|万|美元|欧元)', text):
        return '资本运作'
    # 政府/机构给企业拨款
    if re.search(r'(政府|商务部|能源部|国防部|DOE|DARPA).{0,30}'
                 r'(拨款|资助|补贴|投资|资金支持)', text) and \
       re.search(r'\d+\s*(亿|万|美元|欧元)', text):
        return '资本运作'

    # 2b. 宏观态势（国家政策）
    if re.search(r'(国家|国务院|科技部|工信部|欧盟|白宫)'
                 r'.{0,10}(发布|出台|推出|宣布|启动|实施).{0,10}'
                 r'(政策|战略|规划|计划|法案|法规|路线图|倡议)', text):
        return '宏观态势'

    # 2c. 科技前沿（学术渠道）
    if re.search(r'(Nature|PRL|Physical Review|arXiv|预印本|《自然》|《科学》|Nat\.|Phys\. Rev\.)', text):
        return '科技前沿'
    if re.search(r'Science\s*(?:杂志|期刊|论文|发表|Advances|Bulletin|Robotics)', text, re.IGNORECASE):
        return '科技前沿'

    # 2d. 人事任命（正文回退 — 只在标题没有融资信号时才到这一步）
    if re.search(r'(任命|出任|担任|加盟|加入|晋升|擢升|提升|擢升为).{0,10}'
                 r'(CEO|CTO|CFO|COO|总裁|首席|总经理|董事长|副总裁|总监|合伙人)', text):
        return '企业资讯'
    if re.search(r'(离职|辞任|卸任|退休|离开)', text) and \
       re.search(r'(CEO|CTO|总裁|首席|创始人)', text):
        return '企业资讯'

    return None  # 无法确定，交给 LLM


def _llm_classify_batch(articles_info):
    """Use LLM to classify a batch of articles into 5 weekly categories.

    articles_info: list of (title + content excerpt) strings.
    Each item should provide enough context: title + first 400 chars of content.
    """
    text_list = '\n'.join(
        f'{i+1}. {info[:400]}' for i, info in enumerate(articles_info)
    )
    prompt = f"""将以下量子科技新闻分类到五大类别之一。

==== 判定优先级（严格按此顺序，多标签冲突时唯一归类）====
资本运作 > 科技前沿 > 产品动态 > 企业资讯 > 宏观态势

==== ⚠️ 融资标题绝对优先规则（最高优先级，覆盖所有其他规则）====
当标题的核心事件是融资/投资/IPO/SPAC/估值/收购时，不论正文提到资金用途（商业化/产业化/规模化/建厂/研发等），一律归资本运作。
关键词触发：完成X轮融资、获XX美元/欧元/人民币融资、拟借壳上市、SPAC合并、提交IPO申请、估值达、收购XX公司、获XX政府拨款/资助（给具体企业）
即使标题同时出现"加速商业化""推进产业化""用于产品研发"等词，只要融资是标题核心信息→资本运作。

==== "上市"二字的歧义消解 ====
"借壳上市""SPAC上市""IPO上市""公司上市""提交上市申请"→ 资本运作
"产品上市""新品上市""正式上市销售"→ 产品动态
看主语：主语是公司→资本运作；主语是产品→产品动态。

==== 分类定义 ====

1. 资本运作 —— 钱和所有权的流动
   【属于】企业融资（天使/种子/A/B/C轮、战略投资等）、IPO/借壳上市/SPAC合并、收购并购、财报营收估值、政府资助/拨款/补贴给具体企业（如"美国商务部给IBM XX亿美元"）、企业重大资本支出（百亿级投资建厂，金额是标题核心信息）
   【不属于】政府面向全行业的资助计划→宏观态势 | 政府资助大学/研究机构→宏观态势或科技前沿 | 资金只是背景信息的技术/产品/合作新闻→按内容本质归类 | 注意：不要因为正文提到"用于产品开发/商业化"就把融资新闻错分为产品动态

2. 科技前沿 —— 知识层面的推进，不涉及商业产品
   【属于】学术论文（Nature/Science/PRL/arXiv预印本）、实验突破/新物理现象、新算法/新理论、学术会议成果、学术渠道发布的开源工具
   【不属于】商业产品→产品动态 | 行业白皮书→宏观态势 | 注意：公司新闻稿包装的研究成果，如果本质是学术预印本/论文，仍归科技前沿

3. 产品动态 —— 能买能用能部署的东西
   【属于】新芯片/整机/软件/云服务正式发布可用、通过商业渠道宣布的性能突破（产品发布会、公司新闻稿、官网博客）、商用落地/量产/客户部署/云平台上线、产品认证获批、公司具体产品路线图（含时间节点/性能目标）
   【不属于】论文中报告的性能指标→科技前沿 | 实验室原型机未开放→科技前沿 | 纯理论算法→科技前沿 | 通过arXiv/Nature等学术渠道发布的成果→科技前沿 | 融资/投资新闻（即使提到产品）→资本运作

4. 企业资讯 —— 公司组织层面的变化
   【属于】高管任命（CEO/CTO/VP等，一律归此）、战略合作签约/MoU/联盟加入（无具体成果产出）、办公室/研发中心扩建裁员、公司战略愿景品牌重塑、企业回应辟谣公关声明法律诉讼
   【不属于】合作研究成果发表→科技前沿 | 合作推出产品→产品动态 | 获投资→资本运作

5. 宏观态势 —— 影响整个行业，而非单个公司
   【属于】国家量子战略/政策法规/出口管制、行业路线图（政府/联盟发布）、市场研究报告/竞争格局、人才教育（大学专业/学院）、国际科技合作格局、政府资助给大学/研究机构用于平台建设或产业布局、科普/行业综述
   【不属于】某公司获政府资助→资本运作 | 某公司产品路线图→产品动态 | 单个学术成果→科技前沿

==== 关键边界规则 ====
- 资金核心原则：只有资金数额/融资轮次/估值/所有权变更是新闻核心时才归资本运作，否则按内容本质归类
- ⚠️ 融资不要被"用途"带偏：标题说"融资X亿用于产品研发/商业化"→仍然是资本运作，因为融资是核心事件
- 政府资助分流：给企业→资本运作；给大学/研究机构→宏观态势（强调产业布局）或科技前沿（强调具体科研）
- 人事变动：无论技术还是管理岗位，一律企业资讯
- 发布渠道优先：arXiv/Nature/Science等学术渠道→科技前沿；PR/公司新闻室→产品动态
- 常规声明不转移：论文末尾的"有望应用于量子计算"等不改变科技前沿属性
- 合作区分：签合作协议/MoU（无成果产出）→企业资讯；合作发表论文/研发成功→科技前沿

==== 速查对照 ====
企业获融资（A/B/C轮） → 资本运作 | 企业IPO/SPAC/借壳上市 → 资本运作 | 企业发新芯片（含型号） → 产品动态
政府拨款给具体企业 → 资本运作 | 政府拨款给大学 → 宏观态势 | 企业任命CTO → 企业资讯
Nature论文 → 科技前沿 | 国家量子五年规划 → 宏观态势 | 企业获融资用于商业化 → 仍是资本运作
arXiv论文 → 科技前沿 | 企业回应辟谣 → 企业资讯 | 公司产品路线图（含时间/指标） → 产品动态
公司被收购/并购 → 资本运作 | 企业财报/估值 → 资本运作 | 公司大学联合发表论文 → 科技前沿

==== 常见错分陷阱（务必避免）====
❌ "XX完成A轮融资，加速产品商业化" → 错分为产品动态 | ✅ 应为资本运作（融资是核心事件）
❌ "XX拟借壳上市" → 错分为产品动态（误以为产品上市）| ✅ 应为资本运作（公司IPO）
❌ "XX获政府XX亿美元建厂" → 错分为产品动态 | ✅ 应为资本运作（政府资助企业）
❌ "XX获XX亿美元估值" → 错分为企业资讯 | ✅ 应为资本运作（估值/融资相关）

每条新闻标题后附有正文前400字（| 分隔）。每篇只输出一个类别。输出格式：编号:类别

{text_list}

输出："""

    try:
        import yaml
        cfg = yaml.safe_load(open('D:/Claude_code/rag_system/config.yaml', encoding='utf-8'))
        llm_cfg = cfg['llm']
        sys.path.insert(0, 'D:/Claude_code/rag_system/rag_system')
        from llm_client import LLMClient
        client = LLMClient(provider='openai', api_key=llm_cfg['api_key'],
                          api_base=llm_cfg['api_base'], model=llm_cfg['model'],
                          max_tokens=2048, timeout=120)
        response = client.chat([{'role': 'user', 'content': prompt}])
        # Parse response: "1:资本运作\n2:企业资讯\n..."
        results = {}
        for line in response.strip().split('\n'):
            m = re.match(r'(\d+)[：:]\s*(\S+)', line.strip())
            if m:
                idx = int(m.group(1)) - 1
                cat = m.group(2).strip()
                if cat in CATEGORY_PRIORITY:
                    results[idx] = cat
        return results
    except Exception as e:
        print(f'  LLM classify failed: {e}')
        return {}


def auto_tag(title: str, content: str) -> list:
    """Project-based auto-tagging using unified tagger + dictionary scorer.
    Returns project-based tags dict as JSON string.
    """
    sys.path.insert(0, 'D:/Claude_code/knowledge_graph')
    from core.tagger import tag_article
    result = tag_article(title, content, '')
    # Use dictionary scorer as primary, keyword matching as fallback
    scorer = get_scorer()
    tag = scorer.classify(title, content)
    if not tag:
        # Fallback to keyword matching
        text = (title or '') + ' ' + (content or '')[:2000]
        text_lower = text.lower()
        tag = _match_category(text_lower)
    if tag and tag not in result['weekly']:
        result['weekly'].append(tag)
    return result


def load_cookies():
    if not os.path.exists(COOKIE_PATH):
        print(f"ERROR: Cookie file not found: {COOKIE_PATH}")
        print("Please run update_cookie.bat first after logging in to 量科网.")
        return None
    with open(COOKIE_PATH, 'rb') as f:
        return pickle.load(f)


def get_today_str():
    return datetime.now().strftime('%Y-%m-%d')


def get_target_dates():
    """Return today + yesterday (to catch any missed in yesterday's run)."""
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    return {today.strftime('%Y-%m-%d'), yesterday.strftime('%Y-%m-%d')}


def fetch_homepage_list(cookies):
    """Fetch homepage and extract today's news URLs."""
    print(f"Fetching homepage: {BASE_URL}")
    resp = requests.get(BASE_URL, cookies=cookies, headers=HEADERS, timeout=30)
    resp.encoding = resp.apparent_encoding or 'utf-8'
    soup = BeautifulSoup(resp.text, 'html.parser')

    target_dates = get_target_dates()
    print(f"Looking for news dated: {sorted(target_dates)}")

    articles = []
    seen_urls = set()

    for a in soup.find_all('a', href=True):
        href = a['href'].strip()

        # Skip category/index pages
        if href == '/reference/arxiv':
            continue
        if not (href.startswith('/flash/') or href.startswith('/article/') or href.startswith('/reference/')):
            continue
        # Skip non-specific pages
        if re.match(r'^/(flash|article|reference)/[^/]+$', href) is None:
            continue

        # Look for date pattern in nearby elements
        text_to_search = ''
        elem = a
        for _ in range(4):
            if elem:
                text_to_search += ' ' + elem.get_text(separator=' ', strip=True)
                elem = elem.find_parent()

        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', text_to_search)
        article_date = date_match.group(1) if date_match else None

        title = a.get_text(strip=True)
        if not title or len(title) < 5 or len(title) > 200:
            continue

        full_url = href if href.startswith('http') else BASE_URL + href
        if full_url in seen_urls:
            continue
        seen_urls.add(full_url)

        # Skip articles not from today or yesterday
        if article_date and article_date not in target_dates:
            continue

        articles.append({
            'title': title,
            'url': full_url,
            'date': article_date
        })

    print(f"Found {len(articles)} candidate news items on homepage.")
    return articles


# ── Anti-scraping protection ───────────────────────────────────────

def _polite_delay(min_s=1.0, max_s=3.0):
    """Random delay + UA rotation to avoid triggering anti-scraping detection."""
    time.sleep(random.uniform(min_s, max_s))
    _rotate_ua()


# ── Sub-page list fetchers ──────────────────────────────────────────

def parse_relative_time(text, today_date):
    """Parse relative time strings to approximate dates.

    Handles: 'X小时前' (today), '昨天' (yesterday), 'X天前' (today - X days).
    Returns datetime.date or None if unparseable.
    """
    h_match = re.search(r'(\d+)\s*小时前', text)
    if h_match:
        return today_date

    if '昨天' in text:
        return today_date - timedelta(days=1)

    d_match = re.search(r'(\d+)\s*天前', text)
    if d_match:
        return today_date - timedelta(days=int(d_match.group(1)))

    return None


def fetch_flash_list(cookies, target_dates, max_pages=5):
    """Fetch flash articles from /flash?page=N.

    /flash has explicit <span class='date'>YYYY-MM-DD</span>, so dates are reliable.
    Stops when the earliest date on a page is before min(target_dates).
    """
    min_date = min(datetime.strptime(d, '%Y-%m-%d').date() for d in target_dates)
    articles = []
    seen_urls = set()

    for page in range(max_pages):
        url = f'http://www.qtc.com.cn/flash?page={page}'
        print(f"  Fetching: {url}")
        try:
            resp = requests.get(url, cookies=cookies, headers=HEADERS, timeout=30)
            resp.encoding = resp.apparent_encoding or 'utf-8'
        except Exception as e:
            print(f"  -> Error: {e}")
            break

        soup = BeautifulSoup(resp.text, 'html.parser')
        page_oldest_date = None

        # Find all flash links with their dates
        # Structure: each item has <span class='date'><b class='year'>2026-</b>06-04</span>
        # followed by <a href='/flash/{id}.html'>title</a>
        date_spans = soup.find_all('span', class_='date')
        for ds in date_spans:
            # Parse date from span
            full_text = ds.get_text(strip=True)
            m = re.search(r'(\d{4})-(\d{2})-(\d{2})', full_text)
            if not m:
                continue
            date_str = m.group(0)
            try:
                article_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                continue

            if page_oldest_date is None or article_date < page_oldest_date:
                page_oldest_date = article_date

            # Find the associated link: date span is in div.flash-created,
            # link is in sibling div.txt. Go up to parent first, then next siblings.
            link = None
            date_parent = ds.find_parent()
            if date_parent:
                for sibling in date_parent.find_next_siblings(limit=5):
                    link = sibling.find('a', href=re.compile(r'^/flash/\d+\.html$'))
                    if link:
                        break
            if not link:
                # Fallback: search in the item container
                item_container = ds.find_parent('div', class_=re.compile('item'))
                if item_container:
                    link = item_container.find('a', href=re.compile(r'^/flash/\d+\.html$'))

            if not link:
                continue

            href = link.get('href', '').strip()
            title = link.get_text(strip=True)

            if not title or len(title) < 5:
                continue

            full_url = f'http://www.qtc.com.cn{href}'
            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)

            if date_str not in target_dates:
                continue

            articles.append({'title': title, 'url': full_url, 'date': date_str})

        # Stop condition: the oldest date on this page is before our window
        if page_oldest_date and page_oldest_date < min_date:
            print(f"  -> Page {page} oldest date {page_oldest_date} < {min_date}, stopping")
            break

        # If no dates found at all on this page, stop
        if page_oldest_date is None and len(date_spans) == 0:
            print(f"  -> Page {page} has no date spans, stopping")
            break

        _polite_delay()

    print(f"  Flash: {len(articles)} candidates from {page+1} pages")
    return articles


def fetch_news_list(cookies, target_dates, max_pages=5):
    """Fetch article-type news from /news?page=N.

    /news uses relative time ('X小时前', 'X天前', '昨天'). We parse these to
    approximate dates and filter by target_dates. Stop when a page is entirely
    older than 3 days.
    """
    today = datetime.now().date()
    articles = []
    seen_urls = set()

    for page in range(max_pages):
        url = f'http://www.qtc.com.cn/news?page={page}'
        print(f"  Fetching: {url}")
        try:
            resp = requests.get(url, cookies=cookies, headers=HEADERS, timeout=30)
            resp.encoding = resp.apparent_encoding or 'utf-8'
        except Exception as e:
            print(f"  -> Error: {e}")
            break

        soup = BeautifulSoup(resp.text, 'html.parser')

        # Find article links. The structure is:
        # <a href='/article/{id}.html'>title</a> ... followed by time text nearby
        page_article_links = soup.find_all('a', href=re.compile(r'^/article/\d+\.html$'))

        if not page_article_links:
            print(f"  -> Page {page} has no article links, stopping")
            break

        page_has_recent = False

        for a in page_article_links:
            href = a.get('href', '').strip()
            title = a.get_text(strip=True)

            if not title or len(title) < 5:
                continue

            full_url = f'http://www.qtc.com.cn{href}'
            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)

            # Find time text nearby: go up to <li class='item'> which contains
            # both the link (in <h3>) and time ("X小时前") after it.
            time_text = ''
            # Walk up to <li> or several levels to capture time text
            for ancestor in a.parents:
                if ancestor.name in ('li', 'div') and ancestor.get('class'):
                    cls = ' '.join(ancestor.get('class', []))
                    if 'item' in cls or 'pic-list' in cls:
                        time_text = ancestor.get_text(separator=' ', strip=True)
                        break
            if not time_text:
                # Fallback: just use grandparent
                gp = a.find_parent().find_parent() if a.find_parent() else None
                if gp:
                    time_text = gp.get_text(separator=' ', strip=True)

            approx_date = parse_relative_time(time_text, today)

            if approx_date is None:
                # Can't determine date from listing, include it and verify on detail page
                articles.append({'title': title, 'url': full_url, 'date': None})
                page_has_recent = True
            else:
                approx_str = approx_date.strftime('%Y-%m-%d')
                if approx_str in target_dates:
                    articles.append({'title': title, 'url': full_url, 'date': approx_str})
                    page_has_recent = True
                elif approx_date >= min(datetime.strptime(d, '%Y-%m-%d').date() for d in target_dates) - timedelta(days=1):
                    # Within 1 day of window edge, still include for safety
                    articles.append({'title': title, 'url': full_url, 'date': approx_str})

        if not page_has_recent and page >= 1:
            # Second condition: check if most items are old
            print(f"  -> Page {page}: no recent items, stopping")
            break

        _polite_delay()

    print(f"  News: {len(articles)} candidates from {page+1} pages")
    return articles


def fetch_reference_list(cookies, target_dates, max_pages=15):
    """Fetch reference articles from /reference?page=N.

    /reference uses relative time like /news. 8 pages/day so generous max_pages.
    Stop when a page has no items matching target_dates.
    """
    today = datetime.now().date()
    articles = []
    seen_urls = set()

    for page in range(max_pages):
        url = f'http://www.qtc.com.cn/reference?page={page}'
        print(f"  Fetching: {url}")
        try:
            resp = requests.get(url, cookies=cookies, headers=HEADERS, timeout=30)
            resp.encoding = resp.apparent_encoding or 'utf-8'
        except Exception as e:
            print(f"  -> Error: {e}")
            break

        soup = BeautifulSoup(resp.text, 'html.parser')

        # Find reference article links: href='/reference/{id}.html'
        ref_links = soup.find_all('a', href=re.compile(r'^/reference/\d+\.html$'))

        if not ref_links:
            print(f"  -> Page {page} has no reference links, stopping")
            break

        page_has_recent = False

        for a in ref_links:
            href = a.get('href', '').strip()
            title = a.get_text(strip=True)

            if not title or len(title) < 5:
                continue

            full_url = f'http://www.qtc.com.cn{href}'
            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)

            # Find time text in parent context: <li class='item'> has "X小时前"
            time_text = ''
            for ancestor in a.parents:
                if ancestor.name == 'li' and 'item' in ' '.join(ancestor.get('class', [])):
                    time_text = ancestor.get_text(separator=' ', strip=True)
                    break
            if not time_text:
                gp = a.find_parent().find_parent() if a.find_parent() else None
                if gp:
                    time_text = gp.get_text(separator=' ', strip=True)

            approx_date = parse_relative_time(time_text, today)

            if approx_date is None:
                articles.append({'title': title, 'url': full_url, 'date': None})
                page_has_recent = True
            else:
                approx_str = approx_date.strftime('%Y-%m-%d')
                if approx_str in target_dates:
                    articles.append({'title': title, 'url': full_url, 'date': approx_str})
                    page_has_recent = True

        if not page_has_recent and page >= 1:
            print(f"  -> Page {page}: no recent reference items, stopping")
            break

        _polite_delay()

    print(f"  Reference: {len(articles)} candidates from {page+1} pages")
    return articles


# ── Page-type-specific extractors ──────────────────────────────────

def _extract_ref_link(soup):
    """Common: extract external reference link from a page."""
    # Method 1: <a> tag with "参考来源" or "参考链接" text
    for a in soup.find_all('a', href=True):
        text = a.get_text(strip=True)
        href = a.get('href', '').strip()
        if ('参考来源' in text or '参考链接' in text) and href.startswith('http'):
            return {'text': text, 'url': href}
    # Method 2: label element with nearby <a>
    for el in soup.find_all(['span', 'label', 'div', 'p']):
        if '参考来源' in el.get_text(strip=True) or '参考链接' in el.get_text(strip=True):
            for a in el.parent.find_all('a', href=True):
                href = a.get('href', '').strip()
                if href.startswith('http') and 'qtc.com.cn' not in href:
                    return {'text': a.get_text(strip=True), 'url': href}
    return None


def _extract_liangke_date(soup):
    """Common: extract liangke date from time/date tags on detail page.

    Searches ALL matching elements (not just first), since the first <span class='time'>
    may be an institution name rather than a date.
    """
    # Collect ALL candidate elements
    candidates = []
    candidates.extend(soup.find_all('time'))
    candidates.extend(soup.find_all('span', class_='time'))
    for cls in ['date', 'published', 'post-time']:
        candidates.extend(soup.find_all('span', class_=cls))
        candidates.extend(soup.find_all('div', class_=cls))

    for tag in candidates:
        text = tag.get_text(strip=True)
        m = re.search(r'(\d{4}-\d{2}-\d{2})', text)
        if m:
            try: return datetime.strptime(m.group(1), '%Y-%m-%d').date()
            except ValueError: pass

    # Fallback 1: <span class='date'> with <b class='year'>YYYY-</b>MM-DD
    for date_span in soup.find_all('span', class_='date'):
        year_tag = date_span.find('b', class_='year')
        full_text = date_span.get_text(strip=True)
        m = re.search(r'(\d{4})-(\d{2})-(\d{2})', full_text)
        if m:
            try: return datetime.strptime(m.group(0), '%Y-%m-%d').date()
            except ValueError: pass

    # Fallback 2: Chinese date format "MM月DD日" in body, infer year from context
    body = soup.find('body')
    if body:
        for noise in body.find_all(['nav','header','script','style']):
            noise.decompose()
        body_text = body.get_text()
        m = re.search(r'(\d{1,2})\s*月\s*(\d{1,2})\s*日', body_text)
        if m:
            month, day = int(m.group(1)), int(m.group(2))
            # Infer year: if MM-DD is in the future vs today, use previous year
            today = datetime.now().date()
            year = today.year
            try:
                candidate = datetime(year, month, day).date()
                if candidate > today:
                    candidate = datetime(year - 1, month, day).date()
                return candidate
            except ValueError:
                pass

    return None


def _extract_flash(soup, url):
    """Flash pages: h2 title, body text from page (not div.txt sidebar), external reference link."""
    title = ''
    h2 = soup.find('h2')
    if h2: title = h2.get_text(strip=True)
    if not title:
        ttag = soup.find('title')
        if ttag: title = ttag.get_text(strip=True).split('|')[0].strip()

    # Flash page body: text after h2/date, before related-articles sidebar
    # The content is NOT in div.txt (those are sidebar snippets). Get body text and filter.
    content = ''
    body = soup.find('body')
    if body:
        for noise in body.find_all(['nav','header','footer','script','style']):
            noise.decompose()
        lines = [l.strip() for l in body.get_text(separator='\n', strip=True).split('\n') if l.strip()]
        # Find the article body: first long paragraph after date or title
        content = ''
        title_skipped = False
        for l in lines:
            # Skip first occurrence of title (the heading itself)
            if not title_skipped and title and title[:15] in l:
                title_skipped = True; continue
            if re.match(r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}', l): continue
            if len(l) < 50: continue
            if any(kw in l for kw in ['量科网 - 量子科技中心', '粤ICP', '粤公网', 'Copyright']): break
            content = l; break

    ref = _extract_ref_link(soup)
    return {
        'title': title or '无标题',
        'content': content,
        'primary_reference': ref,
        'liangke_date': _extract_liangke_date(soup),
    }


def _extract_reference(soup, url):
    """Reference pages: h2 title, div.refer-txt content, trim header noise + footer metadata."""
    title = ''
    h2 = soup.find('h2')
    if h2: title = h2.get_text(strip=True)
    if not title:
        ttag = soup.find('title')
        if ttag: title = ttag.get_text(strip=True).split('|')[0].strip()

    content = ''
    content_div = soup.find('div', class_='refer-txt')
    if content_div:
        content = content_div.get_text(separator='\n', strip=True)
    if not content:
        body = soup.find('body')
        if body:
            for noise in body.find_all(['nav','header','footer','script','style']):
                noise.decompose()
            content = body.get_text(separator='\n', strip=True)

    # Trim: everything before the 3rd arrow (参考来源➔ PDF下载➔ HTML版➔ ...)
    arrows = [m.start() for m in re.finditer('➔', content)]
    if len(arrows) >= 3:
        content = content[arrows[2] + 1:].strip()
    # Trim: everything after "作者单位："
    if '作者单位：' in content:
        content = content.split('作者单位：')[0].strip()
    elif '作者单位:' in content:
        content = content.split('作者单位:')[0].strip()

    ref = _extract_ref_link(soup)
    return {
        'title': title or '无标题',
        'content': content,
        'primary_reference': ref,
        'liangke_date': _extract_liangke_date(soup),
    }


def _extract_article(soup, url):
    """Article pages: h1 title + full body, trim only nav crumbs + page footer."""
    title = ''
    h1 = soup.find('h1', class_='page-header') or soup.find('h1')
    if h1: title = h1.get_text(strip=True)
    if not title:
        ttag = soup.find('title')
        if ttag: title = ttag.get_text(strip=True).split('|')[0].strip()

    content = ''
    body = soup.find('body')
    if body:
        for noise in body.find_all(['nav','header','footer','script','style']):
            noise.decompose()
        lines = [l.strip() for l in body.get_text(separator='\n').split('\n') if l.strip()]

        # Find start: after the h1 title line
        start_idx = 0
        for i, l in enumerate(lines):
            if title and title[:15] in l:
                start_idx = i + 1
                break

        # Skip a few metadata lines (date, view count, category, institution name)
        skip_count = 0
        while start_idx + skip_count < len(lines) and skip_count < 5:
            l = lines[start_idx + skip_count]
            is_meta = (
                re.match(r'\d{4}-\d{2}-\d{2}', l) or           # date line
                (l.isdigit() and len(l) < 5) or                 # view count
                l in ('技术研究','行业观点','企业动态') or      # category tag
                (len(l) < 30 and not any(p in l for p in '，。！？'))  # short institution name
            )
            if is_meta:
                skip_count += 1
            else:
                break

        # Take everything from article start to page footer
        result_lines = []
        for l in lines[start_idx + skip_count:]:
            # Trim: nav crumbs, short UI labels
            if l in ('首页','快讯','文章','参考','企服','VIP','企业','所有','短讯',
                     '量科快讯','商业情报','一点数据','知识碎片','实时快讯','用户专享：'):
                continue
            # Stop only at definitive page footer (not mid-content sections)
            if any(kw in l for kw in ['量科网 - 量子科技中心', '粤ICP备', '粤公网安备', 'Copyright']):
                break
            result_lines.append(l)

        content = '\n'.join(result_lines).strip()
        if '注册用户以继续' in content:
            content = content.split('注册用户以继续')[0].strip()
        # Trim after "参考链接¹" — everything after is unrelated
        if '参考链接¹' in content:
            content = content.split('参考链接¹')[0].strip()

    ref = _extract_ref_link(soup)
    return {
        'title': title or '无标题',
        'content': content,
        'primary_reference': ref,
        'liangke_date': _extract_liangke_date(soup),
    }


# ── Main fetch function (dispatches to type-specific extractor) ────

def fetch_article_detail(url, cookies):
    """Fetch full article detail using page-type-specific extraction."""
    try:
        resp = requests.get(url, cookies=cookies, headers=HEADERS, timeout=30)
        resp.encoding = resp.apparent_encoding or 'utf-8'
        soup = BeautifulSoup(resp.text, 'html.parser')

        if resp.status_code == 404 or '404' in (soup.find('title').get_text(strip=True) if soup.find('title') else ''):
            return {'title': 'ERROR', 'time_text': '', 'url': url,
                    'content': f'404: page not found', 'primary_reference': None, 'liangke_date': None}

        if '/reference/' in url:
            result = _extract_reference(soup, url)
        elif '/flash/' in url:
            result = _extract_flash(soup, url)
        else:
            result = _extract_article(soup, url)

        result['url'] = url
        result['time_text'] = ''
        return result
    except Exception as e:
        return {'title': 'ERROR', 'time_text': '', 'url': url, 'content': str(e),
                'primary_reference': None, 'liangke_date': None}


def _extract_keywords(title):
    """Extract meaningful keywords from a title using jieba for Chinese segmentation."""
    import jieba, re
    stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                  'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from',
                  'and', 'or', 'but', 'not', 'this', 'that', 'it', 'its',
                  'has', 'have', 'had', 'will', 'would', 'could', 'should',
                  'may', 'might', 'can', 'new', 'first', 'more', 'than',
                  '了', '的', '在', '是', '和', '与', '及', '或',
                  '为', '以', '等', '从', '到', '对', '被', '把', '向',
                  '将', '就', '也', '都', '还', '而', '但', '却', '因',
                  '所', '其', '中', '上', '下', '之', '已', '于', '该'}
    words = jieba.lcut((title or '').lower())
    return {w.strip() for w in words if len(w.strip()) >= 2 and w.strip() not in stop_words}


def find_similar_article(title, date_str, window_days=3):
    """Check if a semantically similar article exists within N days.

    Uses jieba keyword overlap. Checks a window of window_days around date_str
    to catch articles that were scraped on different dates but are the same content.
    """
    try:
        from db import get_session, Article
        import jieba
        from datetime import timedelta
        session = get_session()
        d = datetime.strptime(date_str, '%Y-%m-%d').date()
        start_d = d - timedelta(days=window_days)
        end_d = d + timedelta(days=window_days)
        nearby_articles = session.query(Article).filter(
            Article.liangke_date >= start_d,
            Article.liangke_date <= end_d
        ).all()

        new_kw = _extract_keywords(title)
        if len(new_kw) < 3:
            session.close()
            return None

        for art in nearby_articles:
            exist_kw = _extract_keywords(art.title or '')
            if len(exist_kw) < 3:
                continue
            overlap = len(new_kw & exist_kw)
            min_len = min(len(new_kw), len(exist_kw))
            # Require both high overlap ratio AND a minimum number of matching terms
            if min_len > 0 and overlap / min_len >= 0.6 and overlap >= 3:
                session.close()
                return {'id': art.id, 'title': art.title}

        session.close()
    except Exception:
        pass
    return None


def check_cookie_valid(cookies):
    """Verify cookie can access logged-in content (参考来源 links)."""
    try:
        test_url = 'http://www.qtc.com.cn/reference/178028316033556.html'
        resp = requests.get(test_url, cookies=cookies, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, 'html.parser')
        # If logged in, "参考来源" link should point to external URL, not /user/login
        for a in soup.find_all('a', href=True):
            text = a.get_text(strip=True)
            href = a.get('href', '').strip()
            if ('参考来源' in text or '参考链接' in text):
                if href.startswith('/user/login'):
                    return False, 'Cookie expired — 参考来源指向登录页'
                if href.startswith('http'):
                    return True, 'OK'
        # No 参考来源 found at all
        login_links = len(soup.find_all('a', href='/user/login'))
        if login_links > 0:
            return False, 'Cookie expired — 页面处于未登录状态'
        return False, '参考来源链接未找到'
    except Exception as e:
        return False, f'Cookie check failed: {e}'


def main():
    cookies = load_cookies()
    if not cookies:
        print('ERROR: No cookie file found. Run update_cookie.bat first.')
        return

    cookie_ok, cookie_msg = check_cookie_valid(cookies)
    if not cookie_ok:
        print(f'ERROR: {cookie_msg}')
        print('Please re-login to www.qtc.com.cn and update the cookie.')
        return
    print(f'Cookie check: {cookie_msg}')

    today = get_today_str()
    target_dates = get_target_dates()
    print(f"Target dates: {sorted(target_dates)}")

    # Three sub-page sources (better coverage than mixed homepage)
    print("\n--- Flash ---")
    articles = fetch_flash_list(cookies, target_dates)
    print("\n--- News (article) ---")
    articles += fetch_news_list(cookies, target_dates)
    print("\n--- Reference ---")
    articles += fetch_reference_list(cookies, target_dates)

    # Dedup by URL (same article may appear on multiple sub-pages)
    seen = set()
    deduped = []
    for a in articles:
        if a['url'] not in seen:
            seen.add(a['url'])
            deduped.append(a)
    articles = deduped

    print(f"\nTotal candidates across all sources: {len(articles)} (after dedup)")

    if not articles:
        print(f"No candidate articles found for target dates: {sorted(target_dates)}.")
        return

    stats = {'inserted': 0, 'updated': 0, 'skipped': 0, 'errors': 0}

    # ── Phase 1: Fetch all details + keyword tags ──
    pending = []  # list of dicts with all info needed for insert
    for i, art in enumerate(articles, 1):
        print(f"\n[{i}/{len(articles)}] {art['title'][:60].encode('gbk', errors='replace').decode('gbk', errors='replace')}")

        detail = fetch_article_detail(art['url'], cookies)
        if detail['title'] == 'ERROR':
            print(f"  -> ERROR: {detail['content'][:100]}")
            stats['errors'] += 1
            continue

        art_date = detail['liangke_date']
        if art_date:
            art_date_str = art_date.strftime('%Y-%m-%d')
        else:
            art_date_str = art.get('date')

        if art_date_str and art_date_str not in target_dates:
            print(f"  -> Skipped (date: {art_date_str}, not in target range)")
            stats['skipped'] += 1
            _polite_delay()
            continue

        # Extract original date from reference link
        ref_url = ''
        ref_title = ''
        original_date = None
        source_domain = ''

        if detail['primary_reference']:
            ref_url = detail['primary_reference']['url']
            ref_title = detail['primary_reference']['text']
            print(f"  -> Ref: {ref_url[:80]}")
            original_date = get_original_date(ref_url)
            if original_date:
                print(f"  -> Original date: {original_date}")
            try:
                source_domain = urlparse(ref_url).netloc
            except Exception:
                pass
            time.sleep(0.3)
        else:
            original_date = None

        # Dedup check
        exists = article_exists(ref_url, detail['url'])
        if exists:
            print(f"  -> SKIP (exists in DB)")
            stats['skipped'] += 1
            _polite_delay()
            continue

        if detail['title']:
            similar = find_similar_article(detail['title'], art_date_str or today)
            if similar:
                print(f"  -> DUPLICATE (similar to id={similar['id']})")
                stats['skipped'] += 1
                _polite_delay()
                continue

        # Keyword tag (temporary, will be overridden by LLM)
        kw_tags = auto_tag(detail['title'], detail['content'])
        weekly_kw = kw_tags.get('weekly', ['宏观态势']) if kw_tags else ['宏观态势']

        # Page type
        page_type = ''
        if '/flash/' in art['url']: page_type = 'flash'
        elif '/reference/' in art['url']: page_type = 'reference'
        elif '/article/' in art['url']: page_type = 'article'

        print(f"  KW tag: {weekly_kw[0] if weekly_kw else '?'} | type: {page_type} | {len(detail['content'])}c")

        pending.append({
            'detail': detail,
            'ref_url': ref_url,
            'ref_title': ref_title,
            'original_date': original_date,
            'source_domain': source_domain,
            'kw_tags': kw_tags,
            'page_type': page_type,
            'art_date_str': art_date_str,
        })

        _polite_delay()

    # ── Phase 2: Dictionary scorer + LLM for uncertain cases ──
    hard_cats = {}   # idx -> category (dictionary scorer)
    llm_cats = {}    # idx -> category (LLM)
    if pending:
        scorer = get_scorer()
        # Step 1: Dictionary-based classification (strong_signals + weighted scoring)
        for idx, p in enumerate(pending):
            title = p['detail']['title']
            content = p['detail']['content'] or ''
            result = scorer.classify(title, content)
            if result:
                hard_cats[idx] = result
                kw_cat = p['kw_tags'].get('weekly', ['?'])[0] if p['kw_tags'] else '?'
                print(f"  [{idx+1}] DICT: {kw_cat} -> {result} | {title[:60]}")

        hard_count = len(hard_cats)
        uncertain_count = len(pending) - hard_count
        print(f"\n--- Dictionary: {hard_count} determined, {uncertain_count} → LLM ---")

        # Step 2: LLM for uncertain cases (batched, max 10 per batch)
        if uncertain_count > 0:
            uncertain_indices = [i for i in range(len(pending)) if i not in hard_cats]
            BATCH_SIZE = 10
            for batch_start in range(0, len(uncertain_indices), BATCH_SIZE):
                batch_indices = uncertain_indices[batch_start:batch_start + BATCH_SIZE]
                info_list = [
                    f"{pending[i]['detail']['title'][:120]} | {((pending[i]['detail']['content'] or '')[:300]).strip()}"
                    for i in batch_indices
                ]
                llm_results = _llm_classify_batch(info_list)
                if llm_results:
                    for local_idx, cat in llm_results.items():
                        if local_idx < len(batch_indices):
                            orig_idx = batch_indices[local_idx]
                            llm_cats[orig_idx] = cat
                            old_cat = pending[orig_idx]['kw_tags'].get('weekly', ['?'])[0] if pending[orig_idx]['kw_tags'] else '?'
                            title_short = pending[orig_idx]['detail']['title'][:60]
                            print(f"  [{orig_idx+1}] LLM: {old_cat} -> {cat} | {title_short}")
                else:
                    print(f"  LLM batch {batch_start//BATCH_SIZE+1} returned empty, using keyword tags as fallback")

    # Merge hard + LLM results
    all_cats = {**hard_cats, **llm_cats}  # hard wins if somehow both exist

    # ── Phase 3: Insert into DB with LLM tags ──
    if pending:
        print(f"\n--- Inserting {len(pending)} articles ---")
    for idx, p in enumerate(pending):
        # Override weekly tag with hard/LLM result
        final_tags = p['kw_tags'] or {}
        if idx in all_cats:
            if isinstance(final_tags, dict):
                final_tags['weekly'] = [all_cats[idx]]
            else:
                final_tags = {'weekly': [all_cats[idx]], 'search_tags': [], 'knowledge_graph': {}}

        try:
            result = insert_or_update_article(
                reference_url=p['ref_url'],
                liangke_url=p['detail']['url'],
                title=p['detail']['title'],
                content=p['detail']['content'],
                original_date=p['original_date'],
                liangke_date=p['detail']['liangke_date'] or datetime.strptime(today, '%Y-%m-%d').date(),
                source_domain=p['source_domain'],
                reference_title=p['ref_title'],
                tags=final_tags,
                page_type=p['page_type']
            )

            if result['action'] == 'inserted':
                stats['inserted'] += 1
            else:
                stats['updated'] += 1
        except Exception as e:
            print(f"  -> DB ERROR: {e}")
            stats['errors'] += 1

    total = get_article_count()
    print(f"\n{'='*50}")
    print(f"Daily scrape completed for {today}")
    print(f"  New articles:     {stats['inserted']}")
    print(f"  Updated articles: {stats['updated']}")
    print(f"  Skipped (old):    {stats['skipped']}")
    print(f"  Errors:           {stats['errors']}")
    print(f"  Total in DB:      {total}")
    print(f"{'='*50}")

    # Sync to OneDrive shared folder
    try:
        from sync_to_onedrive import sync_all
        sync_all()
    except Exception as e:
        print(f'  [WARN] OneDrive sync failed: {e}')


if __name__ == '__main__':
    main()
