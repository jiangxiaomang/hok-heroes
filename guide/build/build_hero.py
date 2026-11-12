# -*- coding: utf-8 -*-
"""
单英雄攻略构建入口。

用法:
  python3 build_hero.py 廉颇 对抗路
  python3 build_hero.py 全部

产物: {英雄名}_{分路}完整攻略.html
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from analyzer import analyze, ROLE_MAP, LANES
from template import (build_html, esc, clean, SNAPSHOT_DATE, CURRENT_SEASON,
                      LANE_OPENING)

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, '..', 'data')
OUT = os.path.join(HERE, '..', '..', '攻略输出')
os.makedirs(OUT, exist_ok=True)

HEROES = json.load(open(os.path.join(DATA, 'heroes_official.json'), encoding='utf-8'))
OFFICIAL = {h['cname']: h for h in
            json.load(open(os.path.join(DATA, 'official_herolist.json'), encoding='utf-8'))}

BY_NAME = {h['cname']: h for h in HEROES}


def official_lanes(h):
    o = OFFICIAL.get(h['cname'])
    if not o:
        return [h.get('primary_lane') or '中路']
    ls = [ROLE_MAP[r] for r in o.get('roles', '').split('|') if r in ROLE_MAP]
    return ls or [h.get('primary_lane') or '中路']


def pick_lane(h, override=None):
    if override:
        return override
    ol = official_lanes(h)
    primary = h.get('primary_lane')
    if primary in ol:
        return primary
    # 官方主分路与现有数据不一致时，取官方列表里最靠前的
    return ol[0]


# ---------------- 英雄专属叙述字段（全部从该英雄自身数据推导） ----------------

def build_ctx(h, lane):
    an = analyze(h)
    off_lanes = official_lanes(h)
    off = OFFICIAL.get(h['cname'], {})
    t = h.get('type_name', '—')
    playstyle = h.get('playstyle', '')
    phases = h.get('phases', '')
    tips = h.get('pro_tips') or []
    diff = None

    core = an['core_skill']
    core_name = core['name'] if core else '—'
    passive_core = clean(an['passive_core'])
    res = an['res_words']
    res_txt = ('、'.join(res) + ' 的获取/消耗节奏') if res else '无独立资源条，靠技能循环与冷却管理'

    # 一句话赢法：取该英雄自己的 playstyle 字段
    win_line = playstyle or f'围绕「{core_name}」建立优势'

    # 核心机制
    core_mech = f'核心技能「{core_name}」' + (f'：{passive_core}' if passive_core else '')
    if an['has_hard_ctrl']:
        core_mech += '；含硬控，是先手与开团的主要来源'
    elif an['has_ctrl']:
        core_mech += '；含软控与状态干扰'
    core_mech += f'。资源管理上以 {res_txt}为主'
    if an['atk_mode']:
        core_mech += f'。输出上有普攻耦合：{clean(an["atk_mode"][0])}'

    # 强势期：取该英雄 phases 的中后段
    sp = phases
    if sp:
        parts = [p.strip() for p in sp.replace('；', '；').split('；') if p.strip()]
        mid = [p for p in parts if p.startswith('中期')]
        late = [p for p in parts if p.startswith('后期')]
        strong_phase = '；'.join((mid + late)[:2]) or sp
    else:
        strong_phase = '待核 · 以局内说明为准'

    fit = []
    if lane == '打野':
        fit.append('愿意在开局 2 分钟内做完全部决策的打野位玩家')
    else:
        fit.append(f'愿意长期稳定打{ lane }位、能接受前期弱势的英雄玩家')
    if an['has_hard_ctrl']:
        fit.append('喜欢自己开节奏、拿团战先手权的人')
    if an['has_res']:
        fit.append('能盯住资源条做计划的人')
    unfit = []
    if lane == '打野':
        unfit.append('只愿意farm、不愿意做地图动作的打野')
    else:
        unfit.append(f'希望{ lane }位能快速滚雪球打穿对手的玩家')
    if an['has_hard_ctrl']:
        unfit.append('依赖队友先手、自己不敢开团的玩家')
    unfit.append('无法接受技能空窗期的人')

    train_std = '能在无干扰训练营里稳定完成：'
    if res:
        train_std += f'独立管理「{res[0]}」并把{ res_txt}转化为一次有效出手；'
    else:
        train_std += '在 10 秒内打出一次完整技能循环且不空大；'
    if an['has_hard_ctrl']:
        train_std += '能在目标位移中命中控制；'
    else:
        train_std += '能稳定命中关键技能；'
    train_std += '能在对方回城/技能交空的窗口完成一次完整收益转化。'

    conclusion = (f'{h["cname"]} 在{ lane }位的收益来自「{core_name}」的机制本身，'
                  f'数值会随版本变动，但机制红利稳定。'
                  f'当前快照（{SNAPSHOT_DATE}）下未取到该英雄的胜率与梯度数据，'
                  '因此不给结论性的强度排名，只给机制结论：'
                  f'{"上限取决于能否稳定先手命中" if an["has_hard_ctrl"] else "上限取决于能否稳定命中并续上后续收益"}。')

    # 连招场景的触发条件 / 关键动作
    scene_trigger = {
        '团战开团': '对方站位成团且关键控制尚未交出',
        '追击收割': '目标残血且有位移或闪现可交',
        '对线消耗': '对方核心技能进入冷却',
        '清线拆塔': '需要快速清线推进或拆塔',
        '逃生保命': '血量进入危险线或被多人包围',
        '常规起手': '常规起手时机成立',
    }
    scene_key = {
        '团战开团': f'以「{core_name}」起手，命中后再接后续伤害',
        '追击收割': '先贴近再补伤害，位移留到确认要追上时',
        '对线消耗': '在对方技能真空期打满一套伤害',
        '清线拆塔': '优先打非英雄单位，避免把技能浪费在兵线上',
        '逃生保命': '先拉开距离再交位移',
        '常规起手': '顺序释放，前段命中后段才接',
    }

    # 该英雄自己的机制要点（供正文引用，均来自官方描述）
    hero_tips = [(clean(t), 'A') for t in (tips or [])]

    missing = []
    if not an['passive_core']:
        missing.append('官方被动描述未取到')
    if not h.get('combos'):
        missing.append('官方连招文本未取到')
    if not h.get('equips'):
        missing.append('官方出装未取到')
    if not h.get('counters') and not h.get('countered_by'):
        missing.append('官方克制标注未取到')
    missing.append('胜率 / 梯度 / 出场率等时效数据未取到（本篇不引用）')
    missing.append('技能数值与装备属性未取到（以局内说明为准）')

    return {
        'hero': h,
        'an': an,
        'lane': lane,
        'off_lanes': off_lanes,
        'hero_type': off.get('hero_type', '—'),
        'missing': missing,
        'win_line': win_line,
        'core_mech': core_mech,
        'strong_phase': strong_phase,
        'fit_who': '；'.join(fit),
        'unfit_who': '；'.join(unfit),
        'train_std': train_std,
        'conclusion': conclusion,
        'combo_trigger': scene_trigger,
        'combo_key': scene_key,
        'hero_tips': hero_tips,
    }


def build_one(name, lane_override=None):
    h = BY_NAME.get(name)
    if not h:
        raise SystemExit(f'未找到英雄：{name}')
    lane = pick_lane(h, lane_override)
    ctx = build_ctx(h, lane)
    html = build_html(ctx)
    fn = os.path.join(OUT, f'{h["cname"]}_{lane}完整攻略.html')
    with open(fn, 'w', encoding='utf-8') as f:
        f.write(html)
    return fn, ctx


if __name__ == '__main__':
    args = sys.argv[1:]
    if not args:
        print('用法: python3 build_hero.py 廉颇 [对抗路] | 全部')
        raise SystemExit(1)
    if args[0] == '全部':
        for h in HEROES:
            lane = pick_lane(h)
            fn, ctx = build_one(h['cname'], lane)
            print('OK', os.path.basename(fn))
    else:
        name = args[0]
        lane = args[1] if len(args) > 1 else None
        fn, ctx = build_one(name, lane)
        print('OK', os.path.basename(fn), len(open(fn, encoding='utf-8').read()), 'bytes')
