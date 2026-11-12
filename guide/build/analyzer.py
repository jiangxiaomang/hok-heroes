# -*- coding: utf-8 -*-
"""
王者荣耀 单英雄攻略 · 机制分析器

从官方技能描述中抽取「该英雄独有」的机制事实，供 13 节模板填充。
原则：只做抽取与归类，不生成与该英雄无关的通用话术。
"""
import re

# 官方 role 编码 -> 分路名
ROLE_MAP = {'1': '对抗路', '2': '打野', '3': '中路', '4': '发育路', '5': '游走'}
LANES = ['对抗路', '打野', '中路', '发育路', '游走']

# 控制类关键词
CTRL_KW = ['击飞', '击 飞', '击退', '眩晕', '晕眩', '减速', '定身', '沉默', '缴械',
           '拉拽', '拉扯', '免控', '霸体', '免疫', '嘲讽', '击晕', '控制', '打断',
           '净化', '驱散', '压制', '禁锢', '束缚', '眩晕']
# 硬控 = 可打断施法/被反打的强控制；沉默、减速、缴械等属软控/状态干扰
HARD_CTRL = ['击飞', '击 飞', '眩晕', '晕眩', '定身', '击退', '免控', '霸体',
             '免疫', '嘲讽', '击晕', '禁锢', '束缚', '拉拽', '拉扯']

# 资源 / 层数机制
RES_KW = ['层', '怒气', '能量', '印记', '碎片', '残暴', '战意', '充能', '蓄力',
          '蓝量', '怒气值', '能量条', '状态', '印记数', 'buff', '叠加']

# 伤害类型
DMG_KW = ['物理伤害', '法术伤害', '真实伤害']

# 射程 / 范围
RANGE_KW = ['远程', '近战', '范围', '全体', '扇形', '直线', '环形', '以自身为中心',
            '指定区域', '指定方向']


def clauses(text):
    """把技能描述切成语义小句。"""
    if not text:
        return []
    text = re.sub(r'\s+', '', text)
    parts = re.split(r'[。；]', text)
    out = []
    for p in parts:
        p = p.strip()
        p = re.sub(r'^(被动|技能效果)?[:：]?', '', p)
        if len(p) >= 4:
            out.append(p)
    return out


def pick(cl, kws, exclude=()):
    """挑出含关键词且不含排除词的句子。"""
    res = []
    for c in cl:
        if any(k in c for k in kws) and not any(k in c for k in exclude):
            res.append(c)
    return res


DROP_UNIT = r'(?:秒|点|米|范围)'
KEEP_UNIT = r'(?:层|次|个|段|团)'


