#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 ASR 文字稿渲染成图片卡片（HTML -> Playwright 长截图）。

用法:
  python3 /usr/bin/python3 asr_to_image.py <txt文件> [--out 输出png] [--json 对应json(带时间戳)]
  python3 asr_to_image.py --all            # 批量生成全部70集到桌面文件夹
"""
import os, sys, glob, re, html, argparse, asyncio

TD = os.path.expanduser("~/Desktop/百度下载/S44-零基础到百段野核教科书（百期连更通用/_transcripts")
OUT = os.path.expanduser("~/Desktop/王者荣耀技巧图文")
CHROME = ("/Users/analyst/.hermes/tools/chromium-1208/chrome-mac-arm64/"
          "Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing")


def parse_name(fname):
    name = os.path.basename(fname).replace(".fixed.txt", "").replace(".txt", "")
    m = re.match(r"【(\d+)】(.+?)\s*\[(\d+)\]", name)
    if m:
        return m.group(1), m.group(2).strip(), m.group(3)
    return "?", name, ""


def cat_of(title):
    if "实战" in title or "特邀" in title: return ("英雄实战", "#e8f5e9", "#2e7d32")
    if any(k in title for k in ["分段", "上分", "星耀", "巅峰", "赛季"]): return ("分段上分", "#e3f2fd", "#1565c0")
    if "出装" in title or "铭文" in title: return ("出装铭文", "#fff3e0", "#e65100")
    if "设置" in title or "操作" in title: return ("操作设置", "#f3e5f5", "#6a1b9a")
    return ("通用方法论", "#eceff1", "#37474f")


def merge_paragraphs(lines, min_len=32, max_len=110):
    """把逐句口语合并成段落：累计到 min_len 且遇句末标点才断段。"""
    paras, cur = [], ""
    for ln in lines:
        ln = ln.strip()
        if not ln or ln.startswith("【字幕"):
            continue
        cur += ln
        # 到达一定长度且是句末
        if len(cur) >= min_len and (ln.endswith(("。", "！", "？", "…", ".", "吧", "了", "的")) or len(cur) >= max_len):
            paras.append(cur)
            cur = ""
    if cur:
        paras.append(cur)
    return paras


def build_html(num, title, cat, lines, with_time=False, json_path=None):
    cat_name, bg, fg = cat
    paras = merge_paragraphs(lines)
    # 时间戳映射（若需要）
    time_map = {}
    if with_time and json_path and os.path.exists(json_path):
        import json
        try:
            obj = json.load(open(json_path, encoding="utf-8"))
            for s in obj.get("segments", []):
                t = int(s.get("start", 0))
                time_map[s.get("text", "").strip()] = f"{t//60:02d}:{t%60:02d}"
        except Exception:
            pass
    body = "\n".join(f"<p>{html.escape(p)}</p>" for p in paras)
    return f"""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<style>
html,body {{ margin:0; padding:0; }}
* {{ box-sizing:border-box; margin:0; padding:0; }}
body {{ width:900px; background:#fff; font-family:"PingFang SC","STHeiti",sans-serif; color:#222; overflow:hidden; }}
.card {{ background:#fff; margin:0; padding:48px 56px 60px; }}
.hd {{ border-bottom:4px solid #1a73e8; padding-bottom:28px; margin-bottom:36px; }}
.badge {{ display:inline-block; background:{bg}; color:{fg}; font-size:22px; font-weight:700;
         padding:8px 20px; border-radius:24px; margin-bottom:20px; }}
.num {{ color:#1a73e8; font-size:26px; font-weight:800; letter-spacing:2px; }}
h1 {{ font-size:46px; line-height:1.35; margin:18px 0 12px; font-weight:800; }}
.meta {{ color:#888; font-size:20px; }}
.content p {{ font-size:28px; line-height:1.95; margin-bottom:26px; text-align:justify; }}
.ft {{ margin-top:48px; padding-top:24px; border-top:2px dashed #ddd; color:#999; font-size:18px; }}
</style></head><body>
<div class="card">
  <div class="hd">
    <span class="badge">{html.escape(cat_name)}</span>
    <div class="num">第 {num} 期 / 共 70 期</div>
    <h1>{html.escape(title)}</h1>
    <div class="meta">百段野核教科书 · 本地语音识别整理</div>
  </div>
  <div class="content">{body}</div>
  <div class="ft">来源：S44《零基础到百段野核教科书》教学视频 · 文字稿由 Whisper 本地识别 + 术语校正生成，仅供参考</div>
</div>
</body></html>"""


async def render_one(html_str, out_png):
    from playwright.async_api import async_playwright
    tmp_html = out_png + ".html"
    with open(tmp_html, "w", encoding="utf-8") as f:
        f.write(html_str)
    async with async_playwright() as pw:
        b = await pw.chromium.launch(executable_path=CHROME, headless=True, args=["--no-sandbox"])
        ctx = await b.new_context(viewport={"width": 900, "height": 1200}, device_scale_factor=2)
        page = await ctx.new_page()
        await page.goto("file://" + os.path.abspath(tmp_html), wait_until="networkidle")
        await page.screenshot(path=out_png, full_page=True, type="png")
        await b.close()
    os.remove(tmp_html)


def process_txt(txt, outdir):
    num, title, _ = parse_name(txt)
    cat = cat_of(title)  # 完整三元组 (名称, 背景色, 前景色)
    lines = open(txt, encoding="utf-8").read().splitlines()
    jp = txt.replace(".fixed.txt", ".fixed.json")
    h = build_html(num, title, cat, lines, with_time=False, json_path=jp)
    out = os.path.join(outdir, f"第{num}期_{title}.png".replace("/", "-"))
    asyncio.get_event_loop().run_until_complete(render_one(h, out))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("txt", nargs="?", help="单个txt文件")
    ap.add_argument("--all", action="store_true", help="批量生成全部到桌面文件夹")
    ap.add_argument("--out", default=OUT, help="输出目录")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    if args.all:
        files = sorted(glob.glob(TD + "/*.fixed.txt"))
    elif args.txt:
        files = [args.txt]
    else:
        ap.error("请指定 txt 文件或 --all")
    for f in files:
        num, title, _ = parse_name(f)
        out = os.path.join(args.out, f"第{num}期_{title}.png".replace("/", "-"))
        if os.path.exists(out):
            print("跳过(已存在):", os.path.basename(out), flush=True)
            continue
        out = process_txt(f, args.out)
        print("生成:", os.path.basename(out), flush=True)


if __name__ == "__main__":
    main()
