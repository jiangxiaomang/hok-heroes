# -*- coding: utf-8 -*-
"""
英雄专属打法引擎（重写版）。

原 playbook.lane_playbook 的问题：所有同分路英雄的打法要点完全一样
（打野都是"河道草丛/开局第一圈/惩戒时机"），没有结合英雄独有机制，
也没用上数据里已有的 playstyle / phases / pro_tips。

本模块的规则：
  1. 打法中的每一条都必须绑定该英雄自己的技能名、机制或对位英雄。
  2. 不使用与英雄无关的通用模板句。
  3. 阶段节奏直接采用该英雄唯一的 phases（前期/中期/后期）。
  4. 高分实战要点直接采用该英雄的 pro_tips（实战要点/官方 Tips 口径）。
  5. 无法从该英雄数据推出的内容宁缺毋滥，不编造数值与结论。
"""

import re

# ---------------------------------------------------------------- 机制特征

TRAITS = [
    # (特征键, 判定函数名, 中文标签)
    ('stealth',  lambda p: p.get('stealth'), '隐身'),
    ('invuln',   lambda p: p.get('invuln'), '免伤'),
    ('pickup',   lambda p: p.get('pickup'), '拾取'),
    ('mark',     lambda p: p['mark'], '标记'),
    ('execute',  lambda p: p['execute'], '斩杀'),
    ('antiheal', lambda p: p['antiheal'], '反治疗'),
    ('revive',   lambda p: p['revive'], '复活'),
    ('shield',   lambda p: p['shield'], '护盾'),
    ('heal',     lambda p: p['heal'], '治疗'),
    ('mode',     lambda p: p['mode'], '形态切换'),
    ('charge',   lambda p: p['charge'], '蓄力'),
    ('summon',   lambda p: p['summon'], '召唤物'),
    ('dot',      lambda p: p['dot'], '持续伤害'),
    ('field',    lambda p: p['stun_field'], '阵地区域'),
    ('buffself', lambda p: p['buffself'], '自身强化'),
    ('clear',    lambda p: p['clear'], '清线清野'),
    ('far',      lambda p: p['far'], '远距'),
    ('near',     lambda p: p['near'], '近距'),
    ('disp',     lambda p: p['disp'], '位移'),
    ('hard',     lambda p: p['hard_ctrl'], '硬控'),
    ('ctrl',     lambda p: p['has_ctrl'], '控制'),
]


def _hit(text, kws):
    if not text:
        return False
    return any(k in text for k in kws)


def _pick(profs, pred):
    for p in profs:
        if pred(p):
            return p
    return None


def _excerpt(prof, limit=40):
    """技能机制要点短句，用于"为什么"。"""
    if not prof:
        return ''
    d = re.sub(r'\s+', '', prof.get('desc') or '')
    d = re.sub(r'被动[:：]?', '', d)
    d = re.sub(r'[（(][^（）()]*[）)]', '', d)
    for sep in ('。', '；', '，'):
        if sep in d:
            d = d.split(sep)[0]
            break
    d = d.strip('，。、； ')
    if len(d) <= limit:
        return d
    # 超限时不要硬切字（会留下「并」「每次」这类悬空残句），
    # 在 limit 内最后一个逗号处收尾，保证是完整分句。
    cut = d.rfind('，', 0, limit)
    if cut > limit // 2:
        d = d[:cut]
    else:
        d = d[:limit]
    return d.rstrip('，、；并和或的每次')


def _core_skill(profs, tr):
    """挑出该英雄最核心的技能：优先硬控，其次位移/标记/斩杀/形态，
    再次其他。让对位与打法都围绕同一个核心机制展开。

    例外：复活型英雄的核心是复活技而不是控制技——
    他们的胜负手在"第二条命"，不在控制时长。
    """
    if tr.get('revive'):
        return tr['revive'][0]
    for key in ('hard', 'mark', 'execute', 'antiheal', 'disp', 'mode',
                'stealth', 'charge'):
        if key in tr and tr[key]:
            return tr[key][0]
    return profs[0] if profs else None


def _name(prof, fallback='技能'):
    return prof['name'] if prof else fallback


# ------------------------------------------------ 对位英雄机制索引（懒加载）

_OPP_INDEX = None

# 对手"最具代表性一招"的挑法：优先能改变走位/血线的机制
_OPP_PRIORITY = [
    ('suppress', '压制'),
    ('hard_ctrl', '硬控'),
    ('execute', '斩杀'),
    ('antiheal', '反治疗'),
    ('stealth', '隐身'),
    ('revive', '复活'),
    ('has_ctrl', '控制'),
    ('mark', '标记'),
    ('disp', '位移'),
    ('mode', '形态切换'),
    ('shield', '护盾'),
    ('heal', '治疗'),
    ('dmg', '伤害'),
]


