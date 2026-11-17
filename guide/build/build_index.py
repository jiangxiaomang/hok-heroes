"""生成完整攻略库索引页 guide/full/index.html。

列出全部 133 篇单英雄 13 节攻略，按分路分组，直接给出直达入口。
浅色主题、纯内联样式、无外部依赖、可打印、离线可用。
"""
import json
import os
import urllib.parse

ROOT = '/Users/analyst/hok-site'
MAN = json.load(open(os.path.join(ROOT, 'guide/data/full_guides.json'), encoding='utf-8'))
GUIDE = json.load(open(os.path.join(ROOT, 'guide/data/heroes.json'), encoding='utf-8'))

LANE_ORDER = ['对抗路', '打野', '中路', '发育路', '游走']
LANE_DESC = {
    '对抗路': '单带与开团两条线都吃香，重点是线权和支援时机',
    '打野': '节奏发动机，先手与补位都要能读懂地图',
    '中路': '支援半径决定上限，中立资源与边路联动是命脉',
    '发育路': '吃发育吃资源，后期靠持续输出与自保翻盘',
    '游走': '视野、跟团和保护后排，是队伍的隐形第四人',
}
LANE_ICON = {'对抗路': '⚔️', '打野': '🌲', '中路': '🌀', '发育路': '🏹', '游走': '🛡️'}

INFO = {g['n']: g for g in GUIDE}


def esc(s):
    return (str(s).replace('&', '&amp;').replace('<', '&lt;')
            .replace('>', '&gt;').replace('"', '&quot;'))


cards = []
for lane in LANE_ORDER:
    names = [n for n, v in MAN.items() if v['lane'] == lane]
    names.sort(key=lambda n: INFO.get(n, {}).get('role', ''))
    items = []
    for n in names:
        g = INFO.get(n, {})
        url = MAN[n]['url']
        badges = ''
        if g.get('role'):
            badges += '<span class="bd r">' + esc(g['role']) + '</span>'
        if g.get('diff'):
            badges += '<span class="bd d">' + esc(g['diff']) + '</span>'
        tags = ''
        for t in (g.get('tags') or [])[:4]:
            tags += '<span class="tg">' + esc(t) + '</span>'
        items.append(
            '<a class="card" href="{u}">'
            '<div class="c-top"><span class="c-name">{n}</span>{b}</div>'
            '<div class="c-feat">{f}</div>'
            '<div class="c-tags">{t}</div>'
            '<div class="c-go">阅读 13 节完整攻略 →</div>'
            '</a>'.format(u=urllib.parse.quote(MAN[n]['file']), n=esc(n),
                          b=badges, f=esc(g.get('feat', '')), t=tags))
    cards.append(
        '<section class="lane" id="lane-{l}">'
        '<div class="lane-head"><span class="lane-ico">{i}</span>'
        '<h2>{l}</h2><span class="lane-n">{c} 位</span></div>'
        '<p class="lane-desc">{d}</p>'
        '<div class="grid">{items}</div>'
        '</section>'.format(l=lane, i=LANE_ICON[lane], c=len(names),
                            d=esc(LANE_DESC[lane]), items=''.join(items)))

nav = ''.join('<a href="#lane-{l}">{l}</a>'.format(l=l) for l in LANE_ORDER)

HTML = """<!DOCTYPE html>
<html lang="zh-CN" data-theme="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>王者荣耀 · 全英雄 13 节完整攻略库</title>
<style>
*{box-sizing:border-box}
body{margin:0;background:#f6f5f1;color:#23262e;
  font-family:"Noto Serif SC","PingFang SC","Microsoft YaHei",serif;line-height:1.7}
.wrap{max-width:1180px;margin:0 auto;padding:22px 18px 60px}
header.top{border-bottom:2px solid #d9c98f;padding-bottom:14px;margin-bottom:16px}
h1{margin:0 0 6px;font-size:23px;letter-spacing:1px}
.sub{color:#6b6f78;font-size:13px}
.nav{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}
.nav a{font-size:12.5px;text-decoration:none;color:#4a4e57;border:1px solid #ddd6c0;
  background:#fff;padding:4px 11px;border-radius:4px}
.nav a:hover{border-color:#c0a75a;color:#8a6d1a}
.lane{margin:26px 0 8px}
.lane-head{display:flex;align-items:center;gap:9px;border-bottom:1px solid #ddd6c0;
  padding-bottom:7px}
.lane-ico{font-size:19px}
.lane-head h2{margin:0;font-size:17px}
.lane-n{font-size:12px;color:#8a8d94}
.lane-desc{margin:8px 0 12px;font-size:13px;color:#6b6f78}
.grid{display:grid;gap:10px;grid-template-columns:repeat(auto-fill,minmax(300px,1fr))}
.card{display:block;text-decoration:none;color:inherit;background:#fff;
  border:1px solid #e3dcc8;border-radius:6px;padding:11px 13px}
.card:hover{border-color:#c0a75a;box-shadow:0 1px 4px rgba(0,0,0,.05)}
.c-top{display:flex;align-items:center;gap:7px;margin-bottom:5px}
.c-name{font-weight:800;font-size:15px;color:#23262e}
.bd{font-size:11px;padding:1px 7px;border-radius:3px;border:1px solid #ddd6c0;
  color:#6b6f78;background:#faf8f2}
.bd.d{color:#8a6d1a;border-color:#e0d3a8}
.c-feat{font-size:12.5px;color:#4a4e57;margin:4px 0 7px}
.c-tags{display:flex;gap:5px;flex-wrap:wrap;margin-bottom:7px}
.tg{font-size:11px;color:#6b6f78;border:1px solid #e7e1d0;border-radius:3px;
  padding:0 6px;background:#fbfaf5}
.c-go{font-size:12px;color:#8a6d1a;border-top:1px dashed #e3dcc8;padding-top:6px}
footer{margin-top:34px;border-top:1px solid #ddd6c0;padding-top:12px;
  font-size:12px;color:#6b6f78}
@media print{.nav{display:none}.card{break-inside:avoid}}
@media(max-width:640px){.grid{grid-template-columns:1fr}}
</style>
</head>
<body>
<div class="wrap">
<header class="top">
  <h1>王者荣耀 · 全英雄 13 节完整攻略库</h1>
  <div class="sub">共 133 篇 · 每篇均为固定 13 节骨架（0 范本说明 → 13 附录）· 浅色主题 · 单文件可离线阅读与打印</div>
  <div class="nav">{nav}</div>
</header>
{cards}
<footer>
  本页为站内导航索引。各篇攻略内均标注「A 官方硬数据 / B 主流观点 / C 体验服未落地 / D 主观判断」四类信息来源，
  并统一采用现行资源时间口径（红隼 0:30、空间之灵 2:00、双龙 10:00、风暴龙王 20:00）。
  数值与版本相关结论均以局内说明为准。
</footer>
</div>
</body>
</html>
"""

out = os.path.join(ROOT, 'guide/full/index.html')
open(out, 'w', encoding='utf-8').write(
    HTML.replace('{nav}', nav).replace('{cards}', ''.join(cards)))
print('written', out, os.path.getsize(out))
