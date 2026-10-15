# Brain Relay

**换一个 AI 窗口，工作也能接着做。**

[English](README.md) · [MIT 许可证](LICENSE)

把目标、背景、已确认决定、候选决定、废弃方案、下一步和资料引用组织为一个任务胶囊。保存到本机，生成交接文本，复制给任意 AI 或明天的自己。主流程无需账户、密钥或模型。

![合成示例的工作区](docs/images/workspace-dark.png)

## 两分钟启动

需要 Python 3.10 或更新版本。在仓库目录运行：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
brain-relay
```

打开 **http://127.0.0.1:7332**。Windows 激活命令为 `.venv\Scripts\activate`。也可以用 `python -m brain_relay`，加 `--port 7340` 更换端口。

1. 点击“加载合成示例”，或“新建胶囊”。
2. 修改目标、背景和各条记录，自己确认决定；候选保持待确认，废弃方案不会进入下一步。
3. 点击“保存到本机”，重启后可从“已保存胶囊”重新打开。
4. 点击“预览交接文本”，核对后复制或下载 `.txt`。
5. 点击“预览 JSON 导出”，检查后下载 `.json`。另一位使用者可导入、编辑并保存。

下载内容与预览一致。**分享前检查你填入的摘录和来源；Relay 不会自动脱敏个人信息。**

## Alpha 已有能力

- 普通表单编辑、UTF-8 JSON 无损导入导出和原子本地保存。
- 严格区分已确认与候选；否定方案不会变成待办。
- 来源、条目记录时间及胶囊更新时间进入交接文本。
- 可选字符预算：完整内容放不下时拒绝生成部分交接，并报告所需字符与遗漏类别，不静默截断。按 Unicode 字符计数，**不是模型 token**。
- 中英界面、明暗主题、键盘操作、移动布局和 `/styleguide` 组件样板。
- 可选模型提炼：只得到待核对草稿，所有决定先设为待确认，不会自动保存成品。

## 可选：模型提炼

启动前设置三个环境变量：`BRAIN_MODEL_URL`（完整 chat-completions 地址）、`BRAIN_MODEL_NAME`、`BRAIN_MODEL_KEY`。三个全部设置或全部留空。不要求认证的本地服务可以使用无敏感信息的占位 key。

本地兼容服务示例：

```bash
export BRAIN_MODEL_URL=http://127.0.0.1:1234/v1/chat/completions
export BRAIN_MODEL_NAME=your-local-model
export BRAIN_MODEL_KEY=local-unused
brain-relay
```

远程服务必须用 HTTPS；通过自己的凭证管理器把 key 注入进程环境，不写进源码、`.env`、浏览器或 shell 历史。应用不会读取凭证库或 `.env`，不会使用 HTTP 代理环境变量。上游重定向一律拒绝，不转发 Authorization。

点击“提炼草稿”才会把粘贴对话、任务标题、schema 和提炼要求发给配置的服务。模型服务可能收费，数据处理取决于该服务的政策。手动编辑不会联系模型；测试只使用本地假 HTTP 服务，不调用真实付费模型。

key 不进入浏览器、本地胶囊、导出和日志。模型报错只显示安全错误；不合 schema 的结果失败，不拿固定示例冒充成功。模型仍可能误读或编造，请逐条检查草稿与来源；引用有效和人工勾选不证明语义正确。

## 数据与边界

默认保存到 `~/.local/share/brain-relay/capsules.json`，可用 `RELAY_DATA_DIR=/path/to/data` 指定目录。备份这个文件即可；也支持逐个胶囊导出。同一 ID 更新覆盖旧值，UI 导入已有 ID 时会确认覆盖。保存期间继续编辑时，只保存请求发出时的快照，后续编辑仍显示未保存；修改内容、切换胶囊或改变预算后，过期预览不会重新出现。写失败保留原文件，已有数据损坏会明确报错，不自动清空。

这是**单人、单进程、本地应用**，一个目录只运行一个进程。没有账户系统、云同步或静态加密。仅监听 `127.0.0.1`；校验回环 Host，同源与 CSRF 拦住跨站写入。不要公开部署 Flask 开发服务器或放到公网反向代理后；用操作系统账户和磁盘保护本地数据。

上限：100 个胶囊；每节 100 条；主要文本字段 20,000 字符；单胶囊 250,000 UTF-8 字节；请求 500,000 字节；对话 60,000 字符。模型任务 2 个工作线程、最多 8 个未完成任务、32 条保留记录、30 分钟保留期。任务仅在内存，重启丢弃；已保存胶囊保留。上游 I/O 超时 35 秒，浏览器等待有界，超出等待窗口可“检查状态”。

不记录聊天历史。粘贴对话只用于提炼请求，不单独存盘；你确认保存的提炼字段可能包含摘录，这些字段会进入导出。

## API 与开发

先 `GET /api/bootstrap` 得到 cookie 和 `csrf_token`，写请求同时携带该 cookie 及 `X-CSRF-Token`，浏览器要求同源。

- `GET /api/example`：合成示例，`origin=demo`，不会自动保存。
- `POST /api/capsules` 或 `/api/import`：直接传完整胶囊对象，校验并保存。
- `GET /api/capsules/<id>/export`：已保存胶囊 JSON 附件。
- `POST /api/handoff`：`{"capsule": {...}, "max_chars": null}`。预算不足返回 422、`budget_too_small`、所需字符及遗漏计数，不返回部分文本。
- `POST /api/extract`：`{"conversation":"...", "title":"..."}`，202 返回 `task_id`。
- `GET /api/jobs/<task_id>`：`queued/running/succeeded/failed`；成功只返回草稿，失败不返回成品。
- `/healthz`、`/`、`/styleguide`：健康检查、工作区和组件样板。

完整 schema 见[合成示例](brain_relay/examples/park-map.json)。只支持版本 1，拒绝未知字段。`confirmed` 必须为 JSON 布尔值，不接受字符串 `"false"`。时间戳必须带时区。`origin` 只有 `manual/demo/configured provider`，只是来源提示，不是防伪签名。

```bash
python -m pip install '.[test]'
python -m pytest -q
```

测试覆盖多语言与多行往返、重启持久化、确认状态、预算、恶意 HTML、跨站请求、模型失败和真实本地 HTTP 协议。CI 使用 Python 3.10/3.14，构建 wheel 后从源码目录外验证已安装模板和示例。无前端构建；UI 规则见 [DESIGN.md](DESIGN.md)。

浏览器状态回归已接入两个 Python 版本的 CI。本机完整运行：安装 `.[test,browser]`，执行 `python -m playwright install chromium`，再执行 `python -m pytest -q`。测试自动启动独立回环服务并使用临时数据，覆盖保存后继续编辑、延迟保存/预览/导入响应与输出失效；未安装 browser extra 时该模块明确跳过。
