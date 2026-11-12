# -*- coding: utf-8 -*-
"""
王者荣耀 单英雄深度攻略 · 打法引擎（playbook）

职责：
  1. skill_profiles()  从该英雄自己的官方技能描述抽出「技能画像」：
     控制类型 / 位移 / 护盾 / 治疗 / 增益 / 蓄力引导 / 射程 / 伤害类型。
  2. build_combos()    依据技能画像，生成「场景化、可执行、带失败点与收益点」的连招。
     每条连招只使用该英雄自己的技能；官方给出的连招原文单独标注为 A 类。
  3. lane_playbook()   依据分路（打野 / 中路 / 发育路 / 对抗路 / 游走）输出地图玩法：
     打什么路线、怎么支援、怎么蹲草藏视野、怎么保护人、怎么推塔。

纪律：只从该英雄自身数据推导机制事实，不生成跨英雄通用话术；
      推断类内容一律标 D（主观判断），官方原文标 A（官方硬数据）。
"""
import re

from analyzer import strip_numbers

# ---------------------------------------------------------------- 控制类型
CTRL_TYPES = [
    ('击飞', ['击飞', '击 飞', '挑飞', '击飞']),
    ('眩晕', ['眩晕', '晕眩', '击晕', '眩晕']),
    ('定身', ['定身']),
    ('击退', ['击退', '推开', '弹开', '撞飞', '击退']),
    ('拉拽', ['拉拽', '拉扯', '拽回', '拉扯']),
    ('禁锢', ['禁锢', '束缚', '锁住']),
    ('嘲讽', ['嘲讽']),
    ('沉默', ['沉默']),
    ('减速', ['减速', '减速', '减速']),
    ('缴械', ['缴械']),
]
HARD_CTRL_KINDS = {'击飞', '眩晕', '定身', '击退', '拉拽', '禁锢', '嘲讽'}

DISP_KW = ['位移', '突进', '冲锋', '后撤', '后跳', '跃', '冲向前',
           '扑向', '滑', '翻滚', '拉扯', '拉向', '拉近', '冲向', '撞向',
           '向前移动', '瞬移', '闪现', '跃向', '扑']
SHIELD_KW = ['护盾']
HEAL_KW = ['治疗', '回血', '恢复生命', '回复生命', '回复已损失', '再生', '每秒回复生命']
REVIVE_KW = ['复活', '替身傀儡', '替身']
BUFF_KW = ['提升', '增加', '强化', '获得', '免疫', '霸体', '攻击速度',
           '攻击力', '移速', '冷却缩减']
CHARGE_KW = ['蓄力', '引导', '持续施法', '蓄']
RANGE_FAR_KW = ['远程', '弹道', '飞行']
RANGE_NEAR_KW = ['近战']
DMG_KW = ['物理伤害', '法术伤害', '真实伤害']


def _hit(text, kws):
    return any(k in text for k in kws)


def skill_profiles(hero):
    """从官方技能描述构建技能画像列表（不含被动）。"""
    out = []
    skills = hero.get('skills') or []
    actives = skills[1:] if len(skills) > 1 else []
    n = len(actives)
    for i, s in enumerate(actives):
        desc = strip_numbers(s.get('desc') or '')
        ctrl = []
        for kind, kws in CTRL_TYPES:
            if _hit(desc, kws):
                ctrl.append(kind)
        prof = {
            'i': i + 1,
            'name': s.get('name', ''),
            'cd': s.get('cd', ''),
            'desc': desc,
            'ctrl': ctrl,
            'hard_ctrl': [c for c in ctrl if c in HARD_CTRL_KINDS],
            'has_ctrl': bool(ctrl),
            'disp': _hit(desc, DISP_KW),
            'shield': _hit(desc, SHIELD_KW),
            'heal': _hit(desc, HEAL_KW),
            'buff': _hit(desc, BUFF_KW),
            'charge': _hit(desc, CHARGE_KW),
            'far': _hit(desc, RANGE_FAR_KW),
            'near': _hit(desc, RANGE_NEAR_KW),
            'dmg': [d for d in DMG_KW if d in desc],
            'clear': _hit(desc, ['兵线', '小兵', '野怪', '单位']),
            'revive': _hit(desc, REVIVE_KW),
            'buffself': _hit(desc, ['自身', '自己'] ) and _hit(desc, ['提升', '增加', '强化', '暴击', '攻速', '移速']),
            'summon': _hit(desc, ['召唤', '傀儡', '分身', '召唤物']),
            'mode': _hit(desc, ['形态', '切换', '展开', '关闭', '弓', '长弓', '进入', '退出']),
            'dot': _hit(desc, ['持续灼烧', '灼烧', '持续伤害', '每秒造成']),
            'execute': _hit(desc, ['斩杀', '处决', '对生命值低于', '已死亡']),
            'antiheal': _hit(desc, ['回复减少', '治疗效果降低', '禁止治疗', '反治疗']),
            'mark': _hit(desc, ['标记', '锁定', '易伤', '破绽', '目标身上']),
            'stun_field': _hit(desc, ['阵法', '领域', '范围持续', '持续8秒', '持续6秒', '持续5秒']),
            'is_ult': (i + 1 == n) and n >= 3,
        }
        out.append(prof)
    return out


