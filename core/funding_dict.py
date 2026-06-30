"""
Funding entity dictionary for quantum investment news tagging.
Unified from: entity_dict.py + investment_extractor.py CHINESE_COMPANIES + investor_patterns.

Project namespace: tags.funding
Does NOT touch tags.weekly / tags.search_tags / tags.knowledge_graph.
"""

# ── Chinese Quantum Companies (被投企业) ────────────────────────────

QUANTUM_COMPANIES = {
    # 超导量子计算
    '本源量子': ['本源量子', '本源量子计算', 'Origin Quantum'],
    '量旋科技': ['量旋科技', 'SpinQ'],
    '相干科技': ['相干科技', '相干（北京）'],
    '逻辑比特': ['逻辑比特', '逻辑比特科技'],
    '矩量光启': ['矩量光启'],
    '武汉超磁科技': ['武汉超磁科技'],
    # 光量子计算
    '玻色量子': ['玻色量子'],
    '图灵量子': ['图灵量子', 'TuringQ'],
    '正则量子': ['正则量子'],
    '奇算光启': ['奇算光启'],
    # 离子阱量子计算
    '华翊量子': ['华翊量子', '华翊博奥'],
    '幺正量子': ['幺正量子'],
    # 中性原子量子计算
    '中科酷原': ['中科酷原'],
    '无量量子': ['无量量子', '中器无量', '上海中器无量量子'],
    '太一量生': ['太一量生'],
    '两仪万象': ['两仪万象', '两仪万向'],
    '无问清芯': ['无问清芯', '杭州无问清芯'],
    '不筹量子': ['不筹量子'],
    '原子矩阵': ['原子矩阵', 'MatriQ'],
    # 量子精密测量 / 仪器
    '国仪量子': ['国仪量子', 'CIQTEK'],
    '国测量子': ['国测量子'],
    '未磁科技': ['未磁科技'],
    '频准激光': ['频准激光'],
    '国光量子': ['国光量子', '中科国光量子', '鲲盾量子'],
    # 量子通信
    '国盾量子': ['国盾量子', '科大国盾', 'QuantumCTek'],
    '国科量子': ['国科量子', '湖北国科量子', '武汉国科量子'],
    # 光通信 / 量子材料
    '森一量子': ['森一量子'],
    # 光量子集成芯片
    '硅臻量子': ['硅臻量子'],
    # 量子AI / 安全
    '矩阵时光': ['矩阵时光', '矩阵时光数字科技'],
    # 量子保密通信（被收购标的）
    '天芯量子': ['天芯量子', '广州市天芯量子'],
    '维刻量光': ['维刻量光'],
    # 量子软件 / 应用
    '微观纪元': ['微观纪元'],
    '量坤科技': ['量坤科技'],
    '瀚海量子': ['瀚海量子'],
    '隧穿智元': ['隧穿智元'],
    # 上游供应链
    '知冷低温': ['知冷低温'],
    '量羲技术': ['量羲技术'],
}

# ── International Quantum Companies ─────────────────────────────────

