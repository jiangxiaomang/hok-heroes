#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""重转ASR幻觉污染的集：关闭上下文依赖 + initial_prompt 引导，防止幻觉滚雪球。"""
import os, glob, json, subprocess, time

BASE = os.path.expanduser("~/Desktop/百度下载/S44-零基础到百段野核教科书（百期连更通用")
TD = BASE + "/_transcripts"
MODEL = os.path.expanduser("~/models/whisper-medium")
PROMPT = "以下是王者荣耀打野教学视频的普通话讲解，内容涉及打野、兵线、河道、野区、反蹲、出装、铭文、核心、节奏。"

NUMS = ["003", "065", "067"]


def fmt_srt(t):
    h=int(t//3600);m=int((t%3600)//60);s=int(t%60);ms=int((t-int(t))*1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def main():
    import mlx_whisper
    for num in NUMS:
        vids = glob.glob(f"{BASE}/【{num}】*.mp4")
        if not vids:
            print(f"[跳过] {num} 无视频"); continue
        v = vids[0]
        name = os.path.splitext(os.path.basename(v))[0]
        wav = f"/tmp/hok_asr/re_{num}.wav"
        print(f"\n=== 重转 {num}: {name} ===", flush=True)
        subprocess.run(["ffmpeg","-y","-i",v,"-vn","-ac","1","-ar","16000","-c:a","pcm_s16le",wav],
                       stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True)
        t0=time.time()
        result = mlx_whisper.transcribe(
            wav, path_or_hf_repo=MODEL, language="zh", verbose=False,
            condition_on_previous_text=False,   # 关键：切断幻觉滚雪球
            initial_prompt=PROMPT,
            temperature=0.0,
        )
        segs=[s for s in result["segments"] if s.get("text","").strip()]
        # 写出三件套（覆盖原 .fixed 之前的原始文件也要覆盖）
        base=os.path.join(TD,name)
        with open(base+".json","w",encoding="utf-8") as f: json.dump(result,f,ensure_ascii=False,indent=2)
        with open(base+".srt","w",encoding="utf-8") as f:
            for i,s in enumerate(segs,1):
                f.write(f"{i}\n{fmt_srt(s['start'])} --> {fmt_srt(s['end'])}\n{s['text'].strip()}\n\n")
        with open(base+".txt","w",encoding="utf-8") as f:
            f.write("\n".join(s["text"].strip() for s in segs))
        print(f"[完成] {len(segs)}段 / {time.time()-t0:.1f}s | 首句: {segs[0]['text'][:40] if segs else '空'}",flush=True)
        os.remove(wav)


if __name__=="__main__":
    main()
