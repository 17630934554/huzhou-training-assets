# 培训资料系统 V3 完整部署 SOP

> **目标**：把 5 份培训资料（已托管在 `https://huzhou-training.pages.dev`）升级到 V3 — GitHub 私有仓库 + Cloudflare Pages 自动部署。
> **效果**：大刘在 GitHub 网页改一行 → 1-2 分钟自动部署生效。新增一条资料 = 跑一行命令 + 一次 git push。

## 阶段总览

| 阶段 | 工作 | 谁 | 时间 |
|---|---|---|---|
| 1 | GitHub 注册 + 邮箱验证 + 手机验证 | 大刘 | 5 分钟 |
| 2 | 创建私有仓库 + 生成 PAT token | 大刘 | 5 分钟 |
| 3 | 主 Agent 用 PAT 推 hosting 目录上 GitHub | 主 Agent | 10 分钟 |
| 4 | Cloudflare Pages 关联 GitHub 仓库 | 大刘 | 5 分钟 |
| 5 | 验证自动部署 | 大刘 + 主 Agent | 2 分钟 |
| **总计** | | | **27 分钟** |

---

## 阶段 1：GitHub 注册（5 分钟，大刘本人操作）

### 步骤 1.1：访问注册页
打开 <https://github.com/signup>

### 步骤 1.2：填注册信息
- **Email**：`316194672@qq.com`（**必填** — 跟 Cloudflare 同邮箱）
- **Password**：跟 Cloudflare 同密码 `lys17630934554` 或另设一个强密码
- **Username**：`huzhou-training-admin` 或其他（这个会出现在 commit 链接里，建议用英文/拼音）
- 勾选 ✅ 接受条款

### 步骤 1.3：邮箱验证
- GitHub 发验证邮件到 `316194672@qq.com`
- **去 QQ 邮箱网页版**（<https://mail.qq.com>）或 QQ 邮箱 App
- 找到 GitHub 邮件 → 点 **Verify email address**

### 步骤 1.4：手机验证
- GitHub 强制要手机号
- ⚠️ **国内手机号（+86）** 能收
- 选 China (+86) → 填手机号 → 收短信 → 填验证码
- 如果收不到，换个时间（GitHub 短信偶发不稳定）

### 步骤 1.5：选 plan
- 选 **Free**（免费版）
- 私有仓库免费版无限制
- 协作者最多 3 人（够用）

### 步骤 1.6：完成
- 进入 GitHub 主界面 <https://github.com>
- 右上角头像能点开就说明成功

---

## 阶段 2：创建私有仓库 + 生成 PAT（5 分钟，大刘本人操作）

### 步骤 2.1：创建仓库

1. GitHub 右上角 **`+`** → **New repository**
2. 填：
   - **Repository name**：`huzhou-training-assets`（**这个要记住**，主 Agent 要用）
   - **Description**：`湖州仓·设备组培训资料系统 V3 — 长期托管 + 自动部署`
   - **Private** ⚠️ **必须选 Private**（不要选 Public，会暴露源码）
   - ⚠️ **Add a README file** ❌ **不要勾**（主 Agent 会推 README）
   - ⚠️ **Add .gitignore** ❌ **不要勾**（None 选这个）
   - ⚠️ **Choose a license** ❌ **不要勾**
3. 点 **Create repository**
4. 创建后**复制仓库 URL**（形如 `https://github.com/316194672@qq.com/huzhou-training-assets`），发主 Agent

### 步骤 2.2：生成 PAT token（Personal Access Token）

1. GitHub 右上角 **头像** → **Settings**
2. 左侧最下 **Developer settings**
3. 左侧 **Personal access tokens** → **Tokens (classic)**
4. 点 **Generate new token** → **Generate new token (classic)**
5. 填：
   - **Note**：`huzhou-training-push`
   - **Expiration**：选 **90 days**（之后可重新生成，主 Agent 会提醒）
   - **Scopes**：**只勾 `repo`**（最小权限，不要勾其他）
     - ☑️ `repo` — Full control of private repositories
     - ❌ 其他全部不勾
