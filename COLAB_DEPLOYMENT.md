# 在 Google Colab 中部署普羅米修斯之火

本指南將引導您如何在 Google Colab 環境中，快速部署並啟動「普羅米修斯之火」量化研究框架。

## 步驟一：準備 Colab 環境

首先，打開一個新的 Colab 筆記本。

## 步驟二：安裝必要的系統套件

為了讓我們的框架順利運行，需要先安裝一些系統層級的工具。在一個 Colab cell 中執行以下命令：

```python
!apt-get update && apt-get install -y git
```

## 步驟三：下載專案原始碼

接下來，我們從 GitHub 上將最新的專案程式碼複製到 Colab 環境中。

```python
!git clone https://github.com/chenchih/prometheus-fire.git
%cd prometheus-fire
```

## 步驟四：安裝 Python 依賴

本專案使用 Poetry 進行依賴管理。我們將安裝 Poetry 並透過它來安裝所有需要的 Python 套件。

```python
!pip install poetry
!poetry install
```

**注意**: Colab 環境可能會預先安裝某些套件的特定版本。如果遇到依賴衝突，可以嘗試 `!poetry install --no-root`。

## 步驟五：啟動服務並取得公開網址

萬事俱備！現在我們將啟動 FastAPI 伺服器與背景工人。我們特別使用 `start_colab.py` 腳本，它整合了 `localhost.run` 服務，能為您的 Colab 實例產生一個公開的網址。

在一個新的 cell 中執行以下命令：

```python
!poetry run python start_colab.py
```

執行後，您應該會在輸出中看到類似以下的訊息：

```
[INFO] Your service is publicly available at: https://<some-random-name>.lhr.life
```

這個 `https://...lhr.life` 就是您的作戰指揮中心的公開網址！將它複製到瀏覽器中打開，即可開始使用。

## 重要提醒

-   **生命週期**: Colab 筆記本的執行環境不是永久的。如果您關閉瀏覽器或閒置時間過長，環境將會被重置，您需要重新執行以上所有步驟。
-   **資源限制**: Colab 的免費方案有計算資源與使用時間的限制。對於大規模、長時間的分析任務，建議在本地或更專業的雲端伺服器上運行。
-   **API 金鑰**: 如果您的分析需要使用到外部 API (例如 FinMind)，請記得在 `config.yml` 檔案中填入您的 API 金鑰。您可以使用 Colab 的檔案編輯器來修改它。
