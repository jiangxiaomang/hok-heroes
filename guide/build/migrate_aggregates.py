# -*- coding: utf-8 -*-
"""
把老目录里"独有的聚合产物"迁移到 guide/heroes/ 下，保证删除老目录不丢功能。

迁移内容：
  guide/cards/cards_all.html   -> guide/heroes/cards_all.html      （133 卡单文件合集）
  guide/cards/cards.md          -> guide/heroes/cards.md            （133 卡 Markdown 合集）
  guide/cards/hok_cards_133.zip -> guide/heroes/hok_cards_133.zip
  guide/cards/hok_cards_133.tar.gz -> guide/heroes/hok_cards_133.tar.gz
  guide/card-images/hok_card_images_133.zip -> guide/heroes/hok_card_images_133.zip
  guide/card-images/hok_card_images_133.tar.gz -> guide/heroes/hok_card_images_133.tar.gz

压缩包内容校验：解包后逐文件与新目录 guide/heroes/<英雄>/ 内同名文件比对 MD5。
"""
import os, shutil, zipfile, tarfile, hashlib, tempfile

ROOT = '/Users/analyst/hok-site'
HEROES = os.path.join(ROOT, 'guide/heroes')

MOVES = [
    ('guide/cards/cards_all.html', 'cards_all.html'),
    ('guide/cards/cards.md', 'cards.md'),
    ('guide/cards/hok_cards_133.zip', 'hok_cards_133.zip'),
    ('guide/cards/hok_cards_133.tar.gz', 'hok_cards_133.tar.gz'),
    ('guide/card-images/hok_card_images_133.zip', 'hok_card_images_133.zip'),
    ('guide/card-images/hok_card_images_133.tar.gz', 'hok_card_images_133.tar.gz'),
]

def md5(p):
    h = hashlib.md5()
    with open(p,'rb') as f:
        for b in iter(lambda: f.read(1<<20), b''): h.update(b)
    return h.hexdigest()

def hero_index():
    """{basename: md5} guide/heroes 下所有文件（不含合集）"""
    idx = {}
    for dp,_,fs in os.walk(HEROES):
        for f in fs:
            p = os.path.join(dp,f)
            idx[f] = md5(p)
    return idx

def check_zip(path):
    """校验 zip 内每个文件在 guide/heroes 里有同 MD5 副本"""
    idx = hero_index()
    same, diff, missing = 0, [], []
    with zipfile.ZipFile(path) as z:
        for n in z.namelist():
            if n.endswith('/'):
                continue
            data = z.read(n)
            m = hashlib.md5(data).hexdigest()
            base = os.path.basename(n)
            if base not in idx:
                missing.append(n)
            elif idx[base] == m:
                same += 1
            else:
                diff.append(n)
    return same, diff, missing

def check_tar(path):
    idx = hero_index()
    same, diff, missing = 0, [], []
    with tarfile.open(path, 'r:gz') as t:
        for m in t.getmembers():
            if not m.isfile():
                continue
            f = t.extractfile(m)
            data = f.read()
            md = hashlib.md5(data).hexdigest()
            base = os.path.basename(m.name)
            if base not in idx:
                missing.append(m.name)
            elif idx[base] == md:
                same += 1
            else:
                diff.append(m.name)
    return same, diff, missing

def main():
    print('=== 压缩包内容校验（与 guide/heroes 逐文件比 MD5）===')
    ok = True
    for src, dst in MOVES:
        s = os.path.join(ROOT, src)
        if not os.path.isfile(s):
            print(f'  [缺失] {src}')
            continue
        if s.endswith('.zip'):
            same, diff, missing = check_zip(s)
            kind = 'zip'
        elif s.endswith('.tar.gz'):
            same, diff, missing = check_tar(s)
            kind = 'tar.gz'
        else:
            print(f'  {src}: 单文件 {os.path.getsize(s)/1e6:.2f} MB -> 迁移')
            continue
        print(f'  {kind} {src}')
        print(f'    内容与新目录 MD5 一致: {same}')
        print(f'    内容不同(旧版): {len(diff)}' + (f' 例: {diff[0]}' if diff else ''))
        print(f'    新目录无同名: {len(missing)}' + (f' 例: {missing[0]}' if missing else ''))
        if diff:
            ok = False
    print('\n=== 执行迁移 ===')
    for src, dst in MOVES:
        s = os.path.join(ROOT, src)
        d = os.path.join(HEROES, dst)
        if not os.path.isfile(s):
            continue
        shutil.copy2(s, d)
        print(f'  {src} -> guide/heroes/{dst}  ({os.path.getsize(d)/1e6:.2f} MB)')
    print('\n迁移完成' if ok else '\n注意：部分压缩包含旧版内容，迁移的是原文件')

if __name__ == '__main__':
    main()
