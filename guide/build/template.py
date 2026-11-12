# -*- coding: utf-8 -*-
"""
王者荣耀 单英雄深度攻略 · HTML 生成器

严格遵循 13 节骨架契约：
  0 范本说明 / 1 一页纸速览 / 2 版本状态与数据口径 / 3 技能机制与被动
  4 出装铭文与召唤师技能 / 5 开局路线 / 6 连招库 / 7 节奏与时间锚点
  8 抓人与绕后(非打野=换血与线权) / 9 团战 / 10 三种局势
  11 适配阵容与克制 / 12 常见失误与训练法 / 13 附录
"""
import json
import os
import re
import datetime

from analyzer import (analyze, clauses, strip_numbers, classify_combo,
                      combo_risk, combo_text, combo_steps, ROLE_MAP, LANES)

# ============================ 全局口径常量 ============================
SNAPSHOT_DATE = '2026-11-12'
CURRENT_SEASON = 'S36'

# 现行野区时间轴（硬约束：河蟹 S36 已移除）
WILD_TIMELINE = [
    ('0:30', '红隼刷新', '首个野怪刷新点，先手方有优势'),
    ('2:00', '空间之灵刷新 / 先知主宰刷新', '先知主宰是 S36 后段的中立资源点'),
    ('10:00', '双龙刷新', '双龙为中后期主要资源争夺点'),
    ('20:00', '风暴龙王刷新', '决胜点资源'),
]

# 各分路的开局路线模板（非打野按分路定制）
LANE_OPENING = {
    '打野': {
        'title': '刷野路线与节奏起点',
        'route': [
            ('0:00', '站红隼侧，等 0:30 红隼刷新', '红隼是全场第一个中立资源，抢到就是开局节奏'),
            ('0:30', '打红隼 → 转向蓝buff', '红隼给经济，蓝buff决定你的第一个技能强度'),
            ('1:30', '蓝buff → 立刻打小野', '不要在蓝buff原地恋战，惩戒要留到关键节点'),
            ('2:00', '升到 4 级，看空间之灵与先知主宰', '4 级是第一个能抓人的节点'),
            ('3:00', '清完第一轮野，蹲边路草丛', '第一波 gank 决定前期节奏'),
        ],
        'punish': [
            ('惩击时机', '惩击留给能改变结果的节点：抢红隼、反野惩戒、或残血野怪收尾。不要开局就交掉。'),
            ('零风险提速点 1', '红隼刷新前提前站位，红隼一出现即可开打，零反蹲风险。'),
            ('零风险提速点 2', '蓝buff到手立刻转小野，用移动时间等小野刷新，不空等。'),
            ('零风险提速点 3', '第一轮野结束后直接进敌方野区视野盲区蹲点，而不是原地刷到 6 级。'),
        ],
        'pivot': '第一波抓人时间锚点',
    },
    '对抗路': {
        'title': '开局对线与第一波节奏',
        'route': [
            ('一级', '站上路河道草丛或己方塔前，观察对方站位', '一级先手权决定这条线的主动权'),
            ('1 级', '抢线权：速清第一波兵', '线权在手才有换血与支援的资格'),
            ('2 级', '看小地图，敌方打野位置不明就不压线', '信息不明时压线＝送被抓'),
            ('3-4 级', '第一波兵推到对方塔前，等对方回城', '回城真空期是唯一安全的换血窗口'),
            ('6 级', '第一波大招换血或直接转线', '第一波大招要么换到血量优势，要么就别交'),
        ],
        'punish': [
            ('站位', '一级站在能第一时间收兵的位置，不要站到对方兵线中间。'),
            ('抢线 / 卡线', '兵线进塔后再推，避免在对方塔下被反打。'),
            ('第一波兵', '抢线权优先于换血，线没抢到换血是亏的。'),
            ('第一次回城', '回城前先把兵线推到对方塔下，让对方先回城。'),
            ('首个节奏点', '对面打野位置未知时，任何主动换血都要留退路。'),
        ],
        'pivot': '第一波换血时间锚点',
    },
    '中路': {
        'title': '开局对线与支援半径',
        'route': [
            ('一级', '站在技能可及范围边缘', '中路的胜负手是技能命中率，不是兵线'),
            ('1 级', '清第一波兵，看清对方技能CD', '记住对方技能CD 是中路的硬信息'),
            ('2-3 级', '抢线权并向河道靠拢', '河道是中路与两侧的连接点'),
            ('4 级', '第一波支援窗口（若队友开团）', '4 级是第一个能参与团战的节点'),
            ('6 级', '清线后向边路转线', '中路英雄的价值在支援半径'),
        ],
        'punish': [
            ('站位', '站在河道草丛或塔前，不要站在兵线正前方。'),
            ('抢线 / 卡线', '中路线权决定支援速度，优先推线再支援。'),
            ('第一波兵', '清完立刻靠河道，不要留在原地等下一波。'),
            ('第一次回城', '回城前把兵线推过去，形成线权真空。'),
            ('首个节奏点', '对方消失时立刻后撤，回中路补视野。'),
        ],
        'pivot': '第一次支援时间锚点',
    },
    '发育路': {
        'title': '开局对线与发育节奏',
        'route': [
            ('一级', '站己方塔前，优先保命', '射手一级对线以不被打消耗为唯一目标'),
            ('1-2 级', '补最后一刀，攒经济', '发育路的经济来自补刀，不是参团'),
            ('3 级', '第一波兵推线，观察敌方辅助位置', '辅助位置比兵线重要'),
            ('4-6 级', '第一波换血窗口（对方技能交完）', '换血只打技能真空期'),
            ('6 级', '出塔接第一波团', '六级的射手是团战输出核心'),
        ],
        'punish': [
            ('站位', '站塔前或河道侧，不要站兵线中间抢平A。'),
            ('抢线 / 卡线', '发育路优先保线权，但塔下补兵优先于推线。'),
            ('第一波兵', '用补刀攒经济，不要为抢人头放弃补刀。'),
            ('第一次回城', '回城前推线到对方塔下，逼对方回城。'),
            ('首个节奏点', '对方辅助消失时后撤，对方打野露头时不贪兵。'),
        ],
        'pivot': '第一波团战时间锚点',
    },
    '游走': {
        'title': '开局对线与游走节奏',
        'route': [
            ('一级', '跟着打野节奏进入野区', '游走的开局跟着第一波入侵或第一波 gank'),
            ('2 级', '占河道视野 / 保护打野', '视野是游走的本职工作'),
            ('4 级', '第一波 gank 配合', '4 级开始游走才有实际威胁'),
            ('6 级', '第一波开团尝试', '第一波大招决定游走能否建立优势'),
            ('中期', '跟打野节奏联动', '游走的存在感 = 打野抓人时的第二选择'),
        ],
        'punish': [
            ('站位', '站在能支援两条路的位置，而不是死守一条线。'),
            ('抢线 / 卡线', '游走不靠线权吃饭，但也不能完全放弃兵线。'),
            ('第一波兵', '跟着打野节奏走，不要独自跑到无视野区。'),
            ('第一次回城', '回城前把视野布好再回。'),
            ('首个节奏点', '打野开团时你必须在侧翼，不是正面。'),
        ],
        'pivot': '第一波开团时间锚点',
    },
}

