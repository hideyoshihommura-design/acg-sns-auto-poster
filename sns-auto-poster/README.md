# SNS自動投稿システム

GCPを使ったSNS自動投稿システムです。WordPress記事の更新や提供素材をもとに、AI（Vertex AI / Gemini）が投稿文を自動生成し、各SNSプラットフォームに投稿します。

## 対応プラットフォーム

- Twitter/X
- Instagram
- Facebook
- TikTok

## システム構成

```
sns-auto-poster/
├── cloud-functions/
│   ├── wordpress-webhook/   # WordPress記事更新を受信
│   └── scheduler-trigger/   # 定期投稿トリガー
├── cloud-run/
│   ├── posting-engine/      # SNS投稿エンジン
│   └── web-ui/              # 管理画面
├── deploy.sh                # デプロイスクリプト
└── README.md
```

## GCPサービス構成

| サービス | 用途 |
|---|---|
| Cloud Functions | WordPress webhook受信・定期トリガー |
| Cloud Run | 投稿エンジン・管理画面 |
| Cloud Tasks | 投稿キュー管理 |
| Cloud Scheduler | 15分ごとの定期実行 |
| Firestore | 投稿データ・履歴・スケジュール管理 |
| Vertex AI / Gemini | 投稿文の自動生成 |
| Vertex AI / Imagen3 | 画像の自動生成 |
| Cloud Storage | 生成画像の保存 |
| Secret Manager | 各SNS APIキーの管理 |

## コンテンツ生成の流れ

### WordPress記事更新時
1. WordPressがWebhookを送信
2. Cloud Functionsが受信
3. 記事内容をGeminiに渡して各SNS向け投稿文を生成
4. 記事の画像をそのまま使用
5. 各SNSに投稿

### 素材からAI生成
1. 管理画面から素材テキストをアップロード
2. Geminiが各SNS向け投稿文を生成
3. Imagen3で画像を生成
4. プレビュー・承認後に投稿またはスケジュール登録

## 初期セットアップ

### 1. 各SNS APIキーを取得

**Twitter/X**
- [Twitter Developer Portal](https://developer.twitter.com/) でアプリ作成
- API Key, API Secret, Access Token, Access Token Secretを取得

**Instagram / Facebook**
- [Meta for Developers](https://developers.facebook.com/) でアプリ作成
- Instagram Graph API、Facebook Graph APIのアクセストークンを取得

**TikTok**
- [TikTok for Developers](https://developers.tiktok.com/) でアプリ作成
- Content Posting APIのアクセストークンを取得

### 2. WordPress Webhookプラグイン設定

WordPressに以下のアクションを送信するWebhookを設定してください：

```json
{
  "post_id": 123,
  "post_title": "記事タイトル",
  "post_content": "記事本文",
  "post_url": "https://example.com/post-slug",
  "post_image_url": "https://example.com/image.jpg",
  "post_status": "publish"
}
```

ヘッダーに `X-Webhook-Secret: {シークレットキー}` を設定してください。

### 3. デプロイ

```bash
# deploy.sh の PROJECT_ID を変更してから実行
chmod +x deploy.sh
./deploy.sh
```

## HubSpot連携

Twitter/X・Instagram・FacebookはHubSpotのソーシャルメディア機能でも管理できます。
HubSpotダッシュボードで投稿履歴・エンゲージメントを確認してください。

TikTokおよび全体の管理は本システムのWeb UIをご使用ください。