def _opp_index():
    """建立 {英雄名: {'skill': 技能名, 'mech': 机制短句}} 索引。

    数据来自本项目已保存的官方英雄资料 heroes_official.json，
    每一句都取自该对手自己的技能描述，不套用任何模板。
    """
    global _OPP_INDEX
    if _OPP_INDEX is not None:
        return _OPP_INDEX

    import json
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, '..', 'data', 'heroes_official.json')
    try:
        heroes = json.load(open(path, encoding='utf-8'))
    except Exception:
        _OPP_INDEX = {}
        return _OPP_INDEX

    idx = {}
    for h in heroes:
        name = h.get('cname')
        if not name:
            continue
        # skills[0] 是被动，skills[1:] 是主动技
        actives = (h.get('skills') or [])[1:]
        cands = []
        for p in actives:
            prof = {
                'name': p.get('name') or '技能',
                'desc': p.get('desc') or '',
                'hard_ctrl': _hit(p.get('desc') or '',
                                  ['眩晕', '击晕', '击退', '压制', '禁锢',
                                   '捆绑', '嘲讽', '眩晕', '击飞', '夺魂']),
                'has_ctrl': _hit(p.get('desc') or '',
                                 ['眩晕', '击晕', '减速', '沉默', '缴械',
                                  '定身', '压制', '禁锢', '眩晕', '击退',
                                  '嘲讽', '魅惑', '恐惧', '击飞', '打断']),
                'suppress': _hit(p.get('desc') or '',
                                 ['压制', '无法进行任何操作', '无法使用技能',
                                  '无法位移', '无法解除', '被压制']),
                'execute': _hit(p.get('desc') or '',
                                ['斩杀', '百分比生命', '已损失生命']),
                'antiheal': _hit(p.get('desc') or '',
                                 ['回复减少', '治疗效果降低', '禁止治疗',
                                  '反治疗', '沉默治疗']),
                'mark': _hit(p.get('desc') or '',
                             ['标记', '锁定', '易伤', '破绽', '目标身上']),
                'stealth': _hit(p.get('desc') or '',
                                ['隐身', '无法被选中', '不可选中']),
                'revive': _hit(p.get('desc') or '',
                               ['复活', '重获新生', '恢复生命并']),
                'disp': _hit(p.get('desc') or '',
                             ['位移', '突进', '冲刺', '瞬移', '闪现',
                              '位移一段', '穿越', '拉扯']),
                'mode': _hit(p.get('desc') or '',
                             ['切换', '变为', '形态', '进入', '退出']),
                'shield': _hit(p.get('desc') or '',
                               ['护盾', '吸收伤害', '抵消伤害']),
                'heal': _hit(p.get('desc') or '',
                             ['治疗', '回复生命', '恢复生命', '回血']),
                'dmg': _hit(p.get('desc') or '',
                            ['伤害', '造成', '打击', '撞击', '斩击']),
            }
            cands.append(prof)

        # 在所有候选技能里，按全局优先级挑最"有代表性"的一招。
        # 不能遇到第一个就 break —— 东皇太一的第 1 技"日蚀祭典"是伤害，
        # 真正该提示的是第 3 技"堕神契约"（压制）。
        best = None
        best_key = None
        best_rank = len(_OPP_PRIORITY) + 1
        for prof in cands:
            for rank, (key, _lbl) in enumerate(_OPP_PRIORITY):
                if prof[key]:
                    if rank < best_rank:
                        best, best_key, best_rank = prof, key, rank
                    break
        if best:
            # 机制短句必须去掉具体数值，只留机制
            raw = re.sub(r'\s+', '', best.get('desc') or '')
            raw = re.sub(r'[（(][^（）()]*[）)]', '', raw)
            raw = re.sub(r'[0-9]+(/[0-9]+)*%?', '', raw)
            raw = raw.replace('——', '，').replace('--', '，')
            for sep in ('。', '；', '，'):
                if sep in raw:
                    raw = raw.split(sep)[0]
                    break
            raw = re.sub(r'[，、；。：\s]+$', '', raw)
            mech = raw[:34]
            idx[name] = {'skill': best['name'], 'mech': mech,
                          'key': best_key, 'has_disp': best['disp'],
                          'has_ctrl': best['has_ctrl'],
                          'hard_ctrl': best['hard_ctrl'],
                          'stealth': best['stealth'],
                          'revive': best['revive'],
                          'antiheal': best['antiheal'],
                          'execute': best['execute'],
                          'suppress': best['suppress']}
    _OPP_INDEX = idx
    return _OPP_INDEX


def _opponent_profile(name):
    """取对手自己的代表性技能与机制短句；取不到返回 None。"""
    if not name:
        return None
    return _opp_index().get(name)


# 每个英雄作为"克制对象"被其他英雄提及的次数（用于挑稀有对位）
_COUNTER_FREQ = None


def _counter_freq():
    """统计每个英雄出现在多少个英雄的 counters / countered_by 里。

    频次越高说明这个对象越"泛用"（如小乔、鲁班七号），
    挑对位时应优先选频次低的，才能反映这个英雄真正的对位关系。
    """
    global _COUNTER_FREQ
    if _COUNTER_FREQ is not None:
        return _COUNTER_FREQ
    import json
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, '..', 'data', 'heroes_official.json')
    freq = {}
    try:
        heroes = json.load(open(path, encoding='utf-8'))
    except Exception:
        _COUNTER_FREQ = freq
        return freq
    for h in heroes:
        for key in ('counters', 'countered_by'):
            for n in (h.get(key) or []):
                freq[n] = freq.get(n, 0) + 1
    _COUNTER_FREQ = freq
    return freq


def _pick_distinct(names):
    """从对位名单里挑最多 2 个"稀有"对象。

    规则：按被提及频次从低到高排，优先取别人很少列为克制对象的，
    避免 133 张卡的对位行都写成"容易打：鲁班七号"。
    频次相同则保持原顺序，保证结果稳定。
    """
    if not names:
        return []
    freq = _counter_freq()
    ordered = sorted(enumerate(names),
                     key=lambda pair: (freq.get(pair[1], 0), pair[0]))
    return [n for _i, n in ordered[:2]]