def _mech(prof, limit=90):
    """技能的机制要点（去掉数值），用于连招表里的关键动作说明。"""
    desc = prof['desc'] or ''
    parts = re.split(r'[。；]', desc)
    best = ''
    for p in parts:
        p = re.sub(r'\s+', '', p)
        p = re.sub(r'被动[:：]?', '', p)
        if not p:
            continue
        if prof['hard_ctrl'] and any(k in p for k in prof['hard_ctrl']):
            best = p
            break
    if not best:
        for p in parts:
            p = re.sub(r'\s+', '', p)
            p = re.sub(r'被动[:：]?', '', p)
            if len(p) >= 6:
                best = p
                break
    best = re.sub(r'[（(]\s*[+＋]?[^（）()]*[）)]', '', best)
    best = re.sub(r'[，、]\s*[。]', '。', best).strip('，。、； ')
    # 去掉残留的斜杠/波浪号等孤立符号
    best = re.sub(r'[~/～*&+＋]{1,}', '', best)
    best = re.sub(r'[，、]{2,}', '，', best)
    best = re.sub(r'^[，、。；\s]+', '', best)
    # 尾部被截断的半截词直接丢掉（避免出现「持续」这种断尾）
    best = re.sub(r'(持续|造成|获得|对|的|和|时|后)$', '', best)
    best = best.strip('，。、； ')
    # 超长时在语义边界（逗号/句号）截断，不做硬切，避免出现「…造成」这种半句
    if len(best) > limit:
        cut = -1
        for sep in ('，', '。', '、'):
            idx = best.rfind(sep, 0, limit)
            if idx > limit * 0.35:
                cut = idx
                break
        if cut > 0:
            best = best[:cut]
        else:
            best = best[:limit]
    # 截断后去掉悬空动词，避免出现「延长持续」这种半句
    for _ in range(3):
        new = re.sub(r'(延长|提升|增加|减少|回复|获得|造成|伤害|持续|对|的|和|时|后)$', '', best)
        if new == best:
            break
        best = new
    best = best.strip('，。、； ')


def _pick(profs, pred, prefer_high_cd=False):
    """按条件挑技能；prefer_high_cd=True 时优先冷却长的（通常是大招）。"""
    cands = [p for p in profs if pred(p)]
    if not cands:
        return None
    if prefer_high_cd:
        cands.sort(key=lambda p: _cd_num(p['cd']), reverse=True)
    return cands[0]


def _cd_num(cd):
    m = re.findall(r'\d+', str(cd or ''))
    return int(m[0]) if m else 0


def _seq(profs):
    """按技能编号返回，供按键序表达。"""
    return {p['i']: p for p in profs}


def _keys(profs):
    """按键号列出技能名。"""
    return '、'.join(f"{p['i']}技能「{p['name']}」" for p in profs)


