# Himawari Dynamic Wallpaper

[English](README.md) | 简体中文

一个基于 Himawari 卫星图的动态壁纸项目，现已整理为更适合上传 GitHub 的结构，并补上：

- Windows / macOS / Linux 自动识别
- 跨平台壁纸设置和登录自启动
- 可选的“仅下载/生成图片，不自动设置壁纸”模式
- Windows 下可选的锁屏同步
- 一个用于常用设置的简易 GUI
- 可安装的 CLI 入口
- 更顺手的初始化脚本
- 基础测试与 CI

## 当前支持

程序会自动识别当前系统：

- Windows：使用 `SystemParametersInfoW` 设置壁纸，支持启动菜单自启动
- Windows 锁屏同步：通过 `UserProfilePersonalizationSettings` 做可选的最佳努力更新
- macOS：使用 `osascript` 设置壁纸，支持 `LaunchAgents`
- Linux：优先尝试 `plasma-apply-wallpaperimage`、`gsettings`、`xfconf-query`、`feh`，支持 `~/.config/autostart`

说明：

- Linux 桌面环境差异很大，已经做成按能力自动降级。
- 如果当前 Linux 桌面不在支持列表内，程序会给出明确报错，而不是静默失败。

## 快速开始

推荐优先使用 conda，统一引导脚本默认也会走 conda：

```bash
python scripts/bootstrap.py
conda activate himawari-wallpaper
```

如果你想显式指定 conda 环境名：

```bash
python scripts/bootstrap.py --manager conda --conda-env-name himawari-wallpaper
conda activate himawari-wallpaper
```

开发依赖一起安装：

```bash
python scripts/bootstrap.py --dev
```

上传 GitHub 前可以一条命令自检：

```bash
python scripts/repo_check.py
```

如果你更希望把运行参数放到文件里，而不是记 CLI 参数：

```bash
# 先复制 config.example.json 为 config.json 并按需修改
python -m himawari_wallpaper --config ./config.json --once
```

也可以直接使用仓库提供的 conda 环境文件：

```bash
conda env create -f environment.yml
conda activate himawari-wallpaper
```

### Windows

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\bootstrap.ps1
conda activate himawari-wallpaper
himawari-wallpaper --once
```

Windows 下如果你仍然想用 venv 作为备选：

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\bootstrap.ps1 -UseVenv -VenvDir .venv
.\.venv\Scripts\Activate.ps1
himawari-wallpaper --once
```

### macOS / Linux

```bash
chmod +x scripts/bootstrap.sh
./scripts/bootstrap.sh
conda activate himawari-wallpaper
himawari-wallpaper --once
```

macOS / Linux 下如果你仍然想用 venv 作为备选：

```bash
chmod +x scripts/bootstrap.sh
./scripts/bootstrap.sh --venv-mode --venv .venv
source .venv/bin/activate
himawari-wallpaper --once
```

如果你显式选择了 venv 备选方案，并且在 Ubuntu / WSL 上第一次执行时看到 `ensurepip is not available` 或 `python3 -m venv` 失败，先安装：

```bash
sudo apt install python3-venv
```

## 手动安装

优先推荐的手动安装方式是 conda：

```bash
conda env create -f environment.yml
conda activate himawari-wallpaper
```

如果你还想加开发依赖：

```bash
python -m pip install -e ".[dev]"
```

