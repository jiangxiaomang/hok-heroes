#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""《全英雄使用指南》数据校验：结构 + 口径禁项。"""
import json, re, sys, os
from collections import Counter

DATA = '/Users/analyst/hok-site/guide/data/heroes.json'
TAGS = {"位移","硬控","团控","免控","护盾","回复","真伤","爆发","持续输出","坦度","远程","手短",
        "吃经济","吃操作","抓人","反野","单带","推塔","前期强","后期强","保人","开团","消耗","拉扯",
        "切后排","无位移","怕控","怕集火","怕制裁","召唤物","变身","能量","法球","暴击","穿墙","隐身","全图支援"}
LANES = {"打野":30, "对抗路":32, "中路":29, "发育路":20, "游走":22}
DIFFS = {"易","中","难","极难"}
ROLES = {"战士","坦克","法师","刺客","射手","辅助"}
TEXT_FIELDS = ["feat","pros","cons","play","counter","weakto"]

# 禁止口径：胜率/梯度/版本号/赛季/价格/CD秒/ban率 等
BANNED = [
    (r"\d+\s*%", "百分比数值"),
    (r"\d+(\.\d+)?\s*胜率", "胜率"),
    (r"\bT[0-4]\b", "梯度T档"),
    (r"版本号|版本\s*\d", "版本号"),
    (r"赛季\s*\d|\bS\d{1,3}\b", "赛季号"),
    (r"出场率|ban\s*率|禁用率", "统计率"),
    (r"\d+\s*金币|金币价格|售价\s*\d", "装备价格"),
    (r"冷却\s*\d|\d+\s*秒", "技能CD秒数"),
    (r"待核", "未核实占位"),
    # sanitize 残留的符号瑕疵
    (r"[+＋]\s*[^=，,。；;]{0,4}", "残留加号"),
    (r"\(\s*\)|（\s*）|\(\s*[,，、]\s*\)|（\s*[，,、]\s*）", "空括号"),
]

def main():
    if not os.path.exists(DATA):
        print("FAIL: 数据文件不存在", DATA); return 1
    D = json.load(open(DATA, encoding="utf-8"))
    errs, warns = [], []

    # 1. 总数
    if len(D) != 133:
        errs.append(f"英雄总数应为 133，实际 {len(D)}")
    # 2. 分路
    lc = Counter(x.get("lane") for x in D)
    for lane, want in LANES.items():
        if lc.get(lane, 0) != want:
            errs.append(f"分路 {lane} 应为 {want}，实际 {lc.get(lane,0)}")
    for lane in lc:
        if lane not in LANES:
            errs.append(f"未知分路 {lane}")
    # 3. 名字唯一
    names = [x.get("n") for x in D]
    dup = [n for n,c in Counter(names).items() if c > 1]
    if dup: errs.append(f"英雄名重复: {dup}")
    # 4. 字段齐全与类型
    for x in D:
        for f in ["n","lane","alt","role","diff","feat","pros","cons","play","counter","weakto"]:
            if f not in x: errs.append(f"{x.get('n','?')} 缺字段 {f}")
        if x.get("role") not in ROLES: errs.append(f"{x.get('n')} role 非法: {x.get('role')}")
        if x.get("diff") not in DIFFS: errs.append(f"{x.get('n')} diff 非法: {x.get('diff')}")
        if not isinstance(x.get("tags"), list): errs.append(f"{x.get('n')} tags 非数组")
        for f in TEXT_FIELDS:
            v = x.get(f)
            if not isinstance(v, str) or not v.strip():
                errs.append(f"{x.get('n')} 文本字段 {f} 为空或非字符串")
        # tags 合法性 + 数量
        tags = x.get("tags") or []
        if not (3 <= len(tags) <= 5): errs.append(f"{x.get('n')} tags 数量 {len(tags)} 不在 3~5")
        for t in tags:
            if t not in TAGS: errs.append(f"{x.get('n')} 自造标签: {t}")
        # 文本长度
        for f in TEXT_FIELDS:
            v = x.get(f) or ""
            if not (10 <= len(v) <= 60):
                warns.append(f"{x.get('n')} {f} 长度 {len(v)} 偏离 15~45")
    # 5. 口径禁项扫描
    blob = json.dumps(D, ensure_ascii=False)
    for pat, label in BANNED:
        if label == "残留加号":
            continue
        hits = re.findall(pat, blob)
        if hits:
            errs.append(f"出现禁止内容[{label}]: {sorted(set(hits))[:5]}")
    # 5b. 逐字段：生成型字段不允许残留加号/空括号（play 为官方原文，不做此限制）
    for x in D:
        for f in ["feat", "pros", "cons", "counter", "weakto"]:
            v = x.get(f) or ""
            if re.search(r"[+＋]\s*(?!\d)", v):
                errs.append(f"{x.get('n')} {f} 残留孤立加号: {v}")
            if re.search(r"[（(]\s*[，,、]?\s*[)）]", v):
                errs.append(f"{x.get('n')} {f} 空括号: {v}")
    # 6. 嵌套双引号
    for x in D:
        for f in TEXT_FIELDS:
            if '"' in (x.get(f) or "") or "“" in (x.get(f) or ""):
                errs.append(f"{x.get('n')} {f} 含嵌套引号")
    # 7. 特点唯一性
    feat_c = Counter(x["feat"] for x in D)
    dupf = [f for f, c in feat_c.items() if c > 1]
    if dupf:
        errs.append(f"特点描述重复: {dupf[:5]}")

    print("=" * 60)
    print(f"英雄总数: {len(D)}   分路: {dict(lc)}")
    print(f"职业: {dict(Counter(x['role'] for x in D))}")
    print(f"难度: {dict(Counter(x['diff'] for x in D))}")
    print(f"标签使用数: {len({t for x in D for t in x['tags']})} / 词表 {len(TAGS)}")
    print(f"唯一特点数: {len({x['feat'] for x in D})}")
    print("-" * 60)
    if warns:
        print(f"警告 {len(warns)} 条:")
        for w in warns[:10]: print("  -", w)
    if errs:
        print(f"错误 {len(errs)} 条:")
        for e in errs[:40]: print("  -", e)
        print("=" * 60); print("校验失败"); return 1
    print("校验通过：0 错误")
    print("=" * 60)
    return 0

if __name__ == "__main__":
    sys.exit(main())
