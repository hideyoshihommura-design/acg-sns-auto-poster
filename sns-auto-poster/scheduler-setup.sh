#!/bin/bash
# Cloud Scheduler のセットアップスクリプト
# 30分ごとに Cloud Run を呼び出すジョブを作成する

PROJECT_ID=${1:-"your-gcp-project-id"}
REGION="asia-northeast1"
CLOUD_RUN_URL="https://acg-sns-auto-poster-xxxxxxxxxx-an.a.run.app"  # デプロイ後に更新

gcloud config set project $PROJECT_ID

# サービスアカウントの作成
gcloud iam service-accounts create acg-sns-scheduler \
  --display-name="ACG SNS Scheduler"

# Cloud Run 呼び出し権限を付与
gcloud run services add-iam-policy-binding acg-sns-auto-poster \
  --region=$REGION \
  --member="serviceAccount:acg-sns-scheduler@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/run.invoker"

# Cloud Scheduler ジョブを作成（30分ごと）
gcloud scheduler jobs create http acg-sns-check \
  --location=$REGION \
  --schedule="*/30 * * * *" \
  --uri="${CLOUD_RUN_URL}/run" \
  --http-method=POST \
  --oidc-service-account-email="acg-sns-scheduler@${PROJECT_ID}.iam.gserviceaccount.com" \
  --time-zone="Asia/Tokyo"

echo "✅ Cloud Scheduler セットアップ完了"
echo "   30分ごとに ${CLOUD_RUN_URL}/run を呼び出します"
