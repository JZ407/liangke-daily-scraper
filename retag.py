"""Re-tag all daily articles with enhanced keywords."""
import pymysql, json

KEYWORDS = {
    '量子计算': ['quantum comput', 'quantum processor', 'qubit', '量子计算', '量子比特', 'qpu', 'quantum chip'],
    '量子通信': ['quantum communic', 'qkd', 'quantum key', '量子通信', '量子密钥', '量子网络', 'quantum internet'],
    '后量子密码': ['post-quantum', 'pqc', 'quantum safe', '后量子密码', '抗量子', '量子安全', 'pqcrypto'],
    '量子传感': ['quantum sens', 'magnetometer', 'gravimeter', '量子传感', '量子雷达', 'quantum radar'],
    '硬件平台': ['superconducting', 'ion trap', 'trapped ion', 'neutral atom', 'photonic', 'topological',
              '超导', '离子阱', '中性原子', '光量子', '拓扑', 'quantum dot', 'silicon spin', '硅自旋',
              '金刚石', 'nv色心', 'majorana', 'transmon'],
    '量子物理': ['quantum mechanic', 'entanglement', 'superposition', '量子纠缠', '量子叠加',
              'bell state', 'ghz', 'schrodinger'],
    '行业应用': ['drug discover', 'material', 'chemistry', 'finance', 'optimization',
              '制药', '材料', '化学', '金融', '优化', '物流', '药物', '分子'],
    '政策标准': ['policy', 'regulation', 'standard', 'nist', '政策', '标准', '法规', '监管', '路线图', '白皮书'],
    '企业与机构': ['ionq', 'ibm', 'google', 'microsoft', 'd-wave', 'rigetti', 'quantinuum',
                '本源量子', '国盾量子', '国仪量子', '华为', '阿里巴巴', '腾讯', '百度',
                'psiquantum', 'xanadu', 'pasqal', 'classiq', 'q-ctrl', 'oxford ionics',
                'oracle', 'nvidia', 'intel', 'amazon', '富士通', '日立', '东芝'],
    '融资商业': ['funding', 'series', 'raised', 'million', 'billion', 'ipo', 'nyse', 'nasdaq',
              '融资', '投资', '收购', '上市', '估值', '财报', '营收', '利润', '股权'],
}

SPECIFIC_TAGS = {
    'QKD': ['qkd', 'quantum key distribution', '量子密钥分发'],
    'PQC': ['pqc', 'post-quantum cryptograph', '后量子密码', '抗量子密码'],
    '超导': ['superconducting', 'transmon', '超导'],
    '离子阱': ['ion trap', 'trapped ion', '离子阱', '囚禁离子'],
    '光量子': ['photonic', 'photon', '光量子', '光子'],
    'NIST': ['nist'],
    'arXiv': ['arxiv', '预印本'],
    '融资': ['funding', 'million', 'billion', 'raised', 'ipo', '融资', '投资', '估值'],
    '量子纠错': ['error correct', 'fault tolerant', 'surface code', '量子纠错', '纠错码', '容错'],
    '半导体': ['semiconductor', 'cmos', 'foundry', 'wafer', '半导体', '制造'],
    'AI/ML': ['machine learning', 'neural network', 'tensorflow', '机器学习', '人工智能', 'llm'],
}

CATEGORY_KEYWORDS = {
    '资本运作': [
        '融资', '投资', '风投', 'vc ', 'pe ', 'ipo', '上市', '招股',
        '估值', '亿美元', '万美元', '千万', '百万', '亿元',
        '收购', '并购', '合并', '分拆', '剥离', '整合',
        '资助', '拨款', '补贴', '基金', '预算', '经费',
        '营收', '收入', '利润', '亏损', '财报', '业绩', '增长',
        '股权', '股东', '控股', '参股', '注资', '增资', '扩股',
        'a轮', 'b轮', 'c轮', 'd轮', '种子轮', '天使轮', '战略融资',
        'raise', 'raised', 'raises', 'raising', 'funding', 'fund', 'funds',
        'series', 'equity', 'offering', 'pricing of', 'closes',
        'completes acquisition', 'completes sale', 'acquires',
        'stock', 'shares', 'shareholder', 'market cap',
        'capital', 'backed by', 'led by', 'investor', 'venture',
        'grant', 'awarded', 'contract award', 'million dollar',
        'billion dollar', 'm deal', 'mn deal', 'loan', 'bond',
        'debt', 'credit', 'capital raise', 'capital raising',
    ],
    '产品动态': [
        '产品', '发布', '推出', '上市', '芯片', '处理器', '计算机',
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


def auto_tag(title, content):
    text = (title or '') + ' ' + (content or '')[:2000]
    text_lower = text.lower()
    tags = []

    for category, words in KEYWORDS.items():
        for word in words:
            if word.lower() in text_lower:
                tags.append(category)
                break

    for tag, words in SPECIFIC_TAGS.items():
        for word in words:
            if word.lower() in text_lower:
                tags.append(tag)
                break

    scores = {}
    for tag, words in CATEGORY_KEYWORDS.items():
        score = 0
        for word in words:
            if word.lower() in text_lower:
                score += 1
        scores[tag] = score

    if max(scores.values()) > 0:
        cat_tag = max(CATEGORY_PRIORITY, key=lambda t: (scores[t], CATEGORY_PRIORITY.index(t)))
    else:
        cat_tag = '宏观态势'
    tags.append(cat_tag)

    return list(set(tags))


if __name__ == '__main__':
    conn = pymysql.connect(host='127.0.0.1', user='scraper', password='scraper123',
                           database='liangke_scraper', charset='utf8mb4')
    c = conn.cursor()
    c.execute('SELECT id, title, content FROM articles ORDER BY id')
    rows = c.fetchall()

    for art_id, title, content in rows:
        new_tags = auto_tag(title or '', content or '')
        c.execute('UPDATE articles SET tags=%s WHERE id=%s', (json.dumps(new_tags, ensure_ascii=False), art_id))

    conn.commit()

    c.execute('''SELECT
        SUM(CASE WHEN tags LIKE "%%资本运作%%" THEN 1 ELSE 0 END) as 资本运作,
        SUM(CASE WHEN tags LIKE "%%产品动态%%" THEN 1 ELSE 0 END) as 产品动态,
        SUM(CASE WHEN tags LIKE "%%企业资讯%%" THEN 1 ELSE 0 END) as 企业资讯,
        SUM(CASE WHEN tags LIKE "%%科技前沿%%" THEN 1 ELSE 0 END) as 科技前沿,
        SUM(CASE WHEN tags LIKE "%%宏观态势%%" THEN 1 ELSE 0 END) as 宏观态势
        FROM articles''')
    row = c.fetchone()
    print('五大标签分布:')
    for i, cat in enumerate(['资本运作', '产品动态', '企业资讯', '科技前沿', '宏观态势']):
        print(f'  {cat}: {row[i]}')
    print(f'  总计: {len(rows)}')

    conn.close()
