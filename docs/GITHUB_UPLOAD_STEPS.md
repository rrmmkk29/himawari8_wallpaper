# GitHub 上传步骤

## 1. 本地先跑通

Windows，推荐 conda：

```powershell
Set-ExecutionPolicy -Scope Process Bypass
python scripts/bootstrap.py --dev
conda activate himawari-wallpaper
python scripts/repo_check.py
```

Windows，venv 备选：

```powershell
Set-ExecutionPolicy -Scope Process Bypass
python scripts/bootstrap.py --manager venv --dev --venv .venv
.\.venv\Scripts\Activate.ps1
python scripts/repo_check.py
```

macOS / Linux，推荐 conda：

```bash
python scripts/bootstrap.py --dev
conda activate himawari-wallpaper
python scripts/repo_check.py
```

macOS / Linux，venv 备选：

```bash
chmod +x scripts/bootstrap.sh
python scripts/bootstrap.py --manager venv --dev --venv .venv
source .venv/bin/activate
python scripts/repo_check.py
```

如果你显式使用 venv 备选方案，并且在 Ubuntu / WSL 的精简环境中首次执行失败，先安装：

```bash
sudo apt install python3-venv
```

## 2. 上传前检查

至少确认这些点：

- README 已说明安装和运行命令
- `requirements.txt` 与 `pyproject.toml` 一致
- 如果你使用配置文件，`config.example.json` 已按需复制成自己的本地 `config.json`
- 如果你修改了抓图相关参数，`config.example.json` 与 README 说明也要同步
- 没有误提交本地缓存、日志、虚拟环境和个人路径
- 三个平台差异已经集中到平台适配层，而不是散落在主逻辑里
- `python scripts/repo_check.py` 可以完整通过
- 如果你用 WSL 做 Linux smoke test，记得区分“无头浏览器可运行”和“真实桌面壁纸可设置”这两层验证

## 3. 初始化 Git（Windows PowerShell）

在仓库根目录运行：

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\init_git.ps1 -RemoteUrl "https://github.com/你的用户名/你的仓库名.git"
```

如果你已经在 macOS / Linux 上有 Git 仓库，也可以手动执行：

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/你的用户名/你的仓库名.git
git push -u origin main
```

## 4. GitHub 仓库建议

- 启用 GitHub Actions
- 启用 secret scanning 与 push protection
- 如果后续引入大图片或缓存样本，使用 Git LFS
- 首次发布前补一条 release note，说明各平台支持范围
- 发布流程可直接参考 [`docs/RELEASING.md`](docs/RELEASING.md)

## 5. 合适的首轮后续任务

- 继续拆分网络抓取和图像拼接逻辑
- 补 Linux 更多桌面环境的壁纸设置实现
- 把运行配置进一步抽到独立配置文件
- 增加非网络单元测试和错误场景测试
