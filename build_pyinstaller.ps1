param(
    [string]$Name = "StickerMaker",
    [switch]$Clean,
    [switch]$Debug,
    [string]$Entry = "app/pyi_launcher.py"
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$distDir = Join-Path $root "dist"
$workDir = Join-Path $root "build"

if ($Clean -and (Test-Path $workDir)) { Remove-Item -Recurse -Force $workDir }
if ($Clean -and (Test-Path $distDir)) { Remove-Item -Recurse -Force $distDir }

New-Item -ItemType Directory -Path $distDir -Force | Out-Null
New-Item -ItemType Directory -Path $workDir -Force | Out-Null

# 只需要 onedir：强制始终使用 --onedir
$modeArgs = @("--onedir")

# 运行时资源（相对工作目录需要匹配代码里的路径）
# - QIcon 需要 `resource/shoko.png`
# - rembg 模型需要 `resource/models/*.onnx`
# - 视频/魔法工具需要 `resource/exe/ffmpeg.exe`、`resource/exe/magick.exe`
# - GIF 合成代码也支持 `gif/magick.exe`（如果存在）
$addDataArgs = @(
    "--add-data", "app/resource/shoko.png;resource",
    "--add-data", "app/resource/models;resource/models",
    "--add-data", "app/resource/exe;resource/exe",
    "--add-data", "gif;gif"
)

$cmd = @(
    "-m", "PyInstaller",
    "--noconfirm",
    "--clean",
    "--name", $Name,
    "--distpath", $distDir,
    "--workpath", $workDir,
    "--paths", "app",
    "--windowed"
) + $modeArgs + $addDataArgs

# PySide6 / qfluentwidgets 有时需要显式收集以避免缺模块
$cmd += @(
    "--collect-all", "PySide6",
    "--collect-all", "qfluentwidgets"
)

if ($Debug) {
    $cmd += "--debug=all"
}

$entryPath = Join-Path $root $Entry
Write-Host "Building: $entryPath"
& python $cmd $entryPath

Write-Host "Done. 输出目录：$distDir"

