import os
import sys
from unittest.mock import MagicMock
import pytest
import requests

# Add project root to the Python path
PROJECT_ROOT_FROM_TEST_P0 = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)
if PROJECT_ROOT_FROM_TEST_P0 not in sys.path:
    sys.path.insert(0, PROJECT_ROOT_FROM_TEST_P0)

from prometheus.services.cli_services import _execute_single_download as execute_download

# Define the path to the fixture files
FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")

@pytest.fixture
def mock_session():
    """Fixture to create a mock requests.Session object."""
    return MagicMock(spec=requests.Session)

def test_execute_download_success(mock_session, tmp_path):
    """
    測試案例一 (成功情境):
    模擬 requests.get 回傳 sample_daily_ohlc_20250711.zip 的位元組內容。
    執行下載器函式。
    斷言 (Assert): 驗證目標路徑下是否成功創建了檔案，且檔案內容與我們的模擬位元組完全一致。
    """
    zip_fixture_path = os.path.join(FIXTURES_DIR, "sample_daily_ohlc_20250711.zip")
    with open(zip_fixture_path, "rb") as f:
        zip_content_bytes = f.read()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = zip_content_bytes
    mock_response.text = ""

    mock_session.get.return_value = mock_response

    task_info = {
        "url": "http://fakeurl.com/Daily_2025_07_11.zip",
        "file_name": "Daily_2025_07_11.zip",
        "min_delay": 0,
        "max_delay": 0,
    }
    output_dir = str(tmp_path)

    status, message = execute_download(mock_session, task_info, output_dir)

    assert status == "success"
    expected_file_path = os.path.join(output_dir, task_info["file_name"])
    assert os.path.exists(expected_file_path)
    with open(expected_file_path, "rb") as f:
        assert f.read() == zip_content_bytes

def test_execute_download_not_found(mock_session, tmp_path):
    """
    測試案例二 (失敗情境 - 404 Not Found):
    模擬 requests.get 回傳 404 狀態碼。
    執行下載器函式。
    斷言函式回傳 'not_found' 狀態，且沒有創建任何檔案。
    """
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_session.get.return_value = mock_response

    task_info = {
        "url": "http://fakeurl.com/not_found.zip",
        "file_name": "not_found.zip",
        "min_delay": 0,
        "max_delay": 0,
    }
    output_dir = str(tmp_path)

    status, message = execute_download(mock_session, task_info, output_dir)

    assert status == "not_found"
    expected_file_path = os.path.join(output_dir, task_info["file_name"])
    assert not os.path.exists(expected_file_path)

def test_execute_download_no_data_response(mock_session, tmp_path):
    """
    測試案例三 (失敗情境 - 查無資料):
    模擬 response.text = "查無資料".
    執行下載器函式。
    斷言函式回傳 'error'。
    """
    html_fixture_path = os.path.join(FIXTURES_DIR, "no_data_response.html")
    with open(html_fixture_path, "rb") as f:
        html_content_bytes = f.read()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = html_content_bytes
    mock_response.text = "查無資料"

    mock_session.get.return_value = mock_response

    task_info = {
        "url": "http://fakeurl.com/find_nothing_here",
        "file_name": "find_nothing_here.html",
        "min_delay": 0,
        "max_delay": 0,
    }
    output_dir = str(tmp_path)

    status, message = execute_download(mock_session, task_info, output_dir)
    assert status == "error"

def test_execute_download_file_already_exists(mock_session, tmp_path):
    """
    測試案例四 (成功情境 - 檔案已存在):
    先在目標路徑創建一個假檔案。
    執行下載器函式。
    斷言函式回傳 'exists' 狀態，且 requests.get() 完全不被呼叫。
    """
    task_info = {
        "url": "http://fakeurl.com/existing_file.zip",
        "file_name": "existing_file.zip",
        "min_delay": 0,
        "max_delay": 0,
    }
    output_dir = str(tmp_path)
    existing_file_path = os.path.join(output_dir, task_info["file_name"])
    with open(existing_file_path, "w") as f:
        f.write("i already exist")

    status, message = execute_download(mock_session, task_info, output_dir)

    assert status == "exists"
    mock_session.get.assert_not_called()

def test_execute_download_request_exception(mock_session, tmp_path):
    """
    測試 requests.exceptions.RequestException 的情境 (重試後依然失敗)。
    """
    mock_session.get.side_effect = requests.exceptions.RequestException(
        "Test network error"
    )

    task_info = {
        "url": "http://fakeurl.com/network_error_target.zip",
        "file_name": "network_error_target.zip",
        "min_delay": 0,
        "max_delay": 0,
    }
    output_dir = str(tmp_path)

    status, message = execute_download(mock_session, task_info, output_dir)

    assert status == "error"
    assert "網路請求失敗" in message
    expected_file_path = os.path.join(output_dir, task_info["file_name"])
    assert not os.path.exists(expected_file_path)
    assert mock_session.get.call_count == 3