INTERNATIONAL_QUANTUM_COMPANIES = {
    # 超导量子计算
    'IBM Quantum': ['IBM Quantum', 'IBM'],
    'Rigetti': ['Rigetti', 'Rigetti Computing'],
    'OQC': ['OQC', 'Oxford Quantum Circuits'],
    'Nord Quantique': ['Nord Quantique'],
    # 离子阱量子计算
    'Quantinuum': ['Quantinuum'],
    'IonQ': ['IonQ'],
    'Oxford Ionics': ['Oxford Ionics'],
    # 中性原子量子计算
    'Pasqal': ['Pasqal', 'PASQAL'],
    'QuEra': ['QuEra', 'QuEra Computing'],
    'Atom Computing': ['Atom Computing'],
    'Infleqtion': ['Infleqtion', 'ColdQuanta'],
    # 光量子计算
    'PsiQuantum': ['PsiQuantum', 'Psi Quantum'],
    'Xanadu': ['Xanadu'],
    'Quandela': ['Quandela'],
    # 硅自旋量子计算
    'Diraq': ['Diraq'],
    'Silicon Quantum Computing': ['Silicon Quantum Computing', 'SQC'],
    'Quobly': ['Quobly'],
    # 拓扑量子计算
    'Microsoft Quantum': ['Microsoft Quantum', 'Microsoft Azure Quantum', 'Azure Quantum'],
    # 量子退火
    'D-Wave': ['D-Wave', 'D-Wave Systems', 'DWave'],
    # 量子软件 / 算法
    'Algorithmiq': ['Algorithmiq'],
    'Classiq': ['Classiq', 'Classiq Technologies'],
    'Q-CTRL': ['Q-CTRL', 'Q Ctrl'],
    'QunaSys': ['QunaSys'],
    'Horizon Quantum': ['Horizon Quantum', 'Horizon Quantum Computing'],
    'Quanscient': ['Quanscient'],
    'Quantum Machines': ['Quantum Machines'],
    # 量子传感 / 测量
    'SBQuantum': ['SBQuantum'],
    'Qnami': ['Qnami'],
    'QuantX Labs': ['QuantX Labs'],
    # 量子通信 / 安全
    'Quantum Bridge': ['Quantum Bridge'],
    'Pramatra Space': ['Pramatra Space'],
    'ID Quantique': ['ID Quantique', 'IDQ'],
    # 上游供应链
    'QuantWare': ['QuantWare'],
    'Alice & Bob': ['Alice & Bob', 'Alice and Bob'],
    # 其他
    'Universal Quantum': ['Universal Quantum'],
    'Quantum Motion': ['Quantum Motion'],
    'SEEQC': ['SEEQC'],
    'DQC': ['DQC', 'Delft Quantum Computing'],
    'Origin Quantum': ['Origin Quantum', '本源量子', '本源量子计算'],
    'QuantumCTek': ['QuantumCTek', '国盾量子', '科大国盾'],
}

# ── Investment Institutions (投资机构) ──────────────────────────────

