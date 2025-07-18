# 檔案: tests/ignition_test.py
import pytest


@pytest.mark.smoke
def test_critical_imports():
    """
    🔥 點火測試 🔥
    此測試的唯一目的，是在不執行任何邏輯的情況下，
    驗證系統所有關鍵組件都可以被成功導入，
    以捕獲循環依賴或頂層導入錯誤。
    """
    try:
        from prometheus.core.clients.client_factory import ClientFactory  # noqa: F401
        from prometheus.core.db.data_warehouse import DataWarehouse  # noqa: F401
        from prometheus.core.queue.sqlite_queue import SQLiteQueue  # noqa: F401
        from prometheus.entrypoints import query_gateway, real_worker_app  # noqa: F401

        print("\n✅ 所有關鍵組件導入成功。")
    except ImportError as e:
        pytest.fail(f"🔥 點火失敗：關鍵組件導入錯誤: {e}")
