#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把速记 JSON 渲染成"看一眼就记住"的紧凑卡片（HTML -> Playwright）。

用法:
  python3 asr_quickcard.py 速记_003.json [--out 输出png]
  python3 asr_quickcard.py --all
"""
import os, sys, glob, json, html, argparse, asyncio

SUMDIR = os.path.expanduser("~/Desktop/王者荣耀技巧图文/_速记JSON")
OUT = os.path.expanduser("~/Desktop/王者荣耀技巧图文/_速记卡")
CHROME = ("/Users/analyst/.hermes/tools/chromium-1208/chrome-mac-arm64/"
          "Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing")

CATS = [
    (("实战", "特邀"), "英雄实战", "#e8f5e9", "#2e7d32"),
    (("分段", "上分", "星耀", "巅峰", "赛季"), "分段上分", "#e3f2fd", "#1565c0"),
    (("出装", "铭文"), "出装铭文", "#fff3e0", "#e65100"),
    (("设置", "操作"), "操作设置", "#f3e5f5", "#6a1b9a"),
]


def cat_of(title):
    for keys, name, bg, fg in CATS:
        if any(k in title for k in keys):
            return name, bg, fg
    return "通用方法论", "#eceff1", "#37474f"


def build_html(o):
    num = int(o["集数"]) if isinstance(o["集数"], (int, str)) and str(o["集数"]).isdigit() else 0
    title = o["标题"]
    cat_name, bg, fg = cat_of(title)
    one = o.get("一句话", "")
    points = o.get("要点", [])
    mnemonic_text = o.get("口诀", "")
    keys = o.get("关键词", [])
    pts = "".join(
        f'<div class="pt"><span class="pn">{i}</span><span class="pc">{html.escape(str(p))}</span></div>'
        for i, p in enumerate(points, 1)
    )
    kws = "".join(f'<span class="kw">{html.escape(str(k))}</span>' for k in keys)
    mnemonic = f'<div class="mn"><span class="mnlabel">记忆口诀</span>{html.escape(mnemonic_text)}</div>' if mnemonic_text else ""
    return f"""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<style>
html,body {{ margin:0;padding:0; }}
body {{ width:760px; background:#f5f6f8; font-family:"PingFang SC","STHeiti",sans-serif; color:#1a1a1a; }}
.card {{ background:#fff; margin:0; padding:52px 56px 56px; }}
.top {{ display:flex; align-items:center; justify-content:space-between; margin-bottom:26px; }}
.badge {{ background:{bg}; color:{fg}; font-size:22px; font-weight:700; padding:9px 22px; border-radius:24px; }}
.issue {{ color:#9aa0a6; font-size:24px; font-weight:700; }}
h1 {{ font-size:42px; line-height:1.3; margin:0 0 34px; font-weight:800; }}
.one {{ background:linear-gradient(135deg,#1a73e8,#1557b0); color:#fff; border-radius:20px;
       padding:32px 34px; font-size:34px; font-weight:800; line-height:1.45; margin-bottom:38px;
       box-shadow:0 10px 24px rgba(26,115,232,.22); }}
.onelabel {{ font-size:18px; font-weight:500; opacity:.85; display:block; margin-bottom:12px; letter-spacing:2px; }}
.sec {{ font-size:20px; color:#9aa0a6; font-weight:700; letter-spacing:2px; margin-bottom:20px; }}
.pt {{ display:flex; align-items:flex-start; gap:20px; margin-bottom:22px; }}
.pn {{ flex:none; width:40px; height:40px; border-radius:12px; background:#eef4ff; color:#1a73e8;
      font-size:24px; font-weight:800; display:flex; align-items:center; justify-content:center; }}
.pc {{ font-size:28px; line-height:1.6; padding-top:3px; }}
.mn {{ margin-top:30px; background:#fff8e1; border-left:6px solid #f5a623; border-radius:12px;
      padding:24px 28px; font-size:28px; font-weight:700; line-height:1.5; color:#8a5a00; }}
.mnlabel {{ display:block; font-size:17px; color:#b8860b; font-weight:500; margin-bottom:10px; letter-spacing:2px; }}
.kws {{ margin-top:34px; padding-top:26px; border-top:2px dashed #e5e5e5; }}
.kw {{ display:inline-block; background:#f1f3f5; color:#555; font-size:20px; font-weight:600;
      padding:9px 20px; border-radius:18px; margin:0 12px 12px 0; }}
.ft {{ margin-top:30px; color:#bbb; font-size:16px; }}
</style></head><body>
<div class="card">
  <div class="top"><span class="badge">{html.escape(cat_name)}</span><span class="issue">第 {num:03d} 期</span></div>
  <h1>{html.escape(title)}</h1>
  <div class="one"><span class="onelabel">一 句 话 记 住</span>{html.escape(one)}</div>
  <div class="sec">核 心 要 点</div>
  {pts}
  {mnemonic}
  <div class="kws">{kws}</div>
  <div class="ft">百段野核教科书 · 速记卡 · 明细见同名长图</div>
</div>
</body></html>"""


async def render(html_str, out_png):
    from playwright.async_api import async_playwright
    tmp = out_png + ".html"
    open(tmp, "w", encoding="utf-8").write(html_str)
    async with async_playwright() as pw:
        b = await pw.chromium.launch(executable_path=CHROME, headless=True, args=["--no-sandbox"])
        ctx = await b.new_context(viewport={"width": 760, "height": 1000}, device_scale_factor=2)
        page = await ctx.new_page()
        await page.goto("file://" + os.path.abspath(tmp), wait_until="networkidle")
        await page.screenshot(path=out_png, full_page=True, type="png")
        await b.close()
    os.remove(tmp)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("jsonfile", nargs="?")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    if args.all:
        files = sorted(glob.glob(SUMDIR + "/速记_*.json"))
    elif args.jsonfile:
        files = [args.jsonfile]
    else:
        ap.error("请指定 json 或 --all")
    loop = asyncio.new_event_loop()
    for f in files:
        o = json.load(open(f, encoding="utf-8"))
        num = str(o["集数"]).zfill(3)
        title = str(o["标题"]).replace("/", "-")
        out = os.path.join(args.out, f"速记{num}_{title}.png")
        loop.run_until_complete(render(build_html(o), out))
        print("生成:", os.path.basename(out), flush=True)


if __name__ == "__main__":
    main()
