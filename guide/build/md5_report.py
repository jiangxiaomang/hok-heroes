# -*- coding: utf-8 -*-
"""
生成 MD5 校验报告：新目录 guide/heroes 各文件 vs 老平铺目录对应文件。
对比规则：按文件名字母名匹配（英雄名 + 后缀），忽略路径。
"""
import os, hashlib

OUT = '/Users/analyst/hok-site/guide/heroes'
OLD = [
    ('攻略输出', ''),
    ('guide/full', ''),
    ('guide/cards', ''),
    ('guide/cards_png', ''),
    ('guide/cards_mini', ''),
    ('guide/cards_mini_jpg', ''),
    ('guide/cards_mini_png', ''),
    ('guide/cards_jpg', ''),
    ('guide/card-images', ''),
]

KEY_SUFFIXES = [
    '_完整攻略.html',
    '_速查卡.html',
    '_速查卡.md',
    '_精华卡.html',
    '_速查卡.jpg',
    '_精华卡.jpg',
    '_速查卡.png',
    '_精华卡.png',
]

def md5(p):
    h = hashlib.md5()
    with open(p,'rb') as f:
        for b in iter(lambda: f.read(1<<20), b''): h.update(b)
    return h.hexdigest()

def scan_dir(base):
    """返回 {basename: path}，同目录内同名只取最后一个。跨目录会有不同键。"""
    res = {}
    if not os.path.isdir(base): return res
    for dp, _, fs in os.walk(base):
        for f in fs:
            # 按"英雄_分路_后缀"命名
            # 对于 images 子目录，文件名一样，我们记录全路径
            full = os.path.join(dp, f)
            res[f] = full
    return res

def build_hero_files():
    """扫描新目录，返回 {hero_dir: {basename: path}}"""
    heroes = {}
    for d in sorted(os.listdir(OUT)):
        hp = os.path.join(OUT, d)
        if not os.path.isdir(hp): continue
        files = scan_dir(hp)  # 含 images/ 里的文件
        # 去掉路径前缀，只保留相对名？不，我们用 basename 作为 key
        # 但同一英雄目录内可能有重复文件名吗？不会，每个子类名唯一
        heroes[d] = files
    return heroes

def main():
    print('='*80)
    print('MD5 校验报告：新目录 guide/heroes vs 老平铺目录')
    print('='*80)

    heroes = build_hero_files()
    total_new_files = sum(len(f) for f in heroes.values())
    total_new_size = sum(
        os.path.getsize(p)
        for fs in heroes.values() for p in fs.values()
    )
    print(f'\n新目录 guide/heroes:')
    print(f'  英雄数: {len(heroes)}')
    print(f'  文件总数：{total_new_files}')
    print(f'  总大小: {total_new_size/1e6:.1f} MB')

    # 逐个英雄校验
    consistent = 0
    inconsistent = []
    new_missing = []
    old_missing = []

    for hero, files in heroes.items():
        # 对每个文件，去老目录找同名文件比对 md5
        for fname, fpath in files.items():
            # 文件名格式：阿古朵_打野_完整攻略.html
            # 找到对应的老目录文件
            found_old = None
            for old_dir, _ in OLD:
                old_path = os.path.join('/Users/analyst/hok-site', old_dir, fname)
                if os.path.isfile(old_path):
                    found_old = old_path
                    break
            if found_old is None:
                new_missing.append((os.path.join(hero, fname),))
                continue

            md5n = md5(fpath)
            md5o = md5(found_old)
            if md5n == md5o:
                consistent += 1
            else:
                inconsistent.append((hero, fname, md5n, md5o, found_old))

    # 再检查老目录是否有新目录缺少的文件（跨所有英雄）
    old_all_files = {}
    for old_dir, _ in OLD:
        od = os.path.join('/Users/analyst/hok-site', old_dir)
        if not os.path.isdir(od): continue
        for dp, _, fs in os.walk(od):
            for f in fs:
                if any(f.endswith(s) for s in KEY_SUFFIXES):
                    # 记录这个文件属于哪个英雄
                    # 从文件名提取英雄名
                    base = f
                    # 找到对应的英雄
                    for d in heroes:
                        if base.startswith(d + '_') or base.endswith('_完整攻略.html') and any(base.startswith(d) for _,_,_ in [(h,fn,p) for h,fn,_,_,_ in inconsistent] if h==d):
                            pass
                    # 简单做法：只看文件名是否在新目录出现
                    if f not in [fn for fs in heroes.values() for fn in fs]:
                        old_missing.append((old_dir, f))

    print(f'\n校验结果:')
    print(f'  一致：{consistent} 文件')
    print(f'  不一致：{len(inconsistent)} 文件')
    print(f'  新存在但老缺失：{len(new_missing)} 文件')
    print(f'  老存在但新缺失：{len(old_missing)} 文件')

    if inconsistent:
        print('\n不一致示例（前 5 个）:')
        for hero, fname, mn, mo, op in inconsistent[:5]:
            print(f'  {hero}/{fname}')
            print(f'    新 MD5: {mn}')
            print(f'    老 MD5: {mo}')
            print(f'    老路径：{os.path.basename(op)}')

    if new_missing:
        print(f'\n新存在但老缺失示例（前 5 个）:')
        for item in new_missing[:5]:
            print(f'  {item[0]}')

    if old_missing:
        print(f'\n老存在但新缺失示例（前 5 个）:')
        for old_dir, fn in old_missing[:5]:
            print(f'  {old_dir}/{fn}')

    # 空间计算
    print('\n' + '='*80)
    print('空间评估')
    print('='*80)

    old_sizes = {}
    for old_dir, _ in OLD:
        od = os.path.join('/Users/analyst/hok-site', old_dir)
        if not os.path.isdir(od): continue
        sz = sum(os.path.getsize(os.path.join(dp,f)) for dp,d,fs in os.walk(od) for f in fs)
        old_sizes[old_dir] = sz
        print(f'{old_dir}: {sz/1e6:.1f} MB')

    total_old = sum(old_sizes.values())
    print(f'\n老目录总大小：{total_old/1e6:.1f} MB')
    print(f'新目录总大小：{total_new_size/1e6:.1f} MB')
    print(f'删除老目录可节省：{total_old/1e6:.1f} MB')
    print(f'总磁盘占用 (保留双份): {total_old/1e6 + total_new_size/1e6:.1f} MB')
    print(f'总磁盘占用 (删除老): {total_new_size/1e6:.1f} MB')

    return consistent, inconsistent, new_missing, old_missing

if __name__ == '__main__':
    main()