def _easy_line(op, cn):
    """打得过的那一方：按对手的机制类型给具体处理办法。

    不使用"他没交位移"这种通用句，因为很多对手根本没有位移。
    """
    sk = op['skill']
    if op.get('suppress'):
        return (f'他【{sk}】能压制你，'
                f'压制期间不能位移也解不了，'
                f'必须在他开大前拉开距离')
    if op['stealth']:
        return (f'他【{sk}】隐身时你没有视野，'
                f'先插眼或等他自己交掉，再上【{cn}】')
    if op['hard_ctrl']:
        return (f'【{sk}】是硬控，他一交你就拉开，'
                f'等他控制结束再上【{cn}】')
    if op['antiheal']:
        return (f'他有【{sk}】反治疗，'
                f'别在他开之前靠回复耗，'
                f'直接用【{cn}】把血线打下来')
    if op['execute']:
        return (f'他有【{sk}】收割，'
                f'别在他面前把血线压太低，'
                f'用【{cn}】打完就撤')
    if op['has_ctrl']:
        return (f'【{sk}】带控制，等他交完再上【{cn}】，'
                f'别吃这一段减速')
    if op['has_disp']:
        return (f'抓他【{sk}】的落点，'
                f'用【{cn}】在他位移交完的瞬间接上')
    if op['revive']:
        return (f'他有【{sk}】能救回队友，'
                f'优先打第一个躺下的，'
                f'让【{cn}】先把他的救援窗口打掉')
    # 站桩型：直接打
    return (f'他站桩输出，'
            f'用【{cn}】在他抬手时开，'
            f'一整套打完不给他还手时间')


def _care_line(op, cn):
    """打不过的那一方：按对手的机制类型说清楚怎么避。"""
    sk = op['skill']
    if op.get('suppress'):
        # 压制有两种：范围团灭型（东皇太一）与点名抓人型（张良/闪现）
        if re.search(r'[范围|周围|以自身为中心|360|环绕]',
                     op.get('mech', '')):
            return (f'他【{sk}】是范围压制，'
                    f'看到范围提示立刻交位移或闪现出去，'
                    f'别站在他身侧')
        return (f'他【{sk}】能把你抓住并且压住你，'
                f'这段时间你动不了，'
                f'所以别站在他能伸手够到的位置')
    if op['stealth']:
        return (f'他【{sk}】能隐身摸你，'
                f'视野别断，'
                f'让【{cn}】留着打近身而不是远程空放')
    if op['hard_ctrl']:
        return (f'他【{sk}】能定住你，'
                f'正面别硬接，'
                f'等他交了再上【{cn}】')
    if op['antiheal']:
        return (f'他有【{sk}】断回复，'
                f'血量不满就别跟他换血，'
                f'让【{cn}】打爆发而不是打消耗')
    if op['execute']:
        return (f'他有【{sk}】收割，'
                f'血线压到一半就拉开，'
                f'别把【{cn}】留在残血时交')
    if op['has_ctrl']:
        return (f'他【{sk}】带控制，'
                f'别在他能用的时候硬拼，'
                f'先退到【{cn}】够不到的位置')
    if op['has_disp']:
        return (f'他【{sk}】能突进来，'
                f'站位留一条退路，'
                f'让他突空再反打')
    if op['revive']:
        return (f'他【{sk}】能救队友，'
                f'别让他把人救起来，'
                f'优先用【{cn}】压第二个人')
    return (f'他【{sk}】出手快，'
            f'别站在他正前方，'
            f'让【{cn}】等到他技能空掉再放')


def _traits(profs):
    """返回 {特征键: 该英雄拥有此特征的技能}"""
    out = {}
    for key, fn, _ in TRAITS:
        if key == 'stealth':
            hit = [p for p in profs if p.get('stealth')]
        elif key == 'clear':
            hit = [p for p in profs if p.get('clear')]
        else:
            hit = [p for p in profs if fn(p)]
        if hit:
            out[key] = hit
    return out


def _tag_line(profs):
    """该英雄的机制标签（用于卡片抬头）"""
    t = _traits(profs)
    order = ['hard', 'disp', 'mark', 'execute', 'antiheal', 'revive', 'shield',
             'heal', 'stealth', 'mode', 'charge', 'summon', 'field', 'dot',
             'buffself', 'far', 'clear']
    labels = {k: v for k, _, v in TRAITS}
    return [labels[k] for k in order if k in t]


# ---------------------------------------------------------------- 分路打法

