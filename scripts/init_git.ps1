param(
    [Parameter(Mandatory=$true)]
    [string]$RemoteUrl,

    [string]$CommitMessage = "Initial public release: cross-platform Himawari dynamic wallpaper"
)

$ErrorActionPreference = 'Stop'

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "Git 未安装或未加入 PATH。"
}

if (-not (Test-Path .git)) {
    git init
}

git add .
git commit -m $CommitMessage 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "首次提交可能因为没有变更或未配置 git 用户信息而失败，请按提示处理。"
}

git branch -M main

if (git remote get-url origin 2>$null) {
    git remote set-url origin $RemoteUrl
} else {
    git remote add origin $RemoteUrl
}

Write-Host "已完成本地 Git 初始化。"
Write-Host "接下来执行："
Write-Host "git push -u origin main"
