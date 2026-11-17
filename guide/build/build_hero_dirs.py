# -*- coding: utf-8 -*-
"""
按英雄拆分独立文件夹。

每个英雄一个目录：
  guide/heroes/<英雄>_<分路>/
    index.html              # 该英雄的个人主页（目录 + 直达入口）
    <英雄>_<分路>完整攻略.html   # 13 节深度攻略
    <英雄>_<分路>速查卡.html      # 完整速查卡（长图版）
    <英雄>_<分路>速查卡.md        # 速查卡 Markdown
    <英雄>_<分路>精华卡.html      # 紧凑精华卡
    images/                  # 该英雄的全部图片产物
      <英雄>_<分路>速查卡.jpg / .png
      <英雄>_<分路>精华卡.jpg / .png

再生成总目录 guide/heroes/index.html，按分路分组列出全部英雄。

用法: python3 build_hero_dirs.py
"""
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GUIDE = os.path.normpath(os.path.join(HERE, '..'))
OUT = os.path.join(GUIDE, 'heroes')

# 源目录 -> (目标子目录, 后缀白名单匹配)
SOURCES = [
    (os.path.join(GUIDE, 'full'), '', ['完整攻略.html']),
    (os.path.join(GUIDE, 'cards'), '', ['速查卡.html', '速查卡.md']),
    (os.path.join(GUIDE, 'cards_mini'), '', ['精华卡.html']),
    (os.path.join(GUIDE, 'card-images'), 'images', ['.jpg']),
    (os.path.join(GUIDE, 'cards_jpg'), 'images', ['.jpg']),
    (os.path.join(GUIDE, 'cards_png'), 'images', ['.png']),
    (os.path.join(GUIDE, 'cards_mini_jpg'), 'images', ['.jpg']),
    (os.path.join(GUIDE, 'cards_mini_png'), 'images', ['.png']),
]

LANE_ORDER = ['对抗路', '打野', '中路', '发育路', '游走']


def hero_base(filename):
    """从文件名里还原 <英雄>_<分路> 前缀。"""
    for suffix in ('完整攻略.html', '速查卡.html', '速查卡.md', '精华卡.html',
                   '速查卡.jpg', '精华卡.jpg', '速查卡.png', '精华卡.png'):
        if filename.endswith(suffix):
            return filename[: -len(suffix)]
    return None


def collect():
    """扫描所有源目录，返回 {base: {relpath: abs_path}}。"""
    found = {}
    for src, subdir, suffixes in SOURCES:
        if not os.path.isdir(src):
            continue
        for fn in sorted(os.listdir(src)):
            base = hero_base(fn)
            if base is None:
                continue
            if not any(fn.endswith(s) for s in suffixes):
                continue
            rel = fn if not subdir else os.path.join(subdir, fn)
            found.setdefault(base, {})[rel] = os.path.join(src, fn)
    return found


def parse_lane(base):
    """<英雄>_<分路> -> (英雄, 分路)；元流之子(刺客) 等带括号名也能正确切。"""
    if '_' not in base:
        return base, '未知'
    hero, lane = base.rsplit('_', 1)
    return hero, lane