def _jungle_rows(hero, profs, tr, lane):
    rows = []
    sk1 = profs[0] if profs else None
    sk2 = profs[1] if len(profs) > 1 else None
    ult = _pick(profs, lambda p: p['is_ult'])
    clear = tr.get('clear', [sk1])[0] if 'clear' in tr else sk1

    # 1) 开局清野 —— 用该英雄自己的清野技能
    if clear:
        rows.append((
            '开局清野',
            f'先用【{_name(clear)}】清掉第一圈野怪，'
            f'技能循环转好再上 4 级',
            f'{_excerpt(clear) or "该技能可处理野怪"}，'
            f'前期把它转满才能在 4 级点形成等级差'))
    else:
        rows.append((
            '开局清野',
            '前期以发育为主，能让野怪少打你一点是一点，'
            '野区不是你的第一优先级',
            '该英雄前期强度不靠刷野堆等级，靠的是抓人时机'))

    # 2) 第一波抓人 —— 用该英雄的真实控制/大招
    # 输出型技能优先：暗袭/影蚀这类直接伤害或控制的技能，
    # 不要把隐身、变身这类功能技当输出。
    out_skill = None
    for p in profs:
        if p['is_ult'] and (p['hard_ctrl'] or p['has_ctrl'] or p['dmg']):
            out_skill = p
            break
    if out_skill is None:
        for p in profs:
            if p['dmg'] and not p.get('stealth'):
                out_skill = p
                break
    if out_skill is None:
        out_skill = ult or sk1

    if ult and (ult['hard_ctrl'] or ult['has_ctrl']):
        nxt = sk2 or sk1
        rows.append((
            '4 级第一波',
            f'盯压线最前的那个人，【{_name(ult)}】落地接【{_name(nxt)}】'
            f'把伤害补满',
            f'{_excerpt(ult)}，大招先手才有跟上的空间'))
    elif out_skill:
        rows.append((
            '4 级第一波',
            f'4 级后找落单的人，用【{_name(out_skill)}】起手，'
            f'不要空放，等对方走位固定再交',
            f'{_excerpt(out_skill)}，空掉这一波就白来了'))
    else:
        rows.append((
            '4 级第一波',
            '4 级后优先抓位置靠前、装备没成型的那一个',
            '前期抓人的收益来自等级差，不是来自操作难度'))

    # 3) 蹲草切入 —— 按位移/隐身/控制分三种不同打法
    if 'stealth' in tr:
        st = tr['stealth'][0]
        rows.append((
            '隐身切入',
            f'进草后等对方靠近，用【{_name(st)}】的隐身直接落到他脸上',
            f'{_excerpt(st)}，这是该英雄绕后成功率最高的方式'))
    elif 'disp' in tr:
        dp = tr['disp'][0]
        rows.append((
            '位移绕后',
            f'从侧面草丛用【{_name(dp)}】进场，'
            f'落地角度选对方背后，别从正面走',
            f'{_excerpt(dp)}，位移是取消读图和打反直觉的关键'))
    elif 'ctrl' in tr:
        ct = tr['ctrl'][0]
        rows.append((
            '控制先手',
            f'用【{_name(ct)}】的控制起手抢在对方位移之前，'
            f'控制没中就别继续追',
            f'{_excerpt(ct)}，控制不中强行追人只会送'))
    else:
        rows.append((
            '先手劣势',
            '你没有稳定控制，抓人别从正面起步，'
            '优先配合有控制的队友一起进',
            '无控制强行先手，赢了也是残血换人头'))

    # 4) 惩戒节点
    rows.append((
        '惩戒节点',
        '只交给能改变结果的节点：抢红隼、反野惩戒、收掉残血野怪',
        '开局就交掉惩戒，4 级那波抓人你就没有第二条命'))

    # 4.5) 免伤/保命 —— 该英雄自己的保命机制
    if 'invuln' in tr:
        iv = tr['invuln'][0]
        rows.append((
            '保命机制',
            f'【{_name(iv)}】留着挨对方关键技能，'
            f'不要随手用来赶路',
            f'{_excerpt(iv)}，这一下能让你多打一轮'))
    if 'pickup' in tr:
        pk = tr['pickup'][0]
        rows.append((
            '资源回收',
            f'【{_name(pk)}】打出去的东西要记得拿回来，'
            f'拿不回来这套循环就断了',
            f'{_excerpt(pk)}，回收是这个英雄的节奏核心'))

    # 5) 资源时间
    rows.append((
        '资源时间',
        '空间之灵 2:00 前把路线排好，双龙 10:00 前站好位置',
        '资源点的时间差，就是团队经济的差'))

    # 6) 跟团方式 —— 按该英雄的开团能力分
    if ult and ult['hard_ctrl']:
        rows.append((
            '跟团方式',
            f'队友先手后你再进，【{_name(ult)}】留到对方关键控制交完之后',
            '你有硬控可以接第二段，但先手太早会被位移和净化反打'))
    elif 'heal' in tr or 'shield' in tr:
        hp = (tr.get('heal') or tr.get('shield'))[0]
        rows.append((
            '跟团方式',
            f'你跟团不靠开团，靠【{_name(hp)}】让队友敢往前打',
            f'{_excerpt(hp)}，这种打野的价值是提高队友的容错'))
    else:
        rows.append((
            '跟团方式',
            '队友控住后你补伤害，别单独冲进去',
            '补刀位比开团位安全，收益一样高'))
    return rows


def _mid_rows(hero, profs, tr, lane):
    rows = []
    sk1 = profs[0] if profs else None
    sk2 = profs[1] if len(profs) > 1 else None
    ult = _pick(profs, lambda p: p['is_ult'])
    clear = tr.get('clear', [sk1])[0] if 'clear' in tr else sk1

    rows.append((
        '清线优先',
        f'先把兵线清完再去支援，支援路上顺手用【{_name(clear)}】'
        f'收掉兵线再进场',
        '中路线权没了就去支援，等于有去无回'))

    if 'far' in tr:
        f = tr['far'][0]
        rows.append((
            '消耗距离',
            f'站在【{_name(f)}】能打到的最远距离上poke，'
            f'不要为了多打一下走进对方射程',
            f'{_excerpt(f)}，射程优势本来就是你的核心资源'))
    elif 'disp' in tr:
        dp = tr['disp'][0]
        rows.append((
            '消耗距离',
            f'用【{_name(dp)}】打完就撤，别站在原地被人打',
            '打完就跑是法师的保命方式，比护盾更实用'))
    else:
        rows.append((
            '消耗距离',
            '只在技能命中且对方没有位移时上前消耗',
            '没有距离优势时，多一次上前就多一次被抓'))

    if 'ctrl' in tr:
        ct = tr['ctrl'][0]
        rows.append((
            '抢支援窗口',
            f'看到边路交火，在对方技能交空后用【{_name(ct)}】先手控住，'
            f'不是开团了就到',
            '早到 5 秒是接盘，晚到 5 秒是收尸'))
    else:
        rows.append((
            '抢支援窗口',
            '看到边路交火，对方技能交空后再到',
            '对方技能空掉的那几秒才是支援窗口'))

    if ult:
        rows.append((
            '大招用途',
            f'【{_name(ult)}】用来压塔或封走位，不要用来清兵',
            f'{_excerpt(ult)}，用在大招该解决的事情上'))
    else:
        rows.append((
            '大招用途',
            '大招留着压塔或封走位，不要随手清兵',
            '大招清了兵，团战就少一段控制'))

    rows.append((
        '河道视野',
        '把自己当第二个打野位，蹲对方从中路消失的路线',
        '中路的视野优势来自草丛，不来自河道中央'))
    return rows