INVESTORS = {
    # 国家队 / 央企基金
    '国家创业投资引导基金': ['国家创业投资引导基金', '国家创投引导基金'],
    '社保基金中关村专项基金': ['社保基金中关村专项基金'],
    '北京信息产业发展投资基金': ['北京信息产业发展投资基金'],
    '北京高精尖产业发展基金': ['北京高精尖产业发展基金', '北工投资'],
    '北京市量子基金': ['北京市量子基金'],
    '北京医药健康基金': ['北京医药健康基金'],
    '上海未来产业基金': ['上海未来产业基金'],
    '中国互联网投资基金': ['中国互联网投资基金', '中网投'],
    '中国电信投资': ['中国电信集团投资', '中国电信投资'],
    '中国移动链长基金': ['中国移动链长基金', '中国移动'],
    '中移数字新经济产业基金': ['中移数字新经济产业基金', '北京中移数字新经济产业基金'],
    '岭澜基金': ['岭澜基金'],
    '千里马资本': ['千里马资本'],
    '中国兵器集团': ['中国兵器集团', '中国兵器装备集团', '南方资产'],
    '深创投': ['深创投', '深圳市创新投资'],
    '深投控': ['深投控', '深圳市投资控股'],
    '合肥高投': ['合肥高投', '合肥国有资本创投'],
    '四川振兴集团': ['四川振兴集团', '四川产业振兴', '四川振兴'],
    '央视融媒体基金': ['央视融媒体基金'],
    '亦庄国投': ['亦庄国投'],

    # 头部 VC
    '中科创星': ['中科创星'],
    '高瓴创投': ['高瓴创投', '高瓴'],
    '红杉中国': ['红杉中国', '红杉资本', '红杉'],
    '顺为资本': ['顺为资本'],
    '经纬创投': ['经纬创投', '经纬中国'],
    '蓝驰创投': ['蓝驰创投'],
    '英诺天使基金': ['英诺天使基金', '英诺天使'],
    '启赋资本': ['启赋资本'],
    '君联资本': ['君联资本'],
    '达晨财智': ['达晨财智'],
    '毅达资本': ['毅达资本'],
    '基石资本': ['基石资本'],
    'IDG资本': ['IDG资本', 'IDG'],
    '鼎晖投资': ['鼎晖投资', '鼎晖'],
    '华控基金': ['华控基金'],
    '东证创新': ['东证创新'],
    '联想创投': ['联想创投'],
    'BV百度风投': ['BV百度风投', '百度风投'],
    '水木清华校友基金': ['水木清华校友基金'],
    '明势创投': ['明势创投'],
    '创新工场': ['创新工场'],
    '天际资本': ['天际资本'],
    '普华资本': ['普华资本'],
    '彬复资本': ['彬复资本'],
    '盈富泰克': ['盈富泰克'],
    '昆仑资本': ['昆仑资本'],
    '朗玛峰创投': ['朗玛峰创投'],
    '盛世投资': ['盛世投资'],
    '逐鹿资本': ['逐鹿资本'],
    '东方嘉富': ['东方嘉富'],
    '华夏恒天': ['华夏恒天'],
    '浙大联创': ['浙大联创投资', '浙大联创'],
    '藕舫天使': ['藕舫天使'],
    '西湖科创投': ['西湖科创投'],
    '元禾原点': ['元禾原点'],
    '北京机器人产业基金': ['北京机器人产业基金'],
    '南京未来产业天使基金': ['南京未来产业天使基金'],
    '国新基金': ['国新基金', '国新'],
    '国科嘉和': ['国科嘉和'],
    '锦富基金': ['锦富基金'],
    '沿海基金': ['沿海基金'],
    '晶凯资本': ['晶凯资本'],
    '恒泰华盛': ['恒泰华盛'],
    '青岛瀚瑞': ['青岛瀚瑞'],
    'L2F光源基金': ['L2F光源创业者基金', 'L2F', '光源创业者基金'],
    '混沌投资': ['混沌投资'],
    '和利资本': ['和利资本'],
    '钧山资本': ['钧山资本'],
    '千乘资本': ['千乘资本'],
    '德同资本': ['德同资本'],
    '复容投资': ['复容投资'],
    '东方富海': ['东方富海'],
    '海愿资本': ['海愿资本'],
    '夏佐全': ['夏佐全', '正轩投资'],

    # 产业资本
    '蚂蚁集团': ['蚂蚁集团'],
    '科大讯飞': ['科大讯飞', '讯飞创投'],
    '华为哈勃': ['华为哈勃', '哈勃投资'],
    '百度': ['百度'],
    '阿里巴巴': ['阿里巴巴', '阿里云'],
    '腾讯': ['腾讯'],
    '吉利资本': ['吉利资本', '吉利'],
    '比亚迪': ['比亚迪'],
    '商汤科技': ['商汤科技', '商汤'],
    '复星': ['复星', '复星资本'],
    '上汽金控': ['上汽金控', '上汽集团'],
    '晶科能源': ['晶科能源'],
    '隆利科技': ['隆利科技'],
    '联美控股': ['联美控股'],
    '金冠电气': ['金冠电气'],
    '中芯聚源': ['中芯聚源'],
    '翌昕投资': ['翌昕投资'],
    '三七互娱': ['三七互娱'],
    '彩讯股份': ['彩讯股份'],
    '国富量子': ['国富量子', '国富创新'],
    '国芯科技': ['国芯科技'],
    '天阳科技': ['天阳科技'],

    # 金融 / 投行系
    '招银国际': ['招银国际'],
    '工银资本': ['工银资本'],
    '北京金控': ['北京金控'],
    '国泰君安创新投资': ['国泰君安创新投资', '国泰君安'],
    '中信建投投资': ['中信建投投资', '中信建投'],
    '华泰联合': ['华泰联合'],
    '财通资本': ['财通资本'],
    '金鼎资本': ['金鼎资本'],

    # 地方国资
    '京国管': ['京国管'],
    '京国盛': ['京国盛'],
    '朝阳顺禧': ['朝阳顺禧'],
    '浦东科创': ['浦东科创', '浦东创投'],
    '成都天创投': ['成都天创投'],
    '光谷天使基金': ['光谷天使基金'],
    '湖北科投': ['湖北科投'],
    '粤科投': ['粤科投'],
    '广州金控': ['广州金控'],
    '朝科创': ['朝科创'],
    '中咨基金': ['中咨基金'],

    # FA / 精品投行
    '光源资本': ['光源资本'],
    '指数资本': ['指数资本'],
    '云岫资本': ['云岫资本'],

    # ── 国际量子公司（作战略投资方时）── 已移至 INTERNATIONAL_QUANTUM_COMPANIES
    # Quantinuum/IonQ 等默认作为被投企业，仅在领投/跟投语境中识别为投资方

    # ── 国际 VC / PE ──
    'United Ventures': ['United Ventures'],
    'Inventure VC': ['Inventure VC', 'Inventure'],
    'CDP Venture Capital': ['CDP Venture Capital', 'CDP', 'Cassa Depositi e Prestiti'],
    'DCVC': ['DCVC'],
    'Bessemer Venture Partners': ['Bessemer Venture Partners', 'Bessemer'],
    'Lightspeed Venture Partners': ['Lightspeed Venture Partners', 'Lightspeed'],
    'Andreessen Horowitz': ['Andreessen Horowitz', 'a16z'],
    'Sequoia Capital': ['Sequoia Capital', 'Sequoia'],
    'SoftBank Vision Fund': ['SoftBank Vision Fund', 'SoftBank', '软银'],
    'Temasek': ['Temasek', '淡马锡'],
    'In-Q-Tel': ['In-Q-Tel', 'IQT'],
    'Prelude Ventures': ['Prelude Ventures'],
    'Founders Fund': ['Founders Fund'],
    'Playground Global': ['Playground Global'],
    'Eclipse Ventures': ['Eclipse Ventures'],
    'Octopus Ventures': ['Octopus Ventures'],
    'Amadeus Capital': ['Amadeus Capital', 'Amadeus Capital Partners'],
    'M Ventures': ['M Ventures'],
    'Capricorn Partners': ['Capricorn Partners'],
    'Vsquared Ventures': ['Vsquared Ventures'],
    'Quantonation': ['Quantonation'],
    '2M Ventures': ['2M Ventures'],
    'LIFTT': ['LIFTT'],
    'Voima Ventures': ['Voima Ventures'],
    'Maki.vc': ['Maki.vc', 'Maki VC'],

    # ── 国际产业资本 ──
    'NVIDIA': ['NVIDIA', 'Nvidia', '英伟达'],
    'Google': ['Google', '谷歌'],
    'Samsung Ventures': ['Samsung Ventures', '三星'],
    'Sony Innovation Fund': ['Sony Innovation Fund', '索尼'],
    'Bosch Ventures': ['Bosch Ventures', '博世'],
    'Siemens': ['Siemens', '西门子'],
    'BMW i Ventures': ['BMW i Ventures', '宝马'],
    'Applied Ventures': ['Applied Ventures'],
    'Lam Research': ['Lam Research'],
    'Cerberus Capital': ['Cerberus Capital', 'Cerberus'],

    # ── 国际政府/公共基金 ──
    'European Innovation Council': ['European Innovation Council', 'EIC', 'EIC Accelerator'],
    'Innovate UK': ['Innovate UK'],
    'Wellcome Leap': ['Wellcome Leap'],
    'DARPA': ['DARPA'],
    'NIST': ['NIST'],
    'BDC Capital': ['BDC Capital', 'BDC'],
    'Business Finland': ['Business Finland'],
    'VTT': ['VTT', 'VTT Technical Research'],
    'NRFC': ['NRFC', 'National Reconstruction Fund'],
}

