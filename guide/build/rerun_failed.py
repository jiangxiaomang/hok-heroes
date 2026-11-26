#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""补跑失败的精读集：用修好的检查逻辑（错字强制修 + 阈值放宽）重新生成并覆盖。"""
import os, sys, glob, time, json
BUILD = os.path.expanduser("~/hok-site/guide/build")
sys.path.insert(0, BUILD)
import asr_digest as D
import full_rerun_best as R

TARGETS = [30,33,37,40,45,53,56,57,59,61,62,66]  # 12份失败的精读集
MODEL = "qwen3.5:122b-a10b-ctx64"

files = {int(D.parse_name(f)[0]): f for f in glob.glob(D.TD + "/*.fixed.txt")}
logf = os.path.expanduser("~/hok-site/guide/build/_rerun_failed.log")
def log(m):
    line=f"[{time.strftime('%H:%M:%S')}] {m}"
    print(line, flush=True)
    open(logf,"a",encoding="utf-8").write(line+"\n")

log(f"===== 补跑 {len(TARGETS)} 份失败精读, 模型={MODEL} =====")
ok=fail=0
for num in TARGETS:
    txt=files.get(num)
    if not txt:
        log(f"精读_{num}: 找不到源文本, 跳过"); fail+=1; continue
    out=os.path.join(D.OUT, f"精读_{num}.json")
    log(f"--- 精读_{num} ---")
    try:
        obj=D.digest(txt, MODEL)  # digest 内已强制纠错 + 放宽退化阈值
        probs=R.check_obj(obj, "精读")
        if probs:
            log(f"  ⚠ 仍有硬伤: {probs} (保留旧文件)")
            fail+=1; continue
        json.dump(obj, open(out,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
        pts=sum(len(s.get("要点",[])) for s in obj.get("小节",[]))
        log(f"  ✅ 覆盖写入 精读_{num}.json ({pts}条)")
        ok+=1
    except Exception as e:
        log(f"  ❌ 异常: {e} (保留旧文件)")
        fail+=1
log(f"===== 补跑结束: 成功{ok} 失败{fail} =====")
