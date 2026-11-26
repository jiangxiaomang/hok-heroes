#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ASR文字稿术语纠正：把Whisper谐音错字替换为王者荣耀正确术语。

只做高置信度替换，宁可漏改不可错改（用户对数据真实性零容忍）。
支持 txt / srt / json 三种格式保持一致。
用法:
  python3 asr_fix_terms.py <txt/srt/json文件或目录>    # 生成 .fixed.<ext>
  python3 asr_fix_terms.py <目录> --report <报告路径>   # 导出替换报告供核对
  python3 asr_fix_terms.py <目录> --inplace            # 原地覆盖
"""
import sys, os, glob, argparse, json

# 常用繁体->简体映射（whisper偶发繁体输出，如第5集）
T2S = {
    "這": "这", "們": "们", "時": "时", "後": "后", "說": "说", "會": "会",
    "經": "经", "對": "对", "開": "开", "關": "关", "發": "发", "現": "现",
    "問": "问", "際": "际", "點": "点", "無": "无", "為": "为", "與": "与",
    "從": "从", "過": "过", "還": "还", "兩": "两", "樣": "样", "將": "将",
    "於": "于", "當": "当", "種": "种", "沒": "没", "嗎": "吗", "麼": "么",
    "稱": "称", "個": "个", "來": "来", "實": "实", "戰": "战", "經": "经",
    "驗": "验", "練": "练", "習": "习", "習": "习", "頭": "头", "線": "线",
    "強": "强", "隻": "只", "進": "进", "遠": "远", "近": "近", "長": "长",
    "間": "间", "題": "题", "規": "规", "劃": "划", "營": "营", "運": "运",
    "動": "动", "靜": "静", "勝": "胜", "敗": "败", "關": "关", "擊": "击",
    "殺": "杀", "傷": "伤", "護": "护", "輔": "辅", "助": "助", "幫": "帮",
    "線": "线", "級": "级", "數": "数", "據": "据", "斷": "断", "續": "续",
    "頻": "频", "視": "视", "覺": "觉", "邊": "边", "際": "际", "預": "预",
    "測": "测", "調": "调", "整": "整", "準": "准", "確": "确", "誤": "误",
    "錯": "错", "導": "导", "異": "异", "聯": "联", "繫": "系", "決": "决",
    "策": "策", "響": "响", "變": "变", "態": "态", "勢": "势", "優": "优",
    "劣": "劣", "勢": "势", "職": "职", "業": "业", "餘": "余",
    # 补全：实际文字稿中出现的繁体字
    "並": "并", "佈": "布", "內": "内", "區": "区", "幾": "几",
    "應": "应", "環": "环", "節": "节", "給": "给", "統": "统",
    "緊": "紧", "裡": "里", "該": "该", "質": "质", "車": "车",
    "連": "连", "銜": "衔", "鍵": "键", "馬": "马", "魚": "鱼",
    "濟": "济", "歡": "欢", "東": "东", "壯": "壮", "線": "线",
    "準": "准", "則": "则", "別": "别", "到": "到", "辦": "办",
}

# 高置信度谐音错字 -> 正确术语（均为多字，避免误伤）
TERMS = {
    "白段野和": "百段野核",
    "白段": "百段",
    "野核客": "野核教科书", "野和客": "野核教科书",
    "野和教科书": "野核教科书",
    "野和": "野核",
    "核道": "河道",
    "核蟹": "河蟹",
    "冰线": "兵线",
    "冰線": "兵线",
    "易兴": "弈星",
    "王昭军": "王昭君", "莫子": "墨子", "晚峰": "晚风", "晚風": "晚风",
    "姜紫牙": "姜子牙",
    "金禅": "金蝉",
    "真姬": "甄姬",
    "亥月": "海月",
    "高健尼": "高渐离",
    "查落补缺": "查漏补缺",
    "四及线": "四级线",
    "前期小张强度": "前期作战强度",
}

# 上下文精确规则（含单字纠正，但限定完整短语）
CONTEXT_RULES = [
    ("的核取得", "的核心取得"),
    ("这个核", "这个核心"),
    ("一个核", "一个核心"),
    ("其他的核", "其他的核心"),
    ("帮其他的核", "帮其他的核心"),
]


def fix_text(s):
    report = []
    # 先做繁->简（whisper偶发繁体输出）
    trad_hits = 0
    for a, b in T2S.items():
        n = s.count(a)
        if n:
            trad_hits += n
            s = s.replace(a, b)
    if trad_hits:
        report.append(("繁体转简体", "-", trad_hits))
    for a, b in CONTEXT_RULES:
        n = s.count(a)
        if n:
            report.append((a, b, n))
            s = s.replace(a, b)
    for a in sorted(TERMS, key=len, reverse=True):
        b = TERMS[a]
        n = s.count(a)
        if n:
            report.append((a, b, n))
            s = s.replace(a, b)
    return s, report


def fix_file(f, inplace):
    """处理单个文件，返回替换报告。"""
    ext = os.path.splitext(f)[1].lower()
    with open(f, encoding="utf-8") as fh:
        raw = fh.read()
    if ext == ".json":
        try:
            obj = json.loads(raw)
        except Exception:
            obj = None
        if obj is not None:
            def walk(o):
                if isinstance(o, str):
                    return fix_text(o)[0]
                if isinstance(o, dict):
                    return {k: walk(v) for k, v in o.items()}
                if isinstance(o, list):
                    return [walk(x) for x in o]
                return o
            fixed_obj = walk(obj)
            _, report = fix_text(raw)
            out = f if inplace else f[:-5] + ".fixed.json"
            with open(out, "w", encoding="utf-8") as fh:
                json.dump(fixed_obj, fh, ensure_ascii=False, indent=2)
            return report
    fixed, report = fix_text(raw)
    out = f if inplace else os.path.splitext(f)[0] + ".fixed" + ext
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(fixed)
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", help="txt/srt/json文件或目录")
    ap.add_argument("--report", default=None, help="导出替换报告JSON供人工核对")
    ap.add_argument("--inplace", action="store_true", help="原地覆盖（默认生成.fixed文件）")
    args = ap.parse_args()

    if os.path.isfile(args.input):
        files = [args.input]
    else:
        files = []
        for ext in ("*.txt", "*.srt", "*.json"):
            files += glob.glob(os.path.join(args.input, ext))
        files = [f for f in files if ".fixed." not in os.path.basename(f)]

    all_report = {}
    for f in sorted(files):
        report = fix_file(f, args.inplace)
        if report:
            all_report[os.path.basename(f)] = report
            print(f"{os.path.basename(f)}: {sum(r[2] for r in report)} 处替换")
    print(f"处理 {len(files)} 个文件，{len(all_report)} 个有替换")

    if args.report:
        with open(args.report, "w", encoding="utf-8") as fh:
            json.dump(all_report, fh, ensure_ascii=False, indent=2)
        print(f"替换报告: {args.report}")


if __name__ == "__main__":
    main()
