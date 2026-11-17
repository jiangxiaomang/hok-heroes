#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 /tmp/hok_cards_final 里重渲染的 jpg 覆盖回项目 images/ 目录。
文件名映射：<英雄>_<分路>速查卡.jpg / 精华卡.jpg -> guide/heroes/<英雄>_<分路>/images/
"""
import os, glob, shutil

SRC = "/tmp/hok_cards_final"
DST_ROOT = os.path.expanduser("~/hok-site/guide/heroes")


def main():
    copied = 0
    missing = []
    for kind in ("quick", "mini"):
        for img in sorted(glob.glob(os.path.join(SRC, kind, "*.jpg"))):
            base = os.path.basename(img)[:-len(".jpg")]   # 黄忠_发育路速查卡
            # 从后缀反推英雄目录名：去掉 速查卡/精华卡
            hero_dir = None
            for suf in ("速查卡", "精华卡"):
                if base.endswith(suf):
                    hero_dir = base[:-len(suf)]
                    break
            if not hero_dir:
                missing.append(base)
                continue
            target_dir = os.path.join(DST_ROOT, hero_dir, "images")
            if not os.path.isdir(target_dir):
                missing.append(base)
                continue
            shutil.copy2(img, os.path.join(target_dir, os.path.basename(img)))
            copied += 1
    print("已覆盖回项目 %d 张 jpg" % copied)
    if missing:
        print("警告 未找到目标:", missing)


if __name__ == "__main__":
    main()
