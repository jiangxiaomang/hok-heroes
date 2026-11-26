#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 B 站视频 BV 号提取 AI 字幕（主播说的话），输出带时间戳的文字稿。

用法:
    python3 bili_transcript.py BV1xx411c7mD
    python3 bili_transcript.py BV1xx411c7mD --json       # 输出JSON
    python3 bili_transcript.py BV1xx411c7mD --plain      # 纯文字（去掉时间戳）

依赖: 登录cookie文件 ~/Downloads/cookies (1).txt (含 SESSDATA)
"""
import sys, os, json, argparse, urllib.request, urllib.parse

COOKIE_FILE = os.path.expanduser("~/Downloads/cookies (1).txt")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36")


def load_cookie_header(path):
    """从 Netscape cookies.txt 读取 bilibili 相关 cookie，拼成 Cookie 请求头。"""
    pairs = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) >= 7 and "bilibili" in parts[0].lower():
                pairs.append((parts[5], parts[6]))
    # 去重（同名保留最后）
    d = dict(pairs)
    return "; ".join(f"{k}={v}" for k, v in d.items())


def http_get(url, cookie=None, referer="https://www.bilibili.com"):
    headers = {"User-Agent": UA, "Referer": referer}
    if cookie:
        headers["Cookie"] = cookie
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.read()


def get_aid_cid(bvid, cookie):
    """BV号 -> aid, cid, 标题"""
    url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
    d = json.loads(http_get(url, cookie))
    if d.get("code") != 0:
        raise RuntimeError(f"获取视频信息失败: {d.get('message')}")
    da = d["data"]
    return da["aid"], da["cid"], da.get("title", ""), da.get("owner", {}).get("name", "")


def get_subtitle(aid, cid, cookie):
    """aid/cid -> AI字幕 body 列表 [{from,to,content}...]"""
    url = f"https://api.bilibili.com/x/player/v2?aid={aid}&cid={cid}"
    d = json.loads(http_get(url, cookie))
    if d.get("code") != 0:
        raise RuntimeError(f"获取播放器信息失败: {d.get('message')}")
    subs = (d.get("data") or {}).get("subtitle", {}).get("subtitles", [])
    if not subs:
        return None, []
    # 优先 ai-zh，否则第一个
    pick = next((s for s in subs if s.get("lan") == "ai-zh"), subs[0])
    suburl = pick["subtitle_url"]
    if suburl.startswith("//"):
        suburl = "https:" + suburl
    # 字幕CDN是独立签名URL，带主站cookie反而可能被拒；直接请求即可
    body = json.loads(http_get(suburl, None)).get("body", [])
    return pick.get("lan"), body


def fmt_time(sec):
    sec = int(sec)
    return f"{sec//60:02d}:{sec%60:02d}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bvid", help="B站视频BV号，如 BV1xx411c7mD")
    ap.add_argument("--json", action="store_true", help="输出JSON")
    ap.add_argument("--plain", action="store_true", help="纯文字稿，无时间戳")
    ap.add_argument("--cookie", default=COOKIE_FILE, help="cookie文件路径")
    args = ap.parse_args()

    cookie = load_cookie_header(args.cookie)
    aid, cid, title, up = get_aid_cid(args.bvid, cookie)
    lan, body = get_subtitle(aid, cid, cookie)

    if args.json:
        print(json.dumps({"bvid": args.bvid, "title": title, "up": up,
                          "aid": aid, "cid": cid, "subtitle_lan": lan,
                          "body": body}, ensure_ascii=False, indent=2))
        return
    if not body:
        print(f"【{title}】UP主: {up} — 无字幕")
        return
    print(f"【{title}】UP主: {up} | 字幕: {lan} | 共 {len(body)} 句")
    print("-" * 50)
    for s in body:
        text = s.get("content", "")
        if args.plain:
            print(text)
        else:
            print(f"[{fmt_time(s.get('from',0))}] {text}")


if __name__ == "__main__":
    main()
