#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用本地 Ollama 把 ASR 文字稿整理成"精读笔记"JSON（保留全部细节，带标点/分节/编号）。

输出: {"小节":[{"标题":"...","要点":["带标点完整句",...]}]}
用法: python3 asr_digest.py <txt> [--out]  或 --all
"""
import os, sys, glob, json, re, argparse, urllib.request
from collections import Counter

TD = os.path.expanduser("~/Desktop/百度下载/S44-零基础到百段野核教科书（百期连更通用/_transcripts")
OUT = os.path.expanduser("~/Desktop/王者荣耀技巧图文/_精读JSON")
OLLAMA = "http://127.0.0.1:11434/api/generate"

SYSTEM = """你是王者荣耀打野教学的资深内容编辑。下面是一段教学视频的语音转文字稿（逐句口语、无标点、有ASR错别字）。
请把它整理成"精读笔记"：保留全部教学干货和细节（不要压缩、不丢信息点），但让它条理清晰、带标点、分小节、编号、合并重复啰嗦的口语。

规则：
1. 【去口水话】删掉"点赞关注、五星好评、下期见、兄弟们"等口播套话；合并"这个、就是、那么、然后"等口头禅。
2. 【纠错】结合王者语境纠正同音错字：编路=边路、单代=单带、敏玥=芈月、暗信=李信暗影形态、铝布=吕布、老福子=老夫子、司空阵=司空震、吃惊劲=吃经济、槽里=草里、核=核心、也兴=弈星、椅和=野核、带空=带控制、名闻=铭文、初号=出装、十音眼=10鹰眼、十红月=10红月、十祸源=10祸源、毫升雷两多岁=10鹰眼10红月、副化=复活、名刀=名刀、毅力不倒=屹立不倒、善面型=善面型（普攻类型）、普刀=普攻。英雄名必须正确。
3. 【分小节】按内容主题分成2-6个小节，每节起一个简短小标题（≤14字）。把讲同一类事物/相似的内容归到同一节（这就是"相似内容整合"）。
4. 【编号要点·关键】每节内用编号列表，每条只讲一个独立信息点，长度≤45字（宁可多拆几条也不要长句）。绝不允许把多个不同操作/装备/技能塞进同一条——例如出装顺序要拆成"出门装…""核心装…""后期装…"多条，操作设置每个开关单独一条。每条是带标点的完整句子，保留具体英雄名、数值、时机、动作。每节通常5-15条。
5. 严格保留原文所有实质信息点，宁可条目多一点，也不要遗漏或概括掉细节。**任何一条如果超过45字，必须拆成多条。**
6. 【严禁复制循环】同一句话/同一信息点最多出现一次。绝对禁止把同一句复制粘贴多次来凑数，即使原文有口吃或重复也要合并成一条。

