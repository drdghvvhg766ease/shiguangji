# Windows 侧安装 FFmpeg（可选，用于视频封面与时长探测）
# 用法：powershell -ExecutionPolicy Bypass -File install-ffmpeg.ps1
# 也可手动下载 https://www.gyan.dev/ffmpeg/builds/ 解压后把 bin 加入 PATH

$ErrorActionPreference = "Stop"
$dest = "C:\tools\ffmpeg"
$zip = "$env:TEMP\ffmpeg.zip"
$url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"

if (Get-Command ffmpeg -ErrorAction SilentlyContinue) {
  Write-Host "ffmpeg 已在 PATH 中：" (Get-Command ffmpeg).Source
  exit 0
}

Write-Host "下载 FFmpeg…"
Invoke-WebRequest -Uri $url -OutFile $zip

Write-Host "解压到 $dest…"
New-Item -ItemType Directory -Force -Path $dest | Out-Null
Expand-Archive -Path $zip -DestinationPath $dest -Force

$bin = Get-ChildItem -Path $dest -Recurse -Directory | Where-Object { $_.Name -eq "bin" } | Select-Object -First 1
if (-not $bin) { throw "未找到 bin 目录" }

$binPath = $bin.FullName
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$binPath*") {
  [Environment]::SetEnvironmentVariable("Path", "$userPath;$binPath", "User")
  Write-Host "已加入用户 PATH: $binPath"
  Write-Host "请重新打开终端后生效。"
}

Write-Host "完成。验证：ffmpeg -version"
