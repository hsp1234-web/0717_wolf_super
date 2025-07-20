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

# --- 產生並顯示公開網址 ---
echo "正在產生 Colab 公開網址..."
poetry run python start_colab.py
