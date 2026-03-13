#!/bin/bash
# SNS投稿自動生成アプリの起動スクリプト
PYTHON="/home/hideyoshihommura/google-cloud-sdk/platform/bundledpythonunix/bin/python3.13"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

cd "$SCRIPT_DIR"

case "${1:-}" in
  --now)
    $PYTHON main.py --now
    ;;
  --web)
    $PYTHON main.py --web
    ;;
  *)
    echo "スケジューラーとWebダッシュボードを起動します..."
    $PYTHON main.py
    ;;
esac
