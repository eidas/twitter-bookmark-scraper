# X.com ブックマークスクレイピングシステム 設計書

## 1. システム概要

X.com のブックマークから投稿情報を抽出し、Google Spreadsheet で管理するシステム。
ユーザー自身のアカウントでログイン済みの Chrome ブラウザを Playwright で制御することで、認証を安全に維持する。

---

## 2. 全体フロー

```
[Phase 1] ブックマーク収集
  ユーザーのChrome → X.com/i/bookmarks → 無限スクロール → URL抽出 → Spreadsheet書き込み

[Phase 2] 手動キュレーション（ユーザー作業）
  Spreadsheet上で不要な行を削除

[Phase 3] 詳細情報取得
  Spreadsheet読み取り → 各ポストを開く → 日付・画像抽出 → Spreadsheet更新
```

---

## 3. 技術スタック

| 要素 | 技術 | 理由 |
|------|------|------|
| ブラウザ自動化 | **Playwright (Python)** | X.comの動的ページに強い。`connect_over_cdp` で既存Chromeに接続可能 |
| Spreadsheet連携 | **gspread + google-auth** | Python から Google Sheets を操作する定番ライブラリ |
| 実行環境 | **Python 3.11+** | 上記ライブラリすべてが Python エコシステム |
| 設定管理 | **YAML / .env** | 日時指定やSpreadsheet IDなどを外部ファイルで管理 |

---

## 4. Playwright の接続方式

### 採用方式：CDP (Chrome DevTools Protocol) 接続

ユーザーが普段使っている Chrome をデバッグポート付きで起動し、Playwright からそこに接続する。
これにより **ログインセッション（Cookie）がそのまま利用** でき、再認証が不要になる。

#### Chrome 起動コマンド（ユーザーが手動で実行）

```bash
# macOS
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir="$HOME/chrome-debug-profile"

# Windows
"C:\Program Files\Google\Chrome\Application\chrome.exe" ^
  --remote-debugging-port=9222 ^
  --user-data-dir="%USERPROFILE%\chrome-debug-profile"

# Linux
google-chrome --remote-debugging-port=9222 \
  --user-data-dir="$HOME/chrome-debug-profile"
```

> **初回のみ**：起動した Chrome で X.com にログインしておく。
> 以降は `chrome-debug-profile` にセッションが保存される。

#### Playwright 接続コード

```python
from playwright.async_api import async_playwright

async def connect_browser():
    pw = await async_playwright().start()
    browser = await pw.chromium.connect_over_cdp("http://localhost:9222")
    context = browser.contexts[0]  # 既存のブラウザコンテキストを取得
    return pw, browser, context
```

---

## 5. ディレクトリ構成

```
x-bookmark-scraper/
├── config.yaml              # 設定ファイル
├── credentials.json          # Google API サービスアカウント鍵
├── requirements.txt
├── src/
│   ├── __init__.py
│   ├── config.py             # 設定読み込み
│   ├── browser.py            # Playwright 接続・操作
│   ├── scraper_bookmarks.py  # Phase 1: ブックマーク収集
│   ├── scraper_details.py    # Phase 3: 詳細情報取得
│   ├── sheets.py             # Google Spreadsheet 操作
│   └── main.py               # CLI エントリーポイント
```

---

## 6. 設定ファイル (config.yaml)

```yaml
# X.com ブックマーク収集の設定
bookmark_cutoff_date: "2025-01-01T00:00:00"  # この日時以降のブックマークを収集

# Google Spreadsheet
spreadsheet_id: "1aBcDeFgHiJkLmNoPqRsTuVwXyZ..."
worksheet_name: "bookmarks"
credentials_path: "./credentials.json"

# Playwright
cdp_endpoint: "http://localhost:9222"
```

---

## 7. Phase 1：ブックマーク URL 収集

### 処理フロー

```
1. CDP で Chrome に接続
2. https://x.com/i/bookmarks を開く
3. 無限スクロールしながらポストを検出
4. 各ポストから URL (https://x.com/{user}/status/{id}) を抽出
5. ポストの表示日時を簡易取得し、cutoff_date より古ければ停止
6. 収集した URL を Spreadsheet に書き込み
```

