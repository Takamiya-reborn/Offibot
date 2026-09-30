# 打包 offibot.exe(单文件,含内置技能)
# 用法:在仓库根目录执行 .\build.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

uv run python -m PyInstaller package.spec --noconfirm
if ($LASTEXITCODE -ne 0) {
    Write-Error "PyInstaller 打包失败(退出码 $LASTEXITCODE)"
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "打包完成: $PSScriptRoot\dist\offibot.exe" -ForegroundColor Green