输出严格JSON（不要markdown代码块、不要任何多余文字）：
{"小节":[{"标题":"小节标题","要点":["带标点的完整句子1","句子2"]}]}"""


def parse_name(fname):
    name = os.path.basename(fname).replace(".fixed.txt", "")
    m = re.match(r"【(\d+)】(.+?)\s*\[(\d+)\]", name)
    return (m.group(1), m.group(2).strip()) if m else ("?", name)


def parse_robust_json(s):
    """容错解析 LLM 输出：去除代码块标记、修复未闭合字符串/尾逗号/截断结构。"""
    s = s.strip()
    s = re.sub(r"^```(?:json)?\s*", "", s)
    s = re.sub(r"\s*```$", "", s)
    i, j = s.find("{"), s.rfind("}")
    s = s[i:j+1] if i >= 0 and j > i else s
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass
    # 修复1：去掉尾逗号 (, } 或 , ])
    s2 = re.sub(r",\s*([}\]])", r"\1", s)
    try:
        return json.loads(s2)
    except json.JSONDecodeError:
        pass
    # 修复2：截断的 JSON —— 尝试逐步回退到最后一个完整的要点，补齐括号
    # 若是字符串中途截断，截到最后一个引号并补齐
    if s2.count('"') % 2 == 1:
        s2 = s2[:s2.rfind('"')]
    # 移除尾部不完整片段（最后一段要点）
    for _ in range(30):
        try:
            return json.loads(s2)
        except json.JSONDecodeError:
            # 回退：删掉最后一个逗号及其后内容，或补括号
            k = s2.rfind(',')
            if k > s2.rfind('{'):
                s2 = s2[:k] + s2[s2.find('[', k):] if '[' in s2[k:] else s2[:k]
            # 补闭合
            cand = s2
            opens = cand.count('[') - cand.count(']')
            opend = cand.count('{') - cand.count('}')
            cand = cand.rstrip()
            if cand and cand[-1] in ':,': cand = cand[:-1]
            cand += ']' * max(0, opens) + '}' * max(0, opend)
            try:
                return json.loads(cand)
            except json.JSONDecodeError:
                s2 = s2[:k] if k > 0 else s2[:-1]
                if not s2: break
    # 兜底：正则逐节提取（应对 qwen3.5 偶发输出结构错乱，如小节缺 {} 包裹）
    secs = []
    for m in re.finditer(r'"标题"\s*:\s*"([^"]*)"\s*,\s*"要点"\s*:\s*\[(.*?)\]', s, re.S):
        title = m.group(1)
        pts = re.findall(r'"((?:[^"\\]|\\.)*)"', m.group(2))
        pts = [json.loads('"' + p + '"') for p in pts]  # 还原转义
        if pts:
            secs.append({"标题": title, "要点": pts})
    if secs:
        return {"小节": secs}
    raise ValueError("JSON无法修复")


def fold_repeats(text):
    """折叠 ASR 幻觉循环：连续重复行 + 行内连续重复短语，避免触发 LLM 复制退化。"""
    # 1) 连续完全相同的行只保留一行
    out = []
    for ln in text.split("\n"):
        s = ln.strip()
        if s and out and s == out[-1].strip():
            continue
        out.append(ln)
    text = "\n".join(out)
    # 2) 行内同一片段连续出现≥3次 → 折叠成 1 次（如"看对面不敢出来"x5）
    for _ in range(4):
        prev = text
        text = re.sub(r"(.{2,16}?)\1{2,}", r"\1", text)
        if text == prev:
            break
    return text


# 输出错字强制替换表（qwen3.5 稳定复现的 ASR 同音错字，写回前兜底）
OUT_FIX = {
    "点尾":"典韦","野和":"野核","公本":"宫本","时马一":"司马懿","司马一":"司马懿",
    "马亿":"司马懿","五泽天":"武则天","五折天":"武则天","五则天":"武则天",
    "名闻":"铭文","初号":"出装","椅和":"野核","野河":"野核","普刀":"普攻",
    "马亿":"司马懿","孙悟控":"孙悟空",
}

def fix_obj_typos(obj: dict) -> tuple:
    """递归替换对象内所有字符串中的错字，返回替换计数。"""
    cnt = Counter()
    def rec(x):
        if isinstance(x, str):
            for k, v in OUT_FIX.items():
                if k in x:
                    cnt[k] += x.count(k)
                    x = x.replace(k, v)
            return x
        if isinstance(x, list):
            return [rec(i) for i in x]
        if isinstance(x, dict):
            return {k: rec(v) for k, v in x.items()}
        return x
    return rec(obj), cnt


def is_degenerate(obj, verbose=False):
    """检测 LLM 输出是否陷入复制循环（同一句反复出现）。"""
    pts = []
    for sec in obj.get("小节", []):
        pts += [str(x).strip() for x in sec.get("要点", []) if str(x).strip()]
    if len(pts) < 5:
        if verbose: print(f"    [退化检测] 总条数仅 {len(pts)} <5", flush=True)
        return True
    top, n = Counter(pts).most_common(1)[0]
    # 只用重复占比判定退化；绝对次数阈值要对长文本宽松（380条里重复4次是正常的）
    deg = n / len(pts) > 0.20 and n >= 5
    if verbose and deg:
        print(f"    [退化检测] 最高频句 {n}/{len(pts)} ({n/len(pts):.0%}): {top[:30]}", flush=True)
    return deg


def digest(txt, model):
    num, title = parse_name(txt)
    text = open(txt, encoding="utf-8").read().strip()
    # 源文本预处理：修高频ASR错字，避免LLM拿到离谱错字无法还原
    SRC_FIX = {
        "名闻": "铭文", "初号": "出装", "初号顺序": "出装顺序", "十音眼": "10鹰眼",
        "十红月": "10红月", "十祸源": "10祸源", "初号名闻": "出装铭文",
        "毫升雷两多岁": "10鹰眼10红月", "副化假": "复活甲", "副化": "复活",
        "毅力不倒": "屹立不倒", "普刀": "普攻", "一横": "野核", "椅和": "野核",
        "野河": "野核", "百段一横": "百段野核", "单带发育路线": "单带发育路线",
    }
    for k, v in SRC_FIX.items():
        text = text.replace(k, v)
    text = fold_repeats(text)  # 折叠ASR循环，从源头掐断复制触发
    import time as _t
    # 重试参数轮换：逐步加大重复惩罚，抑制退化；思考模型统一 think:false
    schedule = [
        {"temperature": 0.3, "top_p": 0.9},
    ]
    last_err = None
    obj = None
    for attempt, param in enumerate(schedule):
        # 每次重试重建 payload（原脚本 bug：payload 在循环外，重试发完全相同的请求）
        body = {
            "model": model, "prompt": text, "system": SYSTEM, "format": "json",
            "stream": False,
            "think": False,  # qwen3.5/gpt-oss 等思考模型：关闭思考，答案进 response
            "options": {"num_ctx": 32768, "num_predict": 8192, **param},
        }
        payload = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(OLLAMA, data=payload, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=900) as r:
                result = json.loads(r.read().decode("utf-8"))
            # 思考模型兼容：优先 response，空则取 thinking
            resp = result.get("response", "") or result.get("thinking", "") or ""
            cand = parse_robust_json(resp)
            if is_degenerate(cand, verbose=True):
                last_err = f"attempt{attempt} 输出退化"
                print(f"  [{num}] attempt{attempt} 退化，加大惩罚重试...", flush=True)
                _t.sleep(1)
                continue
            obj = cand
            if attempt:
                print(f"  [{num}] attempt{attempt} 通过", flush=True)
            break
        except Exception as e:
            last_err = str(e)
            print(f"  [{num}] attempt{attempt} 异常: {e}", flush=True)
            _t.sleep(2)
    if obj is None:
        raise ValueError(f"生成失败/持续退化: {last_err}")
    obj, fixed = fix_obj_typos(obj)  # 写回前强制纠正稳定复现的 ASR 错字
    if fixed:
        print(f"  [{num}] 输出纠错: {dict(fixed)}", flush=True)
    for sec in obj.get("小节", []):
        sec["要点"] = [str(x) for x in sec.get("要点", [])]
    obj["集数"] = int(num) if num.isdigit() else num
    obj["标题"] = title
    return obj


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("txt", nargs="?")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--model", default="qwen2.5:14b")
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--limit", type=int, default=0)
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
        num, _ = parse_name(f)
        out = os.path.join(args.out, f"精读_{num}.json")
        if os.path.exists(out) and not args.force:
            print(f"跳过 {num}", flush=True); continue
        try:
            obj = digest(f, args.model)
            json.dump(obj, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
            ok += 1
            n = sum(len(s["要点"]) for s in obj["小节"])
            print(f"[{num}] {len(obj['小节'])}节/{n}条 | {obj['标题'][:20]}", flush=True)
        except Exception as e:
            print(f"[{num}] 失败: {e}", flush=True)
    print(f"\n完成 {ok}/{len(files)} -> {args.out}")


if __name__ == "__main__":
    main()