def copy_all(found):
    """复制文件到各英雄目录。

    若源目录已被清理（found 为空），保留现有目录内容，只重建索引页，
    避免脚本在老目录删除后误清空 guide/heroes/。
    """
    if not found:
        print('源目录已清理，跳过文件复制（仅重建索引页）')
        return []
    written = []
    for base, items in found.items():
        target = os.path.join(OUT, base)
        if os.path.isdir(target):
            shutil.rmtree(target)
        os.makedirs(target)
        for rel, src in items.items():
            dst = os.path.join(target, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            written.append((base, rel))
    return written


HERO_PAGE = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{hero} · {lane} · 王者荣耀攻略</title>
<style>
:root{{--bg:#f6f4ef;--card:#fff;--ink:#23201c;--ink2:#5b554d;--line:#e3ddd2;
  --accent:#b4442e;--accent2:#2f6f6a;--soft:#f2ece1}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);
  font:14px/1.7 -apple-system,"PingFang SC","Microsoft YaHei",sans-serif}}
.page{{max-width:900px;margin:0 auto;padding:26px 20px 48px}}
.back{{display:inline-block;font-size:13px;color:var(--ink2);text-decoration:none;
  border:1px solid var(--line);background:var(--card);padding:5px 12px;border-radius:999px}}
.back:hover{{border-color:var(--accent);color:var(--accent)}}
.chead{{display:flex;align-items:flex-end;gap:12px;flex-wrap:wrap;
  border-bottom:2px solid var(--ink);padding-bottom:12px;margin:18px 0 20px}}
.ctitle{{font-size:30px;font-weight:800;letter-spacing:1px}}
.chip{{font-size:12px;padding:3px 10px;border-radius:999px;background:var(--soft);
  color:var(--ink2);border:1px solid var(--line)}}
.chip.lane{{background:var(--accent);color:#fff;border-color:var(--accent)}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:12px}}
.item{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px}}
.item a{{color:var(--accent);text-decoration:none;font-weight:700;font-size:15px}}
.item a:hover{{text-decoration:underline}}
.item small{{display:block;color:var(--ink2);margin-top:4px;font-size:12px}}
h2{{font-size:16px;font-weight:800;margin:26px 0 10px;padding-left:9px;
  border-left:4px solid var(--accent)}}
.imgs{{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:12px}}
.imgs a{{display:block;border:1px solid var(--line);border-radius:10px;overflow:hidden;
  background:#fff;text-decoration:none}}
.imgs img{{width:100%;display:block}}
.imgs figcaption{{font-size:12px;color:var(--ink2);padding:6px 10px}}
</style></head><body><div class="page">
<a class="back" href="index.html">← 全部英雄目录</a>
<div class="chead"><div class="ctitle">{hero}</div>
  <span class="chip lane">{lane}</span>
  <span class="chip">{count} 个文件</span></div>

<h2>文档</h2>
<div class="grid">
{items}
</div>

<h2>图片</h2>
<div class="imgs">
{imgs}
</div>
</div></body></html>
"""


def build_pages(found):
    bases = sorted(found.keys())
    if not bases:
        # 老目录已清理：从现有 guide/heroes 目录重建索引页
        for d in sorted(os.listdir(OUT)):
            if os.path.isdir(os.path.join(OUT, d)):
                bases.append(d)
                items = {}
                for dp, _, fs in os.walk(os.path.join(OUT, d)):
                    for f in fs:
                        rel = os.path.relpath(os.path.join(dp, f), os.path.join(OUT, d))
                        items[rel] = os.path.join(dp, f)
                found[d] = items
    for base in bases:
        hero, lane = parse_lane(base)
        items = found[base]
        docs, imgs = [], []
        for rel in sorted(items):
            label = rel.replace('images/', '')
            kind = '图片' if rel.startswith('images' + os.sep) else '文档'
            docs.append(
                '<div class="item"><a href="{u}">{label}</a>'
                '<small>{kind} · {kb} KB</small></div>'.format(
                    u=rel.replace(os.sep, '/'), label=label, kind=kind,
                    kb=round(os.path.getsize(items[rel]) / 1024)))
            if rel.startswith('images' + os.sep):
                imgs.append(
                    '<a href="{u}"><img src="{u}" alt="{label}">'
                    '<figcaption>{label}</figcaption></a>'.format(
                        u=rel.replace(os.sep, '/'), label=label))
        total_kb = round(sum(os.path.getsize(v) for v in items.values()) / 1024)
        html = HERO_PAGE.format(
            hero=hero, lane=lane, count=len(items),
            items='\n'.join(docs), imgs='\n'.join(imgs))
        with open(os.path.join(OUT, base, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(html)

    # 总目录
    groups = {}
    for base in bases:
        hero, lane = parse_lane(base)
        groups.setdefault(lane, []).append((hero, base))
    for lane in groups:
        groups[lane].sort()

    rows = []
    for lane in LANE_ORDER:
        if lane not in groups:
            continue
        rows.append('<h2 id="lane-{lane}">{lane} · {n} 位</h2>\n<div class="grid">'.format(
            lane=lane, n=len(groups[lane])))
        for hero, base in groups[lane]:
            rows.append(
                '<div class="item"><a href="{u}/index.html">{hero}</a>'
                '<small>{lane} · {n} 个文件</small></div>'.format(
                    u=base.replace(os.sep, '/'), hero=hero, lane=lane, n=len(found[base])))
        rows.append('</div>')

    index_html = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>王者荣耀 · 全部英雄独立攻略库</title>
<style>
:root{--bg:#f6f4ef;--card:#fff;--ink:#23201c;--ink2:#5b554d;--line:#e3ddd2;
  --accent:#b4442e;--soft:#f2ece1}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font:14px/1.7 -apple-system,"PingFang SC","Microsoft YaHei",sans-serif}
.page{max-width:1000px;margin:0 auto;padding:26px 20px 48px}
h1{font-size:26px;font-weight:800;margin:0 0 6px}
.sub{color:var(--ink2);margin:0 0 20px}
h2{font-size:16px;font-weight:800;margin:24px 0 10px;padding-left:9px;
  border-left:4px solid var(--accent)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px}
.item{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:11px 13px}
.item a{color:var(--accent);text-decoration:none;font-weight:700;font-size:15px}
.item a:hover{text-decoration:underline}
.item small{display:block;color:var(--ink2);font-size:12px;margin-top:3px}
.dl{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:10px}
.dl a{background:var(--card);border:1px solid var(--line);border-radius:12px;
  padding:12px 14px;text-decoration:none;color:var(--ink);display:block}
.dl a:hover{border-color:var(--accent)}
.dl b{display:block;color:var(--accent);font-size:14px}
.dl span{color:var(--ink2);font-size:12px}
</style></head><body><div class="page">
<h1>王者荣耀 · 全部英雄独立攻略库</h1>
<p class="sub">__TOTAL__ 位英雄 · 每位一个独立文件夹（13 节完整攻略 + 速查卡 + 精华卡 + 全部图片）</p>
__DL__
__ROWS__
</div></body></html>
"""
    dl = ['<h2>离线下载</h2>', '<div class="dl">']
    for fname, desc in [
        ('hok_cards_133.zip', '133 英雄速查卡（HTML+MD 合集）'),
        ('hok_cards_133.tar.gz', '同上 tar.gz 版'),
        ('hok_card_images_133.zip', '全部卡图 jpg（266 张）'),
        ('hok_card_images_133.tar.gz', '同上 tar.gz 版'),
        ('cards_all.html', '133 卡单文件合集（浏览器直接打开）'),
        ('cards.md', '133 卡 Markdown 合集'),
    ]:
        p = os.path.join(OUT, fname)
        if os.path.isfile(p):
            dl.append('<a href="{u}" download><b>{n}</b><span>{d} · {s} MB</span></a>'.format(
                u=fname, n=fname, d=desc, s=round(os.path.getsize(p) / 1e6, 2)))
    dl.append('</div>')
    index_html = (index_html
                  .replace('__TOTAL__', str(len(bases)))
                  .replace('__DL__', '\n'.join(dl))
                  .replace('__ROWS__', '\n'.join(rows)))
    with open(os.path.join(OUT, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(index_html)
    return len(bases)


def main():
    os.makedirs(OUT, exist_ok=True)
    found = collect()
    if not found:
        # 老目录已清理：仅从现有 guide/heroes 重建索引页
        print('源目录已清理，从 guide/heroes 重建索引页')
        n = build_pages(found)
        size = sum(
            os.path.getsize(os.path.join(dp, f))
            for dp, _, fs in os.walk(OUT) for f in fs)
        print('英雄目录数: %d' % n)
        print('总大小: %.1f MB' % (size / 1e6))
        return 0
    copy_all(found)
    n = build_pages(found)
    size = sum(
        os.path.getsize(os.path.join(dp, f))
        for dp, _, fs in os.walk(OUT) for f in fs)
    print('英雄目录数: %d' % n)
    print('总大小: %.1f MB' % (size / 1e6))
    # 校验
    missing = []
    for base, items in found.items():
        for rel in items:
            if not os.path.exists(os.path.join(OUT, base, rel)):
                missing.append((base, rel))
    print('缺失文件:', len(missing))
    return 0


if __name__ == '__main__':
    sys.exit(main())
