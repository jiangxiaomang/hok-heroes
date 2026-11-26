#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按现有文件名规则重出70张速记卡（覆盖原文件，不产生重复）。"""
import os, sys, json, glob, asyncio, shutil
BUILD=os.path.expanduser("~/hok-site/guide/build")
sys.path.insert(0,BUILD)
import asr_quickcard as Q

BASE=os.path.expanduser("~/Desktop/王者荣耀技巧图文")
SUMDIR=os.path.join(BASE,"_速记JSON")
OUT=os.path.join(BASE,"_速记卡")
MAP=os.path.join(BASE,"_重命名回滚映射.json")

# 建立 集数 -> 现有文件名 的映射（从当前目录里的实际文件反推）
existing={}
for f in os.listdir(OUT):
    if not f.lower().endswith('.png'): continue
    # 两种格式：英雄名_速记第NNN期.png  或  速记NNN_标题.png
    import re
    m=re.search(r'第(\d{3})期',f) or re.search(r'^速记(\d{3})_',f)
    if m: existing[int(m.group(1))]=f
print(f"现有速记卡文件名映射: {len(existing)} 个")

loop=asyncio.new_event_loop()
ok=0
for jf in sorted(glob.glob(SUMDIR+"/速记_*.json")):
    o=json.load(open(jf,encoding='utf-8'))
    num=int(o['集数'])
    outname=existing.get(num) or f"速记{num:03d}_{str(o['标题']).replace('/','-')}.png"
    out=os.path.join(OUT,outname)
    loop.run_until_complete(Q.render(Q.build_html(o), out))
    ok+=1
    print(f"  重出 {outname}",flush=True)
print(f"完成: {ok} 张速记卡")