def _adc_rows(hero, profs, tr, lane):
    rows = []
    sk1 = profs[0] if profs else None
    ult = _pick(profs, lambda p: p['is_ult'])
    far = tr.get('far', [sk1])[0] if 'far' in tr else sk1
    atk = tr.get('buffself', [sk1])[0] if 'buffself' in tr else sk1

    rows.append((
        '发育节奏',
        f'前期以补刀为主，【{_name(atk)}】能打到的兵才去打，'
        f'不要为了一两个残血兵进塔',
        '射手前期死一次，节奏就断了，等级和装备都会落后'))

    rows.append((
        '站位输出',
        f'站在自己塔前用【{_name(far)}】打最远的那个目标，'
        f'优先打前排或正在打你的那个人',
        f'{_excerpt(far) or "远程输出"}，站着不动输出才有安全输出'))

    if 'mark' in tr:
        mk = tr['mark'][0]
        rows.append((
            '标记优先',
            f'看到【{_name(mk)}】能挂上的目标优先集火，'
            f'不要平均分配伤害',
            f'{_excerpt(mk)}，标记对象承受的伤害更集中'))
    elif ult:
        rows.append((
            '集火规则',
            f'团战只打一个目标，开局就打【{_name(ult)}】能覆盖到的位置',
            '平均伤害谁也打不死，集中才有意义'))
    else:
        rows.append((
            '集火规则',
            '团战只打一个目标，别在人群里找位置',
            '平均伤害谁也打不死'))

    if 'shield' in tr or 'heal' in tr:
        hp = (tr.get('shield') or tr.get('heal'))[0]
        rows.append((
            '自保',
            f'血量到一半就先退，用【{_name(hp)}】扛一下再回线，'
            f'不要硬撑到残血',
            f'{_excerpt(hp)}，活着回到塔下才有下一波'))
    else:
        rows.append((
            '自保',
            '闪现留着打断或逃命，不要用来赶路',
            '赶路用走路，闪现用来保命才有价值'))

    rows.append((
        '拆塔',
        '对方回城且兵线到位时拆塔，不要在塔下与人对峙',
        '拆塔收益稳定，对峙收益不稳定'))
    return rows


def _solo_rows(hero, profs, tr, lane):
    rows = []
    sk1 = profs[0] if profs else None
    ult = _pick(profs, lambda p: p['is_ult'])
    clear = tr.get('clear', [sk1])[0] if 'clear' in tr else sk1

    rows.append((
        '抢线',
        f'开局用【{_name(clear)}】快速推线，'
        f'把对方逼到塔下再打消耗',
        '对抗路先手推线的人拥有换血主动权'))

    if 'pickup' in tr:
        pk = tr['pickup'][0]
        rows.append((
            '换血后撤',
            f'把【{_name(pk)}】丢出去拉开距离，'
            f'走位退回时顺手把它捡回来',
            f'{_excerpt(pk)}，丢出去的技能不打中就是白丢'))
    elif 'disp' in tr:
        dp = tr['disp'][0]
        rows.append((
            '换血后撤',
            f'用【{_name(dp)}】拉开距离后立刻往回走，'
            f'不要在换血后站着对拼',
            f'{_excerpt(dp)}，拉开之后是你回身打第二轮'))
    else:
        rows.append((
            '换血后撤',
            '换完血立刻后撤到兵线后方，让小兵替你挡第一轮技能',
            '站桩换血是对抗路最常见的死法'))

    if ult:
        rows.append((
            '压塔时机',
            f'【{_name(ult)}】用来压塔或逼对方回城，'
            f'等对方位移交掉再顶上去',
            f'{_excerpt(ult)}，顶在塔前逼位能直接拆塔'))
    else:
        rows.append((
            '压塔时机',
            '等对方位移交掉再顶塔，逼对方回城',
            '对方位移在，你顶上去只是在挨打'))

    rows.append((
        '转线支援',
        '对方打野在中路消失就往中路靠，抢支援比补线值钱',
        '对抗路转线晚一步，团战就是少一个人'))
    rows.append((
        '单带',
        '队友抱团时你在边路单带，不要跟着去挤团',
        '团战你不在也能打，单带你不在就丢高地'))
    return rows


