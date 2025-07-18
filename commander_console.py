# -*- coding: utf-8 -*-
"""
commander_console.py

普羅米修斯計畫 - 指揮官控制台

用於向遠程運行的普羅米修斯系統提交任務。
"""
import argparse
import requests
import sys

def main():
    """主執行函數。"""
    parser = argparse.ArgumentParser(description="向普羅米修斯系統提交任務的指揮官控制台。")
    parser.add_argument(
        "--url",
        required=True,
        help="普羅米修斯系統的公開訪問網址 (由 Colab 提供)。"
    )
    parser.add_argument(
        "--symbol",
        type=str,
        default="TSLA",
        help="要分析的股票代碼。"
    )
    parser.add_argument(
        "--window",
        type=int,
        default=20,
        help="簡單移動平均線 (SMA) 的計算窗口期。"
    )
    args = parser.parse_args()

    api_endpoint = f"{args.url.rstrip('/')}/api/v1/submit_task"

    task_payload = {
        "task_type": "simple_moving_average",
        "payload": {
            "symbol": args.symbol,
            "window": args.window
        }
    }

    print(f"📡 準備向 {api_endpoint} 提交任務...")
    print(f"   - 任務類型: {task_payload['task_type']}")
    print(f"   - 股票代碼: {args.symbol}")
    print(f"   - 計算窗口: {args.window}")

    try:
        response = requests.post(api_endpoint, json=task_payload, timeout=20)
        response.raise_for_status()  # 如果狀態碼不是 2xx，則引發異常

        result = response.json()
        print("\n✅ 任務成功提交！")
        print(f"   - 伺服器回應: {result.get('message')}")
        print(f"   - 任務 ID: {result.get('task_id')}")
        print("\n請在 Colab 的「神之眼」儀表板中觀察日誌以確認執行情況。")

    except requests.exceptions.RequestException as e:
        print(f"\n❌ 提交任務失敗: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
