# -*- coding: utf-8 -*-
"""
英雄速查卡片构建器。

产物（输出到 guide/cards/）:
  index.html                      133 张卡片索引（搜索 / 筛选 / 下载）
  {英雄}_{分路}速查卡.html        单张独立卡片（A4 一页，可打印）
  cards_all.html                  全部 133 张合并为一个文件（便于分享）
  cards.md                        全部 133 张 Markdown 版（便于手机 / 笔记软件）
  {英雄}_{分路}速查卡.md          单张 Markdown

用法:
  python3 build_cards.py 全部
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from analyzer import strip_numbers, ROLE_MAP
from playbook import (skill_profiles, build_combos, lane_playbook,
                      feature_tags, _mech)

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, '..', 'data')
OUT = os.path.join(HERE, '..', 'cards')
os.makedirs(OUT, exist_ok=True)

HEROES = json.load(open(os.path.join(DATA, 'heroes_official.json'), encoding='utf-8'))
OFFICIAL = {h['cname']: h for h in
            json.load(open(os.path.join(DATA, 'official_herolist.json'), encoding='utf-8'))}
LANES = ['打野', '对抗路', '中路', '发育路', '游走']


def official_lanes(h):
    o = OFFICIAL.get(h['cname'], {})
    ls = [ROLE_MAP[r] for r in o.get('roles', '').split('|') if r in ROLE_MAP]
    return ls or [h.get('primary_lane') or '中路']


def pick_lane(h):
    ol = official_lanes(h)
    primary = h.get('primary_lane')
    if primary in ol:
        return primary
    return ol[0]


def esc(s):
    return (str(s).replace('&', '&amp;').replace('<', '&lt;')
            .replace('>', '&gt;').replace('"', '&quot;'))


def first_sentence(text, limit=60):
    """取第一句（可含逗号），用于浓缩长段落。"""
    if not text:
        return ''
    t = re.sub(r'\s+', '', str(text))
    t = re.sub(r'^Tips[:：]?', '', t)
    for sep in ('。', '；', ';'):
        if sep in t:
            t = t.split(sep)[0]
            break
    return t[:limit]


def split_runes(text):
    """'异变×10、鹰眼×10、隐匿×10' -> ['异变','鹰眼','隐匿']"""
    if not text:
        return []
    parts = re.split(r'[、,，/]', str(text))
    out = []
    for p in parts:
        p = re.sub(r'×\s*\d+', '', p).strip()
        if p and p not in out:
            out.append(p)
    return out


def build_card(h, lane):
    """生成一张卡片的结构化内容。"""
    an_profs = skill_profiles(h)
    combos = build_combos(h, an_profs, lane)
    pb = lane_playbook(h, an_profs, lane, h.get('type_name', ''))
    off = OFFICIAL.get(h['cname'], {})

    # --- 连招：实战场景连招优先，官方原文补充 ---
    scene_combos = []
    official_combos = []
    for c in combos:
        raw = c.get('raw') or ''
        if c.get('scene') == '官方给定连招' or not c.get('steps'):
            # 官方原文连招：单独收集，标注官方口径
            if raw:
                note = ''
                m = re.search(r'[（(]([^）)]*)[）)]\s*$', raw)
                if m:
                    note = m.group(1)
                    raw = raw[:m.start()].strip()
                official_combos.append({'raw': raw, 'note': note,
                                        'purpose': c.get('purpose', '')})
            continue
        keys = ' → '.join(f'{n}技能' for n, _nm, _m in c.get('steps', []))
        scene_combos.append({
            'scene': c.get('scene', ''),
            'keys': keys,
            'purpose': c.get('purpose', ''),
            'tip': c.get('tip', '') or c.get('fail', ''),
        })

    # 兜底：数据里若直接给了 combos 字段，也补进官方区（按归一化文本去重）
    def _norm(s):
        return re.sub(r'[（(][^）)]*[）)]', '', str(s)).replace(' ', '').strip()

    seen = {_norm(o['raw']) for o in official_combos}
    for c in (h.get('combos') or [])[:3]:
        if isinstance(c, dict):
            s = c.get('seq') or c.get('name') or ''
        else:
            s = str(c)
        s = s.strip()
        if not s:
            continue
        note = ''
        m = re.search(r'[（(]([^）)]*)[）)]\s*$', s)
        if m:
            note = m.group(1)
            s = s[:m.start()].strip()
        if _norm(s) in seen:
            continue
        seen.add(_norm(s))
        official_combos.append({'raw': s, 'note': note, 'purpose': ''})

    # --- 技能速览 ---
    skills = []
    for p in an_profs:
        skills.append({
            'i': p['i'],
            'name': p['name'],
            'cd': p['cd'] or '—',
            'mech': _mech(p, 70) or _mech(p) or '—',
            'tags': feature_tags(p),
        })

    # --- 分路打法要点：从 playbook 各 section 抽首列要点 ---
    lane_points = []
    for sec in pb.get('sections', []):
        title = sec[0]
        header = sec[1]
        rows = sec[2]
        picked = []
        for r in rows[:3]:
            cells = [re.sub(r'<[^>]+>', '', str(x)) for x in r]
            picked.append(cells)
        lane_points.append({'title': title, 'header': header, 'rows': picked})

    # --- 精华技巧 ---
    tips = []
    for t in (h.get('pro_tips') or [])[:4]:
        tips.append({'text': t, 'src': '实战要点'})
    ot = first_sentence(h.get('official_tips', ''), 70)
    if ot:
        tips.append({'text': ot, 'src': '官方 Tips'})
    ps = first_sentence(h.get('playstyle', ''), 50)
    if ps:
        tips.append({'text': ps, 'src': '玩法定位'})

    # --- 出装 / 铭文 / 召唤师 ---
    equips = (h.get('equips') or [[]])[0] if h.get('equips') else []
    runes = split_runes(h.get('inscriptions', ''))

    # --- 克制 ---
    counters = h.get('counters') or []
    countered_by = h.get('countered_by') or []

    # --- 分阶段打法 ---
    phases = []
    for seg in re.split(r'[；;]', h.get('phases', '') or ''):
        seg = seg.strip()
        if seg:
            phases.append(seg)

    return {
        'cname': h['cname'],
        'title': h.get('title', ''),
        'lane': lane,
        'type': h.get('type_name', '—'),
        'hero_type': off.get('hero_type', '—'),
        'diff': off.get('difficulty_name', ''),
        'off_lanes': official_lanes(h),
        'win_line': h.get('playstyle', ''),
        'scene_combos': scene_combos,
        'official_combos': official_combos,
        'skills': skills,
        'tips': tips,
        'lane_points': lane_points,
        'equips': equips,
        'runes': runes,
        'summoner': h.get('summoner', ''),
        'skill_order': h.get('skill_order', ''),
        'counters': counters,
        'countered_by': countered_by,
        'phases': phases,
        'lineup': h.get('lineup') or {},
    }


# ---------------------------------------------------------------- HTML 渲染

CARD_CSS = """
:root{
  --bg:#f6f4ef; --card:#ffffff; --ink:#23201c; --ink2:#5b554d;
  --line:#e3ddd2; --accent:#b4442e; --accent2:#2f6f6a; --soft:#f2ece1;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font:14px/1.65 -apple-system,"PingFang SC","Microsoft YaHei",sans-serif}
.page{max-width:860px;margin:0 auto;padding:22px 20px 40px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;
  padding:20px 22px;box-shadow:0 1px 0 rgba(0,0,0,.03)}
.chead{display:flex;align-items:flex-end;gap:12px;flex-wrap:wrap;
  border-bottom:2px solid var(--ink);padding-bottom:10px;margin-bottom:14px}
.ctitle{font-size:26px;font-weight:800;letter-spacing:.5px}
.ctitle small{font-size:13px;font-weight:600;color:var(--ink2);margin-left:6px}
.cmeta{margin-left:auto;display:flex;gap:6px;flex-wrap:wrap}
.chip{font-size:11px;padding:3px 9px;border-radius:999px;background:var(--soft);
  color:var(--ink2);border:1px solid var(--line);white-space:nowrap}
.chip.lane{background:var(--accent);color:#fff;border-color:var(--accent)}
.chip.a{background:#efe7db;color:#7a4a20}
.sec{margin:0 0 14px}
.sec>h3{font-size:14px;font-weight:800;margin:0 0 7px;padding-left:9px;
  border-left:4px solid var(--accent);line-height:1.4}
.sec>h3 .n{color:var(--accent2);font-size:11px;margin-left:8px;font-weight:700}
table{width:100%;border-collapse:collapse;font-size:12.5px}
th,td{border:1px solid var(--line);padding:5px 7px;text-align:left;vertical-align:top}
th{background:var(--soft);font-weight:700;font-size:11.5px;color:var(--ink2)}
.combo{margin:0 0 7px;border:1px solid var(--line);border-left:4px solid var(--accent2);
  border-radius:8px;padding:7px 10px;background:#fbfaf7}
.combo b{font-size:12.5px}
.combo .k{font-family:ui-monospace,Menlo,monospace;font-weight:800;color:var(--accent);
  font-size:13px;margin:2px 0}
.combo .d{color:var(--ink2);font-size:12px}
.onote{color:var(--accent2);font-size:11.5px;font-weight:700}
.tips li{margin:0 0 4px;font-size:12.5px}
.tips .s{font-size:10.5px;color:var(--ink2);background:var(--soft);
  border-radius:4px;padding:1px 5px;margin-right:5px}
.chips{display:flex;flex-wrap:wrap;gap:5px}
.rune{font-size:12px;padding:3px 10px;border-radius:6px;background:var(--soft);
  border:1px solid var(--line)}
.equip{font-size:12px;padding:3px 10px;border-radius:6px;background:#eef4f2;
  border:1px solid #d5e4e0;color:#25514d}
.gs{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:7px}
.gs>div{flex:1 1 46%;border:1px solid var(--line);border-radius:8px;padding:7px 9px;
  font-size:12px;background:#fcfbf9}
.gs .gn{font-weight:800;font-size:12.5px}
.gs .gm{color:var(--ink2);font-size:11.5px}
.gs .gt{font-size:10.5px;color:var(--accent2);margin-top:2px}
.kv{display:flex;flex-wrap:wrap;gap:6px 14px;font-size:12.5px}
.kv span{color:var(--ink2)}
.kv b{color:var(--ink)}
footer{margin-top:16px;padding-top:9px;border-top:1px dashed var(--line);
  font-size:11px;color:var(--ink2)}
@media print{
  body{background:#fff}
  .page{max-width:none;padding:0}
  .card{border:none;box-shadow:none;border-radius:0;padding:0}
  .sec{break-inside:avoid}
  @page{size:A4;margin:12mm}
}
"""


def render_card_html(c):
    """渲染单张卡片的独立 HTML（自包含，无外部依赖）。"""
    lane = esc(c['lane'])
    meta = [f'<span class="chip lane">{lane}</span>',
            f'<span class="chip">{esc(c["type"])}</span>']
    if c['diff']:
        meta.append(f'<span class="chip">难度 {esc(c["diff"])}</span>')
    meta.append(f'<span class="chip a">官方分路：{esc("、".join(c["off_lanes"]))}</span>')

    p = []
    p.append('<div class="page"><div class="card">')
    p.append('<div class="chead">')
    p.append(f'<div class="ctitle">{esc(c["cname"])}'
             f'<small>{esc(c["title"])}</small></div>')
    p.append('<div class="cmeta">' + ''.join(meta) + '</div>')
    p.append('</div>')

    # 1 连招（置顶）
    p.append('<div class="sec"><h3>实战连招速查<span class="n">按这个顺序按</span></h3>')
    for sc in c['scene_combos'][:4]:
        p.append('<div class="combo">'
                 f'<b>{esc(sc["scene"])}</b>'
                 f'<div class="k">{esc(sc["keys"])}</div>'
                 f'<div class="d">{esc(sc["purpose"])}</div>')
        if sc['tip']:
            p.append(f'<div class="d">注意：{esc(sc["tip"])}</div>')
        p.append('</div>')
    if c['official_combos']:
        p.append('<table><thead><tr><th style="width:110px">官方连招原文</th><td>')
        for i, oc in enumerate(c['official_combos']):
            if i:
                p.append('　/　')
            p.append(esc(oc['raw']))
            if oc['note']:
                p.append(f'<span class="onote">（{esc(oc["note"])}）</span>')
        p.append('</td></tr></thead></table>')
    p.append('</div>')

    # 2 技能
    p.append('<div class="sec"><h3>技能机制</h3><div class="gs">')
    for s in c['skills']:
        p.append('<div>'
                 f'<div class="gn">{s["i"]}技能 · {esc(s["name"])}'
                 f'<span style="color:#8a847a;font-weight:500">（CD {esc(s["cd"])}）</span></div>'
                 f'<div class="gm">{esc(s["mech"])}</div>')
        if s['tags']:
            p.append(f'<div class="gt">{esc(s["tags"])}</div>')
        p.append('</div>')
    p.append('</div></div>')

    # 3 出装铭文
    p.append('<div class="sec"><h3>出装 · 铭文 · 召唤师</h3><div class="chips">')
    for e in c['equips']:
        p.append(f'<span class="equip">{esc(e)}</span>')
    p.append('</div><div class="chips" style="margin-top:6px">')
    for r in c['runes']:
        p.append(f'<span class="rune">{esc(r)}</span>')
    p.append('</div><div class="kv" style="margin-top:7px">')
    p.append(f'<span>召唤师技能：<b>{esc(c["summoner"])}</b></span>')
    p.append(f'<span>技能加点：<b>{esc(c["skill_order"])}</b></span>')
    p.append('</div></div>')

    # 4 精华技巧
    p.append('<div class="sec"><h3>精华技巧</h3><ul class="tips">')
    for t in c['tips']:
        p.append(f'<li><span class="s">{esc(t["src"])}</span>{esc(t["text"])}</li>')
    p.append('</ul></div>')

    # 5 分路打法
    p.append('<div class="sec"><h3>' + esc(c['lane']) + '位打法要点</h3>')
    for lp in c['lane_points'][:3]:
        p.append(f'<div style="margin:0 0 8px"><b style="font-size:12.5px">'
                 f'{esc(lp["title"])}</b>')
        p.append('<table><thead><tr>')
        for hcell in lp['header']:
            p.append(f'<th>{esc(hcell)}</th>')
        p.append('</tr></thead><tbody>')
        for row in lp['rows']:
            p.append('<tr>' + ''.join(f'<td>{esc(c2)}</td>' for c2 in row) + '</tr>')
        p.append('</tbody></table></div>')
    if c['phases']:
        p.append('<table><thead><tr><th style="width:78px">分阶段</th><th>要点</th>'
                 '</tr></thead><tbody>')
        for ph in c['phases']:
            name, _, rest = ph.partition('：')
            p.append(f'<tr><td><b>{esc(name)}</b></td><td>{esc(rest)}</td></tr>')
        p.append('</tbody></table>')
    p.append('</div>')

    # 6 对位
    p.append('<div class="sec"><h3>对位关系<span class="n">机制层面</span></h3><div class="kv">')
    if c['counters']:
        p.append('<span>克：<b>' + esc('、'.join(c['counters'])) + '</b></span>')
    if c['countered_by']:
        p.append('<span>被克：<b>' + esc('、'.join(c['countered_by'])) + '</b></span>')
    p.append('</div>')
    lu = c.get('lineup') or {}
    if lu.get('composition'):
        p.append('<div class="kv" style="margin-top:6px"><span>体系思路：<b>'
                 + esc(lu['composition']) + '</b></span></div>')
    p.append('</div>')

    p.append('<footer>资料快照 2026-11-12 · 数值随版本变动，以局内说明为准 · '
             '本卡片为机制与打法速查，不含胜率/梯度等时效数据</footer>')
    p.append('</div></div>')

    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='6' fill='%23b4442e'/%3E%3Ctext x='16' y='23' font-size='20' text-anchor='middle' fill='white'%3E%E7%89%8C%3C/text%3E%3C/svg%3E">
<title>{esc(c['cname'])} {esc(c['lane'])} · 速查卡</title>
<style>{CARD_CSS}</style></head>
<body>{''.join(p)}</body></html>"""


def render_card_md(c):
    """Markdown 版（便于手机 / 笔记软件查看）。"""
    L = []
    L.append(f"# {c['cname']}（{c['lane']}）速查卡")
    L.append(f"\n> {c['title']} · {c['type']} · 官方分路：{'、'.join(c['off_lanes'])}"
             f" · 快照 2026-11-12\n")
    L.append("## 实战连招（按顺序按）\n")
    for sc in c['scene_combos'][:4]:
        L.append(f"- **{sc['scene']}**：`{sc['keys']}`")
        L.append(f"  - {sc['purpose']}")
        if sc['tip']:
            L.append(f"  - 注意：{sc['tip']}")
    if c['official_combos']:
        L.append('- 官方连招原文：' + '　/　'.join(
            o['raw'] + (f"（{o['note']}）" if o['note'] else '')
            for o in c['official_combos']))
    L.append("\n## 技能机制\n")
    L.append("| 技能 | CD | 机制要点 | 画像 |")
    L.append("| --- | --- | --- | --- |")
    for s in c['skills']:
        L.append(f"| {s['i']}·{s['name']} | {s['cd']} | {s['mech']} | {s['tags']} |")
    L.append("\n## 出装 / 铭文\n")
    L.append(f"- 出装：{' → '.join(c['equips'])}")
    L.append(f"- 铭文：{'、'.join(c['runes'])}")
    L.append(f"- 召唤师技能：{c['summoner']}")
    L.append(f"- 加点：{c['skill_order']}")
    L.append("\n## 精华技巧\n")
    for t in c['tips']:
        L.append(f"- **[{t['src']}]** {t['text']}")
    L.append(f"\n## {c['lane']}位打法要点\n")
    for lp in c['lane_points'][:3]:
        L.append(f"### {lp['title']}\n")
        L.append('| ' + ' | '.join(lp['header']) + ' |')
        L.append('| ' + ' | '.join(['---'] * len(lp['header'])) + ' |')
        for row in lp['rows']:
            L.append('| ' + ' | '.join(row) + ' |')
        L.append('')
    if c['phases']:
        L.append("| 分阶段 | 要点 |")
        L.append("| --- | --- |")
        for ph in c['phases']:
            name, _, rest = ph.partition('：')
            L.append(f"| {name} | {rest} |")
        L.append('')
    L.append("## 对位\n")
    if c['counters']:
        L.append(f"- 克制：{'、'.join(c['counters'])}")
    if c['countered_by']:
        L.append(f"- 被克制：{'、'.join(c['countered_by'])}")
    lu = c.get('lineup') or {}
    if lu.get('composition'):
        L.append(f"- 体系思路：{lu['composition']}")
    L.append("\n---\n数值随版本变动，以局内说明为准；本卡片不含胜率/梯度等时效数据。\n")
    return '\n'.join(L)


# ---------------------------------------------------------------- 索引页

def render_index(cards):
    rows = []
    for c in cards:
        fn = f"{c['cname']}_{c['lane']}速查卡.html"
        md = f"{c['cname']}_{c['lane']}速查卡.md"
        rows.append({
            'cname': c['cname'], 'lane': c['lane'], 'type': c['type'],
            'file': fn, 'md': md,
            'tags': '、'.join(c['runes'][:3]),
            'win': c['win_line'],
            'combos': ' / '.join(sc['keys'] for sc in c['scene_combos'][:2]),
        })

    data = json.dumps(rows, ensure_ascii=False)
    lane_opts = ''.join(f'<option value="{L}">{L}</option>' for L in LANES)
    opt_html = []
    for r in rows:
        opt_html.append(
            f'<div class="row" data-lane="{r["lane"]}" data-name="{r["cname"]}" '
            f'data-type="{r["type"]}">'
            f'<div class="rh"><b title="{r["cname"]}">{r["cname"]}</b>'
            f'<span class="chip lane">{r["lane"]}</span>'
            f'<span class="chip">{r["type"]}</span>'
            f'<a class="btn dl" href="{r["file"]}" download>下载 HTML</a>'
            f'<a class="btn dm" href="{r["md"]}" download>下载 MD</a>'
            f'<a class="btn op" href="{r["file"]}" target="_blank">打开</a>'
            f'</div>'
            f'<div class="rc"><div class="rl">官方连招</div>'
            f'<div class="rv">{r["combos"]}</div></div>'
            f'<div class="rc"><div class="rl">玩法</div>'
            f'<div class="rv">{r["win"]}</div></div>'
            f'</div>')
    opt_html = '\n'.join(opt_html)

    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='6' fill='%23b4442e'/%3E%3Ctext x='16' y='23' font-size='20' text-anchor='middle' fill='white'%3E%E7%89%8C%3C/text%3E%3C/svg%3E">
<title>王者荣耀 · 133 英雄速查卡片</title>
<style>
:root{{--bg:#f6f4ef;--card:#fff;--ink:#23201c;--ink2:#5b554d;--line:#e3ddd2;
--accent:#b4442e;--soft:#f2ece1}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);
font:14px/1.6 -apple-system,"PingFang SC","Microsoft YaHei",sans-serif}}
.wrap{{max-width:1080px;margin:0 auto;padding:20px 18px 50px}}
h1{{font-size:22px;margin:0 0 4px}}
.sub{{color:var(--ink2);font-size:13px;margin-bottom:14px}}
.bar{{position:sticky;top:0;z-index:9;background:var(--bg);padding:8px 0 10px;
border-bottom:1px solid var(--line)}}
.bar input,select{{font:inherit;font-size:13px;padding:7px 10px;border-radius:8px;
border:1px solid var(--line);background:#fff;color:var(--ink)}}
.bar input{{flex:1;min-width:160px}}
.bar .tools{{display:flex;gap:8px;flex-wrap:wrap;align-items:center}}
#cnt{{font-size:12.5px;color:var(--ink2);margin-left:auto}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:12px;
margin-top:14px}}
.row{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 13px}}
.rh{{display:flex;align-items:center;gap:5px;flex-wrap:nowrap;margin-bottom:7px}}
.rh b{{font-size:15.5px;white-space:nowrap;flex:0 0 auto}}
.rh .chip{{white-space:nowrap;flex:0 0 auto}}
.chip{{font-size:11px;padding:2px 8px;border-radius:999px;background:var(--soft);
border:1px solid var(--line);color:var(--ink2)}}
.chip.lane{{background:var(--accent);color:#fff;border-color:var(--accent)}}
.btn{{margin-left:auto;font-size:11px;padding:3px 8px;border-radius:6px;
text-decoration:none;border:1px solid var(--line);background:#fff;color:var(--ink2);
white-space:nowrap;flex:0 0 auto}}
.btn.dl{{margin-left:auto}}
.btn.dl:hover{{background:var(--accent);color:#fff;border-color:var(--accent)}}
.btn:hover{{border-color:var(--accent);color:var(--accent)}}
.rc{{font-size:12px;display:flex;gap:7px;margin-top:3px}}
.rl{{color:var(--ink2);flex:0 0 62px;font-size:11px}}
.rv{{color:var(--ink);flex:1}}
.empty{{padding:30px;text-align:center;color:var(--ink2)}}
.hint{{font-size:12px;color:var(--ink2);margin:10px 0 0}}
</style></head><body><div class="wrap">
<h1>王者荣耀 · 133 英雄速查卡片</h1>
<div class="sub">每张卡 = 实战连招 + 技能机制 + 出装铭文 + 精华技巧 + 该分路打法要点。
点「下载 HTML」可存到本地单文件离线查看（Ctrl/⌘+P 可打印成 A4 一页）。</div>
<div class="bar"><div class="tools">
<input id="q" placeholder="搜索英雄名 / 玩法 / 连招…">
<select id="lane"><option value="">全部分路</option>{lane_opts}</select>
<span id="cnt"></span></div></div>
<div class="grid" id="grid">
{opt_html}
</div>
<div class="empty" id="empty" style="display:none">没有匹配的英雄</div>
<p class="hint">也可直接下载整包：<a href="hok_cards_133.zip">hok_cards_133.zip</a>
（133 张 HTML + 133 张 Markdown + 索引页）。</p>
</div>
<script>
var rows=[].slice.call(document.querySelectorAll('.row'));
function flt(){{
  var q=document.getElementById('q').value.trim().toLowerCase();
  var ln=document.getElementById('lane').value;
  var n=0;
  rows.forEach(function(r){{
    var ok=(!q||r.textContent.toLowerCase().indexOf(q)>=0)&&(!ln||r.dataset.lane===ln);
    r.style.display=ok?'':'none'; if(ok)n++;
  }});
  document.getElementById('cnt').textContent=n+' / '+rows.length+' 个英雄';
  document.getElementById('empty').style.display=n?'none':'block';
}}
document.getElementById('q').addEventListener('input',flt);
document.getElementById('lane').addEventListener('change',flt);
flt();
</script></body></html>"""


def main():
    cards = []
    for h in HEROES:
        lane = pick_lane(h)
        c = build_card(h, lane)
        cards.append(c)
        base = f"{c['cname']}_{c['lane']}速查卡"
        with open(os.path.join(OUT, base + '.html'), 'w', encoding='utf-8') as f:
            f.write(render_card_html(c))
        with open(os.path.join(OUT, base + '.md'), 'w', encoding='utf-8') as f:
            f.write(render_card_md(c))
    print('cards built:', len(cards))

    # 索引页
    with open(os.path.join(OUT, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(render_index(cards))

    # 合并单文件（便于单次分享）
    merged = ['<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">',
              '<meta name="viewport" content="width=device-width,initial-scale=1">',
              '<title>王者荣耀 · 133 英雄速查卡片（全合集）</title>',
              f'<style>{CARD_CSS}</style></head><body>']
    for c in cards:
        merged.append(render_card_html(c))
    merged.append('</body></html>')
    with open(os.path.join(OUT, 'cards_all.html'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(merged))

    # 合并 Markdown
    with open(os.path.join(OUT, 'cards.md'), 'w', encoding='utf-8') as f:
        for c in cards:
            f.write(render_card_md(c))
            f.write('\n\n---\n\n')
    print('index / cards_all / cards.md written')


if __name__ == '__main__':
    main()