# 三种局势模板
SITUATION = {
    '顺风': {
        'target': '扩大领先，把优势变成地图控制，而不是刷数据',
        'actions': [
            '主动压线，把兵线推进对方塔下，换取更多支援时间差',
            '扩大 gank 范围，从一条线蔓延到两条线',
            '控下中立资源，把经济差滚成装备差',
            '找机会推塔，塔掉了比拿人头更值钱',
        ],
        'never': [
            '不要在优势局无理由接团，把大优势打没',
            '不要单挑进入对方控制范围，优势局最不值的是单挑失误',
        ],
    },
    '均势': {
        'target': '找到唯一的破局点，把平局变成优势',
        'actions': [
            '围绕中立资源做文章，时间点比人数重要',
            '抓对方打野 / 辅助的位置空档，而不是硬打 C 位',
            '跟着队友节奏走，避免单独开团',
            '关键技能留到团战，不要在线上随手交',
        ],
        'never': [
            '不要在均势局主动和对方打野换血，他可能带着人',
            '不要先手开团，除非你确定对方关键控制交了',
        ],
    },
    '逆风': {
        'target': '止损与拖时间，把经济差缩到可打范围',
        'actions': [
            '保 KDA，别再送出人头扩大赏金差',
            '守塔、偷资源、控中立，别做无意义的架',
            '抱团推进，找对方站位失误的架',
            '等对方核心装备还没做出来时打一波',
        ],
        'never': [
            '不要单带孤兵给抓单的机会',
            '不要在没有控制的情况下先手开团',
        ],
    },
}

# 训练法
TRAIN_DRILLS = [
    ('只练一个动作', '连续 20 局只练一个动作，其余照常打。练完再换下一个。'),
    ('录像复盘', '只回看自己这一个动作发生的片段，不看别的。'),
    ('固定场景', '训练营里固定一个假人位置，反复练同一个进场角度。'),
]

# 出装替换表
REPLACE_RULES = [
    ('敌方爆发高 / 强控多', '补一件防御装，把生存位让出来'),
    ('需要跑位和拉扯', '补移动装或攻速装，保证能持续输出'),
    ('后期需要穿人', '补穿透或破甲，把伤害打穿前排'),
]

FROZEN_INFO = [
    ('河道之灵（河蟹）', 'S36 已全部移除。任何"1 分钟抢河蟹"的说法均为旧版本内容，不要照做。'),
    ('旧野区时间轴', '"2 分钟暴君 / 8 分钟主宰"已作废。现行：2:00 先知主宰 + 空间之灵，10:00 双龙，20:00 风暴龙王。'),
    ('打野刀灼烧数值', '打野刀灼烧为公式制、各版本反复调整。不要引用固定每跳数字，改为训练营实测 + 局内说明为准。'),
    ('红刀灼烧', '紫刀普攻触发灼烧；红刀是否带灼烧随版本变动，以局内说明为准。'),
    ('娱乐模式调整', '共鸣之战等娱乐模式的改动不是排位本体加强，不要当成版本更新。'),
    ('体验服调整', '体验服改动未落地前，正文打法一律按正式服写。'),
    ('旧胜率与梯度', '不引用旧赛季胜率、旧梯度榜当当前结论。'),
    ('站桩射手卖鞋', '不是一刀切：急速鞋大后期可卖；抵抗之靴 / 影忍之足别卖；中期不卖。'),
]

# 数据来源分级
SOURCE_LEVELS = [
    ('A', '官方硬数据', '官方英雄数据库 / 公告原文，带日期与口径。可引用，但必须注明快照时间。'),
    ('B', '多来源共识', '三份以上攻略一致的说法，标注「主流观点」，不写「官方结论」。'),
    ('C', '体验服 / 未落地', '体验服与未落地调整，单独成块，不混进当前打法。'),
    ('D', '主观判断', '上手难度、克制归纳、优先级、训练法顺序，作者判断，明说。'),
]


def esc(s):
    s = '' if s is None else str(s)
    return (s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
             .replace('"', '&quot;'))


def lane_of(hero, override=None):
    if override:
        return override
    return hero.get('primary_lane') or '中路'


def official_lanes(hero, offmap):
    """从官方 roles 字段推出分路列表。"""
    o = offmap.get(hero['cname'])
    if not o:
        return [lane_of(hero)]
    ls = [ROLE_MAP[r] for r in o['roles'].split('|') if r in ROLE_MAP]
    return ls or [lane_of(hero)]


def clean(s):
    """去掉技能数值，保留机制。"""
    return strip_numbers(s)


def table(headers, rows, cls=''):
    h = ''.join('<th>' + esc(x) + '</th>' for x in headers)
    body = ''
    for r in rows:
        body += '<tr>' + ''.join('<td>' + (x if isinstance(x, str) and x.startswith('<') else esc(x)) + '</td>'
                                 for x in r) + '</tr>'
    return f'<div class="tw"><table class="tbl {cls}"><thead><tr>{h}</tr></thead><tbody>{body}</tbody></table></div>'


def callout(kind, title, body):
    return f'<div class="co co-{kind}"><div class="co-t">{title}</div><div class="co-b">{body}</div></div>'


def tag(kind):
    """信息类型标注角标。"""
    m = {'A': ('A', '官方硬数据'), 'B': ('B', '主流观点'),
         'C': ('C', '体验服/未落地'), 'D': ('D', '主观判断')}
    k, label = m.get(kind, ('', ''))
    return f'<span class="mk mk-{k}">{k} · {label}</span>'


def sec(num, title, purpose, body, extra=''):
    aid = 's%d' % num
    return f'''<section id="{aid}" class="sec">
<h2><span class="sn">{num}</span>{esc(title)}</h2>
<div class="purpose"><b>本节作用：</b>{esc(purpose)}</div>
{extra}
{body}
</section>'''


