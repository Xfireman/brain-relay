# Brain Relay

## 换个对话，不必再从头解释。

目标已经讲过，两个方案已经否定，下一步也定好了。可一换 AI 对话，你又得花几轮把背景重新说一遍。

**Brain Relay 给下一段对话一个明确的起点：正在做什么，哪些已经定了，哪些还没定，接着做哪一步。**

[试用示例](#试用示例) · [下载 Alpha](https://github.com/Xfireman/brain-relay/releases/tag/v0.1.0-alpha.1) · [English](README.md)

本地运行 · 主流程无需 API key · MIT 开源 · Alpha

### 把决定留下，也把“没决定”留下

普通总结容易抹平重要的区别：“考虑过”变成了“已经决定”，明确否定的方案又被建议一次。

Relay 给不同信息各留一个位置。你核对目标、背景、决定、废弃方案、下一步和来源，再把交接文本复制给下一个 AI。

内置“社区公园地图”虚构示例的交接要点是这样的：

> - **目标**：给新邻居做一份中英双语步行地图。
> - **已确认**：使用可打印的 A4 地图。
> - **待确认**：是否用二维码补充无障碍路线。
> - **已否定**：收集游客位置数据。
> - **下一步**：核对公交站和无障碍入口。

这几种状态会跟着任务一起交过去。下一个 AI 能看到哪些需要确认，哪些已经否定；它后续做得对不对，仍由你核对。

![左侧编辑任务，右侧预览交接文本，内容为虚构示例](docs/images/workspace-dark.png)

*左边整理，右边核对。下载的文本与预览一致。*

### 把工作带到下一个地方

- **换一个 AI 对话**：复制交接文本即可，不需要浏览器插件或关联账户。
- **明天接着做**：重新打开保存的任务，决定和下一步都还在。
- **交给同事**：导出核对过的胶囊，对方导入后可以编辑并继续使用。

你决定哪些信息值得放进任务胶囊。主流程手动编辑、保存在本机，无需模型；也可配置模型，从粘贴的对话中提炼草稿，逐条确认后再保存。

## 试用示例

需要 Python 3.10+ 和 Git。macOS / Linux 执行：

```sh
git clone https://github.com/Xfireman/brain-relay.git
cd brain-relay
python3 -m venv .venv
. .venv/bin/activate
python -m pip install .
brain-relay
```

打开 **http://127.0.0.1:7332**，需要时切换到中文：

1. 点击“加载合成示例”。
2. 看看 A4 地图、二维码和位置数据，分别处于什么状态。
3. 补一条自己的下一步，点击“保存到本机”。
4. “预览交接文本”，核对后复制进一个新的 AI 对话。

需要以后继续编辑时，使用“预览 JSON 导出”与“下载 .json”。分享前检查完整内容，你填入的正文、摘录和来源都会随文件一起分享。

Windows 使用 `py -m venv .venv` 创建环境，执行 `.venv\Scripts\activate` 激活。也可[下载源码压缩包](https://github.com/Xfireman/brain-relay/releases/tag/v0.1.0-alpha.1)，解压后在目录中安装。安装后可在任意目录运行 `brain-relay`，加 `--port 7340` 可更换端口。

### 哪些任务值得带走

当一件事已经积累了足够多的决定，**重新解释开始打断工作**，就适合用 Relay。交接是你能看清、能修改的文本。若设置的字符预算放不下完整内容，它会报告缺口，避免悄悄删掉决定。

首版保存在本机，通过复制文本或传文件来交接，暂不提供账户间自动同步。

想复用一套做事方法，看 [Brain Recipes](https://github.com/Xfireman/brain-recipes)；想向已有笔记提问，看 [Brain Twin](https://github.com/Xfireman/brain-twin)。

## 可选：模型提炼

<details>
<summary>展开对话提炼的模型配置</summary>

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

</details>

## 数据与边界

<details>
<summary>展开存储、隐私和使用边界</summary>

默认保存到 `~/.local/share/brain-relay/capsules.json`，可用 `RELAY_DATA_DIR=/path/to/data` 指定目录。备份这个文件即可；也支持逐个胶囊导出。同一 ID 更新覆盖旧值，UI 导入已有 ID 时会确认覆盖。保存期间继续编辑时，只保存请求发出时的快照，后续编辑仍显示未保存；修改内容、切换胶囊或改变预算后，过期预览不会重新出现。写失败保留原文件，已有数据损坏会明确报错，不自动清空。

这是**单人、单进程、本地应用**，一个目录只运行一个进程。没有账户系统、云同步或静态加密。仅监听 `127.0.0.1`；校验回环 Host，同源与 CSRF 拦住跨站写入。不要公开部署 Flask 开发服务器或放到公网反向代理后；用操作系统账户和磁盘保护本地数据。

上限：100 个胶囊；每节 100 条；主要文本字段 20,000 字符；单胶囊 250,000 UTF-8 字节；请求 500,000 字节；对话 60,000 字符。模型任务 2 个工作线程、最多 8 个未完成任务、32 条保留记录、30 分钟保留期。任务仅在内存，重启丢弃；已保存胶囊保留。上游 I/O 超时 35 秒，浏览器等待有界，超出等待窗口可“检查状态”。

不记录聊天历史。粘贴对话只用于提炼请求，不单独存盘；你确认保存的提炼字段可能包含摘录，这些字段会进入导出。

</details>

## API 与开发

<details>
<summary>展开 API、数据格式与开发说明</summary>

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

</details>
