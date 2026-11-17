#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 guide/cards/ 里重建好的速查卡 html/md 精准覆盖到 guide/heroes/<英雄>/，
只更新「速查卡.html / 速查卡.md」两类文件，绝不删除或改动图片、完整攻略、
精华卡、index.html 等其他内容（避免 build_hero_dirs.py 的 rmtree 误删图片）。
"""
import os
import glob
import shutil

ROOT = os.path.expanduser("~/hok-site/guide")
SRC = os.path.join(ROOT, "cards")
DST = os.path.join(ROOT, "heroes")


def main():
    htmls = sorted(glob.glob(os.path.join(SRC, "*速查卡.html")))
    copied = 0
    missing = []
    for h in htmls:
        base = os.path.basename(h)[:-len(".html")]      # 黄忠_发育路速查卡
        hero_dir_name = base[:-len("速查卡")]            # 黄忠_发育路
        target_dir = os.path.join(DST, hero_dir_name)
        if not os.path.isdir(target_dir):
            missing.append(hero_dir_name)
            continue
        # HTML
        shutil.copy2(h, os.path.join(target_dir, base + ".html"))
        # MD
        md_src = os.path.join(SRC, base + ".md")
        if os.path.exists(md_src):
            shutil.copy2(md_src, os.path.join(target_dir, base + ".md"))
        copied += 1
    # 聚合文件
    for fn in ("cards_all.html", "cards.md", "index.html"):
        s = os.path.join(SRC, fn)
        if os.path.exists(s):
            shutil.copy2(s, os.path.join(DST, fn))
    # 精华卡 HTML：guide/cards_mini/<英雄>精华卡.html -> heroes/<英雄>/
    mini_src = os.path.join(ROOT, "cards_mini")
    mini_copied = 0
    if os.path.isdir(mini_src):
        for m in sorted(glob.glob(os.path.join(mini_src, "*精华卡.html"))):
            base = os.path.basename(m)[:-len(".html")]      # 黄忠_发育路精华卡
            hero_dir_name = base[:-len("精华卡")]            # 黄忠_发育路
            target_dir = os.path.join(DST, hero_dir_name)
            if os.path.isdir(target_dir):
                shutil.copy2(m, os.path.join(target_dir, base + ".html"))
                mini_copied += 1
    print("已覆盖 %d 个英雄的速查卡 html/md" % copied)
    print("已覆盖 %d 个英雄的精华卡 html" % mini_copied)
    if missing:
        print("警告：以下英雄目录不存在，未覆盖：", missing)


if __name__ == "__main__":
    main()