6. 点 **Generate token**
7. ⚠️ **token 只显示一次**！**立即复制**（形如 `ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`），发给主 Agent

### 步骤 2.3：把仓库 URL 和 PAT 发主 Agent

格式：
```
仓库 URL: https://github.com/316194672@qq.com/huzhou-training-assets
PAT token: ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

⚠️ **PAT 风险提示**：
- 这个 token 拥有完整仓库读写权限
- **只能给主 Agent**，不要发给别人
- 90 天后主 Agent 会提醒你重新生成
- 用完可随时在 GitHub Settings → Developer settings → Personal access tokens 撤销

---

## 阶段 3：主 Agent 推 hosting 目录上 GitHub（10 分钟，主 Agent 操作）

主 Agent 收到 PAT 后：

1. 用 GitHub Contents API（**不用 git bash**，更安全）：
   - 逐个上传 `index.html` / `lesson_1.html` ~ `lesson_5.html` / `add_training.py` / `deploy_sop_v3.md` / `.gitignore` / `_v3_template/*` / `scripts/*`
2. 第一次上传是新增（PUT），后续是更新（PATCH）
3. 完成后报告"已推 11 个文件"

⚠️ **lesson_*.html 单文件 400KB~1.4MB**，GitHub Contents API 单文件最大 100MB，OK。

⚠️ **大刘 5 份 lesson 都有大刘的真实截图（base64 内嵌）**，5 份总 5.2MB，符合 GitHub 仓库单文件 < 100MB 限制。

---

## 阶段 4：Cloudflare Pages 关联 GitHub（5 分钟，大刘本人操作）

### 步骤 4.1：进入 Cloudflare Pages 项目
1. 打开 <https://dash.cloudflare.com/>
2. 用 `316194672@qq.com` 登录
3. 左侧 **Workers 和 Pages** → **Pages**
4. 找到 **huzhou-training**（之前 V2.1 部署的）→ 点开

### 步骤 4.2：进入 Builds 设置
1. 点 **Settings** 标签
2. 左侧 **Builds** → **Build configuration**
3. 找到 **Source** 部分（当前可能是 Direct Upload，因为之前是拖的）
4. 点 **Connect to Git** 按钮（或 **Change source** 如果有）

### 步骤 4.3：选 GitHub
1. 选 **GitHub** → 点 **Connect GitHub**
2. 弹出 GitHub 授权页 → 选 `316194672@qq.com` 账号
3. 选 `Only select repositories` → 选 **`huzhou-training-assets`**
4. 点 **Install & Authorize**

### 步骤 4.4：配构建参数
- **Production branch**: `main`（默认）
- **Build command**: **留空**（静态站不需要）
- **Build output directory**: **`/`**（根目录）
- **Root directory (advanced)**: 留空或填 `/`

### 步骤 4.5：保存
- 点 **Save and Deploy**
- Cloudflare 会自动从 GitHub 拉取代码 → 1-3 分钟首次部署完成
- ⚠️ 首次部署期间，旧版（V2.1 拖的）继续在线，不会中断

---

## 阶段 5：验证自动部署（2 分钟）

### 步骤 5.1：大刘改一行测试

1. GitHub 仓库 <https://github.com/316194672@qq.com/huzhou-training-assets>
2. 点开 `index.html` → 右上角 ✏️ Edit
3. 改一行无关紧要的（比如加个空格）→ 点 **Commit changes**
4. 等 1-2 分钟

### 步骤 5.2：检查自动部署

1. Cloudflare Pages → huzhou-training → **Deployments** 标签
2. 应该看到新的一次 deployment 状态 = **Success**
3. 访问 <https://huzhou-training.pages.dev> → 看到新版本生效

### 步骤 5.3：主 Agent 验证

主 Agent 跑：
```bash
curl -I https://huzhou-training.pages.dev
curl -I https://huzhou-training.pages.dev/lesson_1.html
```

都应返回 HTTP 200。

✅ **V3 上线！**

---

## 日常使用 SOP

### 场景 1：改文字 / 改截图 / 改视频

```
GitHub 网页 → 选文件 → Edit → 改 → Commit → 等 1-2 分钟
```

### 场景 2：新增一条培训资料

#### 步骤 A：准备（一次性）
1. 上传视频到 B 站 → 拿 BV 号
2. 写文字稿（Markdown）
3. 复制 `_v3_template/lesson_template.html` → 改占位 → 保存为 `my_lesson_6.html`

#### 步骤 B：跑脚本生成标准件
```bash
cd hosting/
python3 add_training.py \
  --id 6 \
  --html my_lesson_6.html \
  --title "自动分拣机：托盘更换 SOP" \
  --bvid BV1xxxxxxxx \
  --duration "4:30"
```
输出：
- `lesson_6.html`（最终标准版）
- `index.html`（更新，5 份卡片变 6 份）
- `qr/hosting_6_QR卡.png`（新 QR 卡）

#### 步骤 C：推上 GitHub 触发自动部署
```bash
git add lesson_6.html index.html
git commit -m "新增 demo6：托盘更换 SOP"
git push
```
等 1-2 分钟 → `https://huzhou-training.pages.dev/lesson_6.html` 上线

#### 步骤 D：飞书侧同步（可选）
- 把 `qr/hosting_6_QR卡.png` 上传到飞书云空间 QR卡/ 目录
- 在多维表格加一条记录（培训页 + QR卡 字段）

### 场景 3：回滚版本

1. GitHub 仓库 → **Commits** 历史
2. 找到上一个能用的 commit
3. 点 **Revert** 按钮 → 创建反向 commit
4. 等 1-2 分钟 → 自动回滚

### 场景 4：多人协作（加同事）

1. GitHub 仓库 → **Settings** → **Collaborators** → **Add people**
2. 输同事 GitHub 用户名
3. 选 **Write**（可 push）或 **Read**（只能看）
4. 同事接受邮件邀请 → 可共同编辑

---

## 排错指南

### 错误 1：Cloudflare Pages 自动部署失败，状态 = Failed

**症状**：Deployments 标签显示红色 ✗

**排查**：
1. 点失败那次部署 → 看 **Build log**
2. 常见原因：
   - **"No such file or directory"**：build output 设错，应为 `/`
   - **"Build command failed"**：build command 不该填，留空
   - **"404 on repository"**：GitHub 仓库没 push 上去，主 Agent 重推

### 错误 2：改了 GitHub 但 Cloudflare 没自动部署

**排查**：
1. Cloudflare → Settings → Builds → 确认 Source = GitHub（不是 Direct Upload）
2. 确认 Repository = `huzhou-training-assets`（不是其他）
3. 看 Webhook 状态：Settings → Builds → Webhooks → 应该有 GitHub push webhook

### 错误 3：手机收不到 GitHub 验证短信

**解决**：
- 换时间再试（GitHub 短信通道偶发不稳定）
- 用 GitHub App 验证（部分用户可选）

### 错误 4：PAT token 失效

**症状**：主 Agent push 报 401 Unauthorized

**解决**：
1. 大刘重新生成 PAT（步骤 2.2）
2. 把新 PAT 发主 Agent

### 错误 5：GitHub Contents API 单文件 > 100MB

**症状**：lesson_*.html 推不上去

**解决**：
- 当前 5 份 lesson_*.html 总 5.2MB，单文件最大 1.4MB，**远低于 100MB 限制**
- 如未来某份资料 > 100MB，考虑压缩图片或拆成多页

---

## 安全 checklist（一次性）

- [ ] 仓库 Private ✅
- [ ] 不 commit `*.env` / `*token*` / `*.pem`
- [ ] PAT token 仅主 Agent 持有
- [ ] 90 天后主 Agent 提醒重新生成 PAT
- [ ] 用完可在 GitHub 撤销 PAT

## 长期维护

- 视频源：建议在 B 站建立播放列表 <https://space.bilibili.com/405067223>
- 培训资料：每年大版本（V4.0、V5.0...）时更新 README
- 主 Agent 协助：Coze 渠道"九方"
- 数据备份：每季度把 hosting/ 目录下载一份到本地

---

**最后更新**：2026-06-16 22:xx（V3.0 上线）
**维护者**：大刘（湖州仓·设备组）
