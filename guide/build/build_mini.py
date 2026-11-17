# -*- coding: utf-8 -*-
"""
紧凑精华卡（图片版）构建器。

与 build_cards.py 的区别：
  build_cards.py  → 完整速查卡（长图，信息全，适合打印/存档）
  build_mini.py   → 紧凑精华卡（竖版 3:4，一屏看完，适合手机/分享图）

输出 PNG 由 cards_png.js 渲染。这里只负责生成紧凑卡片的 HTML。

用法: python3 build_mini.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from build_cards import (HEROES, OFFICIAL, LANES, pick_lane, esc, build_card,
                         first_sentence)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'cards_mini')
os.makedirs(OUT, exist_ok=True)

MINI_CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{width:1080px;min-width:1080px;background:#f2ede3;
  font:15px/1.5 -apple-system,"PingFang SC","Microsoft YaHei",sans-serif;color:#23201c}
.wrap{padding:0}
.card{background:#fff;margin:0;padding:34px 38px 30px}
.chead{display:flex;align-items:flex-end;gap:14px;
  border-bottom:3px solid #23201c;padding-bottom:14px;margin-bottom:20px}
.ctitle{font-size:52px;font-weight:900;letter-spacing:2px;line-height:1}
.ctitle small{display:block;font-size:17px;font-weight:600;color:#6b655c;
  letter-spacing:1px;margin-top:7px}
.ctags{margin-left:auto;text-align:right}
.chip{display:inline-block;font-size:15px;font-weight:700;padding:5px 13px;
  border-radius:999px;background:#f0e9dc;color:#5b554d;border:1px solid #e0d9cb;
  margin-left:6px}
.chip.lane{background:#b4442e;color:#fff;border-color:#b4442e}
.sec{margin-bottom:19px}
.sec>h2{font-size:22px;font-weight:900;margin-bottom:10px;
  display:flex;align-items:center;gap:10px}
.sec>h2::before{content:"";width:6px;height:22px;background:#b4442e;border-radius:2px}
.sec>h2 em{font-style:normal;font-size:14px;color:#8a847a;font-weight:600}
.combo{display:flex;flex-wrap:wrap;align-items:center;gap:8px 14px;padding:11px 15px;margin-bottom:9px;
  background:#faf8f3;border:1px solid #e5dfd3;border-left:5px solid #2f6f6a;
  border-radius:10px}
.combo .sc{font-size:19px;font-weight:800;flex:0 0 190px}
.combo .kk{font-size:24px;font-weight:900;color:#b4442e;flex:0 1 auto;min-width:0;
  overflow-wrap:anywhere;word-break:break-all;white-space:normal;
  font-family:ui-monospace,Menlo,monospace;letter-spacing:1px}
.combo .pp{font-size:14.5px;color:#5b554d;flex:1 1 100%;min-width:0;line-height:1.45}
.combo .off{flex:0 1 auto;min-width:0}
.combo .off .kk{font-size:19px;color:#6b655c}
.combo .off .n{font-size:13px;color:#2f6f6a;font-weight:700}
.sk{display:flex;gap:11px;margin-bottom:9px}
.sk>div{flex:1;border:1px solid #e5dfd3;border-radius:10px;padding:11px 13px;
  background:#fcfbf8}
.sk .sn{font-size:19px;font-weight:800}
.sk .sn i{font-style:normal;color:#b4442e;margin-right:6px}
.sk .sn u{text-decoration:none;font-size:12.5px;color:#8a847a;font-weight:600;
  margin-left:5px}
.sk .sm{font-size:14px;color:#5b554d;margin:6px 0 4px;line-height:1.45}
.sk .st{font-size:12.5px;color:#2f6f6a;font-weight:700;line-height:1.4}
.row2{display:flex;gap:11px}
.row2>div{flex:1;border:1px solid #e5dfd3;border-radius:10px;padding:11px 13px;
  background:#fcfbf8}
.lab{font-size:12.5px;font-weight:800;color:#8a847a;letter-spacing:1px;
  margin-bottom:7px}
.eq{display:flex;flex-wrap:wrap;gap:6px}
.eq span{font-size:14.5px;font-weight:700;padding:4px 10px;border-radius:7px;
  background:#eaf2f0;color:#20514c;border:1px solid #d2e3df}
.rn span{background:#f2ece1;color:#5b554d;border-color:#e0d9cb}
.su{font-size:15px;color:#5b554d}
.su b{color:#23201c;font-size:17px}
.tips{list-style:none}
.tips li{font-size:15.5px;line-height:1.5;margin-bottom:7px;padding-left:22px;
  position:relative}
.tips li::before{content:"";position:absolute;left:4px;top:9px;width:7px;height:7px;
  border-radius:2px;background:#b4442e}
.tips .s{font-size:12px;color:#8a847a;background:#f2ece1;border-radius:5px;
  padding:2px 7px;margin-right:8px;font-weight:700}
.lanepts{display:flex;gap:10px}
.lanepts>div{flex:1;border:1px solid #e5dfd3;border-radius:10px;padding:11px 13px;
  background:#fcfbf8}
.lanepts .t{font-size:16px;font-weight:800;margin-bottom:6px;color:#2f6f6a}
.lanepts ul{list-style:none}
.lanepts li{font-size:13.5px;color:#5b554d;line-height:1.45;margin-bottom:4px;
  padding-left:13px;position:relative}
.lanepts li::before{content:"";position:absolute;left:0;top:8px;width:5px;height:5px;
  border-radius:50%;background:#2f6f6a}
footer{border-top:1px dashed #e0d9cb;padding-top:11px;font-size:12.5px;
  color:#8a847a;display:flex;justify-content:space-between}
"""


