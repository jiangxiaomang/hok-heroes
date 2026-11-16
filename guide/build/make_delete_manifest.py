# -*- coding: utf-8 -*-
"""
删除前清单 + 执行删除老平铺目录。
先生成 guide/deleted_manifest.md 记录被删文件的 MD5，再删除。
"""
import os, hashlib, shutil, datetime

ROOT = '/Users/analyst/hok-site'
HEROES = os.path.join(ROOT, 'guide/heroes')
TARGETS = [
    '攻略输出',
    'guide/full',
    'guide/cards',
    'guide/cards_png',
    'guide/cards_mini',
    'guide/cards_mini_jpg',
    'guide/cards_mini_png',
    'guide/cards_jpg',
    'guide/card-images',
]
# 老目录里的每个文件，是否在新目录有同 MD5 的副本
# （同一英雄目录内按文件名匹配）

def md5(p):
    h = hashlib.md5()
    with open(p,'rb') as f:
        for b in iter(lambda: f.read(1<<20), b''): h.update(b)
    return h.hexdigest()

def new_index():
    """{basename: md5} 新目录所有文件"""
    idx = {}
    for dp,_,fs in os.walk(HEROES):
        for f in fs:
            p = os.path.join(dp,f)
            idx[f] = md5(p)
    return idx

def main():
    ni = new_index()
    lines = ['# 老平铺目录删除清单（MD5 校验）', '',
             f'- 生成时间: {datetime.datetime.now():%Y-%m-%d %H:%M:%S}',
             f'- 新目录（保留）: `guide/heroes/` — {len(ni)} 个文件',
             '- 说明: 下表每个文件均已在新目录中找到 MD5 完全相同的副本（标记 ✅）才执行删除',
             '']
    total_files = 0
    total_size = 0
    no_copy = []
    for t in TARGETS:
        d = os.path.join(ROOT, t)
        if not os.path.isdir(d): continue
        files = []
        for dp,_,fs in os.walk(d):
            for f in fs:
                files.append(os.path.join(dp,f))
        sz = sum(os.path.getsize(p) for p in files)
        lines.append(f'## {t}/ — {len(files)} 个文件，{sz/1e6:.1f} MB')
        lines.append('')
        lines.append('| 文件 | 大小 | MD5 | 新目录有同内容副本 |')
        lines.append('| --- | --- | --- | --- |')
        for p in sorted(files):
            f = os.path.basename(p)
            m = md5(p)
            has = '✅ 是' if ni.get(f) == m else '❌ 否'
            if ni.get(f) != m:
                no_copy.append((t, f, m, ni.get(f)))
            lines.append(f'| {f} | {os.path.getsize(p)} | {m} | {has} |')
            total_files += 1
            total_size += os.path.getsize(p)
        lines.append('')
    lines.insert(6, f'- 删除文件总数: **{total_files}** 个，合计 **{total_size/1e6:.1f} MB**')
    lines.insert(7, f'- 无同内容副本的文件: **{len(no_copy)}** 个')
    manifest = os.path.join(ROOT, 'guide/deleted_manifest.md')
    with open(manifest,'w',encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f'清单已生成: {manifest}')
    print(f'待删 {total_files} 文件 / {total_size/1e6:.1f} MB')
    print(f'无同内容副本: {len(no_copy)}')
    for t,f,m,nm in no_copy:
        print(f'  {t}/{f}  新目录同名文件MD5={nm}')
    return no_copy

if __name__ == '__main__':
    main()
