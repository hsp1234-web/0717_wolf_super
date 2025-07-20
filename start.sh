#!/bin/bash

# --- 安裝 Poetry ---
echo "正在安裝 Poetry..."
pip install poetry

# --- 安裝專案依賴 ---
echo "正在安裝專案依賴..."
poetry install

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
  # 我們將 ssh 的輸出重新導向到 /dev/null，以避免它佔用終端機
  # 同時，我們將 ssh 在背景執行，這樣腳本才能繼續執行
  ssh -o "StrictHostKeyChecking=no" -o "ExitOnForwardFailure=yes" -R 80:localhost:8000 ssh.localhost.run > ssh_output.log 2>&1 &
  SSH_PID=$!

  # 等待幾秒鐘，看看 localhost.run 是否成功分配了網址
  sleep 10

  # 從 ssh 的日誌中提取網址
  URL=$(grep -o 'https://[a-zA-Z0-9-]*\.loclx.io' ssh_output.log)

  if [ -n "$URL" ]; then
    echo "===================================================================="
    echo "  服務網址： $URL"
    echo "===================================================================="
    # 讓 ssh 繼續在背景執行
    wait $SSH_PID
    break
  else
    kill $SSH_PID
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
      echo "連接失敗或無法取得網址，將在 $RETRY_DELAY 秒後重試..."
      sleep $RETRY_DELAY
    else
      echo "已達到最大重試次數，無法連接到 localhost.run。"
      exit 1
    fi
  fi
done