如果你不想用 conda，`venv` 仍然保留为备选：

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
python -m playwright install chromium
```

支持的环境变量覆盖：

- `HIMAWARI_CONFIG`
- `HIMAWARI_OUTPUT_DIR`
- `HIMAWARI_INTERVAL_SECONDS`
- `HIMAWARI_MAX_ZOOM`
- `HIMAWARI_EARTH_HEIGHT_RATIO`
- `HIMAWARI_Y_OFFSET_RATIO`
- `HIMAWARI_APPLY_WALLPAPER`
- `HIMAWARI_SYNC_LOCK_SCREEN`
- `HIMAWARI_TARGET_URL`
- `HIMAWARI_NAVIGATION_TIMEOUT_MS`
- `HIMAWARI_WARMUP_WAIT_MS`
- `HIMAWARI_PROBE_STEP_SECONDS`
- `HIMAWARI_PROBE_LOOKBACK_STEPS`

优先级：

- CLI 参数高于环境变量
- 环境变量高于配置文件
- 配置文件高于内置默认值

配置文件示例见 [`config.example.json`](config.example.json)。

除了壁纸布局参数，配置文件现在也支持抓图相关参数：

- `target_url`
- `navigation_timeout_ms`
- `warmup_wait_ms`
- `probe_step_seconds`
- `probe_lookback_steps`

这些参数默认值已经适合当前 Himawari 页面，通常不需要改，只有在源站结构或加载节奏变化时才建议调整。

配置文件还支持行为开关：

- `apply_wallpaper`
- `sync_lock_screen`

首次发现阶段的回退顺序现在是：

1. 浏览器资源列表和页面图片
2. HTML 中的嵌入式探针图片 URL
3. `latest.json` 直连最新 D531106 时间
4. 本地缓存探针

这让第一次运行时对页面前端实现细节的依赖小了很多。

## 常用命令

单次刷新：

```bash
himawari-wallpaper --once
```

只生成 PNG 文件，由用户自行决定是否设置为壁纸：

```bash
himawari-wallpaper --once --download-only
```

Windows 下同时同步桌面壁纸和锁屏：

```bash
himawari-wallpaper --once --sync-lock-screen
```

Linux / WSL 抓图 smoke test，但不真正设置桌面壁纸：

```bash
himawari-wallpaper --once --download-only --out ./smoke-output
```

持续运行：

```bash
himawari-wallpaper --run --interval 3600
```

安装登录自启动：

```bash
himawari-wallpaper --install-startup --interval 3600
```

移除登录自启动：

```bash
himawari-wallpaper --remove-startup
```

清理本地运行数据、配置文件和自启动：

```bash
himawari-wallpaper-cleanup --all
```

如果你使用的是 conda，也可以顺手把 conda 环境一起删除：

```bash
python scripts/uninstall.py --all --remove-conda-env himawari-wallpaper
```

指定输出目录：

```bash
himawari-wallpaper --once --out ./data
```

使用配置文件：

```bash
himawari-wallpaper --config ./config.json --once
```

打开简易设置 GUI：

```bash
himawari-wallpaper --gui
# 或
himawari-wallpaper-gui
```

GUI 现在可以保存常用设置、单次运行、安装或移除开机自启、打开输出目录、
预览最新生成的壁纸、显示当前自启状态、显示最近一次生成的壁纸文件、
执行可选项的本地清理/卸载。按钮区现在分成 `Run` 和 `Environment`
两组，让日常操作和系统级操作分开。开机自启现在通过 GUI 中的
`Enable startup at login` 开关控制，
Windows 专属的锁屏相关控件会在 macOS / Linux 上自动禁用，
GUI 顶部还会显示当前识别到的平台，
并在 Windows 下用最新生成的壁纸 PNG 测试锁屏同步。

临时覆盖抓图参数：

```bash
himawari-wallpaper --once --target-url https://himawari.asia/ --navigation-timeout-ms 120000 --warmup-wait-ms 15000
```

## 默认输出目录

未指定 `--out` 时，程序会自动使用用户目录下的可写路径，而不是写进源码目录：

- Windows：`%LOCALAPPDATA%\HimawariDynamicWallpaper`
- macOS：`~/Library/Application Support/HimawariDynamicWallpaper`
- Linux：`$XDG_DATA_HOME/himawari-dynamic-wallpaper` 或 `~/.local/share/himawari-dynamic-wallpaper`

这比原来安装到 site-packages 后再向包目录写文件更稳妥。

## Linux 额外说明

Linux 壁纸设置会按顺序尝试以下后端：

- KDE Plasma: `plasma-apply-wallpaperimage`
- GNOME: `gsettings`
- XFCE: `xfconf-query`
- 通用兜底: `feh`

如果你的桌面环境不提供这些命令中的任何一个，抓图和拼图仍然能运行，但设置壁纸会失败并给出明确错误。

WSL 测试结论：

- `python3 -m pip install --user -e '.[dev]'` 可完成安装
- `python3 scripts/repo_check.py` 可完整通过
- `python3 -m playwright install chromium` 可完成浏览器安装
- WSL 中的无头 Chromium 已实测可启动并成功访问页面
- 可使用 `--once --download-only` 跑真实抓图 smoke test 而不触发桌面壁纸设置
- 真实 smoke test 已成功生成 `last_source_meta.json`、原图 PNG 和壁纸 PNG
- 首次发现失败时，`latest.json` 回退已实测可在 WSL 中拿到最新 D531106 时间并完成下载
- `himawari.asia` 在 WSL Chromium 中首屏导航可能偏慢，默认导航超时已提升到 `120000ms`
- 精简版 Ubuntu/WSL 可能缺少 `python3-venv`，这会影响 `bootstrap.py` / `bootstrap.sh` 的首轮创建虚拟环境
- WSL 不是完整 Linux 桌面会话，因此这里没有验证真实桌面壁纸设置后端

如果你只想先验证安装流程，可以跳过浏览器安装：

```bash
python scripts/bootstrap.py --skip-playwright
```

之后再手动执行：

```bash
python -m playwright install chromium
```

## 兼容旧入口

旧脚本入口仍保留：

```bash
python src/himawari_wallpaper_webzoom.py --once
```

但更推荐使用安装后的命令：

```bash
himawari-wallpaper --once
```

## 测试

```bash
pytest -q
```

## 发布

本地发布前检查：

```bash
python scripts/repo_check.py
python scripts/pack_release.py --label local
```

本地构建 Windows GUI 可执行发布包：

```bash
python -m pip install -e ".[release]"
python scripts/build_windows_bundle.py --label local
```

这个发布包现在会额外附带一个可直接编辑的 `config.json`，并把 Windows 版本信息注入到 `.exe` 文件里。

GitHub 自动发布：

- 推送 `v0.1.0` 这种 tag 后，GitHub Actions 会自动构建源码 zip 和 Windows GUI 发布包
- 也可以手动触发 `Release Package` 工作流，只生成打包产物

详细步骤见 [`docs/RELEASING.md`](docs/RELEASING.md)。
Windows 可执行包的细节见 [`docs/BUILD_WINDOWS_EXE.md`](docs/BUILD_WINDOWS_EXE.md)。

## 上传 GitHub 前建议

- 先运行一次 `himawari-wallpaper --once`
- 再运行 `pytest -q`
- 检查输出目录、日志和缓存没有被误提交
- 按 [`docs/GITHUB_UPLOAD_STEPS.md`](docs/GITHUB_UPLOAD_STEPS.md) 执行仓库初始化
