# 王者荣耀《百段野核教科书》视频→图文项目

最后整理：2026-11-17。所有产物已生成校验完毕（70集 × 4 套）。本文件是完整调用手册，方便后续继续处理新视频或重建产物。

## 一、项目构成

### 1. 脚本目录 `~/hok-site/guide/build/`（8 个脚本）

流水线顺序：
```
视频(MP4)
  → [asr_local.py]            本地 ASR 转写 → .json/.srt/.txt
  → [asr_fix_terms.py]        术语纠正 + 繁简统一 → .fixed.*
  ├→ [asr_to_image.py]        明细长图（口语全文，1800px宽）
  ├→ [asr_summarize.py]  → [asr_quickcard.py]   速记卡（一句话+3-6要点+口诀）
  └→ [asr_digest.py]     → [asr_digestcard.py]  精读卡（分节+编号+标点短句）
```

另有 `asr_retry.py`：ASR 幻觉污染集的针对性重转（一次性修复脚本，保留供参考）。

### 2. 源数据 `~/Desktop/百度下载/S44-零基础到百段野核教科书（百期连更通用/_transcripts/`
- 70 集 × 3 格式：`.fixed.txt` / `.fixed.srt` / `.fixed.json`（带时间戳）
- `_索引.md`：70 集分类索引（含字数、开头摘要）
- `_术语替换报告.json`：术语替换审计

### 3. 产物 `~/Desktop/王者荣耀技巧图文/`（286 MB）
| 路径 | 内容 | 数量 |
|---|---|---|
| 根目录 `*.png` | 明细长图（23 集英雄名前缀，其余原名） | 70 |
| `_速记卡/` | 速记卡 PNG | 70 |
| `_速记JSON/` | 速记结构化数据 | 70 |
| `_精读卡/` | 精读卡 PNG | 70 |
| `_精读JSON/` | 精读结构化数据 | 70 |
| `_重命名回滚映射.json` | 明细图改名的回滚映射 | — |

### 4. 关键资源
- ASR 模型：`~/models/whisper-medium/`（489MB，whisper-medium 的 MLX 版本：config.json + weights.npz）。**已从 /tmp 迁到持久目录，重启不丢。**
- 术语表：`asr_fix_terms.py` 内的 `TERMS` 字典
- Chrome（截图用）：`/Users/analyst/.hermes/tools/chromium-1208/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing`

## 二、运行环境（重要：不同脚本用不同 python）

| 用途 | Python | 说明 |
|---|---|---|
| ASR 转写 | `/opt/homebrew/Caskroom/miniforge/base/envs/mlx-audio/bin/python` | 装了 mlx_whisper；**别用系统 python** |
| 术语纠正 / JSON 处理 | `/usr/bin/python3` | 标准库即可 |
| 图片渲染（Playwright） | `/usr/bin/python3` | 装了 playwright；**后台启动时注意别继承 base conda 环境** |
| 提炼（速记/精读） | `/usr/bin/python3` + 本地 Ollama `http://127.0.0.1:11434` | 模型 qwen2.5:14b |

## 三、完整调用命令

设环境变量（按需）：
```
TD=~/Desktop/百度下载/S44-零基础到百段野核教科书（百期连更通用/_transcripts
OUT=~/Desktop/王者荣耀技巧图文
BUILD=~/hok-site/guide/build
MLXPY=/opt/homebrew/Caskroom/miniforge/base/envs/mlx-audio/bin/python
```

### 步骤1：新视频转写（本地 ASR）
```
$MLXPY $BUILD/asr_local.py <视频文件或目录> --model ~/models/whisper-medium
# --outdir 指定输出目录，--limit N 只处理前N个（测试用）
```

### 步骤2：术语纠正
```
/usr/bin/python3 $BUILD/asr_fix_terms.py <文件或目录> --report $TD/_术语替换报告.json
```

### 步骤3a：明细长图
```
/usr/bin/python3 $BUILD/asr_to_image.py --all --out $OUT
```

### 步骤3b：速记卡
```
/usr/bin/python3 $BUILD/asr_summarize.py --all --model qwen2.5:14b --out $OUT/_速记JSON
/usr/bin/python3 $BUILD/asr_quickcard.py --all --out $OUT/_速记卡
```

### 步骤3c：精读卡
```
/usr/bin/python3 $BUILD/asr_digest.py --all --model qwen2.5:14b --out $OUT/_精读JSON
/usr/bin/python3 $BUILD/asr_digestcard.py --all --out $OUT/_精读卡
```
提炼 + 渲染有"已存在则跳过"逻辑，新增集数后重跑只会处理新文件。

## 四、校验清单（每次重建后跑）

```
# 数量
ls $OUT/*.png | wc -l                    # 应 70
ls $OUT/_速记卡/*.png | wc -l            # 应 70
ls $OUT/_精读卡/*.png | wc -l            # 应 70
# 幻觉污染（应为0）
grep -l "字幕君" $TD/*.fixed.txt | wc -l
# 图片完好（Python PIL 逐张 verify）
```

## 五、踩坑记录（都已解决，勿重蹈）

1. **whisper 幻觉**：静音/纯音乐段会让转写变成"字幕君请不吝点赞订阅转发"循环（本次 003/065/067 集）。检测：统计该词出现≥3次。修复：`asr_retry.py`，关键是 `condition_on_previous_text=False` + `initial_prompt`。
2. **模型下载**：hf-mirror 的 Xet 分块下载会失败，用 curl 直连 `.../whisper-medium/resolve/main/weights.npz` 手动下载。模型必须在持久目录 `~/models/`，放 /tmp 重启会丢。
3. **LLM JSON 损坏**：qwen2.5 即使 `format=json` 也会输出截断/未转义字符串。`asr_digest.py` 已内置 `parse_robust_json` 容错 + `num_predict=8192` + 3 次重试。
4. **精读条目过长**：prompt 必须强制每条≤45字、出装/设置要拆多条，否则整段挤成 1 条。
5. **ASR 离谱错字**：名闻=铭文、初号=出装、毫升雷两多岁=10鹰眼10红月等，光靠 prompt 词表无效，`asr_digest.py` 里对源文本先 `.replace()` 预处理。
6. **文件名误匹配**：`ls *070*` 会命中 BV 号含 070 的其它集（如 060 的 `9907003`），精确匹配用 `ls 【070】*`。
7. **Conda 环境噪音**：后台 shell 启动会报 base conda 插件错误，无害；实际渲染用 `/usr/bin/python3`，不受影响。

## 六、回滚

明细图曾批量加英雄名前缀，如需恢复原名：
```
/usr/bin/python3 - <<'PY'
import json,os
m=json.load(open(os.path.expanduser("~/Desktop/王者荣耀技巧图文/_重命名回滚映射.json"),encoding="utf-8"))
for x in m:
    if os.path.exists(x["new"]): os.rename(x["new"],x["old"])
PY
```
