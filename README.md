# RePKG GUI

RePKG（notscuffed/repkg）的轻量级 Windows 图形封装，负责调度 RePKG.exe 并实时展示日志，本身不实现 PKG/TEX 解析。

## 运行前提

- Windows 10 / 11（x64）
- 已安装 [uv](https://docs.astral.sh/uv/)
- 已安装 .NET 运行时（RePKG.exe 自身依赖，版本见 RePKG 官方说明）
- 自行下载的 `RePKG.exe`（本项目不分发；首次启动时通过文件选择器指定）

## 运行步骤

```bash
cd repkg-gui
uv sync
uv run repkg-gui
```

等价启动方式：

```bash
uv run python -m repkg_gui
```

从终端 `uv run` 启动时终端窗口保持占用属正常现象；RePKG 子进程不会额外弹出控制台窗口。

## 使用说明

- 输入：点击「浏览文件」选择 `.pkg` / `.mpkg` / `.tex`，或「浏览文件夹」；也可直接把文件或文件夹拖进窗口。
- 输出：默认 `桌面/RePKG_Output`，可手动更改。
- 三种模式：
  - 单文件 / 单目录提取：`repkg extract [路径] -o [输出]`
  - 递归批量提取：追加 `-r`
  - 仅 TEX 目录转换：`repkg extract -t -s [目录] -o [输出]`（自动锁定 `-e tex`，禁用 `-c` / `-n` / `--no-tex-convert`）
- 复选框与扩展名过滤对应 CLI 参数：`-c`、`-n`、`--no-tex-convert`、`--overwrite`、`-e`、`-i`。
- 「查看信息」执行 `repkg info [路径] -e -p *`（目录追加 `-r`），输出以信息模式标注。
- 任务运行中可点「取消」终止进程，已生成的文件保留。

## 配置

配置保存在项目根目录 `config.json`（RePKG 路径、默认输出目录、最近输入、最近 10 条历史），已被 `.gitignore` 排除，不入库、不写用户目录。

## 常见问题

- **提示缺少 .NET 运行时**：安装 .NET 6.0 或更高版本后重试。
- **路径含空格失败**：本工具以参数列表启动子进程，不做 shell 拼接，空格路径可直接使用。
- **输出目录无写入权限**：换一个有权限的目录（如用户目录下），不要直接写到系统盘根目录。
- **UnknownMagic / not supported**：文件不是 Wallpaper Engine 正版 PKG/TEX。
