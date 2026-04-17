# 发布流程

## 本地发布前检查

先在仓库根目录执行：

```bash
python scripts/repo_check.py
```

如需本地预打包：

```bash
python scripts/pack_release.py --label local
```

如需本地构建 Windows 可双击运行的 GUI 发布包：

```bash
python -m pip install -e ".[release]"
python scripts/build_windows_bundle.py --label local
```

推荐先使用 conda 环境，再执行这些命令。

产物会输出到 `release/` 目录，目录本身已在 `.gitignore` 中忽略。

## GitHub Actions 自动发布

仓库现在包含发布工作流：

- 文件：`.github/workflows/release.yml`
- 触发方式 1：推送形如 `v0.2.2` 的 tag
- 触发方式 2：在 GitHub Actions 页面手动触发 `Release Package`

## 推荐发布步骤

1. 更新 `CHANGELOG.md`
2. 确认 `pyproject.toml` 版本号正确
3. 检查 `LICENSE`、作者信息、仓库链接等元数据是否正确
4. 运行 `python scripts/repo_check.py`
5. 如需 Windows GUI 包，本地可先执行 `python scripts/build_windows_bundle.py --label vX.Y.Z`
6. 提交改动并推送
7. 创建并推送 tag，例如：

```bash
git tag v0.2.2
git push origin v0.2.2
```

8. 等待 GitHub Actions 生成 release zip 并附加到 GitHub Release

## 卸载与清理

移除本地运行数据、配置和自启动：

```bash
himawari-wallpaper-cleanup --all
```

如果你是用 conda 管理环境，也可以删除 conda 环境：

```bash
python scripts/uninstall.py --all --remove-conda-env himawari-wallpaper
```

现在 Release 会同时产出：

- 源码发布包
- Windows GUI `.exe` 发布包

## 发布包内容

发布 zip 会包含源码、文档和脚本，但会排除：

- 虚拟环境
- 构建目录
- 测试缓存
- 本地 `.env`
- 本地 `config.json`
- 运行时日志与壁纸缓存产物

Windows GUI 发布包会包含：

- `himawari-dynamic-wallpaper-gui.exe`
- `README.md`
- `README.zh-CN.md`
- `config.example.json`
- `config.json`

此外：

- 可执行文件会注入来自 `pyproject.toml` 的 Windows 版本信息
- 如果存在 `assets/windows/app.ico`，打包脚本会自动把它作为程序图标

更多细节见 [`docs/BUILD_WINDOWS_EXE.md`](BUILD_WINDOWS_EXE.md)。

## 注意

- `config.example.json` 会保留在发布包中
- 用户自己的 `config.json` 不会被打包
- 如果你想使用自定义发布标签，可以手动触发工作流并填写 `release_label`