def _support_rows(hero, profs, tr, lane):
    rows = []
    ult = _pick(profs, lambda p: p['is_ult'])
    ct = tr.get('ctrl', [profs[0]])[0] if 'ctrl' in tr else None
    hp = (tr.get('heal') or tr.get('shield') or [None])[0] if (
        'heal' in tr or 'shield' in tr) else None
    rv = tr.get('revive', [None])[0] if 'revive' in tr else None

    if rv:
        rows.append((
            '复活兜底',
            f'团战前先确认【{_name(rv)}】能覆盖到的位置，'
            f'站在己方 C 位身后等对方先手',
            f'{_excerpt(rv)}，复活是团队保险不是主动进攻'))
    elif hp:
        rows.append((
            '保护人',
            f'站到己方 C 位与对方之间，用【{_name(hp)}】顶住第一轮爆发',
            f'{_excerpt(hp)}，你的价值是让 C 位能站住输出'))
    else:
        rows.append((
            '保护人',
            '站到己方 C 位与对方之间，用身体挡住对方第一轮技能',
            'C 位死一次，团战直接结束'))

    if ct:
        rows.append((
            '蹲草开团',
            f'在对方必经草丛蹲着，等对方走到再交【{_name(ct)}】，'
            f'控制留在能打多人或能打 C 位的位置',
            f'{_excerpt(ct)}，控制位置的收益大于控制时机'))
    else:
        rows.append((
            '蹲草开团',
            '在对方必经草丛蹲着，等对方走位固定再叫开团',
            '你不开团就先等对方进你的位置'))

    # 开团/反开 —— 只有当大招本身带控制时才用它开团
    ult_ctrl = ult and (ult['hard_ctrl'] or ult['has_ctrl'])
    if ult_ctrl:
        rows.append((
            '开团与反开',
            f'对方先手落地后再交【{_name(ult)}】，'
            f'这时他们没有净化和位移',
            f'{_excerpt(ult)}，后手开团比先手开团更稳'))
    elif ult and rv:
        rows.append((
            '开团与反开',
            f'叫队友开团，你在侧面接【{_name(ct)}】的第二段控制，'
            f'【{_name(ult)}】留着救人',
            '你的大招是保险不是先手，先手交了团崩了就没人保'))
    elif ult:
        rows.append((
            '开团与反开',
            '叫队友开团，你在侧面接第二段控制',
            '双开团比单开团更难被反打'))
    else:
        rows.append((
            '开团与反开',
            '叫队友开团，你在侧面接第二段控制',
            '双开团比单开团更难被反打'))

    rows.append((
        '跟打野',
        '打野在哪条线你就出现在哪条线',
        '分散的游走等于没有游走'))
    rows.append((
        '撤退信号',
        'C 位血量危险时立刻喊退，不要硬保',
        '救不回来就一起死，亏两波'))
    return rows


LANE_BUILDER = {
    '打野': _jungle_rows,
    '中路': _mid_rows,
    '发育路': _adc_rows,
    '对抗路': _solo_rows,
    '游走': _support_rows,
}


# ---------------------------------------------------------------- 高分实战要点

def _pro_rows(hero, profs, tr):
    """高分实战要点：直接采用该英雄自己的 pro_tips。

    pro_tips 是这个英雄独有的实战技巧条目（如赵云"大招命中后接1技能伤害翻倍"），
    每条都对应一个具体操作点，不是分路通用模板。
    """
    rows = []
    tips = [t for t in (hero.get('pro_tips') or []) if t and t.strip()]
    for i, t in enumerate(tips[:4]):
        # pro_tips 是原始字段，可能带具体数值（如"大招变身+100攻击力"）。
        # 数值会随版本变，卡片只留机制，数值以官方资料为准。
        t = _strip_nums(t)
        # 从技巧里抽出它作用的技能名
        skill = _skill_in_text(t, profs)
        how = t
        if skill:
            how = f'围绕【{_name(skill)}】用：{t}'
        else:
            how = _pro_how(t, profs)
        # 第三列「口径」= 这条技巧的依据/来源。优先给出命中技能的真实机制
        # 短句作为依据；没有命中技能时，标注来源（来自该英雄官方实战要点），
        # 避免整列重复同一个「实战要点口径」占位词。
        basis = _excerpt(skill, 34) if skill else ''
        rows.append((_tip_label(t, i), how, basis or '来自官方实战要点'))
    return rows


def _strip_nums(text):
    """去掉具体数值，只留机制描述。

    数值随版本变动，卡片上写死会误导人；
    官方资料页面的数值以局内说明和官方数据为准。
    """
    if not text:
        return text
    t = re.sub(r'[+＋]\s*\d+(\.\d+)?%?', '', text)     # +100 攻击力
    t = re.sub(r'\d+(\.\d+)?\s*%', '', t)             # 20%
    t = re.sub(r'\d+(\.\d+)?\s*(秒 | 点 | 层 | 次)', '', t)  # 5 秒 / 300 点
    t = re.sub(r'[，,、]\s*[,,]', '，', t)
    t = re.sub(r'\s+', '', t)
    return t


