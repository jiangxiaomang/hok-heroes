#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全量用最强模型 qwen3.5:122b 重生成 70 精读 + 70 速记 JSON。
串行处理（Ollama 单实例），每份生成后立即体检，退化/失败自动重试一次。
日志追加到 _full_rerun.log。"""
import os, sys, glob, json, time, traceback
from collections import Counter

BUILD = os.path.expanduser("~/hok-site/guide/build")
sys.path.insert(0, BUILD)
import asr_digest as D
import asr_summarize as S

TD = D.TD
MODEL = "qwen3.5:122b-a10b-ctx64"
LOG = os.path.expanduser("~/hok-site/guide/build/_full_rerun.log")

# 错字黑名单（生成后校验）
TYPO = {
    "点尾":"典韦","野和":"野核","公本":"宫本","时马一":"司马懿","司马一":"司马懿",
    "马亿":"司马懿","五泽天":"武则天","五折天":"武则天","五则天":"武则天",
    "名闻":"铭文","初号":"出装","椅和":"野核","野河":"野核","普刀":"普攻",
}
HALLU = ["字幕君","不吝点赞","订阅转发"]


def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def check_obj(obj, kind):
    """返回问题列表（空=通过）。错字已由 digest 强制修正，这里只兜底检测。"""
    probs = []
    raw = json.dumps(obj, ensure_ascii=False)
    # 错字兜底（digest 已修，若仍出现说明是速记等未经强制修正的路径）
    for t, corr in TYPO.items():
        n = raw.count(t)
        if n:
            obj2 = json.loads(json.dumps(obj))
            obj2, _ = D.fix_obj_typos(obj2)
            obj.clear(); obj.update(obj2)
            probs.append(f"错字{t}->{corr}x{n}(已修)")
    for h in HALLU:
        if h in raw: probs.append(f"幻觉{h}")
    if kind == "精读":
        pts = []
        for sec in obj.get("小节", []):
            pts += [str(x).strip() for x in sec.get("要点", []) if str(x).strip()]
        if len(pts) < 5:
            probs.append(f"条数过少{len(pts)}")
        c = Counter(pts)
        if c and len(pts) >= 5:
            top, n = c.most_common(1)[0]
            if n / len(pts) > 0.20 and n >= 5:
                probs.append(f"退化重复{n}/{len(pts)}")
        # 超长条仅提示，不作为失败理由（内容详尽的集允许长条）
        longp = [p for p in pts if len(p) > 100]
        if longp: probs.append(f"超长条{len(longp)}")
    else:
        pts = [str(x).strip() for x in obj.get("要点", []) if str(x).strip()]
        if not (3 <= len(pts) <= 6): probs.append(f"要点数{len(pts)}不在3-6")
        c = Counter(pts)
        if c and c.most_common(1)[0][1] >= 3: probs.append("要点全重复")
    # 只把真正的硬伤（幻觉/退化/条数过少/要点数错）当失败；错字已修、超长已放宽
    hard = [p for p in probs if "已修" not in p and "超长条" not in p]
    return hard


def gen_with_retry(txt, kind):
    """生成 + 体检 + 最多2次重试。"""
    last = None
    for attempt in range(3):
        try:
            if kind == "精读":
                obj = D.digest(txt, MODEL)
            else:
                obj = S.summarize(txt, MODEL)
            probs = check_obj(obj, kind)
            if not probs:
                return obj, []
            last = "体检不过: " + ", ".join(probs)
            log(f"    ⚠ attempt{attempt} 体检不过: {probs}")
        except Exception as e:
            last = f"异常: {e}"
            log(f"    ⚠ attempt{attempt} 异常: {e}")
        time.sleep(3)
    return None, last


def main():
    files = sorted(glob.glob(TD + "/*.fixed.txt"),
                   key=lambda f: int(D.parse_name(f)[0]) if D.parse_name(f)[0].isdigit() else 999)
    # 续跑模式：只处理 mtime 早于 cutoff（即本轮尚未生成）的文件
    CUTOFF = os.environ.get("RERUN_CUTOFF", "")
    cutoff_ts = float(CUTOFF) if CUTOFF else 0
    log(f"===== 全量重跑(续): {len(files)}集, cutoff={CUTOFF}, 模型={MODEL} =====")
    ok = fail = skip = 0
    failed_list = []
    for i, f in enumerate(files, 1):
        num, title = D.parse_name(f)
        for kind in ["精读", "速记"]:
            outdir = D.OUT if kind == "精读" else S.SUMDIR
            out = os.path.join(outdir, f"{kind}_{num}.json")
            if cutoff_ts and os.path.exists(out) and os.path.getmtime(out) >= cutoff_ts:
                skip += 1
                continue
            log(f"[{i:02d}/{len(files)}] {kind}_{num} {title[:24]}")
            obj, err = gen_with_retry(f, kind)
            if obj is None:
                fail += 1
                failed_list.append(f"{kind}_{num}: {err}")
                log(f"    ❌ 失败（保留旧文件）: {err}")
            else:
                with open(out, "w", encoding="utf-8") as fp:
                    json.dump(obj, fp, ensure_ascii=False, indent=2)
                ok += 1
                n = sum(len(s["要点"]) for s in obj.get("小节", [])) if kind == "精读" else len(obj.get("要点", []))
                log(f"    ✅ 写入 {kind}_{num}.json ({n}条)")
    skip_msg = f" 跳过{skip}" if skip else ""
    log(f"===== 全量重跑结束: 成功{ok} 失败{fail}{skip_msg} =====")
    if failed_list:
        log("失败清单:")
        for x in failed_list: log("  " + x)


if __name__ == "__main__":
    main()
