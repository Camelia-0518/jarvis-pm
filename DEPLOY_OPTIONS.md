# Jarvis PM 面试作品部署方案

> 目标：将 Jarvis PM 部署为可公网访问的面试展示作品
> 时间：2026-06-26

---

## 已完成的安全加固

| 项目 | 状态 | 说明 |
|------|------|------|
| CORS 配置 | ✅ | 支持 `*.ngrok-free.app`、`*.ngrok.io`、`*.trycloudflare.com` 及 localhost |
| 生产 Dockerfile | ✅ | 多阶段构建、非 root 用户运行、健康检查 |
| docker-compose.prod | ✅ | PostgreSQL + Redis + Nginx 反向代理 |
| Nginx 配置 | ✅ | API 代理、安全响应头、Gzip 压缩 |

---

## 方案对比

### 方案 A：Vercel（前端）+ Railway（后端）⭐ 最推荐

**适合人群**：有 GitHub 账号，追求一键部署和自动更新

| 组件 | 平台 | 费用 | 说明 |
|------|------|------|------|
| 前端 | **Vercel** | 免费 | 自动 CI/CD，全球 CDN，HTTPS |
| 后端 | **Railway** | 免费（$5 额度/月）| 一键部署，自动扩缩容 |
| 数据库 | Railway PostgreSQL | 免费 | 自动备份 |
| 域名 | Vercel 自带 | 免费 | `*.vercel.app` |

**优点**：
- 最专业，面试官最熟悉的部署方式
- 自动 HTTPS，无需配置
- Push 代码自动部署
- 全球 CDN，访问速度快

**缺点**：
- 需要 GitHub 账号
- Railway 免费额度有限（适合演示）
- 后端长时间无访问会休眠（可配置保活）

**部署步骤**：
1. 前端 push 到 GitHub → Vercel 自动部署
2. 后端 push 到 GitHub → Railway 自动部署
3. 配置环境变量（API URL、数据库、AI Key）

---

### 方案 B：Render（前端 + 后端）

**适合人群**：没有 Vercel 账号，想要一个平台搞定

| 组件 | 平台 | 费用 | 说明 |
|------|------|------|------|
| 前端 | Render Static | 免费 | 静态网站托管 |
| 后端 | Render Web Service | 免费 | 自动部署 |
| 数据库 | Render PostgreSQL | 免费 | 90 天有效期 |

**优点**：一个平台搞定全部
**缺点**：免费数据库 90 天过期，长时间无访问会休眠

---

### 方案 C：国内云服务器 + Docker（最稳定）

**适合人群**：有阿里云/腾讯云账号，追求长期稳定运行

| 组件 | 平台 | 费用 | 说明 |
|------|------|------|------|
| 服务器 | 阿里云轻量应用 | ~50-100元/年 | 2核2G 足够 |
| 域名 | 阿里云/腾讯云 | ~50元/年 | 需要备案（国内服务器） |
| 部署 | Docker Compose | 免费 | 已配置好 |

**优点**：
- 最稳定，24/7 运行
- 完全控制
- 适合长期展示

**缺点**：
- 需要购买服务器和域名
- 国内服务器需要备案（约 7-20 天）
- 需要手动配置 SSL

**部署步骤**：
1. 购买服务器和域名
2. 备案（国内服务器）
3. 服务器安装 Docker
4. 上传代码并运行 `docker-compose.prod.yml`

---

### 方案 D：Cloudflare Pages + Tunnel（免费，需要域名）

**适合人群**：已有域名，不想买服务器

| 组件 | 平台 | 费用 | 说明 |
|------|------|------|------|
| 前端 | Cloudflare Pages | 免费 | 静态网站，自动部署 |
| 后端 | Cloudflare Tunnel | 免费 | 暴露本地后端到公网 |
| 域名 | 已有域名 | 已有 | 需要域名 |

**优点**：完全免费，不需要服务器
**缺点**：后端依赖你的电脑开机，Tunnel 有流量限制

---

## 推荐选择

| 场景 | 推荐方案 |
|------|----------|
| 最快上线（今天就能展示）| **方案 A** Vercel + Railway |
| 长期稳定展示 | **方案 C** 国内云服务器 |
| 已有域名，不想花钱 | **方案 D** Cloudflare Pages + Tunnel |
| 不想折腾多个平台 | **方案 B** Render |

---

## 你需要准备

### 方案 A（Vercel + Railway）
- [ ] GitHub 账号
- [ ] Vercel 账号（可用 GitHub 登录）
- [ ] Railway 账号（可用 GitHub 登录）
- [ ] AI API Key（DeepSeek / Kimi / Anthropic 至少一个）

### 方案 B（Render）
- [ ] GitHub 账号
- [ ] Render 账号（可用 GitHub 登录）
- [ ] AI API Key

### 方案 C（国内云服务器）
- [ ] 阿里云/腾讯云账号
- [ ] 域名（阿里云/腾讯云/GoDaddy 等）
- [ ] 身份证（备案用）
- [ ] AI API Key

### 方案 D（Cloudflare）
- [ ] 已有域名
- [ ] Cloudflare 账号
- [ ] AI API Key

---

## 下一步

请告诉我你**已有哪些资源**（GitHub 账号、域名、服务器等），我帮你选择最合适的方案并**一步步执行部署**。

如果你有 GitHub 账号，推荐方案 A（Vercel + Railway），这是面试展示最专业的方式。