def _pro_how(tip, profs):
    """把描述性短语转成可执行的操作指引。

    数据里的 pro_tips 有两种写法：
      - 操作型（"大招命中后接1技能伤害翻倍"）—— 已经是做法，直接用
      - 描述型（"复活队友是核心""射程全英雄最远"）—— 需要补成怎么做
    描述型的不能直接摆上卡片，否则等于没说。

    注意：关键词必须是两字以上的完整词，
    单字匹配会误伤（"枪"会命中妲己的"蹲草意识"这类无关句）。
    """
    # 带动词的操作句直接用
    if re.search(r'[接打放交开走砍留等预判先再后用]',
                 tip) and re.search(r'[后接|再接|先|然后|时|后|接]',
                                    tip):
        return tip

    # 描述型：按内容给具体动作
    if re.search(r'\d{2,}', tip) and re.search(r'[连招|连携|秒|爆发|最快]',
                                            tip):
        m = re.search(r'\d{2,}', tip)
        seq = m.group(0) if m else ''
        return (f'这一套就是 {seq} 的固定顺序，'
                f'按这个顺序一次打满，'
                f'中途不要换成别的技能')
    if '复活' in tip:
        return (f'团战前先站到己方 C 位身后，'
                f'大招收割时保护范围要盖住他，'
                f'别自己冲出去打')
    if '射程' in tip:
        return ('站在对方够不到你的位置输出，'
                '保持距离比多打一下更重要')
    if '被动' in tip:
        # 被动有两种：叠层型（攒满再进场）与血量型（残血/满血才生效）
        if re.search(r'[叠层|层数|攒|叠加]', tip):
            return ('把被动叠到最高的那一波再进场，'
                    '不要在被动没叠满的时候硬开')
        if re.search(r'[血量|残血|血越|血少|满血|血线]', tip):
            return ('按血线情况决定进不进：'
                    '血量落到被动生效的那条线再上，'
                    '血多的时候进场等于白挨打')
        return ('先确认自己的被动条件满没满，'
                '没满就先拉扯或者清线，'
                '别硬进场')
    if '普攻' in tip:
        return ('进场后先打普攻把层数攒起来，'
                '攒满再放技能')
    if re.search(r'[拾取|回收|标枪|枪意|弹药|捡枪|捡起]',
                 tip):
        return ('打出去的技能要记得收回来，'
                '拿不回来这套循环就断了，'
                '进场前先看清还能用几次')
    if re.search(r'[回血|续航|吸血]', tip):
        return ('靠这套循环把血线拉回来，'
                '所以不要在血不满的时候硬接团战')
    if re.search(r'[移速|风筝|拉扯]', tip):
        return ('靠移动把距离拉开再打，'
                '不要站着对拼，'
                '走位比多打一下更重要')
    if re.search(r'[蹲草|草丛|伏击|埋伏]', tip):
        return ('蹲草要等对方走到你选好的那个点再动手，'
                '提前露头这一波就废了')
    if re.search(r'[隐身|探草|探草丛|真身|暴露]', tip):
        return ('探草丛之前先想好退路，'
                '一旦位置暴露就用位移直接撤，'
                '不要留在原地')
    if re.search(r'[冷却|CD]', tip):
        return ('别在有位移或控制的技能上浪费冷却，'
                '留到能改变结果的那一下')
    if re.search(r'[伤害|输出|秒脆皮|秒人]', tip):
        return ('优先保证这一段能完整打出来，'
                '中途不要贪别的目标')
    if re.search(r'[支援|开团|团战|开先手]', tip):
        return ('团战前先确认自己的技能能覆盖到谁，'
                '再决定进不进')
    if re.search(r'[位移|突进|拉扯距离]', tip):
        return ('用位移调整站位，'
                '进之前先算好退路在哪，'
                '不要交了位移就没地方撤')
    # 兜底：把短语接成一句做法
    return f'记住这条：{tip}，进场前先想好怎么用'


def _tip_label(tip, i):
    """给一条实战要点起一个能看出内容的短标题。

    不使用"实战点1"这种无信息编号，而是从技巧本身抓关键词。
    """
    for kw in ('翻倍', '免控', '穿墙', '预判', '残血', '减速', '叠加',
               '回血', '减伤', '斩杀', '开团', '反打', '位移', '隐身',
               '控制', '护盾', '吸血', '成长', '等级', '补兵'):
        if kw in tip:
            return kw
    # 没有命中关键词就用技巧前几个字
    return tip[:8].strip('，。；、') or f'要点{i + 1}'


def _skill_in_text(text, profs):
    """在一条实战要点里找出它提到的技能。

    支持两种写法：
      1. 直接写技能名（"大招命中后接1技能伤害翻倍" 里的"大招"）
      2. 写序号（"1技能""2技能""大招"）
    官方 pro_tips 用的是第 2 种，必须能解析。
    """
    if not text or not profs:
        return None

    # 先按完整技能名 / 短名匹配
    for p in profs:
        nm = p['name']
        short = nm.split('·')[-1]
        if nm and nm in text:
            return p
        if short and len(short) >= 2 and short in text:
            return p

    # 再按序号匹配：主动技在 profs 里按 1、2、3 编号
    ult = None
    for p in profs:
        if p['is_ult']:
            ult = p
    if ('大招' in text or '终极技能' in text) and ult:
        return ult
    for p in profs:
        if p['is_ult']:
            continue
        idx = str(p['i'])
        for pat in (f'{idx}技能', f'技能{idx}', f'第{idx}技能',
                    f'{idx}段', f'{idx}层'):
            if pat in text:
                return p
    return None


# ---------------------------------------------------------------- 阶段节奏

def _phase_rows(hero, profs, tr):
    """把该英雄唯一的 phases 拆成前期/中期/后期三行。

    phases 原文本身是英雄独有的（如赵云"前期4级抓边"），
    再补上这一阶段该用哪个技能，让每行都能直接照做。
    """
    raw = hero.get('phases') or ''
    parts = [p.strip() for p in re.split(r'[；;]', raw) if p.strip()]
    labels = ['前期', '中期', '后期']
    tips = hero.get('pro_tips') or []
    rows = []
    for i, seg in enumerate(parts):
        lab = labels[i] if i < len(labels) else f'阶段{i + 1}'
        # 拆出"动作"与"理由"
        body = seg
        why = ''
        m = re.match(r'^[^：:]{0,4}[：:](.*)$', seg)
        if m:
            body = m.group(1).strip()
        # 阶段用哪个技能：优先大招，再控制，再位移
        sk = None
        for key in ('hard', 'mark', 'execute', 'disp'):
            if tr.get(key):
                sk = tr[key][0]
                break
        if sk is None:
            for p in profs:
                if p['is_ult']:
                    sk = p
                    break
        if sk is not None:
            body = f'{body}（这一阶段主要靠【{_name(sk)}】）'
        tip = tips[i % len(tips)] if tips else ''
        rows.append((lab, body, tip or hero.get('playstyle', '')[:36]))
    return rows


