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

产物会输出到 `release/` 目录，目录本身已在 `.gitignore` 中忽略。

## GitHub Actions 自动发布

仓库现在包含发布工作流：

- 文件：`.github/workflows/release.yml`
- 触发方式 1：推送形如 `v0.1.0` 的 tag
- 触发方式 2：在 GitHub Actions 页面手动触发 `Release Package`

## 推荐发布步骤

1. 更新 `CHANGELOG.md`
2. 确认 `pyproject.toml` 版本号正确
3. 运行 `python scripts/repo_check.py`
4. 提交改动并推送
5. 创建并推送 tag，例如：

```bash
git tag v0.1.0
git push origin v0.1.0
```

6. 等待 GitHub Actions 生成 release zip 并附加到 GitHub Release

## 发布包内容

发布 zip 会包含源码、文档和脚本，但会排除：

- 虚拟环境
- 构建目录
- 测试缓存
- 本地 `.env`
- 本地 `config.json`
- 运行时日志与壁纸缓存产物

## 注意

- `config.example.json` 会保留在发布包中
- 用户自己的 `config.json` 不会被打包
- 如果你想使用自定义发布标签，可以手动触发工作流并填写 `release_label`
