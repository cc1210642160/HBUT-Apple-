# HBUT 课表自动同步到 Apple 日历（GitHub Actions + Pages）

这个项目会定时抓取 HBUT 教务课表，生成标准 `.ics` 文件，供 Apple 日历通过订阅链接自动更新。

## 功能

- 每周自动同步（默认：周一 + 周四 07:00，北京时间）
- 半自动登录态（Cookie）刷新，降低验证码/风控导致的中断概率
- 输出固定订阅地址：`https://<github-username>.github.io/<repo>/<ICS_TOKEN>.ics`
- 提供手动触发和 Cookie 有效性校验工作流
- 解析器支持 JSON 优先，HTML 回退（建议用真实样本持续校准）

## 目录结构

- `src/hbut_timetable/`：核心代码
- `config/term.json`：学期参数
- `config/periods.json`：节次起止时间
- `config/calendar_meta.json`：日历元信息
- `docs/`：Pages 发布目录（运行时生成 `.ics`，不再提交回仓库）
- `.github/workflows/sync-ics.yml`：定时同步
- `.github/workflows/validate-cookie.yml`：定时/手动校验 Cookie
- `tests/`：单元测试

## 1. 本地准备

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
pytest
```

## 2. 修改配置

### `config/term.json`

- `xnxq`：学年学期（例：`2025-2026-2`）
- `term_start` / `term_end`：学期日期范围（`YYYY-MM-DD`）

### `config/periods.json`

按学校真实作息填写节次对应时间，例如：

```json
"1": {"start": "08:00", "end": "08:45"}
```

### `config/calendar_meta.json`

- `name`：Apple 日历显示名称
- `timezone`：默认 `Asia/Shanghai`

## 3. 提供真实响应样本（强烈建议）

当前仓库内 `tests/fixtures/sample_payload.json` 是示例结构，不保证和你的教务系统完全一致。

建议你抓一次已登录请求响应，并替换/新增夹具：

1. 浏览器登录教务系统
2. 打开开发者工具 Network
3. 找到 `queryKbForXsd?xnxq=...` 请求
4. 复制 Response 原文到 `tests/fixtures/` 下
5. 根据真实字段调整 `src/hbut_timetable/parser.py` 的别名映射

## 4. GitHub 仓库配置

1. 把项目推送到 GitHub 仓库。
2. 在仓库 `Settings -> Secrets and variables -> Actions` 添加：

- `HBUT_COOKIE`：登录后的完整 Cookie 字符串
- `ICS_TOKEN`：随机长字符串（建议 32+ 位），用于文件名

3. 在 `Settings -> Pages`：

- Source 选择 `GitHub Actions`

## 5. 手动运行与校验

### 本地手动同步

```bash
export HBUT_COOKIE='...'
export ICS_TOKEN='your_random_token'
hbut-sync --repo-root . --no-jitter
```

输出文件：`docs/<ICS_TOKEN>.ics`

如果你不想在本地生成 `latest-sync.json`：

```bash
hbut-sync --repo-root . --no-jitter --skip-meta
```

### 只校验 Cookie 是否可用

```bash
export HBUT_COOKIE='...'
hbut-check-cookie --repo-root .
```

## 6. 自动同步工作流

- `sync-ics.yml`：
  - 定时：每周一/周四 07:00（北京时间）
  - 也支持 `workflow_dispatch` 手动触发
  - 失败时自动创建 issue 提醒排障

- `validate-cookie.yml`：
  - 每天 06:30（北京时间）自动触发
  - 也支持手动触发
  - 快速判断 `HBUT_COOKIE` 是否过期/失效

## 7. Apple 日历订阅

当 Actions 首次成功后，订阅链接为：

`https://<github-username>.github.io/<repo>/<ICS_TOKEN>.ics`

在 iPhone/macOS 日历中添加“订阅日历”并粘贴链接。

注意：Apple 的订阅刷新频率由系统控制，不保证实时。

## 8. 常见问题

- 提示跳转登录：`HBUT_COOKIE` 失效，重新抓取并更新 Secret
- 课程数量为 0：课表接口字段结构变化，需按真实响应更新 `parser.py`
- 订阅没变化：检查 Actions 是否成功、Pages 部署是否成功、Apple 端是否已刷新

## 9. 防封禁策略（已内置）

- 每次任务随机抖动 10-60 秒
- 单轮最多 1 次重试
- 低频定时（每周 2 次）
- 固定 User-Agent，不做并发轰炸
