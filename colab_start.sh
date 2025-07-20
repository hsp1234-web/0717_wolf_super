#!/bin/bash

# --- 安裝 Poetry ---
echo "正在安裝 Poetry..."
pip install poetry

# --- 安裝專案依賴 ---
echo "正在安裝專案依賴..."
poetry install

# --- 安裝 ngrok ---
echo "正在安裝 ngrok..."
pip install pyngrok

# --- 在背景啟動 ngrok ---
echo "正在啟動 ngrok..."
poetry run python start_ngrok.py &

# --- 等待 ngrok 啟動 ---
sleep 5

# --- 啟動 Gunicorn 伺服器 ---
echo "正在啟動 Gunicorn 伺服器..."
poetry run gunicorn -c gunicorn.conf.py prometheus.entrypoints.query_gateway:app