### X.com ブックマークページの DOM 構造（抽出戦略）

ブックマークページは `article[data-testid="tweet"]` 要素の繰り返しで構成される。各 article 内から以下を取得する。

```python
async def extract_bookmark_urls(page, cutoff_date):
    collected = []
    previous_count = 0
    
    while True:
        articles = await page.query_selector_all('article[data-testid="tweet"]')
        
        for article in articles[previous_count:]:
            # ポストURLの取得：article 内の status リンクを探す
            link = await article.query_selector('a[href*="/status/"]')
            if not link:
                continue
            href = await link.get_attribute("href")
            url = f"https://x.com{href}" if href.startswith("/") else href
            
            # 時刻要素の取得（簡易判定用）
            time_el = await article.query_selector("time")
            if time_el:
                datetime_str = await time_el.get_attribute("datetime")
                if parse_datetime(datetime_str) < cutoff_date:
                    return collected  # cutoff に到達、終了
            
            collected.append({"url": url, "datetime_hint": datetime_str})
        
        previous_count = len(articles)
        
        # スクロールして追加読み込み
        await page.evaluate("window.scrollBy(0, window.innerHeight)")
        await page.wait_for_timeout(2000)  # レート制限を考慮
        
        # 新しい article が読み込まれなければ終了
        new_articles = await page.query_selector_all('article[data-testid="tweet"]')
        if len(new_articles) == previous_count:
            break
    
    return collected
```

### Spreadsheet 書き込みフォーマット（Phase 1 完了時）

| A: URL | B: 取得日時 | C: ステータス |
|--------|-----------|-------------|
| `https://x.com/user/status/123` | `2025-06-15T10:30:00` | `pending` |

---

## 8. Phase 2：手動キュレーション（ユーザー作業）

ユーザーが Spreadsheet を開き、以下を行う。

- 各 URL を開いて内容を確認
- 不要な行を削除、または C列のステータスを `remove` に変更
- 残す行のステータスを `keep` に変更（任意、未変更でも可）

Phase 3 はステータスが `remove` **以外** の行を処理対象とする。

---

## 9. Phase 3：詳細情報取得

### 処理フロー

```
1. Spreadsheet からステータスが remove 以外の URL リストを読み取り
2. CDP で Chrome に接続
3. 各 URL を順番に開く
4. ポストの正確な投稿日時を取得
5. ポスト内の画像 URL を検出
6. 画像 URL に name=small パラメータを付与し =IMAGE() 数式を生成
7. Spreadsheet の該当行を更新
```

### ポスト詳細の抽出

```python
async def extract_post_details(page, url):
    await page.goto(url, wait_until="networkidle")
    await page.wait_for_timeout(2000)
    
    # 投稿日時（正確）
    time_el = await page.query_selector('article[data-testid="tweet"] time')
    post_date = None
    if time_el:
        post_date = await time_el.get_attribute("datetime")
    
    # 画像の取得
    images = []
    img_elements = await page.query_selector_all(
        'article[data-testid="tweet"] img[src*="pbs.twimg.com/media"]'
    )
    for img in img_elements:
        src = await img.get_attribute("src")
        if src:
            images.append(src)
    
    return {"post_date": post_date, "image_urls": images}
```

### サムネイルの Spreadsheet 反映方法

X.com の画像 URL（`pbs.twimg.com`）は公開アクセス可能なため、URL パラメータで縮小版を直接指定し、Google Sheets の `IMAGE` 関数で表示する。ダウンロードやリサイズ処理は不要。

```python
def to_small_image_url(original_url: str) -> str:
    """X.com の画像URLを小サイズに変換する。
    
    例:
      入力: https://pbs.twimg.com/media/AbCdEf.jpg
      出力: https://pbs.twimg.com/media/AbCdEf?format=jpg&name=small
    """
    import re
    # 既存のパラメータと拡張子を除去し、name=small を付与
    base = re.split(r'[?.]', original_url)[0]
    # 元の拡張子を format パラメータとして保持
    ext_match = re.search(r'\.(jpg|jpeg|png|webp)', original_url)
    fmt = ext_match.group(1) if ext_match else "jpg"
    return f"{base}?format={fmt}&name=small"

def build_image_formula(image_urls: list[str]) -> str:
    """IMAGE 関数の数式文字列を返す。複数画像は1枚目のみ使用。"""
    if not image_urls:
        return ""
    small_url = to_small_image_url(image_urls[0])
    return f'=IMAGE("{small_url}")'
```

