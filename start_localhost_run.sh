#!/bin/bash

# --- 在背景啟動 Gunicorn 伺服器 ---
echo "正在啟動 Gunicorn 伺服器..."
poetry run gunicorn -c gunicorn.conf.py prometheus.entrypoints.query_gateway:app &

# --- 等待 Gunicorn 啟動 ---
sleep 5

# --- 使用重試機制連接到 localhost.run ---
MAX_RETRIES=5
RETRY_DELAY=5
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
  echo "正在嘗試連接到 localhost.run (第 $((RETRY_COUNT + 1)) 次)..."
  ssh -o "StrictHostKeyChecking=no" -o "ExitOnForwardFailure=yes" -R 80:localhost:8000 ssh.localhost.run

  if [ $? -eq 0 ]; then
    echo "成功連接到 localhost.run！"
    break
  else
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
      echo "連接失敗，將在 $RETRY_DELAY 秒後重試..."
      sleep $RETRY_DELAY
    else
      echo "已達到最大重試次數，無法連接到 localhost.run。"
      exit 1
    fi
  fi
done