# ---------------------------------------------------------------- 连招生成
def build_combos(hero, profs, lane):
    """
    返回连招列表，每条：
      scene / purpose / trigger / steps[(技能号, 技能名, 机制要点)]
      fail / gain / drill / level('A'=官方原文, 'D'=机制推演) / note
    """
    combos = []

    # ---- A 类：官方原文连招（保留，标注为官方硬数据） ----
    for c in (hero.get('combos') or []):
        t = c if isinstance(c, str) else (c.get('name', '') + '：' + str(c.get('seq', '')))
        m = re.search(r'[（(]([^）)]+)[）)]', t)
        note_in = m.group(1).strip() if m else ''
        base = re.sub(r'[（(][^）)]*[）)]', '', t).strip()
        combos.append({
            'scene': '官方给定连招',
            'purpose': '官方攻略给出的标准起手顺序' + (f'，官方另注：{note_in}' if note_in else ''),
            'trigger': '按局面直接起手，命中后接后续' + (f'（官方标注：{note_in}）' if note_in else ''),
            'steps': [],
            'raw': t,
            'fail': '官方连招的每一段仍依赖前段命中，被打断后剩余技能不接上',
            'gain': '把该英雄最常用的起手收益稳定兑现',
            'drill': '训练营里对着木桩把这条连招连打 10 次，确保不出现空段',
            'level': 'A',
            'note': '原文口径来自官方英雄攻略数据',
        })

    if not profs:
        return combos

    ult = _pick(profs, lambda p: p['is_ult'])
    hard = _pick(profs, lambda p: p['hard_ctrl'])
    soft = _pick(profs, lambda p: p['has_ctrl'] and not p['hard_ctrl'])
    ctrl_any = hard or soft
    disp = _pick(profs, lambda p: p['disp'])
    # 纯伤害技能：优先「不靠位移也能打伤害」的技能，避免把位移当成输出
    dmg = _pick(profs, lambda p: p['dmg'] and not p['disp']) or _pick(profs, lambda p: p['dmg'])
    tank = _pick(profs, lambda p: p['shield'] or p['heal'])
    clear_skill = _pick(profs, lambda p: p['clear'])
    cheap = _pick(profs, lambda p: p['dmg'] and not p['is_ult'] and _cd_num(p['cd']) <= 8)

    def chain_of(*cands):
        """按顺序收集技能，索引不重复；跳过与前面同索引的。"""
        out = []
        seen = set()
        for p in cands:
            if p is None or p['i'] in seen:
                continue
            seen.add(p['i'])
            out.append(p)
        return out

    def step(p):
        return (p['i'], p['name'], _mech(p))

    # ---- 1. 开团先手（有硬控） ----
    if hard:
        chain = chain_of(hard, disp, ult, dmg)
        combos.append({
            'scene': '团战开团先手',
            'purpose': '用最短时间把对方关键位控住，把先手权换成团战收益',
            'trigger': '对方核心控制尚未交出、目标站位成团、且你能先于对方开团',
            'steps': [step(p) for p in chain],
            'fail': '硬控落空或被对方前排挡下，后面所有技能都变成空放',
            'gain': '控住对方 C 位一个技能周期，队友的输出窗口直接打开',
            'drill': '训练营里把假人固定在墙边，练习硬控命中后能否在对方位移前接上后续技能',
            'level': 'D',
            'note': '按该英雄硬控机制推演的顺序链',
        })

    # ---- 2. 藏视野绕后（有位移） ----
    if disp and ctrl_any:
        ctrl = ctrl_any
        chain = chain_of(disp, ctrl, ult, dmg)
        combos.append({
            'scene': '蹲草绕后突袭',
            'purpose': '用位移取消读图时间，让对方来不及交控制',
            'trigger': '目标单独走位且无位移可用、对方辅助不在附近、你有侧向位移可绕后',
            'steps': [step(p) for p in chain],
            'fail': '位移落点被地形卡住，或位移方向与目标相反，导致控技能甩空',
            'gain': '对方反应时间被压缩到不足交出一个技能',
            'drill': '训练营里从河道草丛进场，固定练同一个进场角度，练到不用看小地图也能落点',
            'level': 'D',
            'note': '按该英雄位移机制推演',
        })

    # ---- 2b. 草丛埋伏突袭（有控制，无位移也能打） ----
    if ctrl_any and not disp:
        combos.append({
            'scene': '草丛埋伏突袭',
            'purpose': '用草丛消除对方反应时间，靠控制先手换血或击杀',
            'trigger': '目标单独路过且路线经过草丛、对方辅助不在附近、你已就位',
            'steps': [step(ctrl_any)],
            'fail': '从草丛正面走出才放技能，等于告诉对方「草里有人」，对方会提前交位移',
            'gain': '对方少交一个技能，己方就能多打一套完整输出',
            'drill': '训练营里把假人放进固定路线，练「不出草先出技能」',
            'level': 'D',
            'note': '按该英雄控制机制、结合草丛先手推演',
        })

    # ---- 3. 对线换血消耗 ----
    if cheap and ctrl_any:
        combos.append({
            'scene': '对线换血消耗',
            'purpose': '用最低成本的技能起手，确认对方状态后再决定是否打满',
            'trigger': '对方核心技能刚交完、或对方血量低于你可一套打死的程度',
            'steps': [step(p) for p in chain_of(cheap, ctrl_any)],
            'fail': '第一段落空后继续按后续技能，等于把所有技能一次性交到空气上',
            'gain': '用一次小技能换掉对方一次状态判断机会，后续由队友接手或自己回撤',
            'drill': '训练营里练「小技能先手 → 对方位移后仍能接上控制」的两种落点',
            'level': 'D',
            'note': '按该英雄技能冷却与控制类型推演',
        })
    elif cheap:
        combos.append({
            'scene': '对线换血消耗',
            'purpose': '在对方技能真空期打满伤害',
            'trigger': '对方核心技能刚交完、血线已进入可击杀区间',
            'steps': [step(cheap)],
            'fail': '技能落空后仍继续前压，换血变单方面挨打',
            'gain': '抢到一次血量差，为下一次换血或推塔拿到主动权',
            'drill': '训练营里用假人练技能命中后的补刀节奏',
            'level': 'D',
            'note': '按该英雄输出技能推演',
        })

    # ---- 4. 追击收割（有位移） ----
    if disp and dmg:
        chain = chain_of(disp, dmg, hard)
        combos.append({
            'scene': '追击与残血收割',
            'purpose': '把已经交掉关键技能的残血目标彻底收掉',
            'trigger': '目标残血、位移与闪现已交、且你没有更重要的战场任务',
            'steps': [step(p) for p in chain],
            'fail': '位移留到残血才交，目标一个闪现或加速就脱离，交空后你被反打',
            'gain': '把一个人头的赏金与经济差一次性兑现',
            'drill': '训练营里练「先贴近再补伤害」，确认位移不会与伤害技能抢先后顺序',
            'level': 'D',
            'note': '按该英雄位移与伤害机制推演',
        })

    # ---- 5. 逃生保命 ----
    if disp:
        chain = chain_of(disp, tank)
        combos.append({
            'scene': '残血逃生保命',
            'purpose': '拉开距离，把命保住而不是换人头',
            'trigger': '血量进入危险线、对方还有控制未交、己方无支援',
            'steps': [step(p) for p in chain],
            'fail': '朝敌人方向交位移，等于主动送进控制范围',
            'gain': '保住这条线的塔与下一波兵线，等级与经济不断档',
            'drill': '训练营里对着假人练反向位移，养成「往己方塔下交位移」的习惯',
            'level': 'D',
            'note': '按该英雄位移机制推演',
        })

    # ---- 6. 拆塔清线（推塔/清兵） ----
    if clear_skill or dmg:
        cl = clear_skill or dmg
        combos.append({
            'scene': '拆塔与清线',
            'purpose': '把优势转成塔与经济，而不是无意义换人头',
            'trigger': '兵线已到对方塔下、对方回城或位置靠后',
            'steps': [step(cl)],
            'fail': '把范围技能浪费在兵线上，或在对方塔下强开导致被反杀',
            'gain': '拆塔进度与补刀经济同时到手，优势真正变成推塔能力',
            'drill': '训练营里练「兵线到塔下再放技能」，避免提前空放',
            'level': 'D',
            'note': '按该英雄输出技能推演',
        })

    # ---- 6b. 复活/保护位专属连招 ----
    revive = _pick(profs, lambda p: p['revive'])
    if revive:
        combos.append({
            'scene': '保护 C 位 / 复活兜底',
            'purpose': '把复活当保险而不是进攻手段，让己方 C 位敢于压上输出',
            'trigger': '己方 C 位在前排附近、对方有开团英雄在场、你的复活已就绪',
            'steps': [step(revive)],
            'fail': '在安全位置提前交掉复活，等真正需要时已经没有可用次数',
            'gain': 'C 位敢于站位输出，团队总伤害直接上一个台阶',
            'drill': '训练营里让假人站到对方脸上，练「第一时间把替身挂上去」的判断',
            'level': 'D',
            'note': '按该英雄复活机制推演',
        })

    # ---- 7. 打断与保护（控制型） ----
    if ctrl_any:
        combos.append({
            'scene': '打断与保护队友',
            'purpose': '在关键动作读条时把对方打断，或在队友被追时把人拉回来',
            'trigger': '对方正在读关键大招/传送，队友血量告急需要喘息',
            'steps': [step(ctrl_any)],
            'fail': '控制交早，对手交了净化或加速后你进入空窗',
            'gain': '一次控制救下队友，或直接掐掉对方一波团',
            'drill': '训练营里专门练「读条最后一刻出手」的时机',
            'level': 'D',
            'note': '按该英雄控制类型推演',
        })

    # ---- 8. 分路专属连招 ----
    if lane == '打野':
        if disp and ctrl_any:
            combos.append({
                'scene': '打野抓人（贴脸开团）',
                'purpose': '利用野区地形把控制打满，达到击杀或逼出闪现',
                'trigger': '目标被逼到墙角或河道草丛、你的技能已到齐',
                'steps': [step(p) for p in chain_of(disp, ctrl_any, hard)],
                'fail': '在没有墙体的开阔地强开，位移落点暴露，控制被对方用位移躲开',
                'gain': '一条命 + 一波野区经济差，直接进入下一轮滚雪球',
                'drill': '训练营里在墙角固定假人，练「位移贴墙 → 控制贴脸」两段衔接',
                'level': 'D',
                'note': '按该英雄位移与控制机制、结合打野地形推演',
            })
        if disp and dmg:
            combos.append({
                'scene': '打野入野区抢资源',
                'purpose': '快速进场抢红隼或反野，用位移抢在对方打野之前到位',
                'trigger': '红隼刷新前后、或对方打野位置未知但你有信息优势',
                'steps': [step(p) for p in chain_of(disp, dmg)],
                'fail': '位移进场太早暴露位置，被对方打野反蹲',
                'gain': '拿到全场第一个中立资源，并掌握开局的野区主动权',
                'drill': '训练营里掐表练红隼刷新前的进场路线',
                'level': 'D',
                'note': '按该英雄位移与输出机制推演',
            })
    if lane == '中路':
        if ctrl_any and disp:
            combos.append({
                'scene': '中路支援开团',
                'purpose': '用河道草丛的突进把对面后排从阵型里拉出来',
                'trigger': '边路队友已经先手、对方 C 位站位靠前、你能比对方辅助先到',
                'steps': [step(p) for p in chain_of(disp, ctrl_any, hard)],
                'fail': '兵线未清就支援，回线时掉塔，或者支援路上被对方埋伏',
                'gain': '把一次边路小团变成团灭，中路顺势推线扩大优势',
                'drill': '训练营里练「清线 → 河道草丛 → 突进」三段位移',
                'level': 'D',
                'note': '按该英雄位移与控制机制、结合中路支援半径推演',
            })
    if lane == '发育路':
        if dmg and cheap:
            combos.append({
                'scene': '发育路输出起手',
                'purpose': '在最短时间内把伤害打满，逼出对方保命技能',
                'trigger': '对方站位靠前、位移与保命技能未交',
                'steps': [step(p) for p in chain_of(cheap, dmg)],
                'fail': '第一段落空后站在原地继续平A，被对方贴脸反打',
                'gain': '换掉对方一套技能，为己方开团创造时间差',
                'drill': '训练营里练「命中后立刻后撤到攻击距离边缘」的节奏',
                'level': 'D',
                'note': '按该英雄输出技能推演',
            })
    if lane == '对抗路':
        if hard and disp:
            combos.append({
                'scene': '对抗路越塔开团',
                'purpose': '用控制把对方留在塔下，配合兵线完成击杀',
                'trigger': '对方回城未满、兵线已进塔、你有足够战力打这一波',
                'steps': [step(p) for p in chain_of(disp, hard, ult)],
                'fail': '越塔后伤害不够、对方防御塔伤害高，被塔换掉',
                'gain': '击杀 + 推塔，把单线优势滚成全局优势',
                'drill': '训练营里对着塔假人练「越塔前先清掉塔下一波兵」',
                'level': 'D',
                'note': '按该英雄位移与硬控机制推演',
            })
    if lane == '游走':
        if ctrl_any:
            combos.append({
                'scene': '游走反开团 / 保护开团',
                'purpose': '在对方先手落空的瞬间控制住人，或把要打己方 C 位的人先控住',
                'trigger': '对方先手刚落地、己方 C 位还在输出位置',
                'steps': [step(ctrl_any)],
                'fail': '控制交早被对方净化或加速抵消，己方 C 位仍然被秒',
                'gain': '护住己方核心输出，把被反打的团战变成可打的团战',
                'drill': '训练营里练「对方开团落地后再出手」的延迟判断',
                'level': 'D',
                'note': '按该英雄控制机制、结合游走保护职责推演',
            })

    return combos