# ── Round Classification ─────────────────────────────────────────────

# Priority order: more specific patterns first
ROUND_PATTERNS = [
    # IPO stages (most specific first, Pre-IPO before generic IPO)
    (r'IPO注册通过|注册获批|注册批复|证监会.*注册', 'IPO-注册'),
    (r'IPO过会|上市委.*通过|科创板.*过会|创业板.*过会', 'IPO-过会'),
    (r'提交注册|IPO受理|上市辅导|辅导备案', 'IPO-辅导'),
    (r'Pre-IPO|上市前融资', 'Pre-IPO'),
    (r'(?<!Pre-)SPAC|借壳上市|特殊目的收购', 'SPAC'),
    (r'(?<!Pre-)(?<![a-zA-Z])IPO|首次公开|上市申请|敲钟|挂牌', 'IPO'),
    # M&A
    (r'收购|并购|acquires?\b|acquisition', '收购'),
    # Fund — only when article is about fund establishment, not fund-as-investor
    (r'基金设立|设立.*基金|基金成立|基金落地|基金.*启航|基金.*发布|参设.*基金|出资.*基金|设立.*产业基金', '基金'),
    # Rounds (Pre-A before A to avoid false matches)
    (r'E\+{0,2}轮', 'E轮'),
    (r'D\+{0,2}轮', 'D轮'),
    (r'C\+{0,2}轮', 'C轮'),
    (r'B\+{0,2}轮', 'B轮'),
    (r'(?<!Pre-)A\+{1,2}轮', 'A+轮'),
    (r'Pre-A|PreA', 'Pre-A'),
    (r'(?<!Pre-)(?<![a-zA-Z])A轮', 'A轮'),
    (r'种子轮', '种子轮'),
    (r'天使\+{0,1}轮', '天使轮'),
    # Strategic
    (r'战略投资|战略融资|战投|注资|增资|战略配售', '战略融资'),
]