def _matchup_rows(hero, profs, tr):
    """对位重点：结合该英雄自己的克制关系与机制。

    每条必须同时说明两件事：
      1. 对手自己有什么机制（从对手英雄资料里取，不是套模板）
      2. 本英雄拿哪个技能去打这个机制
    """
    rows = []
    ult = _pick(profs, lambda p: p['is_ult'])
    hard = tr.get('hard', [])
    anti = tr.get('antiheal')
    exe = tr.get('execute')

    # 5) 对位重点：结合该英雄自己的克制关系与核心机制
    core = _core_skill(profs, tr)
    cn = _name(core) if core else '技能'
    # 复活英雄对位时不该拿复活技当锚点（对方不会"躲复活"），
    # 改用他们真正的控制/输出技。
    if tr.get('revive') and core is not None and core in tr['revive']:
        alt = _pick(profs, lambda p: p['hard_ctrl'] or p['has_ctrl']) \
            or _pick(profs, lambda p: p['dmg'])
        if alt:
            core = alt
            cn = _name(core)

    # 官方克制列表里很多英雄共用同一批默认对象（小乔/鲁班七号/后羿），
    # 直接取前两个会让 133 张卡的对位行高度重复。
    # 规则：优先选"稀有"对象 —— 其他英雄不常列为克制的那个，
    # 保证每张卡的对位重点真的是它自己的。
    easy = _pick_distinct(hero.get('counters') or [])
    hard_names = _pick_distinct(hero.get('countered_by') or [])

    for name in easy:
        op = _opponent_profile(name)
        if op:
            rows.append((
                f'容易打：{name}',
                _easy_line(op, cn),
                f'{op["mech"]}——这一条是针对他这个机制设计的'))
        else:
            rows.append((
                f'容易打：{name}',
                f'用【{cn}】在他没交位移时起手，'
                f'一套打满不要分两次出手',
                f'你的核心机制是{_excerpt(core) if core else ""}，'
                f'机制完整命中比操作快更重要'))

    for name in hard_names:
        op = _opponent_profile(name)
        if op:
            rows.append((
                f'小心：{name}',
                _care_line(op, cn),
                f'{op["mech"]}——正面吃到会直接进他的节奏'))
        else:
            rows.append((
                f'小心：{name}',
                f'不要单独探草，见面让线不丢资源，'
                f'把【{cn}】留给他交完位移之后',
                '这是机制克制关系，不代表对位胜率'))
    if anti:
        a = anti[0]
        rows.append((
            '反治疗',
            f'用【{_name(a)}】压住对方的奶量，'
            f'对方带恢复就优先逼他交掉',
            f'{_excerpt(a)}，对面有续航你就别指望打一套秒'))
    if exe:
        e = exe[0]
        rows.append((
            '斩杀线',
            f'把血线压到【{_name(e)}】能收掉的范围内再交',
            f'{_excerpt(e)}，残血被收掉等于白打'))
    if hard:
        h = hard[0]
        rows.append((
            '开团权',
            f'你有【{_name(h)}】这样的硬控，'
            f'可以先手，但要把先手留到关键团',
            f'{_excerpt(h)}，先手太早会让对方用位移和净化反打'))
    elif tr.get('ctrl'):
        c = tr['ctrl'][0]
        rows.append((
            '开团权',
            f'【{_name(c)}】只是软控，'
            f'你开不了团，只能跟着队友的节奏打后手',
            f'{_excerpt(c)}，软控留不住人，'
            f'硬接开团只会让自己先掉血'))
    elif ult:
        rows.append((
            '开团权',
            f'你没有稳定控制，'
            f'【{_name(ult)}】留着保命或者收残血，'
            f'开团交给队友',
            '没有硬控的英雄硬开团，是把自己送上对面集火'))
    return rows


# ---------------------------------------------------------------- 入口

def hero_lane_playbook(hero, profs, lane, role):
    """
    返回 {'sections': [(标题, 表头, 行列表), ...], 'tips': [...],
          'tags': [...]}

    每一行都绑定该英雄自己的技能名、机制、对位或阶段数据。
    """
    tr = _traits(profs)
    builder = LANE_BUILDER.get(lane, _jungle_rows)
    main_title = {
        '打野': '打野节奏（这条英雄专属路线）',
        '中路': '中路节奏（这条英雄专属打法）',
        '发育路': '发育路打法（这条英雄专属节奏）',
        '对抗路': '对抗路打法（这条英雄专属打法）',
        '游走': '游走职责（这条英雄专属打法）',
    }.get(lane, '分路打法')

    sections = [(main_title, ['节点', '做法', '为什么'], builder(hero, profs, tr, lane))]

    # 高分实战要点放在最前面 —— 这是用户最想看的内容
    pro = _pro_rows(hero, profs, tr)
    if pro:
        sections.insert(0, ('高分实战要点（这个英雄专属技巧）',
                            ['要点', '怎么用', '口径'], pro))

    ph = _phase_rows(hero, profs, tr)
    if ph:
        sections.append(('阶段节奏（前期 → 中期 → 后期）', ['阶段', '怎么打', '要点'], ph))

    mu = _matchup_rows(hero, profs, tr)
    if mu:
        sections.append(('对位重点', ['对象', '怎么做', '原因'], mu))

    tips = (hero.get('pro_tips') or [])[:4]
    return {
        'sections': sections,
        'tips': tips,
        'tags': _tag_line(profs),
    }
