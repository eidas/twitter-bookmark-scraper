# タスク一覧

plan.md の各ステップを実行可能な単位に分解したタスクリスト。

---

## Step 1: プロジェクト基盤セットアップ

- [ ] 1-1. `src/` ディレクトリと空モジュールファイルの作成（`__init__.py`, `config.py`, `browser.py`, `scraper_bookmarks.py`, `scraper_details.py`, `sheets.py`, `main.py`）
- [ ] 1-2. `requirements.txt` の作成
- [ ] 1-3. `.gitignore` の作成
- [ ] 1-4. `config.yaml` テンプレートの作成（値はプレースホルダー）

---

## Step 2: 設定読み込みモジュール

- [ ] 2-1. `src/config.py` に YAML 読み込み関数 `load_config(path)` を実装
- [ ] 2-2. 必須項目（`spreadsheet_id`, `worksheet_name`, `credentials_path`）のバリデーション追加
- [ ] 2-3. デフォルト値の設定（`cdp_endpoint`: `http://localhost:9222`, `bookmark_cutoff_date`: なし）

---

## Step 3: ブラウザ接続モジュール

- [ ] 3-1. `src/browser.py` に `connect_browser(cdp_endpoint)` を実装（Playwright CDP 接続）
- [ ] 3-2. 接続失敗時のエラーメッセージ（Chrome 未起動の場合のガイダンス表示）
- [ ] 3-3. 非同期コンテキストマネージャ化（`async with` 対応でリソース解放を保証）

---

## Step 4: Google Spreadsheet 連携モジュール

- [ ] 4-1. `src/sheets.py` に `get_sheets_client(credentials_path)` を実装（サービスアカウント認証）
- [ ] 4-2. `get_worksheet(client, spreadsheet_id, worksheet_name)` を実装
- [ ] 4-3. `get_existing_urls(worksheet)` を実装（A列から既存 URL を取得、重複チェック用）
- [ ] 4-4. `append_bookmarks(worksheet, bookmarks)` を実装（URL・取得日時・ステータス `pending` を追記）
- [ ] 4-5. `get_pending_urls(worksheet)` を実装（ステータス ≠ `remove` かつ D列が空の行を返す）
- [ ] 4-6. `update_details(worksheet, row_number, post_date, image_formula)` を実装（D列・E列を更新）

---

## Step 5: Phase 1 — ブックマーク URL 収集

- [ ] 5-1. `src/scraper_bookmarks.py` に `extract_bookmark_urls(page, cutoff_date)` を実装
  - `article[data-testid="tweet"]` で各ポストを検出
  - `a[href*="/status/"]` で URL 抽出
  - `time[datetime]` で日時を取得し cutoff_date と比較
  - スクロール間 2〜3 秒待機
  - 新規 article なしで終了
- [ ] 5-2. `collect_bookmarks(config)` を実装（ブラウザ接続 → URL 収集 → 重複除外 → Spreadsheet 書き込み）
- [ ] 5-3. 進捗ログの出力（収集件数のカウント表示）

---

## Step 6: Phase 3 — 詳細情報取得

- [ ] 6-1. `src/scraper_details.py` に `extract_post_details(page, url)` を実装（投稿日時 + 画像 URL 取得）
- [ ] 6-2. `to_small_image_url(original_url)` を実装（`?format=jpg&name=small` 形式への変換）
- [ ] 6-3. `build_image_formula(image_urls)` を実装（`=IMAGE("...")` 数式生成、1枚目のみ）
- [ ] 6-4. `fetch_details(config)` を実装（Spreadsheet から対象行取得 → 各ポスト巡回 → 更新）
- [ ] 6-5. `safe_goto(page, url)` を実装（tenacity で最大3回リトライ、指数バックオフ最大30秒）
- [ ] 6-6. `rate_limited_wait()` を実装（3〜5 秒のランダム待機）

---

## Step 7: CLI エントリーポイント

- [ ] 7-1. `src/main.py` に click グループ（`cli`）を定義
- [ ] 7-2. `collect-bookmarks` サブコマンドの実装（`--config` オプション付き、Phase 1 を呼び出す）
- [ ] 7-3. `fetch-details` サブコマンドの実装（`--config` オプション付き、Phase 3 を呼び出す）
- [ ] 7-4. `__main__.py` の作成（`python -m src.main` での実行対応）
