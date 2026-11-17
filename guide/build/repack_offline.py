# -*- coding: utf-8 -*-
"""
重新打包 guide/heroes/ 内容为两个离线包（内容取自新目录最新版）。

  hok_cards_133.zip / .tar.gz   — 133 英雄速查卡 HTML+MD 合集 + 合集页 + Markdown 合集
  hok_card_images_133.zip/.tar.gz — 全部卡图 jpg/png

生成后逐文件与 guide/heroes 内源文件比对 MD5，确保包内即最新版。
"""
import os, zipfile, tarfile, hashlib, shutil, datetime

ROOT = '/Users/analyst/hok-site'
HEROES = os.path.join(ROOT, 'guide/heroes')

def md5b(data):
    return hashlib.md5(data).hexdigest()

def md5f(p):
    h = hashlib.md5()
    with open(p,'rb') as f:
        for b in iter(lambda: f.read(1<<20), b''): h.update(b)
    return h.hexdigest()

def hero_dirs():
    return sorted(d for d in os.listdir(HEROES)
                  if os.path.isdir(os.path.join(HEROES, d)))

def build_cards_zip():
    """卡包：每个英雄目录只放速查卡 html+md（不含完整攻略，避免重复）"""
    entries = []
    for d in hero_dirs():
        for f in sorted(os.listdir(os.path.join(HEROES, d))):
            if f.endswith('速查卡.html') or f.endswith('速查卡.md'):
                entries.append((f, os.path.join(HEROES, d, f)))
    for extra in ['cards_all.html', 'cards.md']:
        p = os.path.join(HEROES, extra)
        if os.path.isfile(p):
            entries.append((extra, p))
    return entries

def build_images_zip():
    """图片包：按分路拆分，每包仅含 jpg（png 体积翻倍且浏览器直接看 jpg 足够，png 仍在目录内逐文件托管）。

    GitHub 单文件硬限制 100 MiB，整体打包 jpg 会超限，故按分路拆成 5 包。
    """
    entries = []
    for d in hero_dirs():
        imgd = os.path.join(HEROES, d, 'images')
        if not os.path.isdir(imgd):
            continue
        lane = d.split('_')[-1]
        for f in sorted(os.listdir(imgd)):
            if f.endswith('.jpg'):
                entries.append((lane, os.path.join(d, 'images', f), os.path.join(imgd, f)))
    return entries

def write_zip(entries, out):
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for arc, src in entries:
            z.write(src, arc)

def write_tar(entries, out):
    with tarfile.open(out, 'w:gz', compresslevel=9) as t:
        for arc, src in entries:
            t.add(src, arcname=arc)

def verify_zip(path, entries):
    src_map = {arc: md5f(src) for arc, src in entries}
    bad = []
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        for arc, m in src_map.items():
            if arc not in names:
                bad.append((arc, '缺失')); continue
            if md5b(z.read(arc)) != m:
                bad.append((arc, 'MD5不符'))
    return bad, len(src_map)

def verify_tar(path, entries):
    src_map = {arc: md5f(src) for arc, src in entries}
    bad = []
    with tarfile.open(out_tar := path, 'r:gz') as t:
        members = {m.name: m for m in t.getmembers() if m.isfile()}
        for arc, m in src_map.items():
            if arc not in members:
                bad.append((arc, '缺失')); continue
            if md5b(t.extractfile(members[arc]).read()) != m:
                bad.append((arc, 'MD5不符'))
    return bad, len(src_map)

def main():
    # 卡包：133 英雄速查卡（整体一个小文件，无超限风险）
    pkg = 'hok_cards_133'
    entries = [(f, p) for f, p in build_cards_zip()]
    zp = os.path.join(HEROES, pkg + '.zip')
    tp = os.path.join(HEROES, pkg + '.tar.gz')
    print(f'=== {pkg} ({len(entries)} 个文件) ===')
    write_zip(entries, zp)
    write_tar(entries, tp)
    bz, n = verify_zip(zp, entries)
    bt, _ = verify_tar(tp, entries)
    print(f'  zip     {os.path.getsize(zp)/1e6:.2f} MB  校验 {n} 文件, 问题 {len(bz)}')
    print(f'  tar.gz  {os.path.getsize(tp)/1e6:.2f} MB  校验 {n} 文件, 问题 {len(bt)}')
    for arc, why in (bz + bt)[:5]:
        print(f'    ! {arc}: {why}')

    # 图片包：按分路拆包，避免单文件超 GitHub 100 MiB 限制
    imgs = build_images_zip()
    by_lane = {}
    for lane, arc, src in imgs:
        by_lane.setdefault(lane, []).append((arc, src))
    for lane, ents in sorted(by_lane.items()):
        pkg = f'hok_card_images_{lane}'
        zp = os.path.join(HEROES, pkg + '.zip')
        tp = os.path.join(HEROES, pkg + '.tar.gz')
        print(f'=== {pkg} ({len(ents)} 个文件) ===')
        write_zip(ents, zp)
        write_tar(ents, tp)
        bz, n = verify_zip(zp, ents)
        bt, _ = verify_tar(tp, ents)
        for f in (zp, tp):
            mb = os.path.getsize(f) / 1024 / 1024
            flag = '  [!! 超 GitHub 100 MiB 限制]' if mb >= 100 else ''
            print(f'  {os.path.basename(f):38s} {mb:7.2f} MiB  校验 {n} 文件, 问题 {len(bz)+len(bt)}{flag}')
        for arc, why in (bz + bt)[:3]:
            print(f'    ! {arc}: {why}')
    # 清理旧的整包（超过限制的那个）
    for old in ('hok_card_images_133.zip', 'hok_card_images_133.tar.gz'):
        p = os.path.join(HEROES, old)
        if os.path.isfile(p):
            size_mb = os.path.getsize(p) / 1e6
            os.remove(p)
            print(f'  已移除超限旧整包: {old} ({size_mb:.2f} MB)')
    print(f'  时间: {datetime.datetime.now():%Y-%m-%d %H:%M:%S}')

if __name__ == '__main__':
    main()