# ============================ 各节构建 ============================

def sec0(ctx):
    rows = [
        ('0', '范本说明', '说明本篇结构、标注规范与写作纪律'),
        ('1', '一页纸速览', '一屏内判断这英雄能不能上、怎么赢'),
        ('2', '版本状态与数据口径', '明确数据时间与来源，避免把旧数据当结论'),
        ('3', '技能机制与被动', '讲透被动怎么叠、怎么控，机制红利与浪费点'),
        ('4', '出装铭文与召唤师技能', '一套默认解 + 按局势替换 + 后期换装链'),
        ('5', '开局路线', ('刷野路线与惩击时机' if ctx['lane'] == '打野' else '开局对线与首个节奏点')),
        ('6', '连招库', '按场景分类，每条给触发条件、关键动作、失败点'),
        ('7', '节奏与时间锚点', '四拍闭环 + 提前量 + 五个时间点 + 五条自检'),
        ('8', ('抓人与绕后' if ctx['lane'] == '打野' else '换血与线权'),
         ('如何选目标、如何绕后、哪里翻车' if ctx['lane'] == '打野' else '换血窗口、线权归属、支援与防 gank 站位')),
        ('9', '团战', '进场前进场后两栏、目标选择、撤退方式、第二种用法'),
        ('10', '三种局势', '顺风/均势/逆风各自的目标、动作、禁区'),
        ('11', '适配阵容与克制', '机制层面的克制关系与组合思路'),
        ('12', '常见失误与训练法', '失误表 + 20 局只练一个动作'),
        ('13', '附录', '来源分级、避坑清单、仍存疑的点'),
    ]
    body = ''
    body += '<h3>13 节骨架</h3>'
    body += table(['#', '章节', '作用'], rows, 'skel')
    body += '<h3>四类信息标注规范</h3>'
    body += table(['标注', '含义', '使用规则'],
                  [[f'<span class="mk mk-{k}">{k} · {v}</span>', v, w]
                   for k, v, w in SOURCE_LEVELS])
    body += '<h3>三条写作纪律</h3>'
    body += table(['#', '纪律', '本篇执行方式'], [
        ('1', '时间敏感信息必须带日期与来源',
         f'本篇数据快照日期 {SNAPSHOT_DATE}；官方口径与主流观点分开标注，冲突数据并列呈现。'),
        ('2', '机制优先于数值',
         '正文以机制与红利为主体，技能数值已剥离；数值以局内说明为准。'),
        ('3', '克制只写机制层面共性',
         '只写机制层面的克制逻辑，不编对位胜率；热门组合不等于最优组合。'),
    ])
    body += '<h3>本篇输入声明</h3>'
    body += table(['项', '内容'], [
        ('英雄', f"{ctx['hero']['cname']}（{ctx['hero']['title']}）"),
        ('分路', f"本篇按 {ctx['lane']} 写" +
                (f"；官方标注分路：{'、'.join(ctx['off_lanes'])}" if ctx['off_lanes'] else '')),
        ('资料快照日期', SNAPSHOT_DATE),
        ('未查到 / 未落地的数据', '；'.join(ctx['missing']) if ctx['missing'] else '无'),
    ])
    return sec(0, '范本说明',
                '声明本篇结构、信息标注规范与写作纪律，并列明本次输入与资料缺口',
                body)


def sec1(ctx):
    h = ctx['hero']
    a = ctx['an']
    feats = []
    if a['passive_core']:
        feats.append(clean(a['passive_core']))
    core = a['core_skill']
    core_name = core['name'] if core else '—'
    strong = h.get('phases', '')
    rows = [
        ('定位', f"{h.get('type_name','—')} · {ctx['lane']} · 官方分路标注：{'、'.join(ctx['off_lanes']) or '—'}"),
        ('一句话赢法', ctx['win_line']),
        ('核心机制', ctx['core_mech']),
        ('强势期', ctx['strong_phase']),
        ('适合谁', ctx['fit_who']),
        ('不适合谁', ctx['unfit_who']),
        ('练成标准', ctx['train_std']),
        ('当前结论', ctx['conclusion']),
    ]
    body = table(['项', '说明'], rows, 'oneliner')
    body += callout('a', '本篇核心技能锚点',
                    f"{tag('A')} 核心技能：<b>{esc(core_name)}</b>；"
                    f"被动机制：{esc(clean(a['passive_core']) or '—')}。"
                    '下文所有连招与打法都围绕这一条展开。')
    if strong:
        body += callout('b', '强势期原文依据',
                        f"{tag('A')} 阶段打法：{esc(strong)}")
    return sec(1, '一页纸速览',
                '一屏内判断这英雄能不能上、怎么赢、什么时候最强、值不值得练',
                body)


def sec2(ctx):
    h = ctx['hero']
    a = ctx['an']
    body = ''
    body += '<h3>官方数据带（快照）</h3>'
    body += table(['项', '值', '来源与日期'], [
        ('英雄名称', h['cname'], f'官方英雄数据库 herolist.json · 快照 {SNAPSHOT_DATE}'),
        ('英雄ID（ename）', str(h.get('eid', '—')), f'官方英雄数据库 · 快照 {SNAPSHOT_DATE}'),
        ('称号', h.get('title', '—'), f'官方英雄数据库 · 快照 {SNAPSHOT_DATE}'),
        ('官方定位（hero_type）', str(ctx.get('hero_type', '—')), f'官方英雄数据库 · 快照 {SNAPSHOT_DATE}'),
        ('官方分路（roles）', '、'.join(ctx['off_lanes']), f'官方英雄数据库 · 快照 {SNAPSHOT_DATE}'),
        ('技能条目数', str(a['skill_count']), f'官方技能描述 · 快照 {SNAPSHOT_DATE}'),
    ])
    body += callout('a', '口径说明',
                    f"{tag('A')} 本篇所有官方字段取自同一份官方英雄数据快照（{SNAPSHOT_DATE}），"
                    '因此内部自洽。官方站点的部分明细接口本次不可访问，'
                    '技能数值、装备属性、胜率与梯度等需要实时查询的字段未取到，'
                    '正文中不出现这些数值，以局内说明为准。')
    body += '<h3>口径打架时的并列呈现</h3>'
    body += table(['口径', '说法 A', '说法 B', '本篇处理'], [
        ('版本号', '官方站新闻与客户端显示可能存在推送时差',
         '第三方攻略站常直接沿用上一版本号',
         '本篇不引用版本号做结论，只用「快照日期 + 机制描述」'),
        ('分路归属', '官方 roles 字段可能一名多路',
         '攻略站会按版本强势度推荐「最适合上分的一路」',
         f"本篇按 {ctx['lane']} 写，并在开篇注明官方分路标注"),
    ])
    body += '<h3>体验服 / 未落地调整</h3>'
    body += callout('c', '体验服区块（未落地，不进正文）',
                    f"{tag('C')} 本次未取到可核实的体验服公告原文，"
                    '故此区块不写任何具体改动。'
                    '若后续官方发布体验服调整，需单独记录来源与日期，'
                    '且正文打法仍按正式服执行。')
    return sec(2, '版本状态与数据口径',
                '明确数据时间、来源与冲突口径的处理方式，避免把旧数据当结论',
                body)