> **注意**: ポストが削除されると画像 URL も無効になる。永続保存が必要になった場合は Google Drive へのアップロード方式に切り替えること。

### Spreadsheet 更新後フォーマット（Phase 3 完了時）

| A: URL | B: 取得日時 | C: ステータス | D: 投稿日時 | E: サムネイル |
|--------|-----------|-------------|-----------|-------------|
| `https://x.com/user/status/123` | `2025-06-15T10:30:00` | `keep` | `2025-06-14T08:00:00` | `=IMAGE(...)` |

---

## 10. Google Spreadsheet 連携の設定手順

### サービスアカウント方式（推奨）

```
1. Google Cloud Console でプロジェクト作成
2. Google Sheets API を有効化
3. サービスアカウントを作成し、鍵 (JSON) をダウンロード
4. credentials.json としてプロジェクトに配置
5. サービスアカウントのメールアドレスを Spreadsheet に「編集者」として共有
```

### gspread 接続コード

```python
import gspread
from google.oauth2.service_account import Credentials

def get_sheets_client(credentials_path):
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
    ]
    creds = Credentials.from_service_account_file(credentials_path, scopes=scopes)
    return gspread.authorize(creds)

def get_worksheet(client, spreadsheet_id, worksheet_name):
    spreadsheet = client.open_by_key(spreadsheet_id)
    return spreadsheet.worksheet(worksheet_name)
```

---

## 11. CLI インターフェース

```bash
# Phase 1: ブックマーク収集
python -m src.main collect-bookmarks

# Phase 3: 詳細情報取得
python -m src.main fetch-details

# ヘルプ
python -m src.main --help
```

`main.py` では `argparse` または `click` でサブコマンドを実装する。

---

## 12. エラーハンドリングとレート制限

### リトライ戦略

```python
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=30))
async def safe_goto(page, url):
    await page.goto(url, wait_until="networkidle", timeout=30000)
```

### レート制限

X.com はアクセス頻度が高いとレート制限やCAPTCHAを表示する。以下で対策する。

- ポスト間の待機時間：**3〜5秒**（ランダム）
- スクロール間の待機時間：**2〜3秒**
- エラー発生時：**指数バックオフ**で最大30秒
- 1セッションあたりの上限：**連続200件を目安**に分割実行

```python
import random

async def rate_limited_wait():
    await asyncio.sleep(random.uniform(3.0, 5.0))
```

### 中断・再開

Spreadsheet 自体が進捗の永続化を兼ねる。

- Phase 1：既に Spreadsheet にある URL はスキップ（重複チェック）
- Phase 3：D列（投稿日時）が空の行だけを処理対象とする

これにより、途中でスクリプトが落ちても再実行で続きから処理できる。

---

## 13. 依存パッケージ (requirements.txt)

```
playwright>=1.40
gspread>=6.0
google-auth>=2.0
pyyaml>=6.0
tenacity>=8.0
click>=8.0
```

---

## 14. セキュリティ上の注意

- `credentials.json` は `.gitignore` に追加し、リポジトリにコミットしない
- `chrome-debug-profile` ディレクトリにはセッション情報が含まれるため取扱い注意
- CDP ポート (9222) はローカルのみでリッスンされるが、他アプリからもアクセス可能なため、使用後は Chrome を終了するか、ポートを閉じる
- X.com の利用規約上、スクレイピングは制限される可能性がある。個人利用・自身のブックマークに限定すること

---

## 15. 拡張候補（将来）

- **ポスト本文の取得**：テキスト内容もSpreadsheetに保存
- **画像の永続保存**：Google Drive にサムネイルをアップロードし、ポスト削除後も画像を保持
- **リポスト元の追跡**：引用リポストの場合、元ポストも記録
- **タグ付け機能**：Spreadsheet にカテゴリ列を追加し分類
- **定期実行**：cron / タスクスケジューラで新しいブックマークを自動収集
