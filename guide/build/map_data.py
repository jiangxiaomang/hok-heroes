#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从现有 hok-site/index.html 的 HEROES 数据映射出《全英雄使用指南》新字段结构。
零成本：全部基于已有官方数据 + 机制共识规则推导，不编造胜率/梯度/数值。
"""
import re, json, os

SRC = '/Users/analyst/hok-site/index.html'
OUT_DIR = '/Users/analyst/hok-site/guide/data'
OUT = os.path.join(OUT_DIR, 'heroes.json')

# ---------------------------------------------------------------- 标签词表 (37)
TAGS = ["位移","硬控","团控","免控","护盾","回复","真伤","爆发","持续输出","坦度","远程","手短",
        "吃经济","吃操作","抓人","反野","单带","推塔","前期强","后期强","保人","开团","消耗","拉扯",
        "切后排","无位移","怕控","怕集火","怕制裁","召唤物","变身","能量","法球","暴击","穿墙","隐身","全图支援"]
TAG_SET = set(TAGS)

# ---------------------------------------------------------------- 关键词 -> 标签
# (标签, 触发词, 需要的最小命中数)
TAG_RULES = [
    ("位移",   ["位移","突进","突袭","冲锋","闪现","穿越","瞬移","突进","二段","位移"], 1),
    ("穿墙",   ["穿墙","穿越墙体","翻越"], 1),
    ("硬控",   ["眩晕","击飞","击退","定身","嘲讽","沉默","控制","减速","缴械","拉扯"], 1),
    ("团控",   ["范围击飞","群体击飞","击退","定身","嘲讽","控制","强制位移"], 2),
    ("免控",   ["霸体","免疫控制","免控","无法控制","不受控制","不可被控制"], 1),
    ("护盾",   ["护盾","结界","屏障"], 1),
    ("回复",   ["治疗","回复","回血","吸血","恢复生命","回复生命"], 1),
    ("真伤",   ["真伤","无视护盾","无视防御"], 1),
    ("爆发",   ["爆发","瞬间","极高伤害","巨额伤害"], 1),
    ("持续输出",["持续伤害","每秒","持续输出","灼烧","持续"], 2),
    ("坦度",   ["减伤","吸收伤害","抗伤","护甲","防御","承伤"], 1),
    ("远程",   ["远程"], 1),
    ("手短",   ["近程","短距离","贴身"], 1),
    ("吃经济", ["需要经济","经济","装备成型"], 1),
    ("吃操作", ["操作","手速","预判","时机","极限","难度","上限"], 1),
    ("抓人",   ["抓人","gank","突袭","埋伏","蹲"], 1),
    ("反野",   ["反野","入侵","抢野"], 1),
    ("单带",   ["带线","单带","牵制"], 1),
    ("推塔",   ["推塔","拆塔","拆防御塔"], 1),
    ("前期强", ["前期","一级","早期","开局"], 2),
    ("后期强", ["后期","发育成型","装备齐全","后期核心"], 2),
    ("保人",   ["保护","为队友","护盾队友","治疗队友","保护队友"], 1),
    ("开团",   ["开团","先手","进场","起手"], 1),
    ("消耗",   ["消耗","远程骚扰","poke"], 1),
    ("拉扯",   ["拉扯","拉开距离","拉开身位","位移拉扯"], 1),
    ("切后排", ["后排","敌方后排","切入","切后"], 1),
    ("无位移", ["无位移","没有位移","无法位移"], 1),
    ("召唤物", ["召唤","宠物","分身","镜像","召唤物"], 1),
    ("变身",   ["变身","形态切换","切换形态","两种形态","双形态"], 1),
    ("能量",   ["能量","怒气","气值"], 1),
    ("法球",   ["法球","球体","球"], 1),
    ("暴击",   ["暴击"], 1),
    ("隐身",   ["隐身","隐匿","无法被选中"], 1),
    ("全图支援",["全图","传送","回城","支援","全屏"], 1),
]

# ---------------------------------------------------------------- 职业通用机制共性
# 优势 / 弱点 / 克制 / 被克制 全部是机制层面共性，不含任何数值与对位胜率
ROLE_PROFILE = {
    "战士": dict(
        pros="近身开团与持续输出兼备，兼具位移与打断能力",
        cons="远程消耗拉扯下较难接近，起手后自身位移有限易被集火",
        counter="擅长贴近并击杀缺乏位移与自保手段的脆皮后排",
        weakto="被远程持续消耗与强控制阵容牵制，起手容易被反打断",
    ),
    "坦克": dict(
        pros="承伤能力强，兼具范围控制与团队保护，开团容错高",
        cons="机动与输出能力有限，被高爆发阵容针对时后排伤害跟不上",
        counter="擅长吸收火力并强开针对需要推进的射手与近战",
        weakto="被制裁型与高爆发阵容快速击穿，怕被多线同时施压拉扯",
    ),
    "法师": dict(
        pros="范围爆发与清线能力强，后期团战输出上限高",
        cons="自身身板脆弱怕被强开贴近，依赖技能命中与施法空间",
        counter="擅长范围爆发克制抱团站桩与推进型阵容",
        weakto="怕被强控开团切入或被刺客直接贴身秒杀",
    ),
    "刺客": dict(
        pros="切入爆发能力极强，善于抓单与切后排，机动性高",
        cons="入场后血量与容错有限，怕被集火与控制直接打崩",
        counter="擅长秒杀无位移自保手段的后排与脆皮射手",
        weakto="被开团反制与集火针对，怕被控制打断入场节奏",
    ),
    "射手": dict(
        pros="持续输出与远程压制能力强，后期伤害转化效率高",
        cons="身板脆弱怕被强开贴近，自身缺乏保命手段时容错低",
        counter="擅长持续消耗与远程压制，克制推进慢的前排与近战",
        weakto="怕被强控与刺客切入，怕被前排贴脸打断输出环境",
    ),
    "辅助": dict(
        pros="开团与保护能力强，能稳定给队友提供增益与容错",
        cons="自身输出与生存依赖队友，后期强度不如核心位",
        counter="擅长保护核心位并针对依赖单一爆发点的阵容",
        weakto="怕被多线施压与集火，怕对面制裁型阵容压制视野",
    ),
}

# ---------------------------------------------------------------- 职业 -> 常见副分路
ROLE_ALT = {
    "战士": ["打野", "游走"],
    "坦克": ["对抗路", "游走"],
    "法师": ["中路", "游走"],
    "刺客": ["打野", "对抗路"],
    "射手": ["发育路", "中路"],
    "辅助": ["游走", "中路"],
}

# ---------------------------------------------------------------- 具体威胁 -> 被克制共性补充
# 根据已有 countered_by 名单里的典型英雄，补一条更具体的机制共性
THREAT_PATTERNS = [
    (["张良", "东皇太一", "钟馗", "墨子"], "被强控开团体系直接限制进场"),
    (["盾山", "钟馗"], "被位移封路与强制位移打乱走位"),
    (["兰陵王", "镜", "澜", "韩信", "李白"], "被隐身与高机动切入威胁后排"),
    (["公孙离", "孙尚香", "马可波罗", "伽罗"], "被灵活拉扯的射手持续消耗难以贴身"),
    (["大乔", "明世隐", "蔡文姬", "孙膑"], "被保护体系与续航阵容拉扯消耗"),
    (["女娲", "扁鹊", "曹操", "芈月", "程咬金"], "被高回复与高续航阵容消耗战拖垮"),
    (["盾山", "苏烈", "廉颇", "牛魔"], "被前排开团强控抢先手"),
    (["鲁班大师", "太乙真人", "鬼谷子"], "被辅助体系反开与视野压制"),
]

# ---------------------------------------------------------------- 克制对象补充
COUNTER_PATTERNS = [
    (["鲁班七号", "后羿", "伽罗", "虞姬", "狄仁杰"], "擅长击杀无位移的自保不足射手"),
    (["小乔", "妲己", "王昭君", "甄姬"], "擅长范围爆发压制站桩型法师"),
    (["廉颇", "白起", "牛魔", "张飞"], "擅长强开打断后排输出环境"),
    (["马可波罗", "公孙离", "孙尚香"], "擅长拉扯与持续消耗对手"),
    (["张良", "东皇太一"], "擅长针对依赖技能节奏的控制型打法"),
]

def pick_alt(role, primary):
    cands = [c for c in ROLE_ALT.get(role, []) if c != primary]
    return cands[0] if cands else ""

def pick_diff(role, text):
    t = text
    hard = ["操作上限极高", "极难", "需要极强", "手速", "极限操作", "精准时机"]
    if any(k in t for k in hard):
        return "极难"
    if role in ("刺客", "法师") and any(k in t for k in ["操作", "手速", "预判", "时机", "难度", "上限"]):
        return "难"
    if any(k in t for k in ["操作", "手速", "预判", "时机", "难度", "上限", "连招", "精准"]):
        return "难"
    if role in ("辅助", "坦克") and not any(k in t for k in ["手速", "极限", "预判极"]):
        return "易"
    return "中"

def build_tags(h):
    blob = " ".join([
        h.get("playstyle") or "", h.get("phases") or "",
        " ".join(h.get("pro_tips") or []),
        " ".join((s.get("desc") or "") for s in (h.get("skills") or [])),
        " ".join((s.get("name") or "") for s in (h.get("skills") or [])),
    ])
    hits = []
    for tag, words, need in TAG_RULES:
        c = sum(blob.count(w) for w in words)
        if c >= need:
            hits.append((c, tag))
    hits.sort(key=lambda x: -x[0])
    tags = [t for _, t in hits]
    # 必选语义修正
    if not any(t in ("位移", "无位移") for t in tags):
        tags.append("位移" if any(w in blob for w in ["位移", "突进", "突袭", "闪现", "冲锋"]) else "无位移")
    # 控/保人语义修正
    if h.get("type_name") == "辅助" and "保人" not in tags:
        tags.append("保人")
    if h.get("type_name") == "坦克" and "开团" not in tags and any(w in blob for w in ["开团", "先手", "击飞", "嘲讽"]):
        tags.append("开团")
    # 上限 5 个，按命中频次保序
    tags = tags[:5]
    # 保证 3~5 个：不足则用职业默认补
    defaults = {"战士": ["位移", "爆发"], "坦克": ["坦度", "团控"], "法师": ["远程", "爆发"],
                "刺客": ["位移", "切后排"], "射手": ["远程", "持续输出"], "辅助": ["保人", "团控"]}
    for d in defaults.get(h.get("type_name"), []):
        if len(tags) >= 3:
            break
        if d not in tags:
            tags.append(d)
    return [t for t in tags if t in TAG_SET][:5]

def first_sentence(text, lo=15, hi=45):
    """把长文本压成 15~45 字的单句。"""
    if not text:
        return ""
    t = re.sub(r"\s+", " ", text).strip()
    t = t.replace("。", "。 ").replace("；", "； ")
    parts = [p.strip() for p in t.split("。 ") if p.strip()]
    if not parts:
        return t[:hi]
    out = parts[0]
    if len(out) < lo and len(parts) > 1:
        out = out + "。" + parts[1]
    out = out.strip("。 ")
    if len(out) > hi:
        # 在标点处截断
        cut = out[:hi]
        for sep in ("，", "；", "、"):
            if sep in cut:
                idx = cut.rfind(sep)
                if idx >= lo:
                    cut = cut[:idx]
                    break
        out = cut
    return out + "。"

FEAT_SEEN = set()

def pick_feat(h):
    """特点 = 定位 + 核心机制，合成一句 15~45 字的描述。

    playstyle 形如 "狂战士打野，嗜血；大招真伤吸血，越战越勇。"
    -> 取前半定位 + 后半机制，合成 "狂战士打野，大招真伤吸血越战越勇。"
    playstyle 被填成铭文 Tips 的英雄，改用职业定位 + 进阶技巧里的机制。
    """
    role = h.get("type_name") or "战士"
    ps = (h.get("playstyle") or "").strip()

    if ps and not ps.startswith("Tips"):
        segs = [s.strip().rstrip("。") for s in re.split(r"[；;]", ps) if s.strip()]
        if len(segs) >= 2:
            head = segs[0]
            mech = sanitize_text(segs[1])
            # 去掉重复的称号部分
            if "，" in head:
                head = head.split("，")[0].strip()
            if mech and len(mech) >= 4:
                out = f"{head}，{mech}" if head else mech
                out = out[:40].rstrip("，、")
                # 避免与同职业其他英雄撞描述：追加该英雄独有的机制关键词
                if out in FEAT_SEEN:
                    extra = hero_uniq_mechanism(h)
                    if extra and extra[:12] not in out:
                        out = f"{out}，{extra[:14]}"[:40].rstrip("，、")
                FEAT_SEEN.add(out)
                return out + "。"
        core = segs[0] if segs else ""
        if len(core) >= 8:
            FEAT_SEEN.add(core[:40])
            return core[:40] + "。"

    # playstyle 是铭文 Tips -> 用职业定位 + 进阶技巧里的机制描述
    mech = ""
    for t in (h.get("pro_tips") or []):
        s = sanitize_text(t.rstrip("。"))
        if len(s) >= 8 and any(k in s for k in ["大招", "被动", "技能", "形态", "护盾", "免控", "霸体",
                                              "位移", "治疗", "真伤", "隐身", "召唤", "暴击",
                                              "层数", "叠", "冷却", "霸体", "机动", "移速"]):
            mech = s
            break
    if not mech:
        # 退化：分阶段打法里的中期/后期机制
        phase = (h.get("phases") or "").strip()
        segs = [s.strip().rstrip("。") for s in re.split(r"[；;]", phase) if s.strip()]
        for s in segs[1:]:
            t = sanitize_text(s)
            if len(t) >= 6:
                mech = t
                break
        if not mech and segs:
            mech = sanitize_text(segs[0])
    if not mech:
        names = [s.get("name") for s in (h.get("skills") or []) if s.get("name")]
        if names:
            mech = "核心机制围绕" + "、".join(names[1:3]) + "展开"
    if not mech:
        return f"{role}定位英雄，机制以局内说明为准。"
    out = f"{role}，{mech}" if len(mech) < 26 else mech
    return out[:40].rstrip("，、") + "。"

def build_pros(h, role):
    """优势 = 职业共性 + 该英雄独有机制，追加个性化后半句。"""
    base = ROLE_PROFILE[role]["pros"]
    uniq = hero_uniq_mechanism(h)
    if not uniq:
        return base
    if _sem_keys(uniq) & _sem_keys(base):
        return f"{base}；{uniq}。"
    return f"{base}；{uniq}。"

def build_cons(h, role):
    """弱点 = 职业共性 + 该英雄的具体短板（从 countered_by / 技能描述反推）。"""
    base = ROLE_PROFILE[role]["cons"]
    extra = None
    cb = set(h.get("countered_by") or [])
    if role == "法师" and cb & {"兰陵王", "镜", "澜", "韩信", "李白"}:
        extra = "被高机动刺客切入时缺少反制位移"
    elif role == "射手" and cb & {"兰陵王", "镜", "澜", "公孙离", "马可波罗"}:
        extra = "缺乏硬保命手段，团战站位失误易被直接秒杀"
    elif role == "刺客" and cb & {"张良", "东皇太一", "钟馗", "墨子"}:
        extra = "入场路径容易被预判，反控直接打崩节奏"
    elif role == "坦克" and cb & {"芈月", "程咬金", "曹操", "扁鹊"}:
        extra = "面对高回复阵容难以速杀，团战拖延反而吃亏"
    elif role == "辅助" and cb & {"兰陵王", "镜", "澜"}:
        extra = "视野与信息支援有限，被强开时难以第一时间到位"
    elif role == "战士" and any(k in (h.get("phases") or "") for k in ["一套", "连招", "秒杀"]):
        extra = "爆发依赖连招衔接，被控制打断后伤害严重不足"
    if extra:
        return f"{base}；{extra}。"
    return base

# ---------------------------------------------------------------- 语义去重
# 不同来源的补充句可能出现同义重复（如"擅长击杀无位移射手，擅长秒杀脆皮射手"），
# 用关键词重合度判断：若补充句已覆盖职业共性句的核心对象，则只保留更具体的补充句。
SEM_KEYS = ["后排", "射手", "脆皮", "法师", "前排", "站桩", "推进", "刺客", "射手",
            "控制", "开团", "反控", "集火", "爆发", "团战", "拉扯", "消耗"]


def _sem_keys(text):
    return {k for k in SEM_KEYS if k in text}


def merge_clauses(specific, base):
    """合并两句，若核心对象重合则只保留更具体的一句，避免同义重复。"""
    if not specific:
        return base
    if not base:
        return specific
    ks, kb = _sem_keys(specific), _sem_keys(base)
    # 交集占比过高说明描述的是同一件事
    inter = ks & kb
    if not inter:
        return f"{specific}，{base}。"
    if len(inter) >= min(len(ks), len(kb)):
        return specific
    return f"{specific}，{base}。"


def build_counter(h, role):
    """克制 = 具体克制对象共性 + 职业共性补充。"""
    specific = None
    for names, phrase in COUNTER_PATTERNS:
        if set(names) & set(h.get("counters") or []):
            specific = phrase
            break
    base = ROLE_PROFILE[role]["counter"]
    if specific and specific != base:
        return merge_clauses(specific, base)
    return base

def build_weakto(h, role):
    """被克制 = 具体威胁共性 + 职业共性补充。"""
    specific = None
    for names, phrase in THREAT_PATTERNS:
        if set(names) & set(h.get("countered_by") or []):
            specific = phrase
            break
    base = ROLE_PROFILE[role]["weakto"]
    if specific and specific != base:
        return merge_clauses(specific, base)
    return base

def hero_uniq_mechanism(h):
    """从 pro_tips 提取该英雄独有的机制描述，用于个性化优势。"""
    tips = h.get("pro_tips") or []
    blob = " ".join(tips)
    # 选取与技能直接相关的机制描述（排除纯操作/心理类）
    for t in tips:
        if any(k in t for k in ["大招", "被动", "技能", "形态", "护盾", "免控", "霸体", "位移",
                                "治疗", "真伤", "隐身", "召唤", "暴击", "护甲", "冷却", "层数", "叠"]):
            return sanitize_text(t.rstrip("。"))
    if tips:
        return sanitize_text(tips[0].rstrip("。"))
    return ""


def sanitize_text(t):
    """去掉机制描述里的具体数值，改写成不含数字的定性表述。"""
    if not t:
        return ""
    out = t
    # 百分比与时长：改为定性表述
    out = re.sub(r"\d+(\.\d+)?\s*%", "", out)
    out = re.sub(r"\d+(\.\d+)?\s*秒", "", out)
    # 数值加成型（+100攻击力 / 攻击+100）：连同前置符号删除
    out = re.sub(r"[+＋]\s*\d+(\.\d+)?", "", out)
    out = re.sub(r"\d+(\.\d+)?\s*(?=[%秒])", "", out)
    out = re.sub(r"[（(]\s*[，,、；;]?\s*[)）]", "", out)
    out = re.sub(r"\s{2,}", " ", out)
    out = out.replace("（）", "").replace("()", "")
    out = re.sub(r"[+＋]{2,}", "", out)
    # 孤立的加号（原本是 "+100攻击力+免伤" 去掉数值后的残留）：改为顿号分隔
    out = re.sub(r"\s*[+＋]\s*(?!\d)", "、", out)
    out = re.sub(r"[，、]{2,}", "，", out)
    out = re.sub(r"[，、]\s*。", "。", out)
    out = out.strip("，。、；; ")
    out = out.rstrip("。")
    return out.strip()


def core_of_playstyle(ps):
    """取 playstyle 中 "职业定位，称号" 里的职业定位部分。"""
    if not ps or ps.startswith("Tips"):
        return ""
    core = ps.split("；")[0].split(";")[0].strip().rstrip("。")
    if "，" in core:
        head = core.split("，")[0].strip()
        if 3 <= len(head) <= 12:
            return head
    return ""


def map_hero(h, hero_map):
    role = h.get("type_name") or "战士"
    skill_blob = " ".join((s.get("desc") or "") for s in (h.get("skills") or []))
    tip_blob = " ".join(h.get("pro_tips") or [])

    return {
        "n": h["cname"],
        "lane": h.get("primary_lane") or "",
        "alt": pick_alt(role, h.get("primary_lane") or ""),
        "role": role,
        "diff": pick_diff(role, skill_blob + " " + tip_blob),
        "feat": pick_feat(h),
        "pros": build_pros(h, role),
        "cons": build_cons(h, role),
        "play": first_sentence(h.get("phases") or ""),
        "counter": build_counter(h, role, hero_map),
        "weakto": build_weakto(h, role, hero_map),
        "tags": build_tags(h),
    }


def end_punct(t):
    """统一句末标点：中文句号结尾。"""
    if not t:
        return t
    t = t.rstrip().rstrip("。；;，,")
    return t + "。"

# ---------------------------------------------------------------- 英雄索引（供克制/被克制引用真实英雄）
HERO_INDEX = {}


def hero_role(name):
    h = HERO_INDEX.get(name)
    if not h:
        return None
    return h.get("type_name")


def role_group(role):
    """把职业归并成玩家看得懂的对手类型。"""
    return {
        "战士": "近战战士", "坦克": "前排坦克", "法师": "爆发法师",
        "刺客": "突进刺客", "射手": "远程射手", "辅助": "辅助",
    }.get(role, role)


def build_counter(h, role, hero_map):
    """克制 = 真实克制名单中的英雄职业画像 + 职业共性补充。"""
    names = [n for n in (h.get("counters") or []) if n in hero_map]
    if not names:
        return ROLE_PROFILE[role]["counter"]
    roles = []
    for n in names:
        r = hero_map[n].get("type_name")
        if r and r not in roles:
            roles.append(r)
    if not roles:
        return ROLE_PROFILE[role]["counter"]
    groups = []
    for r in roles:
        g = role_group(r)
        if g not in groups:
            groups.append(g)
    sample = "、".join(names[:3]) + ("等" if len(names) > 3 else "")
    desc = "擅长压制" + "、".join(groups) + f"（如{sample}）"
    # 具体名单已经说明了克制对象，不再追加同义的职业共性句
    return desc


def build_weakto(h, role, hero_map):
    """被克制 = 真实威胁名单中的英雄职业画像 + 职业共性补充。"""
    names = [n for n in (h.get("countered_by") or []) if n in hero_map]
    if not names:
        return ROLE_PROFILE[role]["weakto"]
    roles = []
    for n in names:
        r = hero_map[n].get("type_name")
        if r and r not in roles:
            roles.append(r)
    if not roles:
        return ROLE_PROFILE[role]["weakto"]
    groups = []
    for r in roles:
        g = role_group(r)
        if g not in groups:
            groups.append(g)
    sample = "、".join(names[:3]) + ("等" if len(names) > 3 else "")
    desc = "容易被" + "、".join(groups) + f"针对（如{sample}）"
    # 同理：真实威胁名单已足够具体
    return desc


def main():
    src = open(SRC, encoding="utf-8").read()
    m = re.search(r"const HEROES\s*=\s*(\[.*?\]);", src, re.S)
    H = json.loads(m.group(1))
    hero_map = {h["cname"]: h for h in H}
    HERO_INDEX.update(hero_map)
    out = [map_hero(h, hero_map) for h in H]
    for o in out:
        for k in ("feat", "pros", "cons", "play", "counter", "weakto"):
            o[k] = end_punct(o[k])
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    # 同时产出浏览器可直接引用的 heroes.js（保持与 json 同源，避免两份漂移）
    js_path = os.path.join(OUT_DIR, "heroes.js")
    with open(js_path, "w", encoding="utf-8") as f:
        f.write("// 《全英雄使用指南》数据 —— 由 guide/build/map_data.py 生成，勿手改\n")
        f.write("// 规则映射自现有官方英雄数据，零成本、零模型调用；不含胜率/梯度/数值\n")
        f.write("window.GUIDE_DATA=")
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\n")

    from collections import Counter
    print("英雄数:", len(out))
    print("分路:", dict(Counter(x["lane"] for x in out)))
    print("职业:", dict(Counter(x["role"] for x in out)))
    print("难度:", dict(Counter(x["diff"] for x in out)))
    print("标签数:", len({t for x in out for t in x["tags"]}))
    bad = [t for x in out for t in x["tags"] if t not in TAG_SET]
    print("非法标签:", bad)
    lens = [(len(x[k]), x["n"], k) for x in out for k in ("feat", "pros", "cons", "play", "counter", "weakto")]
    oob = [l for l in lens if not (8 <= l[0] <= 60)]
    print("超长/过短字段:", len(oob), oob[:10])
    print("输出:", OUT)

if __name__ == "__main__":
    main()