def sec3(ctx):
    h = ctx['hero']
    a = ctx['an']
    body = ''
    body += '<h3>被动怎么叠 / 怎么控</h3>'
    if a['passive_clauses']:
        rows = []
        for c in a['passive_clauses'][:6]:
            tagk = 'A'
            if any(k in c for k in ('免控', '霸体', '免疫')):
                tagk = 'A'
            rows.append([tag(tagk), esc(c)])
        body += table(['标注', '官方被动描述'], rows)
    else:
        body += callout('a', '被动说明缺失', f"{tag('A')} 本英雄官方数据未附被动描述文本，待核 · 以局内说明为准。")

    body += '<h3>各技能机制锚点</h3>'
    rows = []
    for x in a['skills']:
        mech = ''
        for group in (x['ctrl'], x['res'], x['dmg'], x['rng']):
            if group:
                mech = clean(group[0])
                break
        if not mech and x['clauses']:
            mech = clean(x['clauses'][0])
        rows.append([
            tag('A'), esc(x['name']), esc(x['cd'] or '—'),
            esc(mech or '待核'),
            ('有' if x['has_ctrl'] else '无'),
            ('有' if x['has_res'] else '无'),
        ])
    body += table(['标注', '技能', 'CD（官方）', '机制要点', '含控制', '含资源'], rows)

    body += '<h3>机制红利（跨版本稳定的部分）</h3>'
    if a['bonus']:
        rows = [[tag('A'), esc(clean(c))] for c in a['bonus'][:5]]
        body += table(['标注', '机制红利'], rows)
    else:
        body += callout('a', '待核', f"{tag('A')} 未从官方描述中提取到明确的叠加型红利条款，待核 · 以局内说明为准。")

    body += '<h3>最容易浪费的点</h3>'
    if a['waste']:
        rows = [[tag('A'), esc(clean(c))] for c in a['waste'][:5]]
        body += table(['标注', '浪费点（官方机制原文）'], rows)
        body += callout('d', '主观判断',
                        f"{tag('D')} 上表列的是官方文本里的<b>限制条件</b>。"
                        f"{esc(ctx['hero']['cname'])} 的红利通常是可累积的，"
                        '在红利没叠到位就交火，等于把本该在下一轮兑现的收益提前打掉。')
    else:
        body += callout('a', '待核', f"{tag('A')} 未提取到明确限制条款，待核 · 以局内说明为准。")

    body += '<h3>输出方式与伤害构成</h3>'
    rows = []
    # 各维度取互不相同的原文句，避免重复
    atk_s = next((c for c in a['atk_mode'] if c not in a['res_mech']), '')
    res_s = next((c for c in a['res_mech'] if c not in a['atk_mode']), '')
    if not atk_s and a['atk_mode']:
        atk_s = a['atk_mode'][0]
    if not res_s and a['res_mech']:
        res_s = a['res_mech'][0]
    if atk_s:
        rows.append([tag('A'), '普攻相关机制', esc(clean(atk_s))])
    if a['dmg_types']:
        rows.append([tag('A'), '伤害类型', '、'.join(a['dmg_types'])])
    if res_s:
        rows.append([tag('A'), '资源/次数管理', esc(clean(res_s))])
    if a['has_hard_ctrl']:
        rows.append([tag('A'), '控制来源', '存在硬控技能，可作为先手与开团手段'])
    elif a['has_ctrl']:
        rows.append([tag('A'), '控制来源', '只有软控/状态干扰，先手能力依赖装备与召唤师技能'])
    if rows:
        body += table(['标注', '维度', '机制要点'], rows)
    else:
        body += callout('a', '待核', f"{tag('A')} 未提取到输出方式信息，待核 · 以局内说明为准。")
    return sec(3, '技能机制与被动',
                '讲透该英雄被动如何叠加、如何转化为控制与收益，并标出机制红利与最易浪费的点',
                body)


def sec4(ctx):
    h = ctx['hero']
    equips = h.get('equips') or []
    rows = []
    for i, e in enumerate(equips[:2]):
        rows.append([f'方案 {i+1}', ' → '.join(e)])
    if not rows:
        rows = [['默认', '待核 · 以局内说明为准']]
    body = '<h3>默认解</h3>'
    body += table(['方案', '出装顺序'], rows)
    body += table(['项', '内容'], [
        ('铭文', h.get('inscriptions', '待核 · 以局内说明为准')),
        ('召唤师技能', h.get('summoner', '待核 · 以局内说明为准')),
        ('技能加点', h.get('skill_order', '待核 · 以局内说明为准')),
    ])
    body += '<h3>按局势替换</h3>'
    rows = []
    for cond, act in REPLACE_RULES:
        rows.append([cond, act, '以局内说明与实际对局为准'])
    body += table(['局势信号', '替换动作', '备注'], rows)
    body += '<h3>后期换装链</h3>'
    body += table(['阶段', '动作', '说明'], [
        ('中期', '不卖防御位', '中期装备还没成型，卖鞋等于裸奔'),
        ('后期', '按需把急速鞋换成保命装', '急速鞋大后期可卖；抵抗之靴 / 影忍之足别卖'),
        ('复活甲 / 名刀', '轮换链：复活甲 → 名刀 → 复活甲',
         '按对手控制与爆发决定轮换顺序'),
    ])
    body += callout('d', '主观判断',
                    f"{tag('D')} 上表是基于该英雄定位的装备优先级排序，不是版本最优解；"
                    '不同分段与版本的最优出装会变化。')
    return sec(4, '出装铭文与召唤师技能',
                '给出一套可直接抄的默认解，并提供局势替换与后期换装的决策路径',
                body)