# ---------------------------------------------------------------- 分路玩法
def lane_playbook(hero, profs, lane, role):
    """
    返回 dict：{'sections': [(标题, 表头, 行列表), ...], 'tips': [...] }
    每段都是可执行的动作，不是空话。
    """
    has_hard = any(p['hard_ctrl'] for p in profs)
    has_ctrl = any(p['has_ctrl'] for p in profs)
    has_disp = any(p['disp'] for p in profs)
    has_tank = any(p['shield'] or p['heal'] for p in profs)
    has_ult = any(p['is_ult'] for p in profs)
    ult = _pick(profs, lambda p: p['is_ult'])
    ult_name = ult['name'] if ult else '大招'

    sections = []

    # ---------- 通用：视野与蹲草（所有分路都要） ----------
    vision_rows = [
        ('河道草丛', '蹲守边缘，不要站草丛正中',
         '草丛边缘既能看到对方来向，又能在对方进草丛前先看到人影'),
        ('己方野区入口', '打完野顺手插眼，别把视野只放在河道',
         '河道有眼不等于安全，对方可从侧面野区直接进塔'),
        ('对方野区盲区', '没有视野信息时不要主动进',
         '盲区里的信息为零，等于把先手权交给对方'),
        ('兵线后方', '换血后立刻后撤到兵线后方',
         '对方打野从侧面来时，兵线能替你挡住第一轮技能'),
    ]
    if has_disp:
        vision_rows.append(('草丛 + 侧向位移', '准备绕后时先掐住位移角度',
                            '有位移的英雄可以取消一段读图时间，这是最隐蔽的开团方式'))
    sections.append(('蹲草与藏视野', ['站位', '要点', '为什么'], vision_rows))

    # ---------- 分路专属 ----------
    if lane == '打野':
        route_rows = [
            ('开局第一圈', '红隼 → 蓝buff → 小野 → 猪 → 红buff 一路刷完',
             '把第一轮野清完再升 4 级，避免野区被反'),
            ('惩戒时机', '只交给能改变结果的节点：抢红隼、反野惩戒、收掉残血野怪',
             '开局就交掉惩戒，你在 4 级那波抓人就没有第二条命'),
            ('第一波抓人', '4 级后看边路，谁在压线就先看谁',
             '压线的人位置最靠前，是最容易形成击杀的对象'),
            ('4 级那波', '抓不到就回野区继续刷，不要在河道空等',
             '抓人失败的代价是等级与野区经济双输'),
            ('中期控资源', '把双龙与空间之灵的时间点提前 30 秒排进路线',
             '资源点的时间差就是团队经验的差'),
            ('后期', '不打无视野架，专挑对方落单与回城位',
             '后期对方装备起来，抓错人比不抓更亏'),
        ]
        sections.append(('刷野路线与节奏', ['节点', '动作', '原因'], route_rows))
        support_rows = [
            ('跟团', '队友先手后再进，不要自己先手开团',
             '打野等级领先但装备不一定领先，先手失败就是白送'),
            ('补控', '队友控住后你补伤害与控制，不要单独冲',
             '补刀位比开团位安全，收益一样高'),
            ('反蹲', '看见对方打野消失就往同一侧靠',
             '对方打野消失多半是来蹲你，先到先站位'),
        ]
        sections.append(('打野与队友的配合', ['场景', '做法', '原因'], support_rows))

    if lane == '中路':
        route_rows = [
            ('清线优先级', '先清完再支援，除非对方打你队友且你离得近',
             '中路线权没了，支援就是有去无回'),
            ('支援路线', '走河道草丛而不是从中路直线穿',
             '直线穿等于把位置送给对方打野'),
            ('抢支援窗口', '看到边路交火，在对方技能交空后到，不是开团了就到',
             '早到 5 秒是接盘，晚到 5 秒是收尸'),
            ('回中', '打完立刻回中路补线与补视野',
             '中路空一秒，下一波兵就推进对方塔下'),
            ('河道草丛', '把自己当第二个打野位，蹲对方从中路消失的路线',
             '中路的视野优势来自草丛，不来自河道中央'),
        ]
        sections.append(('中路支援与转线', ['场景', '做法', '原因'], route_rows))
        push_rows = [
            ('中路推进', '支援回线后把兵线推过去，再去下一波',
             '推线是把支援换成经济与地图压力'),
            ('拆塔窗口', '对方回城且兵线到位时拆，不要在塔下与人对峙',
             '拆塔收益稳定，对峙收益不稳定'),
        ]
        sections.append(('推塔与经济', ['场景', '做法', '原因'], push_rows))

    if lane == '发育路':
        route_rows = [
            ('补刀节奏', '补最后一刀优先于抢人头',
             '发育路的经济来自补刀，人头只是附带'),
            ('站位', '站在己方塔前或兵线后侧，不要站兵线中间',
             '站中间会被对方贴脸消耗，掉的血比掉的兵贵'),
            ('消耗窗口', '对方技能交了再打，打完立刻后撤',
             '换血的目的只是换掉对方技能，不是换掉对方人'),
            ('推线', '兵线推到对方塔前再回城，不要在野区浪费回城时间',
             '兵线进塔能逼对方回城，为你换回血线时间'),
            ('参团时机', '对方控制交了再进场，不要用第一个技能开团',
             '射手的第一轮输出比第二轮值钱得多'),
            ('抱团', '中期开始跟打野节奏一起转线',
             '射手脱离队友单独行动，死亡率远高于收益'),
        ]
        sections.append(('发育路线与输出环境', ['节点', '动作', '原因'], route_rows))
        protect_rows = [
            ('站位跟团', '站在辅助或坦克身后，而不是队伍最前面',
             '前排能替你挡第一轮技能'),
            ('被开团时', '先交保命技能，不要先交输出技能',
             '活着才有第二轮输出'),
        ]
        sections.append(('团战里的自保', ['场景', '做法', '原因'], protect_rows))

    if lane == '对抗路':
        route_rows = [
            ('开局换血', '对方技能交完再上去打一套，打完回塔下',
             '对抗路的第一波优势来自换血时机，不是操作'),
            ('兵线管理', '把兵线留在对方塔前，不要站在塔下互耗',
             '线在对方塔前，对方就不敢随便打你'),
            ('支援取舍', '中路的团优先，单线的团看兵线与等级差',
             '对抗路一次支援的代价是一整波兵线'),
            ('支援方式', '支援前先把兵线推过去，让对方必须回城',
             '对方回城时你不在，等于白丢一波线'),
            ('单带时机', '中期队友抱团时单带，后期团战前先带线',
             '带线能逼对方回城，等于用兵线换人数'),
            ('回防', '对方打野位置不明时立刻回塔，不要贪兵',
             '对抗路被抓一次，节奏会直接崩掉'),
        ]
        sections.append(('对抗路线、支援与推塔', ['节点', '动作', '原因'], route_rows))
        protect_rows = [
            ('团战位置', '团战开团你第二进场，或站在侧面保护射手',
             '对抗路的价值在承伤与开团，不在单杀'),
            ('带线与参团', '队友开团后再进场，不要提前交位移',
             '先手权让给开团位，你能打满输出'),
        ]
        sections.append(('团战定位', ['场景', '做法', '原因'], protect_rows))

    if lane == '游走':
        route_rows = [
            ('开局', '跟着打野的第一波入侵或第一波抓人进场',
             '游走的价值在于让打野敢抓人'),
            ('游走路线', '优先游走对方射手与中路之间',
             '这条线最容易出事，也最容易救'),
            ('视野布置', '把视野放在对方进攻方向，而不是自家野区',
             '视野要放在对方来的方向才有价值'),
            ('保护时机', '对方刺客消失就往 C 位靠',
             '保护是在对方出现前到位，不是出现后赶过去'),
            ('跟团', '打野在哪条线你就出现在哪条线',
             '分散的游走等于没有游走'),
            ('不该做的', '不要在己方无输出的时间点独自去抓人',
             '没有输出的抓人只是送人头'),
        ]
        sections.append(('游走路线与保护职责', ['节点', '动作', '原因'], route_rows))
        protect_rows = [
            ('护 C 位', '站在己方 C 位与对方之间',
             '对方要打 C 位必须先穿过你'),
            ('先手开团', '己方有人能开团时，你在侧面接第二段控制',
             '双开团比单开团更难被反打'),
            ('反开团', '对方开团落地后再交控制',
             '这时对方没有净化与位移'),
            ('撤退信号', 'C 位血量危险时立刻喊退，不要硬保',
             '救不回来就一起死，亏两波'),
        ]
        sections.append(('保护人的具体做法', ['场景', '做法', '原因'], protect_rows))

    # ---------- 通用三件套：读图 / 转线 / 撤退 ----------
    common_rows = [
        ('读图频率', '每打完一波就看一眼小地图，别等出事才看',
         '地图信息比操作更早决定胜负'),
        ('提前量', '看到对方消失就动，比对方出现在你脸上早 20~30 秒',
         '这 20~30 秒就是你的绕后或转线窗口'),
        ('转线顺序', '先清线、再转线、再进野区',
         '顺序错了就会出现两头空'),
        ('撤退', '每次动手前先想好退路，退路比收益重要',
         '残血站在原地等于把优势送回去'),
    ]
    sections.append(('通用三件套：读图、转线、撤退', ['要点', '做法', '为什么'], common_rows))

    # ---------- 角色补充 ----------
    role_rows = []
    if role == '辅助' or lane == '游走':
        role_rows.append(('保护优先级', '射手 > 法师 > 打野', 'C 位死一次，团战直接结束'))
    if has_hard:
        role_rows.append(('开团权', '你有硬控，可以先手，但要把先手留到关键团',
                           '先手太早会让对方用位移和净化反打'))
    elif has_ctrl:
        role_rows.append(('开团权', '你只有软控，先手收益低，优先打后手与补控',
                           '软控先手容易被净化和加速抵消'))
    else:
        role_rows.append(('开团权', '你没有控制，开团交给有控制的人，你负责跟伤害',
                           '无控制强行开团等于送'))
    if has_tank:
        role_rows.append(('承伤位', '你该第一个进场，但必须站在己方 C 位正前方',
                           '承伤位站错位置，伤害全打到 C 位身上'))
    if has_ult:
        role_rows.append(('大招时机', '大招留到对方关键控制交完之后',
                           '大招早交等于给对面一次免费撤退时间'))
    if role_rows:
        sections.append(('按你的定位补一条', ['项', '做法', '原因'], role_rows))

    tips = []
    for t in (hero.get('pro_tips') or [])[:4]:
        tips.append(t)
    return {'sections': sections, 'tips': tips}


