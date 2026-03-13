# SNS投稿自動生成アプリ

毎日最新のトレンド・ニュースをもとに、Claude AIがSNS投稿文を自動生成します。

## 対応プラットフォーム

| SNS | 文字数制限 |
|-----|----------|
| X（Twitter） | 制限なし（有料プラン） |
| Instagram | 2,200文字 |
| Facebook | 制限なし（500〜800字推奨） |
| LinkedIn | 3,000文字 |

## セットアップ

### 1. 依存パッケージのインストール

```bash
cd sns-auto-poster
pip install -r requirements.txt
```

### 2. 環境変数の設定

```bash
cp .env.example .env
```

`.env` を編集して以下を設定：

```env
ANTHROPIC_API_KEY=your_api_key_here   # 必須: Claude APIキー
SNS_THEME=AIを活用したビジネス効率化    # 投稿のテーマ
BUSINESS_NAME=あなたのサービス名        # ビジネス・サービス名
SCHEDULE_TIME=09:00                    # 毎日自動生成する時刻
WEB_PORT=5000                          # WebダッシュボードのポートURL
```

APIキーは https://console.anthropic.com で取得できます。

## 使い方

### 今すぐ1回生成する

```bash
python main.py --now
```

### 毎日自動生成（スケジューラー起動）

```bash
python main.py
```

設定した時刻に自動で投稿文が生成されます。
ブラウザで http://localhost:5000 を開くとダッシュボードが表示されます。

### Webダッシュボードのみ起動

```bash
python main.py --web
```

## ダッシュボードの機能

- **今日の投稿** — 生成された各SNS向け投稿文を確認・コピー
- **トレンド情報** — 参照したGoogleトレンドキーワードとニュース記事の一覧
- **過去の投稿** — 過去30日間の生成履歴

## 仕組み

```
毎日 09:00（設定可能）
    ↓
Googleトレンド + ニュースRSSを取得
    ↓
Claude AIが各SNS向けに最適化した投稿文を生成
    ↓
output/YYYY-MM-DD.json に保存
    ↓
Webダッシュボードで確認・コピー
```

## トレンド収集元

- Google Trends（日本）
- NHKニュース、朝日新聞、ITmedia、TechCrunch Japan、日経テクノロジー
- AIsmiley、AI-SCHOLAR、AINOW（AIビジネス向け）

## ファイル構成

```
sns-auto-poster/
├── main.py          # メインスクリプト（スケジューラー）
├── generator.py     # Claude APIによる投稿文生成
├── trends.py        # トレンド・ニュース収集
├── storage.py       # 投稿データの保存・読み込み
├── web_ui.py        # Flaskダッシュボード
├── requirements.txt # 依存パッケージ
├── .env.example     # 環境変数テンプレート
└── output/          # 生成された投稿データ（自動作成）
    └── 2026-03-05.json
```