def sec5(ctx):
    lane = ctx['lane']
    cfg = LANE_OPENING[lane]
    body = f'<h3>{cfg["title"]}</h3>'
    body += table(['时间点', '动作', '原因'],
                  [[t, esc(a), esc(r)] for t, a, r in cfg['route']])
    body += '<h3>关键节点细则</h3>'
    rows = [[esc(k), esc(v)] for k, v in cfg['punish']]
    body += table(['节点', '要点'], rows)
    if lane == '打野':
        body += '<h3>现行中立资源时间轴</h3>'
        body += table(['时间', '事件', '意义'],
                      [[t, esc(e), esc(m)] for t, e, m in WILD_TIMELINE])
        body += callout('a', '避坑',
                        f"{tag('A')} 河道之灵（河蟹）已于 S36 全部移除；"
                        '不要出现「1 分钟抢河蟹」。旧时间轴「2 分钟暴君 / 8 分钟主宰」已作废。')
    else:
        body += '<h3>现行中立资源时间轴（对线期相关）</h3>'
        body += table(['时间', '事件', '意义'],
                      [[t, esc(e), esc(m)] for t, e, m in WILD_TIMELINE])
    return sec(5, '开局路线',
                cfg['title'],
                body)


def sec6(ctx):
    h = ctx['hero']
    combos = h.get('combos') or []
    if not combos:
        combos = ['待核 · 以局内说明为准']
    buckets = {}
    for c in combos:
        sc = classify_combo(c)
        buckets.setdefault(sc, []).append(combo_text(c))
    body = '<h3>按场景分类的连招</h3>'
    skill_list = ctx['an']['skills']
    for sc, items in buckets.items():
        body += f'<h4>{esc(sc)}</h4>'
        rows = []
        for c in items:
            steps = combo_steps(c, skill_list)
            if steps:
                key = ' → '.join(f'{n}（{clean(m)}）' if m else n for n, m in steps)
            else:
                key = ctx['combo_key'].get(sc, '顺序释放')
            rows.append([tag('A'), esc(c),
                         esc(ctx['combo_trigger'].get(sc, '按局面直接起手')),
                         esc(key),
                         esc(combo_risk(c))])
        body += table(['标注', '连招', '触发条件', '关键动作（该英雄技能机制）', '失败点'], rows)
    body += '<h3>三条铁律</h3>'
    body += table(['#', '铁律', '理由'], [
        ('1', '没有场景就不按键', '每条连招都必须对应一个明确的局面触发条件'),
        ('2', '连招是顺序链，不是按键清单',
         '每一段依赖前一段命中，中断后剩余技能不接上'),
        ('3', '关键技能只留一次机会',
         '关键技能交空后的一整轮，就是对方的免费反打窗口'),
    ])
    body += callout('d', '主观判断',
                    f"{tag('D')} 连招的「关键动作」一栏是按 {esc(h['cname'])} 的机制推演，"
                    '不是逐帧录像复刻，建议在自己的录像里对照修正。')
    if ctx.get('hero_tips'):
        body += '<h3>该英雄的官方实战要点</h3>'
        body += table(['标注', '要点'],
                      [[tag('A'), esc(t)] for t, _ in ctx['hero_tips']])
    return sec(6, '连招库',
                '把连招按使用场景归类，每条注明触发条件、关键动作与失败点',
                body)


def sec7(ctx):
    lane = ctx['lane']
    is_jungle = lane == '打野'
    body = '<h3>四拍闭环</h3>'
    if is_jungle:
        loop = [('刷野 / 对线', '把资源与等级转成经济优势'),
                ('读图', '看小地图，判断对方五人位置与状态'),
                ('出手', '在对方状态真空时抓落单'),
                ('转化', '把抓到的优势转成推塔或控资源'),
                ('回线回野区', '回到自己的资源循环，继续攒经济')]
    else:
        loop = [('对线 / 转线', '把兵线与等级转成线上优势'),
                ('读图', '看小地图，判断对方打野与辅助位置'),
                ('出手', '在对方技能真空期换血或支援'),
                ('转化', '把优势转成推塔、控龙或转线收益'),
                ('回线回野区', '回到兵线与视野节奏，继续攒经济')]
    body += table(['拍', '动作', '目的'], [[a, esc(b)] for a, b in loop])
    body += callout('d', '主观判断',
                    f"{tag('D')} 提前量：看到对方消失就要动，比对方出现在你脸上早 "
                    f'{20}~30 秒。这 20~30 秒就是你的绕后或转线窗口。')
    body += '<h3>五个时间点</h3>'
    pts = [
        ('0:30', '红隼刷新点', '第一个资源'),
        ('2:00', '空间之灵 + 先知主宰', '第一个能影响局势的中立点'),
        ('4 级', '第一个可抓人节点', '此时的技能组合决定第一次 gank 质量'),
        ('10:00', '双龙刷新', '中后期资源争夺点'),
        ('20:00', '风暴龙王刷新', '决胜点资源'),
    ]
    body += table(['时间点', '事件', '为什么重要'], [[t, esc(e), esc(w)] for t, e, w in pts])
    body += '<h3>五条自检</h3>'
    checks = [
        '我现在在哪一拍的哪一步？',
        '对方五个人分别在哪、状态如何？',
        ('我这轮资源（惩击 / 技能）还在不在？' if is_jungle else '我这波兵线优势在不在？'),
        '我出手的窗口是不是已经关闭了？',
        '打完这一波，我下一步去哪？',
    ]
    body += table(['#', '自检问题'], [[str(i + 1), c] for i, c in enumerate(checks)])
    return sec(7, '节奏与时间锚点',
                '用四拍闭环、提前量与固定时间点，把「什么时候该做什么」变成可执行的节奏表',
                body)


