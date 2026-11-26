#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全量重跑后处理：对 140 份 JSON 做强制术语/幻觉修正 + 退化体检。
- 错字：直接文本替换（qwen3.5 偶发漏改）
- 退化重复：报告出来，需人工/重新生成
用法: python3 postcheck_fix.py [--fix]
"""
import os, json, sys
from collections import Counter

BASE = os.path.expanduser("~/Desktop/王者荣耀技巧图文")
FIX = {
    "点尾":"典韦","野和":"野核","公本":"宫本","时马一":"司马懿","司马一":"司马懿",
    "马亿":"司马懿","五泽天":"武则天","五折天":"武则天","五则天":"武则天",
    "名闻":"铭文","初号":"出装","椅和":"野核","野河":"野核","普刀":"普攻",
    "云中":"云中君","篮":"蓝",  # 注意：篮->蓝 可能影响"篮球"等，慎用
}
HALLU = ["字幕君","不吝点赞","订阅转发"]

def walk_obj(o, fn):
    """递归替换字符串中的错字，返回替换次数。"""
    cnt = Counter()
    def rec(x):
        if isinstance(x, str):
            for k,v in FIX.items():
                if k in x and not (k=="篮"):  # 篮单独跳过，避免误伤
                    n=x.count(k); x=x.replace(k,v); cnt[k]+=n
            return x
        if isinstance(x, list): return [rec(i) for i in x]
        if isinstance(x, dict): return {k:rec(v) for k,v in x.items()}
        return x
    return rec(o), cnt

def check_deg(obj, kind):
    pts=[]
    if kind=="精读":
        for sec in obj.get("小节",[]):
            pts += [str(x).strip() for x in sec.get("要点",[]) if str(x).strip()]
        if len(pts)<8: return f"条数过少{len(pts)}"
    else:
        pts = [str(x).strip() for x in obj.get("要点",[]) if str(x).strip()]
    c=Counter(pts)
    if c:
        top,n=c.most_common(1)[0]
        if n>=4 or (pts and n/len(pts)>0.25): return f"退化{n}/{len(pts)}"
    return None

def main():
    do_fix = "--fix" in sys.argv
    total_bad = 0
    for sub, kind in [("_精读JSON","精读"),("_速记JSON","速记")]:
        d=os.path.join(BASE,sub)
        for fn in sorted(os.listdir(d)):
            if not fn.endswith('.json') or fn.startswith('_'): continue
            p=os.path.join(d,fn)
            o=json.load(open(p,encoding='utf-8'))
            raw=json.dumps(o,ensure_ascii=False)
            hallu=[h for h in HALLU if h in raw]
            newo, cnt = walk_obj(o, fn)
            deg = check_deg(newo, kind)
            if cnt or hallu or deg:
                print(f"{fn}: 替换{dict(cnt)} 幻觉{hallu} {deg or ''}")
                total_bad+=1
                if do_fix and (cnt or hallu):
                    json.dump(newo, open(p,'w',encoding='utf-8'), ensure_ascii=False, indent=2)
                    print("   -> 已修正写回")
    print(f"\n合计需关注 {total_bad} 份" + ("(已修正错字)" if do_fix else "(加 --fix 执行修正)"))

if __name__=="__main__": main()