def feature_tags(p):
    """把技能画像转成一行人类可读的机制标签。"""
    f = []
    if p['hard_ctrl']:
        f.append('硬控：' + '、'.join(p['hard_ctrl']))
    elif p['ctrl']:
        f.append('控制：' + '、'.join(p['ctrl']))
    if p['disp']:
        f.append('位移/拉拽')
    if p['revive']:
        f.append('复活保护')
    if p['shield']:
        f.append('护盾')
    if p['heal']:
        f.append('治疗/回复')
    if p['buffself'] or p['buff']:
        f.append('自身强化')
    if p['mode']:
        f.append('形态切换')
    if p['stun_field']:
        f.append('持续区域')
    if p['mark']:
        f.append('标记/锁定')
    if p['antiheal']:
        f.append('反治疗')
    if p['execute']:
        f.append('斩杀')
    if p['dot']:
        f.append('持续伤害')
    if p['charge']:
        f.append('蓄力/引导')
    if p['summon']:
        f.append('召唤物')
    if p['far']:
        f.append('远程')
    if p['near']:
        f.append('近战')
    if p['dmg']:
        f.append('、'.join(p['dmg']))
    if p['is_ult']:
        f.append('大招')
    if p['clear']:
        f.append('可清线')
    return '、'.join(f) or '—'
