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

[uv](https://docs.astral.sh/uv/) で依存パッケージを管理している（`pyproject.toml` / `uv.lock`）。

```bash
uv sync
uv run playwright install chromium
```

### 2. Google Spreadsheet の準備

1. [Google Cloud Console](https://console.cloud.google.com/) でプロジェクトを作成
2. Google Sheets API を有効化
3. サービスアカウントを作成し、鍵 (JSON) をダウンロード
4. `credentials.json` としてプロジェクトルートに配置
5. サービスアカウントのメールアドレスを Spreadsheet に「編集者」として共有

### 3. 設定ファイルの編集

サンプルをコピーして `config.yaml` を作成し、環境に合わせて編集する。
`config.yaml` は `.gitignore` 対象のため Git にはコミットされない。

```bash
# macOS / Linux
cp config.sample.yaml config.yaml

# Windows (PowerShell)
Copy-Item config.sample.yaml config.yaml
```

```yaml
bookmark_cutoff_date: "2025-01-01T00:00:00"  # この日時以降のブックマークを収集
bookmark_until_date: "2025-06-30T23:59:59"  # この日時以前のブックマークだけを収集（省略・空なら上限なし）
spreadsheet_id: "YOUR_SPREADSHEET_ID_HERE"
worksheet_name: "bookmarks"
credentials_path: "./credentials.json"
cdp_endpoint: "chrome"
```

### 4. Chrome のリモートデバッグを有効化

普段使いの Chrome（X.com にログイン済みのもの）にそのまま接続する。

1. Chrome で `chrome://inspect/#remote-debugging` を開く
2. リモートデバッグを許可する設定を有効にする
3. スクリプト実行時に Chrome に接続確認のダイアログが表示されたら「許可」を選択する

`cdp_endpoint: "chrome"` の場合、Chrome がユーザーデータフォルダに書き出す `DevToolsActivePort` ファイルから接続先を自動で読み取る。

| OS | ユーザーデータフォルダ |
|----|----------------------|
| Windows | `%LOCALAPPDATA%\Google\Chrome\User Data` |
| macOS | `~/Library/Application Support/Google/Chrome` |
| Linux | `~/.config/google-chrome` |

#### 別の方法: デバッグポート付きで Chrome を起動する

専用プロフィールの Chrome を起動して接続することもできる。この場合は `config.yaml` の `cdp_endpoint` を `"http://localhost:9222"` に変更する。

```bash
# macOS
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir="$HOME/chrome-debug-profile"

# Windows (PowerShell)
& "C:\Program Files\Google\Chrome\Application\chrome.exe" `
  --remote-debugging-port=9222 `
  --user-data-dir="$env:USERPROFILE\chrome-debug-profile"

# Windows (コマンドプロンプト)
"C:\Program Files\Google\Chrome\Application\chrome.exe" ^
  --remote-debugging-port=9222 ^
  --user-data-dir="%USERPROFILE%\chrome-debug-profile"

# Linux
google-chrome --remote-debugging-port=9222 \
  --user-data-dir="$HOME/chrome-debug-profile"
```

> この方法では普段のプロフィールとは別になるため、初回のみ起動した Chrome で X.com にログインしておく。以降はセッションが保存される。

## 使い方

### Phase 1: ブックマーク URL 収集

```bash
uv run python -m src.main collect-bookmarks
```

ブックマークページを無限スクロールし、各ポストの URL を Spreadsheet に書き込む。
`bookmark_cutoff_date` より古いポストに到達すると自動停止する。
`bookmark_until_date` を指定すると、その日時より新しいポストは収集せずに読み飛ばす（スクロールは続ける）。

> X.com はブックマークした日時を表示しないため、どちらの日付もポストの投稿日時で判定する。

### Phase 2: 手動キュレーション

Spreadsheet を開き、不要な行のステータス（C列）を `remove` に変更する。

### Phase 3: 詳細情報取得

```bash
uv run python -m src.main fetch-details
```

ステータスが `remove` 以外の行を順に開き、投稿日時とサムネイル画像を取得して Spreadsheet を更新する。

### オプション

```bash
uv run python -m src.main --help                           # ヘルプ表示
uv run python -m src.main collect-bookmarks --config path  # 設定ファイルを指定
```

### 開発用コマンド

```bash
uv run pytest            # テスト
uv run ruff format .     # フォーマット
uv run ruff check .      # リント
```

## Spreadsheet フォーマット

| A: URL | B: 投稿日時（一覧から取得） | C: ステータス | D: サムネイル | E: 投稿日時 |
|--------|-----------|-------------|-----------|-------------|
| `https://x.com/user/status/123` | `2025-06-15T10:30:00` | `keep` | `=IMAGE(...)` | `2025-06-14T08:00:00` |

- Phase 1 完了時: A〜C列が埋まる（ステータスは `pending`）
  - B列はブックマーク一覧に表示されたポストの日時。Phase 3 では個別ページから投稿日時を取り直して E列に書く
- Phase 3 完了時: D列（1枚目の画像のサムネイル。画像がなければ空）と E列（投稿日時）が埋まる

## 注意事項

- `credentials.json` はリポジトリにコミットしないこと（`.gitignore` で除外済み）
- リモートデバッグはローカルのみでリッスンされるが、使用後は `chrome://inspect/#remote-debugging` で無効化する（またはデバッグ用 Chrome を終了する）こと
- X.com のレート制限を考慮し、ポスト間に 3〜5 秒の待機を挟んでいる
- 個人利用・自身のブックマークに限定して使用すること
