# 湖州仓·设备组培训资料系统 V3

> **长期托管** · **Git 版本控制** · **扫码即看** · **永久有效**

本仓库是湖州仓·设备组培训资料系统的 V3 升级版，配合 [Cloudflare Pages](https://pages.cloudflare.com/) 实现：
- 改一行 → 1-2 分钟自动部署
- 新增一条 → 跑一行命令 → 自动同步
- 完整版本控制（改错可回滚）

## 📂 仓库内容

```
hosting/
├── index.html              # 5 份资料导航页（白底+深蓝+金色装饰条）
├── lesson_1.html ~ lesson_5.html  # 5 份培训资料（永久托管）
├── add_training.py         # 端到端新增资料脚本
├── deploy_sop_v3.md        # V3 完整部署 SOP
├── .gitignore              # 忽略备份/缓存/QR 卡 PNG
├── _v3_template/           # 新增资料 HTML 模板
│   ├── lesson_template.html
│   └── README.md
├── scripts/                # 部署辅助脚本
│   ├── repack_zip.py
│   └── verify_urls.py
├── _old_qr_backup/         # V1 飞书版 QR 卡备份（不入版本）
└── training_hosting.zip    # 部署临时包（不入版本）
```

## 🎯 5 份资料

| # | 标题 | 永久 URL |
|---|---|---|
| 01 | 自动贴单机：对贴面单报警故障处理 | <https://huzhou-training.pages.dev/lesson_1.html> |
| 02 | 自动贴单机：频繁断底纸+收纸器不收纸故障处理 | <https://huzhou-training.pages.dev/lesson_2.html> |
| 03 | 自动贴单机：标签电眼的调试 | <https://huzhou-training.pages.dev/lesson_3.html> |
| 04 | 自动贴单机：整机开箱调试及操作 | <https://huzhou-training.pages.dev/lesson_4.html> |
| 05 | 自动分拣机：动态秤校准调试 | <https://huzhou-training.pages.dev/lesson_5.html> |

主域名：<https://huzhou-training.pages.dev>

## 🚀 大刘自助操作清单

### ✅ 修改一条资料（改文字/改截图/改视频）

1. 打开 GitHub 仓库 <https://github.com/316194672@qq.com/huzhou-training-assets>（私有）
2. 点开 `lesson_3.html` → 右上角 ✏️ Edit
3. 改你要改的部分（直接 HTML 编辑）
4. 点 **Commit changes**
5. 等 1-2 分钟 → `https://huzhou-training.pages.dev/lesson_3.html` 同步生效

### ✅ 新增一条培训资料（视频+文字 → 长期有效）

1. **前期准备**（一次性）：
   - 上传视频到 B 站公开频道（拿 1 个 BV 号）
   - 写好培训资料文字稿（Markdown 格式）
   - 按 `_v3_template/lesson_template.html` 模板改一份新 HTML

2. **跑脚本**（一行命令）：
   ```bash
   python3 add_training.py \
     --id 6 \
     --html _v3_template/my_lesson_6.html \
     --title "自动分拣机：托盘更换 SOP" \
     --bvid BV1xxx \
     --duration "4:30"
   ```
   - 自动生成 `lesson_6.html` + QR 卡 + 更新 `index.html`

3. **推上 GitHub**（触发自动部署）：
   ```bash
   git add lesson_6.html index.html
   git commit -m "新增 demo6：托盘更换 SOP"
   git push
   ```
   - 等 1-2 分钟 → `https://huzhou-training.pages.dev/lesson_6.html` 上线

4. **飞书侧同步**（可选）：
   - 把 QR 卡 PNG 上传到飞书云空间 QR卡/ 目录
   - 在多维表格 `Ul0Kb1Fy6arl8EsOqqPcsCkInvd` 加一条记录

### ✅ 回滚版本

1. GitHub 仓库 → Commits 历史
2. 找到上一个能用的 commit → "Revert this commit" 按钮
3. 自动反向部署 → Cloudflare Pages 1-2 分钟同步

## 🔒 协作权限

- **大刘（你）**：仓库 Owner → 完整读写
- **受邀同事**（如需要）：GitHub Settings → Collaborators → Add people → 选 Write/Read
- **其他人**：无 GitHub 账号，**只能通过公开 URL 查看**（天然只读）✅

## ⚙️ Cloudflare Pages 关联配置

- **Production branch**: `main`
- **Build command**: （空，静态站）
- **Build output directory**: `/`（根目录）
- **环境变量**: 无
- **自动部署**: push → 1-2 分钟生效

## 🚨 安全提示

- 仓库**必须 Private**（已设）
- 不要把 `*.env` / `*token*` / PAT token 提交到仓库
- PAT token 仅给主 Agent 用一次，**用完可在 GitHub Settings 撤销**
- B 站 vd_source 是公开参数，不算敏感

## 📞 联系

- 维护：大刘（湖州仓·设备组）
- 主 Agent 协助：Coze 平台"九方"
- 仓库：<https://github.com/316194672@qq.com/huzhou-training-assets>

## 📜 变更历史

- **V3.0** (2026-06-16 22:xx) — 升级到 GitHub + Cloudflare Pages 自动部署
- **V2.1** (2026-06-16 19:34) — Cloudflare Pages 拖拽部署 5 份
- **V2** (2026-06-16 17:00) — 飞书 docx 路线作废（飞书 system 强制登录拦截）
- **V1** (2026-06-16 16:00) — 飞书 file HTML（飞书 App 扫码空白，仅作 backup）
- **V0** (2026-06-16 14:00) — Coze 短链（30 天到期，已自然失效）