def render_mini(c):
    p = []
    p.append('<div class="card">')

    # 头
    p.append('<div class="chead"><div class="ctitle">' + esc(c['cname']))
    p.append('<small>' + esc(c['title']) + '</small></div>')
    p.append('<div class="ctags"><span class="chip lane">' + esc(c['lane']) + '</span>')
    p.append('<span class="chip">' + esc(c['type']) + '</span>')
    if c['diff']:
        p.append('<span class="chip">难度 ' + esc(c['diff']) + '</span>')
    p.append('</div></div>')

    # 连招（置顶）
    p.append('<div class="sec"><h2>实战连招<em>按这个顺序按</em></h2>')
    for sc in c['scene_combos'][:4]:
        p.append('<div class="combo"><div class="sc">' + esc(sc['scene']) + '</div>')
        p.append('<div class="kk">' + esc(sc['keys']) + '</div>')
        p.append('<div class="pp">' + esc(sc['purpose']) + '</div></div>')
    if c['official_combos']:
        off = '　/　'.join(o['raw'] + (f'（{o["note"]}）' if o['note'] else '')
                          for o in c['official_combos'])
        p.append('<div class="combo off"><div class="sc" style="font-size:16px;'
                 'color:#8a847a">官方连招原文</div>')
        p.append('<div class="kk">' + esc(off) + '</div><div></div></div>')
    p.append('</div>')

    # 技能
    p.append('<div class="sec"><h2>技能机制</h2><div class="sk">')
    for s in c['skills']:
        p.append('<div><div class="sn"><i>' + str(s['i']) + '</i>' + esc(s['name']))
        p.append('<u>CD ' + esc(s['cd']) + '</u></div>')
        p.append('<div class="sm">' + esc(s['mech']) + '</div>')
        p.append('<div class="st">' + esc(s['tags']) + '</div></div>')
    p.append('</div></div>')

    # 出装 + 铭文
    p.append('<div class="sec"><div class="row2">')
    p.append('<div><div class="lab">出装</div><div class="eq">')
    for e in c['equips']:
        p.append('<span>' + esc(e) + '</span>')
    p.append('</div></div>')
    p.append('<div><div class="lab">铭文 · 召唤师</div><div class="eq rn">')
    for r in c['runes']:
        p.append('<span>' + esc(r) + '</span>')
    p.append('</div><div class="su" style="margin-top:8px">召唤师：<b>'
             + esc(c['summoner']) + '</b>　加点：<b>' + esc(c['skill_order'])
             + '</b></div></div>')
    p.append('</div></div>')

    # 精华技巧
    p.append('<div class="sec"><h2>精华技巧</h2><ul class="tips">')
    for t in c['tips']:
        p.append('<li><span class="s">' + esc(t['src']) + '</span>' + esc(t['text'])
                 + '</li>')
    p.append('</ul></div>')

    # 分路打法要点
    if c['lane_points']:
        p.append('<div class="sec"><h2>' + esc(c['lane']) + '位打法要点</h2>')
        p.append('<div class="lanepts">')
        for lp in c['lane_points'][:3]:
            p.append('<div><div class="t">' + esc(lp['title']) + '</div><ul>')
            for r in lp['rows'][:3]:
                p.append('<li><b>' + esc(r[0]) + '</b>：' + esc(r[1]) + '</li>')
            p.append('</ul></div>')
        p.append('</div></div>')

    p.append('<footer><span>数值随版本变动，以局内说明为准</span>'
             '<span>快照 2026-11-12 · 不含胜率/梯度</span></footer>')
    p.append('</div>')
    return ('<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">'
            '<style>' + MINI_CSS + '</style></head><body><div class="wrap">'
            + ''.join(p) + '</div></body></html>')


def main():
    n = 0
    for h in HEROES:
        lane = pick_lane(h)
        c = build_card(h, lane)
        base = f"{c['cname']}_{c['lane']}精华卡"
        with open(os.path.join(OUT, base + '.html'), 'w', encoding='utf-8') as f:
            f.write(render_mini(c))
        n += 1
    print('mini cards built:', n)


if __name__ == '__main__':
    main()
