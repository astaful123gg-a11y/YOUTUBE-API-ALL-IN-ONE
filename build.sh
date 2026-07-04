#!/usr/bin/env bash
# Render build script — installs ffmpeg + Node.js (needed for yt-dlp EJS challenge solver)
set -e

echo "==> Installing system packages..."
apt-get update -qq
apt-get install -y -qq ffmpeg nodejs npm

echo "==> Installing Python packages..."
pip install --upgrade pip
pip install -r requirements.txt

echo "==> Build complete."