def sec8(ctx):
    lane = ctx['lane']
    is_jungle = lane == '打野'
    body = ''
    if is_jungle:
        body += '<h3>目标判断</h3>'
        body += table(['目标类型', '判断标准', '处理方式'], [
            ('落单射手', '位置靠前且无位移可用', '优先抓，抓到就是节奏'),
            ('残血法师', '血量低但有控制', '先逼控制再进，勿硬吃'),
            ('游走位辅助', '总在侧翼出现', '改为抓同路的 C 位'),
            ('满血战士', '状态全、无位移', '价值低，优先换资源'),
        ])
        body += '<h3>绕后四步</h3>'
        body += table(['步', '动作', '要点'], [
            ('1', '读图确认对方位置与状态', '目标不在视野就不要盲进'),
            ('2', '清视野 + 卡视野盲区', '把自己从对方小地图上抹掉'),
            ('3', '贴近到爆发距离', '距离太远等于给对方反应时间'),
            ('4', '进场命中并立刻转化', '打完立刻推塔或控资源，别恋战'),
        ])
        body += '<h3>三个翻车点</h3>'
        body += table(['#', '翻车点', '后果'], [
            ('1', '目标有视野，己方无视野', '被反蹲'),
            ('2', '技能全交空在位移上', '关键技能真空被反打'),
            ('3', '打完不走，站着回城', '被对方打野抓死'),
        ])
    else:
        body += '<h3>换血窗口</h3>'
        body += table(['窗口', '判断标准', '动作'], [
            ('对方技能交完', '关键控制与位移已用', '上前打一套伤害'),
            ('我方技能齐', '核心技能与强化都在', '主动压线换血'),
            ('对方回城', '兵线已进塔', '越塔强开或拆塔'),
        ])
        body += '<h3>线权归属</h3>'
        body += table(['状态', '含义', '可以做什么'], [
            ('线权在我', '兵线在我方塔前', '可以支援、可以越塔、可以抓单'),
            ('线权在对方', '兵线在对方塔前', '守塔、补刀、等人来'),
            ('线权在河道', '双方兵线相接', '视野优先，勿先手'),
        ])
        body += '<h3>支援与防 gank 站位</h3>'
        body += table(['场景', '站位', '原因'], [
            ('准备支援', '靠河道侧，先清视野', '支援路上不被打断'),
            ('对方打野露头', '退回塔前', '不出塔送被抓'),
            ('自己打野在抓人', '站河道草丛侧翼', '形成二面夹击'),
        ])
        body += '<h3>三个翻车点</h3>'
        body += table(['#', '翻车点', '后果'], [
            ('1', '无视野深压线', '被 gank 无支援'),
            ('2', '技能先手但没打中', '被反打且失去线权'),
            ('3', '支援路上被截', '两头空'),
        ])
    body += callout('d', '主观判断',
                    f"{tag('D')} 目标判断与翻车点是按 {esc(ctx['hero']['cname'])} 的机制归纳，"
                    '属于操作层面的判断，不是数据结论。')
    return sec(8, '抓人与绕后' if is_jungle else '换血与线权',
                '抓人与绕后' if is_jungle else '换血与线权',
                body)


def sec9(ctx):
    h = ctx['hero']
    body = '<h3>进场前 / 进场后</h3>'
    body += table(['阶段', '要做的事', '判断依据'], [
        ('进场前', '确认关键控制是否已交、目标是否成团',
         '对方控制未交时不要先手开团'),
        ('进场前', '站位选在对方C位与自己的距离之外',
         '进场角度决定能否一击命中'),
        ('进场后', '第一时间打出关键控制或伤害',
         '犹豫一秒就是被反打'),
        ('进场后', '目标明确，只打一个方向',
         '不要在团战里换目标'),
        ('打完怎么撤', '留好撤退技能，打完即走',
         '残血站在原地就是送'),
    ])
    body += '<h3>目标选择</h3>'
    body += table(['优先级', '目标', '原因'], [
        ('1', '敌方核心输出位', '打掉输出比打掉坦克收益高'),
        ('2', '开团者', '拆掉开团点能救队友'),
        ('3', '残血可收', '收掉能滚雪球'),
        ('4', '前排坦克', '除非团战有利，否则不优先'),
    ])
    body += '<h3>核心技能的第二种用法</h3>'
    body += callout('d', '主观判断',
                    f"{tag('D')} 除常规团战开团外，"
                    f"{esc(h['cname'])} 的核心技能还有「非正面使用」的价值——"
                    '用于拉扯、封路、分割阵型或保护队友撤离，具体用法以局内实况判断。')
    return sec(9, '团战',
                '把团战拆成进场前与进场后两段，明确目标选择、撤退方式与技能的非常规用法',
                body)


def sec10(ctx):
    body = ''
    for key in ['顺风', '均势', '逆风']:
        s = SITUATION[key]
        body += f'<h3>{key}</h3>'
        body += table(['目标', '动作', '别做'],
                      [[esc(s['target']),
                        '<br>'.join('· ' + esc(a) for a in s['actions']),
                        '<br>'.join('· ' + esc(a) for a in s['never'])]])
    body += callout('d', '主观判断',
                    f"{tag('D')} 三种局势的动作清单是按 {esc(ctx['hero']['cname'])} 的定位归纳，"
                    '属于思路建议，不是数据结论。')
    return sec(10, '三种局势',
                '按顺风 / 均势 / 逆风三种局面给出目标、动作与禁区，避免用同一套打法硬套',
                body)


def sec11(ctx):
    h = ctx['hero']
    counters = h.get('counters') or []
    countered = h.get('countered_by') or []
    body = '<h3>官方克制标注</h3>'
    if counters or countered:
        body += table(['方向', '官方标注英雄', '标注'], [
            ('该英雄克制的方向', '、'.join(counters) if counters else '无', tag('A')),
            ('克制该英雄的方向', '、'.join(countered) if countered else '无', tag('A')),
        ])
    else:
        body += callout('a', '待核', f"{tag('A')} 官方数据未提供该英雄的克制标注，待核 · 以局内说明为准。")
    body += '<h3>机制层面的共性</h3>'
    body += table(['方向', '机制共性（主观归纳）', '为什么'], [
        ('较难处理的方向', '、'.join(countered) if countered else '—',
         '这些英雄的机制能直接针对本篇核心机制的释放窗口'),
        ('较容易处理的方向', '、'.join(counters) if counters else '—',
         '本篇核心机制在这些对局里能形成先手'),
    ])
    body += callout('d', '重要声明',
                    f"{tag('D')} 以上克制关系为<b>主观归纳</b>，"
                    '是机制层面的共性描述，<b>不是对位胜率</b>。'
                    '本篇不提供任何对位胜率数字。')
    body += '<h3>适配阵容思路</h3>'
    lu = h.get('lineup') or {}
    rows = []
    if lu.get('teammates'):
        rows.append(['搭档思路', '、'.join(lu['teammates'])])
    if lu.get('synergy'):
        rows.append(['强势原因', lu['synergy']])
    if lu.get('composition'):
        rows.append(['体系思路', lu['composition']])
    if rows:
        body += table(['项', '内容'], rows)
    else:
        body += callout('a', '待核', f"{tag('A')} 官方数据未提供该英雄的阵容配合信息，待核 · 以局内说明为准。")
    body += callout('d', '说明',
                    f"{tag('D')} 热门组合不等于最优组合；"
                    '阵容思路应按当前段位与己方已有体系来选。')
    return sec(11, '适配阵容与克制',
                '给出机制层面的克制关系与组合思路，并明确区分主观归纳与官方标注',
                body)