# ── Amount Extraction Patterns ──────────────────────────────────────

# (regex, scale) - scale is the multiplier to get CNY
AMOUNT_PATTERNS_NUMERIC = [
    (r'(\d+(?:\.\d+)?)\s*亿\s*美?元?', 1e8),   # 2亿元, 1.5亿美元
    (r'(\d+(?:\.\d+)?)\s*万\s*美?元?', 1e4),   # 3000万元
    (r'(\d+(?:\.\d+)?)\s*百万\s*美?元?', 1e6),  # 5百万美元
]

AMOUNT_PATTERNS_VAGUE = [
    # (regex, estimated CNY)
    ('数亿', 3e8),
    ('近亿', 9e7),
    ('逾亿', 1.5e8),
    ('超亿', 1.5e8),
    ('亿元级', 1.5e8),
    ('数千万', 3e7),
    ('近千万', 9e6),
    ('逾千万', 1.5e7),
    ('超千万', 1.5e7),
]

# USD exchange rate (approximate)
USD_RATE = 7.2


# ── Alias Resolution ─────────────────────────────────────────────────

def build_alias_map():
    """Build flat alias→canonical map from QUANTUM_COMPANIES + INVESTORS."""
    alias_map = {}
    for canonical, aliases in {**QUANTUM_COMPANIES, **INTERNATIONAL_QUANTUM_COMPANIES, **INVESTORS}.items():
        for alias in aliases:
            alias_map[alias.lower()] = canonical
    return alias_map

_ALIAS_MAP = build_alias_map()


def normalize_entity(name):
    """Return canonical entity name if known, else original."""
    return _ALIAS_MAP.get(name.lower().strip(), name.strip())
