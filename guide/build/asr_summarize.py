#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用本地 Ollama 把 ASR 文字稿提炼成速记卡（结构化 JSON）。

输出结构：
{
  "一句话": "看完只记这一句",
  "要点": ["要点1", "要点2", ...],      # 3-6条，每条<=30字
  "口诀": "可选，朗朗上口的记忆点",
  "关键词": ["词1","词2",...]
}
用法:
  python3 asr_summarize.py <txt> [--out 输出json] [--model qwen2.5:14b]
  python3 asr_summarize.py --all [--model ...]
"""
import os, sys, glob, json, re, argparse, urllib.request, time

TD = os.path.expanduser("~/Desktop/百度下载/S44-零基础到百段野核教科书（百期连更通用/_transcripts")
SUMDIR = os.path.expanduser("~/Desktop/王者荣耀技巧图文/_速记JSON")
OLLAMA = "http://127.0.0.1:11434/api/generate"

SYSTEM = """你是王者荣耀打野教学的内容编辑。下面是一段教学视频的语音转文字稿（有ASR错别字）。
请把它的核心方法提炼成"看一眼就记住"的速记卡。要求：

1. 【错别字纠正】结合王者荣耀语境纠正同音错字，例如：编路=边路、单代=单带、敏玥=芈月、暗信=李信(暗影形态)、铝布=吕布、老福子=老夫子、司空阵=司空震、狂铁/曹操/杨戬/姬小满保留、吃惊劲=吃经济、槽里=草里、核=核心、也兴=弈星。英雄名、术语必须正确。

2. 输出严格JSON（不要任何其他文字、不要markdown代码块），格式：
{"一句话":"用一句大白话概括这条视频最核心的方法，20字内","要点":["要点1","要点2","要点3"],"口诀":"可选的简短记忆口诀，没有就留空字符串","关键词":["关键词1","关键词2","关键词3"]}

3. 要点3-6条，每条≤30字，用祈使句或结论句（如"选出芈月要防反野，抓其压线一两步"），保留具体英雄名和可执行动作，不要空话。

4. 只提炼教学干货，删掉"点赞关注、五星好评、下期见"等口播套话。"""

USER_TPL = """视频标题：{title}

文字稿：
{text}

请输出速记卡JSON："""


def parse_name(fname):
    name = os.path.basename(fname).replace(".fixed.txt", "").replace(".txt", "")
    m = re.match(r"【(\d+)】(.+?)\s*\[(\d+)\]", name)
    return (m.group(1), m.group(2).strip()) if m else ("?", name)


def call_ollama(prompt, model, timeout=900):
    payload = json.dumps({
        "model": model, "prompt": prompt, "system": SYSTEM,
        "format": "json", "stream": False,
        "think": False,  # 思考模型(qwen3.5等)关闭思考，答案进 response
        "options": {"temperature": 0.3, "top_p": 0.9, "num_ctx": 32768},
    }).encode("utf-8")
    req = urllib.request.Request(OLLAMA, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        result = json.loads(r.read().decode("utf-8"))
    return result.get("response", "") or result.get("thinking", "") or ""


def clean_json(s):
    s = s.strip()
    s = re.sub(r"^```(?:json)?\s*", "", s)
    s = re.sub(r"\s*```$", "", s)
    # 截取第一个 {...}
    i, j = s.find("{"), s.rfind("}")
    return s[i:j+1] if i >= 0 and j > i else s


def summarize(txt, model):
    num, title = parse_name(txt)
    text = open(txt, encoding="utf-8").read().strip()
    prompt = USER_TPL.format(title=title, text=text)
    raw = call_ollama(prompt, model)
    obj = json.loads(clean_json(raw))
    # 规范化 + 校验
    obj["集数"] = int(num) if num.isdigit() else num
    obj["标题"] = title
    obj.setdefault("一句话", "")
    obj.setdefault("要点", [])
    obj.setdefault("口诀", "")
    obj.setdefault("关键词", [])
    obj["要点"] = [str(x) for x in obj["要点"]][:6]
    obj["关键词"] = [str(x) for x in obj["关键词"]][:6]
    return obj


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("txt", nargs="?")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--model", default="qwen2.5:14b")
    ap.add_argument("--out", default=SUMDIR)
    ap.add_argument("--limit", type=int, default=0, help="只处理前N集(测试用)")
    ap.add_argument("--force", action="store_true", help="覆盖已存在的输出文件")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    if args.all:
        files = sorted(glob.glob(TD + "/*.fixed.txt"), key=lambda f: int(parse_name(f)[0]) if parse_name(f)[0].isdigit() else 999)
    elif args.txt:
        files = [args.txt]
    else:
        ap.error("请指定 txt 或 --all")
    if args.limit:
        files = files[:args.limit]
    ok = 0
    for f in files:
        num, title = parse_name(f)
        out = os.path.join(args.out, f"速记_{num}.json")
        if os.path.exists(out) and not args.txt and not args.force:
            print(f"跳过 {num}", flush=True); continue
        try:
            obj = summarize(f, args.model)
            with open(out, "w", encoding="utf-8") as fp:
                json.dump(obj, fp, ensure_ascii=False, indent=2)
            ok += 1
            print(f"[{num}] {obj['一句话'][:30]} | 要点{len(obj['要点'])}条", flush=True)
        except Exception as e:
            print(f"[{num}] 失败: {e}", flush=True)
    print(f"\n完成 {ok}/{len(files)} -> {args.out}")


if __name__ == "__main__":
    main()
