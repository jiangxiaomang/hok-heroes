#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把精读 JSON 渲染成条理清晰的"精读卡"（HTML -> Playwright）。

用法: python3 asr_digestcard.py 精读_003.json [--out]  或 --all
"""
import os, sys, glob, json, html, argparse, asyncio, re

OUT = os.path.expanduser("~/Desktop/王者荣耀技巧图文/_精读卡")
CHROME = ("/Users/analyst/.hermes/tools/chromium-1208/chrome-mac-arm64/"
          "Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing")
JDIR = os.path.expanduser("~/Desktop/王者荣耀技巧图文/_精读JSON")
HERO = {"玄策":"百里玄策","典韦":"典韦","扉":"暃","飞":"暃","暃":"暃","宫本":"宫本武藏","宫本武藏":"宫本武藏",
        "澜":"澜","影":"影","镜":"镜","司马懿":"司马懿","橘右京":"橘右京","老虎":"裴擒虎","裴擒虎":"裴擒虎",
        "曜":"东方曜","马超":"马超","云中君":"云中君","猴子":"孙悟空","孙悟空":"孙悟空"}
def is_hero(t): return ("共创操作技巧" in t) or ("特邀专场" in t and "实战" in t) or ("实战全局教学" in t)
def hero_of(t):
    m=re.search(r'(.+?)共创操作技巧',t) or re.search(r'一万[六七八九](.+?)实战',t) or re.search(r'(.+?)实战全局教学',t)
    if not m: return None
    raw=re.sub(r'^.*?专场[：:]?','',m.group(1).strip()).strip()
    return HERO.get(raw,raw)
def cat_of(t):
    if "实战" in t or "特邀" in t: return "英雄实战","#e8f5e9","#2e7d32"
    if any(k in t for k in ["分段","上分","星耀","巅峰","赛季"]): return "分段上分","#e3f2fd","#1565c0"
    if "出装" in t or "铭文" in t: return "出装铭文","#fff3e0","#e65100"
    if "设置" in t or "操作" in t: return "操作设置","#f3e5f5","#6a1b9a"
    return "通用方法论","#eceff1","#37474f"


def build_html(o):
    num=int(o["集数"]); title=o["标题"]
    cat,bg,fg=cat_of(title)
    hero=hero_of(title) if is_hero(title) else None
    hero_tag=f'<span class="herotag">{html.escape(hero)}打法</span>' if hero else ''
    secs=[]
    for s in o["小节"]:
        pts="".join(f'<div class="pt"><span class="pn">{i}</span>{html.escape(str(p))}</div>'
                    for i,p in enumerate(s["要点"],1))
        secs.append(f'<div class="sec"><div class="sectitle"><span class="bar"></span>{html.escape(str(s["标题"]))}</div>{pts}</div>')
    return f"""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<style>
html,body{{margin:0;padding:0;}}
body{{width:800px;background:#fff;font-family:"PingFang SC","STHeiti",sans-serif;color:#1f2329;}}
.card{{padding:50px 56px 60px;}}
.top{{display:flex;align-items:center;gap:14px;margin-bottom:22px;flex-wrap:wrap;}}
.badge{{background:{bg};color:{fg};font-size:20px;font-weight:700;padding:8px 20px;border-radius:22px;}}
.herotag{{background:#1a73e8;color:#fff;font-size:20px;font-weight:700;padding:8px 20px;border-radius:22px;}}
.issue{{color:#9aa0a6;font-size:22px;font-weight:700;margin-left:auto;}}
h1{{font-size:40px;line-height:1.3;margin:0 0 40px;font-weight:800;}}
.sec{{margin-bottom:38px;}}
.sectitle{{font-size:27px;font-weight:800;color:#1557b0;margin-bottom:18px;display:flex;align-items:center;gap:12px;}}
.bar{{width:6px;height:28px;background:#1a73e8;border-radius:3px;}}
.pt{{display:flex;align-items:flex-start;gap:14px;font-size:24px;line-height:1.75;margin-bottom:12px;}}
.pn{{flex:none;min-width:32px;height:32px;border-radius:9px;background:#eef4ff;color:#1a73e8;font-size:19px;font-weight:800;display:flex;align-items:center;justify-content:center;padding:0 6px;}}
.ft{{margin-top:44px;padding-top:22px;border-top:2px dashed #e5e5e5;color:#b0b0b0;font-size:16px;}}
</style></head><body><div class="card">
<div class="top"><span class="badge">{html.escape(cat)}</span>{hero_tag}<span class="issue">第 {num:03d} 期</span></div>
<h1>{html.escape(title)}</h1>
{''.join(secs)}
<div class="ft">百段野核教科书 · 精读卡（整理自语音转写，保留全部要点，已纠正术语与标点）</div>
</div></body></html>"""


async def render(h, out):
    from playwright.async_api import async_playwright
    tmp=out+".html"; open(tmp,"w",encoding="utf-8").write(h)
    async with async_playwright() as pw:
        b=await pw.chromium.launch(executable_path=CHROME,headless=True,args=["--no-sandbox"])
        ctx=await b.new_context(viewport={"width":800,"height":1000},device_scale_factor=2)
        page=await ctx.new_page()
        await page.goto("file://"+os.path.abspath(tmp),wait_until="networkidle")
        await page.screenshot(path=out,full_page=True,type="png")
        await b.close()
    os.remove(tmp)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("jsonfile",nargs="?")
    ap.add_argument("--all",action="store_true")
    ap.add_argument("--out",default=OUT)
    args=ap.parse_args()
    os.makedirs(args.out,exist_ok=True)
    if args.all: files=sorted(glob.glob(JDIR+"/精读_*.json"))
    elif args.jsonfile: files=[args.jsonfile]
    else: ap.error("请指定 json 或 --all")
    loop=asyncio.new_event_loop()
    for f in files:
        o=json.load(open(f,encoding="utf-8"))
        num=str(o["集数"]).zfill(3)
        title=str(o["标题"]).replace("/","-")
        hero=hero_of(o["标题"]) if is_hero(o["标题"]) else None
        base=f"{hero}_精读第{num}期.png" if hero else f"精读第{num}期_{title}.png"
        out=os.path.join(args.out,base)
        loop.run_until_complete(render(build_html(o),out))
        print("生成:",os.path.basename(out),flush=True)

if __name__=="__main__": main()