def strip_numbers(s):
    """把技能数值剥离，只保留机制描述（数值会随版本变，不进机制结论）。

    顺序：整块数值列表 -> 数字+可丢弃单位 -> 数字+保留单位 -> 裸数字
    -> 清理空括号/残留符号 -> 整理标点。
    """
    if not s:
        return ''
    # 1) 斜杠数值列表（350/420/490 或 30%/32%/34%）
    s = re.sub(r'\d+(?:\.\d+)?(?:%\s*[&+＋]?\s*/\s*\d+(?:\.\d+)?%?)+', '', s)
    # 2) 波浪号区间（30~72 / 30~72点 / 30~72%）
    s = re.sub(r'\d+(?:\.\d+)?\s*[~～]\s*\d+(?:\.\d+)?\s*(?:' + DROP_UNIT + r'|%)?', '', s)
    # 3) 数字 + 可丢弃单位
    s = re.sub(r'\d+(?:\.\d+)?\s*' + DROP_UNIT, '', s)
    # 4) 数字 + 保留单位（保留名词，去掉数字）
    s = re.sub(r'\d+(?:\.\d+)?\s*(' + KEEP_UNIT + ')', r'\1', s)
    # 5) 裸数字（含百分号）
    s = re.sub(r'\d+(?:\.\d+)?%?', '', s)
    # 5b) 纯数值加成括号整体删除（含 攻击 / 加成 / 最大生命 / 护盾 的括号）
    s = re.sub(r'[（(]\s*[+＋][^（）()]{0,30}(?:攻击|加成|最大生命|护盾)[^（）()]{0,12}[）)]', '', s)
    # 6) 空括号 / 加成号残留
    s = re.sub(r'[（(]\s*[+＋]?\s*[）)]', '', s)
    s = re.sub(r'点(?=(?:物理|法术|真实)伤害|(?:物理|法术|真实)防御|护盾|加成)', '', s)
    s = re.sub(r'\s*[+＋]\s*(?=[）)。，,、])', '', s)
    s = re.sub(r'[（(]\s*[）)]', '', s)
    # 7) 孤立符号
    s = re.sub(r'\s*[~/～*&+＋]{1,}\s*(?=[）。，,、])', '', s)
    s = re.sub(r'(?<=[，。；：、])\s*[~/～*&+＋]+\s*', '', s)
    s = re.sub(r'[~/～*&+＋]{2,}', '', s)
    s = re.sub(r'[（(]\s*\)', '', s)
    # 8) 合并重复的括号加成段
    for _ in range(3):
        s = re.sub(r'(\([^()]{1,40}\))(?:\1)+', r'\1', s)
    # 9) 整理
    s = re.sub(r'\s+', '', s)
    s = s.replace('、、', '、').replace('，，', '，')
    s = re.sub(r'[，、]\s*[。]', '。', s)
    s = s.strip('，。、 ；;')
    return s