def sec12(ctx):
    body = '<h3>常见失误表</h3>'
    rows = [
        ('1', '技能全交在无价值目标上', '关键技能进入长 CD，被对方直接反打'),
        ('2', '进场前没确认对方控制是否已交', '被反控，开团变送'),
        ('3', '打完不撤，留在原地', '残血被收，经济与节奏双输'),
        ('4', '资源不用完就换目标', '机制红利没叠满就交火'),
        ('5', '视野盲区盲目经过', '被埋伏'),
        ('6', '支援时不看地图', '两头空，两边都亏'),
        ('7', '顺风乱接团', '把大优势打没'),
        ('8', '逆风单带孤兵', '给对手抓单机会'),
    ]
    body += table(['#', '失误', '后果'], [[a, esc(b), esc(c)] for a, b, c in rows])
    body += '<h3>接下来 20 局只练一个动作</h3>'
    body += table(['训练项', '做法'],
                  [[esc(a), esc(b)] for a, b in TRAIN_DRILLS])
    body += callout('d', '训练法说明',
                    f"{tag('D')} 训练顺序与优先级属于主观判断，"
                    f'针对 {esc(ctx["hero"]["cname"])} 的机制特点设计。')
    return sec(12, '常见失误与训练法',
                '把高频失误列成可对照的表，并给出一个 20 局只做一件事的最小训练单元',
                body)


def sec13(ctx):
    body = '<h3>数据来源分级</h3>'
    body += table(['级别', '含义', '使用规则'],
                  [[f'<span class="mk mk-{k}">{k} · {v}</span>', esc(v), esc(w)]
                   for k, v, w in SOURCE_LEVELS])
    body += '<h3>数据出处</h3>'
    body += table(['数据项', '来源', '日期 / 口径'], [
        ('英雄名称、ID、称号、官方定位、官方分路',
         '官方英雄数据库 herolist.json', f'快照 {SNAPSHOT_DATE}'),
        ('技能名称、CD、官方技能描述',
         '官方英雄技能数据', f'快照 {SNAPSHOT_DATE}'),
        ('出装、铭文、召唤师技能、加点、连招、阶段打法、对位标注、官方攻略',
         '官方英雄攻略文本数据', f'快照 {SNAPSHOT_DATE}'),
        ('克制标注', '官方英雄数据中的对位字段', f'快照 {SNAPSHOT_DATE}'),
        ('上手难度、克制归纳、优先级、训练法顺序',
         '作者主观判断', '本篇写作时点'),
        ('胜率、梯度、出场率、禁用率、版本统计',
         '<b>未取到</b>（本篇不引用）', '—'),
        ('体验服调整', '<b>未取到可核实原文</b>（本篇不引用）', '—'),
    ])
    body += '<h3>过时信息避坑清单</h3>'
    body += table(['项', '避坑说明'],
                  [[esc(a), esc(b)] for a, b in FROZEN_INFO])
    body += '<h3>配套索引</h3>'
    body += table(['内容', '位置'], [
        ('一键速览', '第 1 节'),
        ('技能机制与被动细节', '第 3 节'),
        ('连招与失败点', '第 6 节'),
        ('时间锚点与自检', '第 7 节'),
        ('局势应对', '第 10 节'),
        ('失误对照', '第 12 节'),
    ])
    body += '<h3>仍存疑的点</h3>'
    body += table(['#', '存疑点', '状态'], [
        ('1', '技能数值、装备属性（会随版本变动）', '待核 · 以局内说明为准'),
        ('2', '当前版本胜率、梯度、出场率、禁用率', '待核 · 未取到可靠来源，本篇不引用'),
        ('3', '体验服 / 未落地调整', '待核 · 未取到可核实原文'),
        ('4', '打野刀灼烧的具体公式与每跳数值', '待核 · 以训练营实测 + 局内说明为准'),
        ('5', '本文对位克制关系的量化强度', '待核 · 属主观归纳，非对位胜率'),
    ])
    return sec(13, '附录',
                '给出数据来源分级、出处、避坑清单与仍存疑的点，便于后续核对与更新',
                body)


# ============================ 模板 ============================

