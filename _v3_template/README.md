# _v3_template/ - 新增培训资料 HTML 模板

## 用途

复制 `lesson_template.html` → 改占位 → 保存为 `my_lesson_N.html` → 跑 `../add_training.py`。

## 占位说明

模板里有 5 个占位需要替换：

| 占位 | 替换为 | 例子 |
|---|---|---|
| `{{TITLE}}` | 资料标题 | `自动分拣机：托盘更换 SOP` |
| `{{META_DESCRIPTION}}` | 资料简短描述（用于 index.html 卡片） | `托盘更换步骤 · 安全规范 · 6 张操作截图` |
| `{{BVID}}` | B 站 BV 号（去掉 BV 前缀或保留都可以） | `BV1xxxxxxxx` |
| `{{LESSON_ID}}` | 资料编号（与 add_training.py --id 一致） | `6` |
| `{{DURATION}}` | 视频时长 | `4:30` 或 `270s` |

## 工作流（完整）

### 步骤 1：上传视频到 B 站
- 用大刘 B 站账号"喃呵咦檬"（UID 405067223）上传
- 选"公开"频道
- 拿 1 个 BV 号（如 `BV1xxxxxxxx`）

### 步骤 2：写文字稿
- 写 Markdown 格式文字稿
- 包含：场景描述、操作步骤、故障分析、注意事项
- 拍照关键步骤（base64 内嵌或上传到 hosting/figs/ 子目录）

### 步骤 3：复制模板
```bash
cp lesson_template.html my_lesson_6.html
```

### 步骤 4：替换占位
- 用文本编辑器（VSCode、记事本）打开 `my_lesson_6.html`
- 替换 5 个占位（见上表）
- 在 4 个 `<div class="section">` 里填实际内容

### 步骤 5：跑 add_training.py
```bash
cd ../
python3 add_training.py \
  --id 6 \
  --html _v3_template/my_lesson_6.html \
  --title "自动分拣机：托盘更换 SOP" \
  --bvid BV1xxxxxxxx \
  --duration "4:30"
```

### 步骤 6：推上 GitHub
```bash
git add lesson_6.html index.html
git commit -m "新增 demo6：托盘更换 SOP"
git push
```

等 1-2 分钟 → `https://huzhou-training.pages.dev/lesson_6.html` 上线。

## 永久禁词（2026-06-16 大刘要求）

**不要在 HTML 任何位置写**：
- "AI 生成"
- "湖州仓·设备组"（培训页 footer 里也不要）

`add_training.py` 跑前会自动检查禁词。

## 颜色规范

为保持视觉一致：
- 主色（深蓝）：`#1e40af`
- 深色（深海军蓝）：`#0a2a5e`
- 装饰（金色）：`#d4a847`
- 文字深灰：`#1a202c`
- 文字中灰：`#4a5568`
- 文字浅灰：`#6b7280`

## 字号规范

- 标题（H1）：22-28px
- 章节标题（H2）：16px
- 正文：14px
- 副文字：12-13px
