# -*- coding: utf-8 -*-
"""攻略 HTML 交稿前自检。"""
import re
import sys
import os

FORBIDDEN = [
    (r'河蟹', '出现已移除的河道之灵'),
    (r'1\s*分钟[^。]{0,10}河蟹', '旧版河蟹时间轴'),
    (r'2\s*分钟暴君', '旧赛季时间轴'),
    (r'8\s*分钟主宰', '旧赛季时间轴'),
    (r'每跳', '固定灼烧数值'),
    (r'剩\d+血可以走', '固定灼烧血线'),
    (r'共鸣之战[^。]{0,12}(加强|提升)', '娱乐模式误判'),
]

SECTION_TITLES = [
    (0, '范本说明'), (1, '一页纸速览'), (2, '版本状态与数据口径'),
    (3, '技能机制与被动'), (4, '出装铭文与召唤师技能'), (5, '开局路线'),
    (6, '连招库'), (7, '节奏与时间锚点'), (8, None), (9, '团战'),
    (10, '三种局势'), (11, '适配阵容与克制'), (12, '常见失误与训练法'),
    (13, '附录'),
]


def check(path):
    s = open(path, encoding='utf-8').read()
    errs = []
    warns = []

    # 13 节
    ids = re.findall(r'<section id="s(\d+)"', s)
    if ids != [str(i) for i in range(14)]:
        errs.append(f'章节编号异常: {ids}')
    # 每节本节作用
    n_purpose = len(re.findall(r'本节作用：', s))
    if n_purpose != 14:
        errs.append(f'本节作用标签数 {n_purpose}，应为 14')
    # 标题顺序
    for num, title in SECTION_TITLES:
        m = re.search(r'<section id="s%d".*?<h2>.*?</h2>' % num, s, re.S)
        if not m:
            errs.append(f'缺少 s{num}')
            continue
        if title:
            if title not in m.group(0):
                errs.append(f's{num} 标题不含「{title}」')
    # 非打野章节替换
    lane = re.search(r'本篇按\s*(\S+?)\s*写', s)
    lane = lane.group(1) if lane else '?'
    if lane != '打野':
        if '惩击' in s and '刷野路线' in s:
            errs.append('非打野出现惩击/刷野路线')
        if '换血与线权' not in s:
            errs.append('非打野缺少「换血与线权」章节')
    else:
        if '绕后四步' not in s:
            errs.append('打野缺少绕后四步')
    # A/B/C/D
    for k in 'ABCD':
        if f'mk-{k}' not in s:
            errs.append(f'缺少 {k} 类标注')
    # C 类独立成块
    if '体验服' not in s:
        errs.append('缺少体验服区块')
    # 禁用词（允许在「避坑 / 不要 / 已作废」语境中出现否定式提及）
    NEG = ['不要', '禁', '已', '作废', '避免', '不是', '别', '移除', '过时', '旧版', '旧赛季',
            '不引用', '未取到', '待核', '不可', '不要照做', '非']
    for pat, why in FORBIDDEN:
        for m in re.finditer(pat, s):
            ctx = s[max(0, m.start() - 160):m.end() + 160]
            if any(k in ctx for k in NEG):
                continue
            errs.append(f'禁用内容: {why}')
    # 必含口径
    for must in ['数据出处', '仍存疑的点', '以局内说明为准',
                 '主观归纳', '不是对位胜率', '2026-11-12']:
        if must not in s:
            errs.append(f'缺少必需内容: {must}')
    # 时间轴现行口径
    for t in ['0:30', '2:00', '10:00', '20:00']:
        if t not in s:
            errs.append(f'缺少现行时间锚点 {t}')
    # 主题浅色 + 内联
    if 'http://' in s.replace('http://www.w3.org', '') or '<link ' in s or 'src="http' in s:
        errs.append('存在外部依赖')
    if '@media print' not in s:
        warns.append('缺少打印样式')
    if '<nav class="anchors"' not in s:
        errs.append('缺少锚点导航')

    return errs, warns, lane


if __name__ == '__main__':
    for p in sys.argv[1:]:
        e, w, lane = check(p)
        print(f'== {os.path.basename(p)}  分路: {lane}')
        for x in e:
            print('  [FAIL]', x)
        for x in w:
            print('  [WARN]', x)
        if not e:
            print('  [OK] 全部检查通过')
