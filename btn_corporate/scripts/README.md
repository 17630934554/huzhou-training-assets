# btn_html_slides.py · 贝泰妮品牌 HTML 幻灯片生成器

> 从 JSON / YAML / Markdown 配置 → 输出 BTN 品牌 HTML 幻灯片
> 6+ 种页面模板 · 文字可编辑 · 视频内嵌 · 单文件自包含

---

## 1. 快速开始

```bash
# 1) 用 YAML 配置
python3 btn_html_slides.py --config report.yaml --output report.html

# 2) 用 JSON 配置
python3 btn_html_slides.py --config report.json --output report.html

# 3) 用 Markdown 配置（适合手写）
python3 btn_html_slides.py --config report.md --output report.html

# 4) 强制单文件自包含（默认就是）
python3 btn_html_slides.py --config report.yaml --output report.html --self-contained

# 5) 不要内联（用相对路径引用资源）
python3 btn_html_slides.py --config report.yaml --output report.html --no-inline
```

输出文件可直接用浏览器打开（file://）或部署到任何静态托管（Cloudflare Pages / GitHub Pages 等）。

---

## 2. 页面类型

| 类型 | 说明 | 用途 |
|------|------|------|
| `cover` | 品牌蓝渐变封面 + 大标题 | 开场 |
| `toc` | 大数字目录 | 列出要点 |
| `stat` | 4 个 KPI 数字 | 关键数据 |
| `two-column` | 时间线 + 成就卡 | 重点案例 |
| `intro` | 3 列卡片 | 部门介绍 |
| `cta` | 多引用块 | 改造案例 |
| `planning` | 时间线 | 下半年规划 |
| `video` | 视频嵌入 | 视频演示 |
| `section` | 大数字章节 | 章节过渡 |
| `thanks` | 品牌渐变结束 | 致谢 |

---

## 3. 配置格式（YAML）

```yaml
meta:
  title: "贝泰妮物流部·设备组 2026 H1 汇报"
  brand: "贝泰妮集团"
  footer: "贝泰妮集团 物流部"

pages:
  # ================ 1. 封面 ================
  - type: cover
    kicker: "2026 · 年中汇报"
    title: "设备组<br><span>年中汇报</span>"
    lede: "培训资料系统 V3 · 改造案例 · 技术升级"
    logo: true  # 显示品牌 logo（默认 true）

  # ================ 2. 目录 ================
  - type: toc
    kicker: "Agenda"
    title: "汇报四件事"
    lede: "简短说明"  # 可选
    items:
      - n: "01"
        t: "设备文件管理"
        d: "培训资料系统 V2.1 → V3"
      - n: "02"
        t: "关键数据"
        d: "5 份 / 5 个 B 站 / 0 登录墙"
      - n: "03"
        t: "重点案例 V3"
        d: "GitHub + Cloudflare 自动部署"
      - n: "04"
        t: "改造案例"
        d: "动态秤 / 报警电眼 / 收纸机构"

  # ================ 3. 关键数据 ================
  - type: stat
    kicker: "Result"
    title: "一组关键数字"
    lede: "培训资料系统 V2.1 → V3 升级完成，扫码即看成为常态。"
    kpis:
      - v: "5"
        l: "份标准 SOP 培训页"
      - v: "5"
        l: "个 B 站教学视频"
      - v: "0"
        l: "登录墙 · 全部扫码即看"
      - v: "1"
        l: "行命令新增培训项"
    quote:  # 可选：底部引用块
      tag: "交付"
      body: "V3 升级 100% 上线：GitHub 私有仓库 + Cloudflare Pages 自动部署。"
      who: "2026-06-16 23:14 上线"

  # ================ 4. 双栏（时间线 + 成就卡）================
  - type: two-column
    kicker: "Case · V3"
    title: "V3 升级：4 段时间线"
    lede: "可选副标题"
    timeline:
      - time: "21:38 · V2.1 终态"
        what: "Cloudflare Pages hosting 上线"
        why: "5 份 lesson + QR 卡 · 永久有效链接"
      - time: "22:40 · Git 初始化"
        what: "私有仓库就绪 + add_training.py"
        why: "一条命令新增培训项，端到端验证"
    achievements:
      - icon: "01"
        t: "永久链接"
        d: "Cloudflare Pages 全球 CDN<br>HTTP 200 验证 5/5 通过"
      - icon: "02"
        t: "扫码即看"
        d: "本人 / 内部 / 外部 / 匿名<br>全部无登录墙"
      - icon: "03"
        t: "自助更新"
        d: "add_training.py 一条命令<br>新视频 5 分钟内上线"

  # ================ 5. 部门介绍 ================
  - type: intro
    kicker: "Department"
    title: "部门介绍"
    lede: "设备组 · 5 人 · 湖州仓"
    sections:
      - num: "01"
        title: "人员"
        body: "5 人 · 1 主管 + 4 工程师"
      - num: "02"
        title: "职责"
        body: "设备运维 / SOP 编写 / 改造"
      - num: "03"
        title: "范围"
        body: "贴单机 / 分拣机 / 打印机"

  # ================ 6. 改造案例 ================
  - type: cta
    kicker: "Optimization"
    title: "设备改造 3 个案例"
    lede: "小成本改造，解决一线痛点。"
    cases:
      - tag: "CASE 01"
        title: "动态秤校准机构改造"
        body: "加装气缸定位模块，秤盘归位偏差从 ±3mm 降到 ±0.5mm，故障率下降 60%。"
        who: "包裹称重工位 · SOP 培训页 lesson_2"
      - tag: "CASE 02"
        title: "报警电眼升级"
        body: "替换为漫反射 + 偏振滤镜方案，强光环境下误报率从 8% 降到 0.5%。"
        who: "自动贴面单机 · SOP 培训页 lesson_1"

  # ================ 7. 下半年规划 ================
  - type: planning
    kicker: "H2 Planning"
    title: "下半年 3 件事"
    timeline:
      - time: "Q3 · 培训资料 5 → 8"
        what: "再上 3 份设备 SOP"
        why: "覆盖团购新线 / 退货设备 / 异常处理"
      - time: "Q3 · 设备改造 5 项"
        what: "动态秤 / 报警电眼 / 收纸机构"
        why: "故障率再降 30%"
      - time: "Q4 · V4 系统升级"
        what: "扫码统计 + 培训效果看板"
        why: "谁看了 / 看几次 / 看多久"

  # ================ 8. 视频 ================
  - type: video
    kicker: "Demo"
    title: "现场讲解视频"
    lede: "扫码即看 · 永久有效"
    bv_id: "BV1xx411c7mD"  # B 站 BV 号（去掉 BV 前缀也可）
    # 或
    # video: "videos/demo.mp4"
    # video_type: "mp4"
    tip: "B 站视频可直接在线播放，无需登录"  # 可选

  # ================ 9. 结束 ================
  - type: thanks
    kicker: ""
    title: "感谢聆听"
    lede: "设备组 · 2026 年中汇报"
    logo: true
    hints: true  # 显示操作提示
```