def analyze(hero):
    """对一个英雄做机制抽取，返回可直接进模板的结构。"""
    skills = hero.get('skills') or []
    passive = ''
    actives = []
    for i, s in enumerate(skills):
        if i == 0:
            passive = s.get('desc', '')
        else:
            actives.append(s)

    pcl = clauses(passive)
    # 被动：机制型句子优先
    p_res = pick(pcl, RES_KW)
    p_ctrl = pick(pcl, CTRL_KW)
    p_rng = pick(pcl, RANGE_KW)
    p_dmg = pick(pcl, DMG_KW)

    passive_core = None
    for c in p_res + p_ctrl + p_rng + p_dmg:
        if len(c) >= 6:
            passive_core = c
            break
    if not passive_core and pcl:
        passive_core = pcl[0]

    # 各主动技能标签
    sk = []
    for i, s in enumerate(actives):
        cl = clauses(s.get('desc', ''))
        ctrl = [c for c in cl if any(k in c for k in CTRL_KW)]
        res = [c for c in cl if any(k in c for k in RES_KW)]
        dmg = [c for c in cl if any(k in c for k in DMG_KW)]
        rng = [c for c in cl if any(k in c for k in RANGE_KW)]
        sk.append({
            'i': i + 1,
            'name': s.get('name', ''),
            'cd': s.get('cd', ''),
            'mana': s.get('mana', ''),
            'ctrl': ctrl, 'res': res, 'dmg': dmg, 'rng': rng,
            'clauses': cl,
            'has_ctrl': bool(ctrl),
            'has_res': bool(res),
            'is_ult': (i + 1) == len(actives) and len(actives) >= 3,
        })

    # 核心技能：带控制或资源转换的那个
    core = None
    for x in sk:
        if x['ctrl'] or x['res']:
            core = x
            break
    if core is None and sk:
        core = sk[-1]

    # 资源机制：谁提供、怎么消耗、上限多少
    res_mech = []
    for c in pcl + [x for x_ in sk for x in x_['clauses']]:
        if any(k in c for k in ['叠', '层', '最多', '消耗', '获得', '攒', '充能',
                                '弹药', '次数', '能量', '怒气', '印记', '碎片',
                                '叠加', '重置', '清空', '上限', '攒满']):
            if c not in res_mech:
                res_mech.append(c)

    # 输出方式：普攻 / 技能 / 强化普攻
    atk_mode = []
    for c in pcl + [x for x_ in sk for x in x_['clauses']]:
        if any(k in c for k in ['普攻', '普通攻击', '下次攻击', '强化', '暴击',
                                '攻击速度', '攻速', '平A']):
            if c not in atk_mode:
                atk_mode.append(c)

    # 伤害类型构成
    dmg_types = []
    for c in pcl + [x for x_ in sk for x in x_['clauses']]:
        for t in DMG_KW:
            if t in c and t not in dmg_types:
                dmg_types.append(t)

    # 资源关键词（用于写"资源怎么管"）；排除泛用词「层/次」
    RES_WORDS = ['怒气', '能量', '印记', '碎片', '战意', '充能', '蓄力', '残暴',
                 '灵力', '怒气值', '能量条', '弹药', '怒气条', 'buff']
    res_words = []
    for c in pcl + [c for x in sk for c in x['clauses']]:
        for w in RES_WORDS:
            if w in c and w not in res_words:
                res_words.append(w)
    # 「层数」型资源单独记（需同时出现叠加上限类表述）
    if any(k in c for c in pcl for k in ('叠加', '最多叠加', '层数')):
        if '层数' not in res_words:
            res_words.append('层数')

    # 机制红利：被动/核心技能中"越用越强"类句子
    bonus = []
    seen = set()
    for c in pcl + (core['clauses'] if core else []):
        if c in seen:
            continue
        if any(k in c for k in ['每', '每次', '最多', '持续', '提升', '回复', '刷新',
                                '返还', '减少', '增加', '获得', '触发', '可以',
                                '叠加', '额外', '强化', '暴击', '回复']):
            bonus.append(c)
            seen.add(c)

    # 最容易浪费的点：涉及"脱离战斗/衰减/清空/限制"的句子
    waste = []
    for c in pcl + (core['clauses'] if core else []):
        if any(k in c for k in ['脱战', '脱离战斗', '衰减', '消失', '清空', '解除',
                                '只能', '无法', '不能', '消耗所有', '消耗全部',
                                '仅对', '只对', '失效', '冷却', '目标', '不可']):
            waste.append(c)

    return {
        'passive_raw': passive,
        'passive_clauses': pcl,
        'passive_core': passive_core or '',
        'passive_res': p_res,
        'passive_ctrl': p_ctrl,
        'skills': sk,
        'core_skill': core,
        'res_words': res_words,
        'res_mech': res_mech,
        'atk_mode': atk_mode,
        'dmg_types': dmg_types,
        'bonus': bonus,
        'waste': waste,
        'has_ctrl': any(x['has_ctrl'] for x in sk),
        'has_res': any(x['has_res'] for x in sk) or bool(p_res),
        'has_hard_ctrl': any(any(k in c for k in HARD_CTRL) for x in sk for c in x['ctrl']),
        'skill_count': len(skills),
        'active_count': len(actives),
    }


# ---------- 连招场景化 ----------
SCENE_RULES = [
    ('残血反打', ['反打', '残血', '血量低', '低血']),
    ('追击收割', ['追击', '收割', '突进', '冲锋', '位移']),
    ('逃生保命', ['逃生', '保命', '撤退', '逃跑']),
    ('清线拆塔', ['清线', '推塔', '兵线', '拆塔', '拆']),
    ('对线消耗', ['消耗', '对线', '换血', '普攻', '平A', 'A']),
    ('团战开团', ['大招', '3', '一三', '开团', '团战', '先手', '控制', '击飞', '眩晕']),
]


def combo_text(c):
    """连招字段可能是字符串，也可能是 {name, seq, desc} 结构，统一成可读文本。"""
    if isinstance(c, dict):
        name = c.get('name', '')
        seq = c.get('seq', '')
        desc = c.get('desc', '')
        parts = [x for x in (name, seq, desc) if x]
        return '：'.join(parts)
    return str(c)


