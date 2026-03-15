# X.com ブックマークスクレイピングシステム 実装計画

design.md に基づく段階的な実装計画。

---

## Step 1: プロジェクト基盤セットアップ

**目的**: 開発に必要なファイル構成・依存関係・設定管理を整える

- [ ] ディレクトリ構成の作成
  ```
  src/__init__.py, src/config.py, src/browser.py,
  src/scraper_bookmarks.py, src/scraper_details.py,
  src/sheets.py, src/main.py
  ```
- [ ] `requirements.txt` の作成（playwright, gspread, google-auth, pyyaml, tenacity, click）
- [ ] `.gitignore` の作成（credentials.json, chrome-debug-profile/, __pycache__/, .env 等）
- [ ] `config.yaml` のテンプレート作成（bookmark_cutoff_date, spreadsheet_id, worksheet_name, credentials_path, cdp_endpoint）

**成果物**: 空のモジュールファイルと設定ファイルが揃った状態

---

## Step 2: 設定読み込みモジュール (`src/config.py`)

**目的**: config.yaml を読み込み、アプリケーション全体で利用できる設定オブジェクトを提供する

- [ ] YAML ファイルの読み込み処理
- [ ] 設定値のバリデーション（必須項目の存在チェック）
- [ ] デフォルト値の定義（cdp_endpoint: `http://localhost:9222` 等）

---

## Step 3: ブラウザ接続モジュール (`src/browser.py`)

**目的**: Playwright を使って既存の Chrome に CDP 接続する機能を実装

- [ ] `connect_browser()`: CDP エンドポイントに接続し、既存のブラウザコンテキストを取得
- [ ] 接続エラー時の分かりやすいエラーメッセージ（Chrome が起動していない場合等）
- [ ] コンテキストマネージャ対応（async with で安全にクリーンアップ）

---

## Step 4: Google Spreadsheet 連携モジュール (`src/sheets.py`)

**目的**: gspread を使った Spreadsheet の読み書き機能を実装

- [ ] `get_sheets_client()`: サービスアカウント認証でクライアント取得
- [ ] `get_worksheet()`: spreadsheet_id と worksheet_name からワークシート取得
- [ ] `append_bookmarks(worksheet, bookmarks)`: Phase 1 用 — URL・取得日時・ステータスを追記
- [ ] `get_pending_urls(worksheet)`: Phase 3 用 — ステータスが `remove` 以外かつ投稿日時（D列）が空の行を取得
- [ ] `update_details(worksheet, row, details)`: Phase 3 用 — 投稿日時・サムネイル数式を更新
- [ ] 重複チェック: 既存 URL との照合

---

## Step 5: Phase 1 — ブックマーク URL 収集 (`src/scraper_bookmarks.py`)

**目的**: ブックマークページから URL を収集して Spreadsheet に書き込む

- [ ] `extract_bookmark_urls(page, cutoff_date)`: 無限スクロール + URL 抽出
  - `article[data-testid="tweet"]` からポストを検出
  - `a[href*="/status/"]` から URL を取得
  - `time` 要素から日時を取得し、cutoff_date 判定で停止
  - スクロール間に 2〜3 秒の待機
  - 新しい article が読み込まれなくなったら終了
- [ ] `collect_bookmarks(config)`: メイン処理（接続 → 収集 → Spreadsheet 書き込み）
- [ ] 既存 URL の重複スキップ

---

## Step 6: Phase 3 — 詳細情報取得 (`src/scraper_details.py`)

**目的**: 各ポストページを開いて投稿日時と画像を取得し Spreadsheet を更新する

- [ ] `extract_post_details(page, url)`: 個別ポストから詳細を抽出
  - 正確な投稿日時（`time` 要素の `datetime` 属性）
  - 画像 URL（`img[src*="pbs.twimg.com/media"]`）
- [ ] `to_small_image_url(original_url)`: 画像 URL を `?format=jpg&name=small` 形式に変換
- [ ] `build_image_formula(image_urls)`: `=IMAGE("...")` 数式を生成（1枚目のみ）
- [ ] `fetch_details(config)`: メイン処理（Spreadsheet 読み取り → 各ポスト処理 → 更新）
- [ ] レート制限対応: ポスト間 3〜5 秒のランダム待機
- [ ] リトライ: tenacity による指数バックオフ（最大3回、最大30秒）

---

## Step 7: CLI エントリーポイント (`src/main.py`)

**目的**: click でサブコマンドを実装し、ユーザーが簡単に実行できるようにする

- [ ] `collect-bookmarks` サブコマンド: Phase 1 を実行
- [ ] `fetch-details` サブコマンド: Phase 3 を実行
- [ ] `--config` オプション: config.yaml のパス指定（デフォルト: `./config.yaml`）
- [ ] `--help` の表示

**実行方法**:
```bash
python -m src.main collect-bookmarks
python -m src.main fetch-details
```

---

## 実装順序まとめ

```
Step 1 (基盤) → Step 2 (設定) → Step 3 (ブラウザ) → Step 4 (Sheets)
                                                          ↓
                                        Step 5 (Phase 1: 収集) → Step 6 (Phase 3: 詳細)
                                                                          ↓
                                                                  Step 7 (CLI)
```

Step 2〜4 は独立しているため並行して実装可能。Step 5 は Step 2〜4 すべてに依存する。