---

## 4. 关键特性

### 4.1 文字可编辑 + localStorage 自动保存

打开 HTML 后，**双击**进入编辑模式，所有文字可直接编辑。修改后自动保存到 `localStorage`，刷新不丢失。

- 默认所有 `contenteditable="true"` 元素可编辑
- 双击切换编辑模式（再次双击退出）
- 编辑模式有视觉提示（背景 + 圆角 + 编辑栏）
- localStorage key 跟 title 关联，刷新仍保留

### 4.2 视频嵌入（3 种方式）

```yaml
# 方式 1：B 站 BV 号（推荐，扫码即看，永久有效）
- type: video
  bv_id: "BV1xx411c7mD"  # 自动转 iframe 嵌入

# 方式 2：本地 mp4
- type: video
  video: "videos/lesson_1.mp4"  # 相对路径
  video_type: "mp4"

# 方式 3：远程 URL
- type: video
  video: "https://example.com/video.mp4"
  video_type: "mp4"
```

### 4.3 单文件自包含

生成的 HTML 把所有 CSS / JS 内联进 `<head>` 和 `<body>` 末尾：
- `fonts.css` + `base.css` + `btn-corporate.css` + `animations.css` 全部内联
- `runtime.js`（键盘翻页 + 主题切换）全部内联
- 单文件约 50-80KB，可直接 `file://` 打开

如需保持外链（用于 GitHub Pages 等），加 `--no-inline` 参数。

### 4.4 BTN 品牌主题

内置 `btn-corporate.css` 主题（深蓝 #0a2540 + 亮蓝 #1d4ed8 + 金色 #c9a35d + 14px 圆角）：
- `cover` / `thanks` 页用品牌蓝渐变
- `toc` / `stat` / `two-column` 页用白色背景 + 品牌蓝点缀
- KPI 数字自动用渐变色 + 金色错位
- 时间线节点用品牌蓝 + 金色交替
- 成就卡左侧渐变条

---

## 5. 键盘快捷键

生成的幻灯片支持：
- `←` / `→`：上 / 下一页
- `T`：切换主题
- `A`：切换动画
- `F`：全屏
- `O`：概览模式
- `S`：演讲者备注
- **双击空白处**：进入 / 退出编辑模式

---

## 6. 部署

### Cloudflare Pages

```bash
# 单文件部署
cp report.html /path/to/hosting/report.html
git add report.html
git commit -m "feat(btn-corporate): add H1 report"
git push origin main
# Cloudflare Pages 自动部署
```

### GitHub Pages

```bash
# 上传到 docs/ 目录
mkdir -p docs
cp report.html docs/index.html
git add docs/
git commit -m "deploy"
git push
```

---

## 7. 示例

- `examples/btn-deck.html` — 6 页示范
- `examples/btn-report-2026h1.html` — 8+ 页完整版（设备组年中汇报）

---

## 8. 依赖

- Python 3.8+
- 配置文件若是 YAML 格式，需 `pip install pyyaml`

---

## 9. 配套资源

- `../assets/btn-corporate.css` — 贝泰妮品牌主题
- `../../skills/html-ppt/assets/runtime.js` — 键盘翻页 + 主题切换
- `../../skills/html-ppt/assets/base.css` — 基础样式
- `../../skills/html-ppt/assets/animations/animations.css` — 动画

---

## 10. 路线图

- [x] 6 种基础页面模板
- [x] 文字可编辑 + localStorage
- [x] 视频嵌入（B 站 / 本地 / 远程）
- [x] 单文件自包含
- [ ] 导出 PDF（用 puppeteer）
- [ ] 飞书多维表格同步
- [ ] 模板变量插值
- [ ] 多人协作编辑