def classify_combo(c):
    """按关键词给连招归类场景。"""
    t = combo_text(c)
    for name, kws in SCENE_RULES:
        if any(k in t for k in kws):
            return name
    return '常规起手'


RISK_RULES = [
    (['大招', '3'], '大招命中后才有后续收益，空放等于白给一轮冷却'),
    (['闪现'], '闪现落点决定成败，墙面地形会吃满伤害'),
    (['蓄力', '2技能', '2蓄力'], '蓄力过程会被控打断，失败即空窗'),
    (['普攻', 'A'], '普攻前摇吃英雄本体调整，站桩位容易被打断'),
    (['大招可配合闪现', '大闪'], '闪现与大招的先后顺序错位会变成原地起手'),
    (['位移'], '位移落点是技能释放终点，落点选错等于送脸'),
    (['连续', '连', '-'], '连招是顺序技能，中断后剩余技能不会接上'),
]


def combo_risk(c):
    t = combo_text(c)
    for kws, txt in RISK_RULES:
        if any(k in t for k in kws):
            return txt
    return '每一段都依赖前一段的命中，前段失误后面全是空放'


def _skill_mech(x):
    mech = ''
    for group in (x['ctrl'], x['res'], x['dmg'], x['rng']):
        if group:
            mech = group[0]
            break
    if not mech and x['clauses']:
        mech = x['clauses'][0]
    return mech


def combo_steps(c, skills):
    """把连招文本拆成步骤序列，返回 [(技能名, 机制要点)]。

    技能只来自该英雄自己的技能列表；支持真名、阿拉伯数字序号、
    中文序数（一技能/二技能/大招）三种写法，按在原文中的出现顺序排列。
    """
    t = combo_text(c)
    if not skills:
        return []

    # 1) 收集候选命中：名称 或 序号
    hits = []          # (位置, 技能下标)

    for i, x in enumerate(skills):
        nm = x['name']
        if nm:
            for m in re.finditer(re.escape(nm), t):
                hits.append((m.start(), i))

    cn_map = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
               '1': 1, '2': 2, '3': 3, '4': 4, '5': 5}
    for m in re.finditer(r'([一二三四五12345])\s*技能', t):
        n = cn_map.get(m.group(1))
        if n and n <= len(skills):
            hits.append((m.start(), n - 1))
    for m in re.finditer(r'大招|终极技能', t):
        hits.append((m.start(), len(skills) - 1))
    # 纯数字序列（排除已带"技能"后缀的）
    for m in re.finditer(r'(?<![技能])([12345])(?![技能])', t):
        n = int(m.group(1))
        if n <= len(skills):
            hits.append((m.start(), n - 1))

    if not hits:
        return []

    # 同一位置的多种命中只保留优先级最高的一个：
    # 位置相同 => 视为同一次按键（不同规则解析同一段文本）
    hits.sort(key=lambda x: (x[0], x[1]))
    dedup = []
    for pos, idx in hits:
        if dedup and abs(pos - dedup[-1][0]) <= 1 and idx == dedup[-1][1]:
            continue
        dedup.append((pos, idx))

    # 组装成有序步骤（允许同一技能在不同位置重复出现，如 3→2→A→1→A）
    out = []
    for pos, idx in dedup:
        out.append((skills[idx]['name'], _skill_mech(skills[idx])))
    # 若整体仍偏长（同一技能连续重复），保留首次出现
    comp = []
    for nm, m in out:
        if comp and comp[-1][0] == nm:
            continue
        comp.append((nm, m))
    # 连招描述里同一套技能可能以不同写法重复出现（如「3→2→A」+「大招击飞，二技能…」），
    # 只保留第一轮，长度不超过该英雄的技能数。
    if len(comp) > len(skills):
        comp = comp[:len(skills)]
    return comp
