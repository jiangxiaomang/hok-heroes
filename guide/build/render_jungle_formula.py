#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把打野公式源数据渲染成一张实用长图。"""
import os, json, html, asyncio

SRC=os.path.expanduser("~/hok-site/guide/build/打野公式_源数据.json")
OUT=os.path.expanduser("~/Desktop/王者荣耀技巧图文/打野逻辑总纲_上分公式.png")
CHROME=("/Users/analyst/.hermes/tools/chromium-1208/chrome-mac-arm64/"
        "Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing")

def build_html(o):
    chain="".join(
      f'<div class="step"><span class="sn">{i}</span><span class="st">{html.escape(s)}</span></div>'
      + ('<span class="arrow">›</span>' if i<len(o["决策链"]) else '')
      for i,s in enumerate(o["决策链"],1))
    mods=[]
    for m in o["模块"]:
        pts="".join(f'<li>{html.escape(p)}</li>' for p in m["points"])
        mods.append(f'''
      <div class="mod">
        <div class="mhead" style="background:{m['bg']};border-left:7px solid {m['color']}">
          <span class="tag" style="color:{m['color']}">{html.escape(m['tag'])}</span>
          <span class="mname">{html.escape(m['name'])}</span>
        </div>
        <div class="mbody">
          <div class="heart" style="border-color:{m['color']}">{html.escape(m['heart'])}</div>
          <ul style="list-style:none;margin:0;padding:0">
          {''.join(f'<li class="pt"><span class="dot" style="background:{m["color"]}"></span>{html.escape(p)}</li>' for p in m['points'])}
          </ul>
        </div>
      </div>''')
    return f'''<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<style>
*{{box-sizing:border-box}}
html,body{{margin:0;padding:0}}
body{{width:1000px;background:#f4f6f9;font-family:"PingFang SC","STHeiti",sans-serif;color:#1a1a1a}}
.wrap{{padding:0 0 60px}}
.hero{{background:linear-gradient(135deg,#0d47a1,#1565c0 55%,#1e88e5);color:#fff;padding:56px 60px 48px}}
.hero h1{{font-size:60px;margin:0 0 14px;font-weight:900;letter-spacing:2px}}
.hero .sub{{font-size:26px;opacity:.92;font-weight:500}}
.hero .src{{font-size:18px;opacity:.75;margin-top:18px}}
.chain{{background:#fff;padding:30px 60px;border-bottom:3px solid #eef1f5;display:flex;align-items:center;flex-wrap:wrap;gap:4px}}
.step{{display:flex;align-items:center;gap:10px}}
.sn{{width:34px;height:34px;border-radius:50%;background:#1565c0;color:#fff;font-size:19px;font-weight:800;display:flex;align-items:center;justify-content:center}}
.st{{font-size:23px;font-weight:800;color:#0d47a1}}
.arrow{{font-size:30px;color:#b0bec5;margin:0 8px;font-weight:700}}
.grid{{padding:34px 44px 0;display:grid;grid-template-columns:1fr 1fr;gap:26px}}
.mod{{background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 4px 14px rgba(0,0,0,.06)}}
.mhead{{padding:18px 24px;display:flex;align-items:baseline;gap:16px;flex-wrap:wrap}}
.tag{{font-size:19px;font-weight:900;letter-spacing:1px}}
.mname{{font-size:27px;font-weight:900;color:#111}}
.mbody{{padding:20px 26px 26px}}
.heart{{font-size:21px;font-weight:700;line-height:1.6;color:#37474f;background:#fafbfc;border-left:5px solid;padding:14px 18px;border-radius:8px;margin-bottom:18px}}
.pt{{display:flex;align-items:flex-start;gap:14px;font-size:21px;line-height:1.6;margin-bottom:13px;color:#333}}
.dot{{flex:none;width:11px;height:11px;border-radius:50%;margin-top:12px}}
.mn{{margin:34px 44px 0;background:linear-gradient(135deg,#fff8e1,#ffecb3);border:3px solid #ffb300;border-radius:18px;padding:30px 36px}}
.mnlabel{{display:block;font-size:20px;color:#b8860b;font-weight:800;letter-spacing:3px;margin-bottom:14px}}
.mntext{{font-size:29px;font-weight:800;line-height:1.65;color:#6d4c00}}
.ft{{text-align:center;color:#9aa0a6;font-size:17px;margin-top:36px}}
</style></head><body>
<div class="wrap">
  <div class="hero">
    <h1>{html.escape(o['标题'])}</h1>
    <div class="sub">{html.escape(o['副标题'])}</div>
    <div class="src">一图打通：读局 → 决策 → 执行 → 终结</div>
  </div>
  <div class="chain">{chain}</div>
  <div class="grid">{''.join(mods)}</div>
  <div class="mn">
    <span class="mnlabel">总 口 诀</span>
    <div class="mntext">{html.escape(o['口诀'])}</div>
  </div>
  <div class="ft">{html.escape(o['落款'])}</div>
</div>
</body></html>'''

async def main():
    o=json.load(open(SRC,encoding='utf-8'))
    h=build_html(o)
    tmp=OUT+".html"; open(tmp,'w',encoding='utf-8').write(h)
    from playwright.async_api import async_playwright
    async with async_playwright() as pw:
        b=await pw.chromium.launch(executable_path=CHROME,headless=True,args=["--no-sandbox"])
        ctx=await b.new_context(viewport={"width":1000,"height":1400},device_scale_factor=2)
        page=await ctx.new_page()
        await page.goto("file://"+os.path.abspath(tmp),wait_until="networkidle")
        await page.screenshot(path=OUT,full_page=True,type="png")
        await b.close()
    os.remove(tmp)
    print("生成:",OUT,os.path.getsize(OUT)//1024,"KB")

if __name__=="__main__":
    asyncio.run(main())
