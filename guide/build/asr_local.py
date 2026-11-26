#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本地视频批量转写：ffmpeg 提音频 + mlx_whisper ASR -> srt/txt/json。

用 mlx-audio 环境的 python 跑：
  /opt/homebrew/Caskroom/miniforge/base/envs/mlx-audio/bin/python \
    ~/hok-site/guide/build/asr_local.py <视频或目录> --model /tmp/hok_asr/models/whisper-medium

输出目录默认 <视频所在目录>/_transcripts/
断点续跑：已存在同名 .json 结果的跳过。
"""
import sys, os, glob, json, argparse, subprocess, time

MODEL_DEFAULT = os.path.expanduser("~/models/whisper-medium")


def extract_wav(video, wav_path):
    subprocess.run([
        "ffmpeg", "-y", "-i", video, "-vn", "-ac", "1", "-ar", "16000",
        "-c:a", "pcm_s16le", wav_path
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)


def fmt_srt_time(sec):
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    ms = int((sec - int(sec)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_outputs(result, base):
    segs = result.get("segments", [])
    # json
    with open(base + ".json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    # srt
    with open(base + ".srt", "w", encoding="utf-8") as f:
        for i, s in enumerate(segs, 1):
            f.write(f"{i}\n{fmt_srt_time(s['start'])} --> {fmt_srt_time(s['end'])}\n")
            f.write(s["text"].strip() + "\n\n")
    # txt
    with open(base + ".txt", "w", encoding="utf-8") as f:
        f.write("\n".join(s["text"].strip() for s in segs))


def transcribe_one(video, outdir, model, mlx_whisper, keep_wav=False):
    name = os.path.splitext(os.path.basename(video))[0]
    base = os.path.join(outdir, name)
    if os.path.exists(base + ".json"):
        print(f"[跳过] {name}（已有结果）", flush=True)
        return True
    wav = os.path.join(outdir, "_tmp.wav")
    try:
        extract_wav(video, wav)
        t0 = time.time()
        result = mlx_whisper.transcribe(wav, path_or_hf_repo=model,
                                        language="zh", verbose=False)
        write_outputs(result, base)
        dt = time.time() - t0
        print(f"[完成] {name} — {len(result.get('segments',[]))} 段 / {dt:.1f}s", flush=True)
        return True
    except Exception as e:
        print(f"[失败] {name}: {e}", flush=True)
        return False
    finally:
        if not keep_wav and os.path.exists(wav):
            os.remove(wav)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", help="视频文件或包含视频的目录")
    ap.add_argument("--model", default=MODEL_DEFAULT, help="本地whisper模型路径")
    ap.add_argument("--outdir", default=None, help="输出目录，默认<目录>/_transcripts")
    ap.add_argument("--limit", type=int, default=0, help="最多处理N个（0=全部）")
    args = ap.parse_args()

    import mlx_whisper  # 延迟导入

    if os.path.isfile(args.input):
        videos = [args.input]
        outdir = args.outdir or os.path.join(os.path.dirname(args.input), "_transcripts")
    else:
        videos = sorted(glob.glob(os.path.join(args.input, "*.mp4")))
        outdir = args.outdir or os.path.join(args.input, "_transcripts")
    os.makedirs(outdir, exist_ok=True)
    if args.limit:
        videos = videos[:args.limit]

    print(f"共 {len(videos)} 个视频，输出目录: {outdir}", flush=True)
    ok = fail = 0
    for v in videos:
        if transcribe_one(v, outdir, args.model, mlx_whisper):
            ok += 1
        else:
            fail += 1
    print(f"完成: 成功 {ok} / 失败 {fail}", flush=True)


if __name__ == "__main__":
    main()
