# X.com ブックマークスクレイピングシステム

X.com のブックマークから投稿情報を抽出し、Google Spreadsheet で管理するツール。
ユーザー自身のログイン済み Chrome ブラウザを Playwright で制御することで、認証を安全に維持する。

## 全体フロー

```
[Phase 1] ブックマーク収集
  ユーザーのChrome → x.com/i/bookmarks → 無限スクロール → URL抽出 → Spreadsheet書き込み

[Phase 2] 手動キュレーション（ユーザー作業）
  Spreadsheet上で不要な行を削除、またはステータスを remove に変更

[Phase 3] 詳細情報取得
  Spreadsheet読み取り → 各ポストを開く → 日付・画像抽出 → Spreadsheet更新
```

## セットアップ

### 1. 依存パッケージのインストール

```bash
uv pip install -r requirements.txt
python -m playwright install chromium
```

### 2. Google Spreadsheet の準備

1. [Google Cloud Console](https://console.cloud.google.com/) でプロジェクトを作成
2. Google Sheets API を有効化
3. サービスアカウントを作成し、鍵 (JSON) をダウンロード
4. `credentials.json` としてプロジェクトルートに配置
5. サービスアカウントのメールアドレスを Spreadsheet に「編集者」として共有

### 3. 設定ファイルの編集

`config.yaml` を環境に合わせて編集する。

```yaml
bookmark_cutoff_date: "2025-01-01T00:00:00"  # この日時以降のブックマークを収集
spreadsheet_id: "YOUR_SPREADSHEET_ID_HERE"
worksheet_name: "bookmarks"
credentials_path: "./credentials.json"
cdp_endpoint: "http://localhost:9222"
```

### 4. Chrome をデバッグポート付きで起動

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

> **初回のみ**: 起動した Chrome で X.com にログインしておく。以降はセッションが保存される。

## 使い方

### Phase 1: ブックマーク URL 収集

```bash
python -m src.main collect-bookmarks
```

ブックマークページを無限スクロールし、各ポストの URL を Spreadsheet に書き込む。
`bookmark_cutoff_date` より古いポストに到達すると自動停止する。

### Phase 2: 手動キュレーション

Spreadsheet を開き、不要な行のステータス（C列）を `remove` に変更する。

### Phase 3: 詳細情報取得

```bash
python -m src.main fetch-details
```

ステータスが `remove` 以外の行を順に開き、投稿日時とサムネイル画像を取得して Spreadsheet を更新する。

### オプション

```bash
python -m src.main --help                           # ヘルプ表示
python -m src.main collect-bookmarks --config path  # 設定ファイルを指定
```

## Spreadsheet フォーマット

| A: URL | B: 取得日時 | C: ステータス | D: 投稿日時 | E: サムネイル |
|--------|-----------|-------------|-----------|-------------|
| `https://x.com/user/status/123` | `2025-06-15T10:30:00` | `keep` | `2025-06-14T08:00:00` | `=IMAGE(...)` |

- Phase 1 完了時: A〜C列が埋まる（ステータスは `pending`）
- Phase 3 完了時: D〜E列が追加される

## 注意事項

- `credentials.json` はリポジトリにコミットしないこと（`.gitignore` で除外済み）
- CDP ポート (9222) はローカルのみでリッスンされるが、使用後は Chrome を終了すること
- X.com のレート制限を考慮し、ポスト間に 3〜5 秒の待機を挟んでいる
- 個人利用・自身のブックマークに限定して使用すること