CSS = """
:root{
  --bg:#f6f5f1; --panel:#ffffff; --ink:#1c2027; --ink2:#4a5058; --ink3:#6f7680;
  --line:#e2ded4; --line2:#cfc9bb; --gold:#8a6d1a; --gold2:#b48a20;
  --blue:#2b6cb0; --green:#1e8449; --red:#b03a2e; --purple:#6b3fa0;
  --soft:#faf8f3; --soft2:#f1ede3;
}
*{box-sizing:border-box}
body{
  margin:0;background:var(--bg);color:var(--ink);
  font:15px/1.75 -apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;
}
.wrap{max-width:1080px;margin:0 auto;padding:0 20px 80px}
header.top{
  background:var(--panel);border-bottom:2px solid var(--gold2);
  padding:26px 20px 20px;margin-bottom:22px;
}
header.top .inner{max-width:1080px;margin:0 auto}
h1{margin:0 0 6px;font-size:27px;letter-spacing:.5px}
.sub{color:var(--ink3);font-size:13.5px;margin-bottom:12px}
.hmeta{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.badge{
  font-size:12px;padding:2px 9px;border:1px solid var(--line2);border-radius:3px;
  background:var(--soft);color:var(--ink2);
}
.badge.k{background:#fdf6e0;border-color:var(--gold2);color:var(--gold)}
nav.anchors{
  position:sticky;top:0;z-index:50;background:var(--panel);
  border-bottom:1px solid var(--line);margin-bottom:22px;
}
nav.anchors .inner{
  max-width:1080px;margin:0 auto;padding:8px 20px;
  display:flex;gap:4px;flex-wrap:wrap;
}
nav.anchors a{
  font-size:12.5px;color:var(--ink2);text-decoration:none;
  padding:3px 8px;border:1px solid transparent;border-radius:3px;
}
nav.anchors a:hover{background:var(--soft2);border-color:var(--line2);color:var(--ink)}
nav.anchors a.act{background:#fdf6e0;border-color:var(--gold2);color:var(--gold);font-weight:700}
.sec{
  background:var(--panel);border:1px solid var(--line);border-radius:6px;
  padding:20px 22px;margin-bottom:18px;
}
.sec>h2{
  margin:0 0 12px;font-size:19px;padding-bottom:9px;
  border-bottom:2px solid var(--gold2);display:flex;align-items:baseline;gap:10px;
}
.sn{
  display:inline-block;background:var(--gold);color:#fff;font-size:13px;
  width:24px;height:24px;border-radius:3px;text-align:center;line-height:24px;
  font-weight:700;flex-shrink:0;
}
.purpose{
  background:var(--soft);border-left:3px solid var(--gold2);
  padding:8px 12px;font-size:13px;color:var(--ink2);margin-bottom:14px;
}
.purpose b{color:var(--gold)}
h3{font-size:15.5px;margin:18px 0 8px;color:var(--ink)}
h3:first-of-type{margin-top:6px}
h4{font-size:14px;margin:14px 0 6px;color:var(--ink2)}
.tw{overflow-x:auto;margin-bottom:12px}
table.tbl{
  width:100%;border-collapse:collapse;font-size:13.5px;
  background:var(--panel);
}
table.tbl th{
  background:var(--soft2);color:var(--ink);font-weight:700;text-align:left;
  padding:8px 10px;border:1px solid var(--line2);white-space:nowrap;
}
table.tbl td{
  padding:8px 10px;border:1px solid var(--line);vertical-align:top;line-height:1.65;
}
table.tbl tbody tr:nth-child(even){background:var(--soft)}
table.tbl.skel td:first-child,table.tbl.skel td:nth-child(2){white-space:nowrap}
table.tbl.oneliner td:first-child{
  width:96px;font-weight:700;background:var(--soft2);white-space:nowrap;
}
.co{
  border:1px solid var(--line2);border-left-width:4px;border-radius:4px;
  padding:10px 13px;margin:10px 0;background:var(--soft);
}
.co-t{font-weight:700;font-size:13.5px;margin-bottom:4px}
.co-b{font-size:13.5px;color:var(--ink2);line-height:1.7}
.co-a{border-left-color:var(--blue)}
.co-b{border-left-color:var(--green)}
.co-c{border-left-color:var(--purple);background:#f7f2fb}
.co-d{border-left-color:var(--gold2)}
.mk{
  display:inline-block;font-size:11px;padding:1px 7px;border-radius:3px;
  border:1px solid var(--line2);background:var(--soft2);color:var(--ink2);
  white-space:nowrap;font-weight:700;
}
.mk-A{border-color:#9fc4e4;background:#eaf3fb;color:#1d5b96}
.mk-B{border-color:#a9d8bd;background:#eaf7f0;color:#1a7040}
.mk-C{border-color:#cdb0e0;background:#f5ecfa;color:#6b3fa0}
.mk-D{border-color:#e2c67e;background:#fdf6e0;color:#8a6d1a}
.foot{
  color:var(--ink3);font-size:12.5px;text-align:center;
  padding:22px 20px;border-top:1px solid var(--line);margin-top:26px;
}
@media print{
  body{background:#fff;font-size:11.5pt}
  .wrap{max-width:none;padding:0}
  nav.anchors{display:none}
  header.top{border-bottom-width:1px}
  .sec{break-inside:avoid;page-break-inside:avoid;border-color:#bbb;margin-bottom:10px}
  table.tbl{font-size:10pt}
  table.tbl th{background:#eee !important}
  table.tbl tbody tr:nth-child(even){background:#fff}
  a{text-decoration:none;color:inherit}
}
"""

JS = """
(function(){
  var links=[].slice.call(document.querySelectorAll('nav.anchors a'));
  var secs=[].slice.call(document.querySelectorAll('section.sec'));
  function onScroll(){
    var y=window.scrollY+140,cur=secs[0];
    for(var i=0;i<secs.length;i++){if(secs[i].offsetTop<=y)cur=secs[i];}
    links.forEach(function(a){
      a.classList.toggle('act',a.getAttribute('href')==='#'+cur.id);
    });
  }
  window.addEventListener('scroll',onScroll,{passive:true});
  onScroll();
  var btn=document.getElementById('printBtn');
  if(btn)btn.onclick=function(){window.print();};
})();
"""


def build_html(ctx):
    h = ctx['hero']
    a = ctx['an']
    secs = [sec0(ctx), sec1(ctx), sec2(ctx), sec3(ctx), sec4(ctx), sec5(ctx),
            sec6(ctx), sec7(ctx), sec8(ctx), sec9(ctx), sec10(ctx), sec11(ctx),
            sec12(ctx), sec13(ctx)]
    nav = ''.join(
        f'<a href="#s{i}">{i} {t}</a>' for i, t in [
            (0, '范本说明'), (1, '速览'), (2, '版本与口径'), (3, '技能机制'),
            (4, '出装铭文'), (5, '开局路线'), (6, '连招库'), (7, '节奏锚点'),
            (8, '抓人与绕后' if ctx['lane'] == '打野' else '换血与线权'),
            (9, '团战'), (10, '三种局势'), (11, '阵容与克制'),
            (12, '失误与训练'), (13, '附录')])
    lanes_note = f"本篇按 {ctx['lane']} 写"
    off = '、'.join(ctx['off_lanes'])
    meta = (f'<span class="badge k">{esc(lanes_note)}</span>'
            f'<span class="badge">官方分路：{esc(off)}</span>'
            f'<span class="badge">定位：{esc(h.get("type_name", "—"))}</span>'
            f'<span class="badge">资料快照：{SNAPSHOT_DATE}</span>'
            f'<span class="badge">当前赛季：{CURRENT_SEASON}</span>'
            f'<button id="printBtn" class="badge" style="cursor:pointer">🖨 打印 / 导出 PDF</button>')
    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(h['cname'])} · {esc(ctx['lane'])} · 王者荣耀单英雄完整攻略</title>
<style>{CSS}</style>
</head>
<body>
<header class="top"><div class="inner">
<h1>{esc(h['cname'])} · {esc(ctx['lane'])}完整攻略</h1>
<div class="sub">{esc(h.get('title',''))} ｜ {lanes_note} ｜ 官方定位 {esc(h.get('type_name','—'))}</div>
<div class="hmeta">{meta}</div>
</div></header>
<nav class="anchors"><div class="inner">{nav}</div></nav>
<div class="wrap">
{''.join(secs)}
</div>
<div class="foot">
{esc(h['cname'])} · {esc(ctx['lane'])}完整攻略 ｜ 资料快照 {SNAPSHOT_DATE} ｜ 品质 {esc(CURRENT_SEASON)}<br>
本篇含官方数据快照与作者主观判断两类信息，已按 A/B/C/D 分级标注。
胜率、梯度等时效数据未取到，本篇不引用；数值以局内说明为准。
</div>
<script>{JS}</script>
</body>
</html>'''
