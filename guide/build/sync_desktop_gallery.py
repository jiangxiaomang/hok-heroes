#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 hok-site 项目里的英雄图片，真实复制到桌面图片库（方便随时复制分享）。
默认 copy 模式：复制真实文件，覆盖旧文件，按分路分类。
可选 --link 模式：改回符号链接（真源在项目里，不占空间，但不适合分享）。

用法：
    python3 sync_desktop_gallery.py            # 真实复制（默认）
    python3 sync_desktop_gallery.py --link     # 符号链接模式
"""
import os
import sys
import glob
import shutil

SRC_ROOT = os.path.expanduser("~/hok-site/guide/heroes")
DST_ROOT = os.path.expanduser("~/Desktop/王者荣耀图片库")
LANES = ["对抗路", "打野", "中路", "游走", "发育路"]
MODE = "--link" if "--link" in sys.argv else "copy"


def main():
    if not os.path.isdir(SRC_ROOT):
        raise SystemExit("找不到项目图片源目录: " + SRC_ROOT)
    os.makedirs(DST_ROOT, exist_ok=True)
    for lane in LANES:
        os.makedirs(os.path.join(DST_ROOT, lane), exist_ok=True)

    count = 0
    for hero_dir in sorted(glob.glob(os.path.join(SRC_ROOT, "*"))):
        if not os.path.isdir(hero_dir):
            continue
        lane = os.path.basename(hero_dir).rsplit("_", 1)[-1]
        if lane not in LANES:
            continue
        for img in sorted(glob.glob(os.path.join(hero_dir, "images", "*.jpg"))):
            name = os.path.basename(img)
            dst = os.path.join(DST_ROOT, lane, name)
            # 先清掉可能存在的旧链接/旧文件，保证落地的是真实文件
            if os.path.islink(dst) or os.path.exists(dst):
                os.remove(dst)
            if MODE == "link":
                os.symlink(img, dst)
            else:
                shutil.copy2(img, dst)
            count += 1

    mode_cn = "符号链接" if MODE == "link" else "真实文件"
    print("同步完成：%d 张图片（%s）→ %s" % (count, mode_cn, DST_ROOT))


if __name__ == "__main__":
    main()
