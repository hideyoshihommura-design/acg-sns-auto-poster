#!/bin/bash
# SNS自動投稿システム GCPデプロイスクリプト

set -e

# ===== 設定 =====
PROJECT_ID="your-gcp-project-id"
REGION="asia-northeast1"
REPO="sns-auto-poster"

# ===== Artifact Registry リポジトリ作成 =====
gcloud artifacts repositories create $REPO \
  --repository-format=docker \
  --location=$REGION \
  --project=$PROJECT_ID 2>/dev/null || echo "リポジトリは既に存在します"

# ===== Secret Manager にシークレットを登録 =====
echo "各SNS APIキーをSecret Managerに登録してください:"
echo "  gcloud secrets create twitter-api-key --data-file=-"
echo "  gcloud secrets create twitter-api-secret --data-file=-"
echo "  gcloud secrets create twitter-access-token --data-file=-"
echo "  gcloud secrets create twitter-access-token-secret --data-file=-"
echo "  gcloud secrets create instagram-access-token --data-file=-"
echo "  gcloud secrets create instagram-account-id --data-file=-"
echo "  gcloud secrets create facebook-access-token --data-file=-"
echo "  gcloud secrets create facebook-page-id --data-file=-"
echo "  gcloud secrets create tiktok-access-token --data-file=-"
echo "  gcloud secrets create webhook-secret --data-file=-"

# ===== 投稿エンジンをビルド・デプロイ =====
echo "投稿エンジンをビルド中..."
gcloud builds submit \
  --tag $REGION-docker.pkg.dev/$PROJECT_ID/$REPO/posting-engine \
  cloud-run/posting-engine/

echo "投稿エンジンをCloud Runにデプロイ中..."
gcloud run deploy posting-engine \
  --image $REGION-docker.pkg.dev/$PROJECT_ID/$REPO/posting-engine \
  --platform managed \
  --region $REGION \
  --project $PROJECT_ID \
  --set-env-vars GCP_PROJECT=$PROJECT_ID,GCP_LOCATION=$REGION,GCS_BUCKET=$PROJECT_ID-sns-images \
  --service-account sns-poster@$PROJECT_ID.iam.gserviceaccount.com \
  --port 8080 \
  --cpu 1 \
  --memory 1Gi \
  --min-instances 0 \
  --max-instances 10 \
  --no-allow-unauthenticated

POSTING_ENGINE_URL=$(gcloud run services describe posting-engine \
  --region $REGION --project $PROJECT_ID \
  --format "value(status.url)")

# ===== Web UIをビルド・デプロイ =====
echo "Web UIをビルド中..."
gcloud builds submit \
  --tag $REGION-docker.pkg.dev/$PROJECT_ID/$REPO/web-ui \
  cloud-run/web-ui/

echo "Web UIをCloud Runにデプロイ中..."
gcloud run deploy sns-web-ui \
  --image $REGION-docker.pkg.dev/$PROJECT_ID/$REPO/web-ui \
  --platform managed \
  --region $REGION \
  --project $PROJECT_ID \
  --set-env-vars GCP_PROJECT=$PROJECT_ID,POSTING_ENGINE_URL=$POSTING_ENGINE_URL \
  --service-account sns-poster@$PROJECT_ID.iam.gserviceaccount.com \
  --port 8081 \
  --cpu 1 \
  --memory 512Mi \
  --min-instances 0 \
  --max-instances 5 \
  --no-allow-unauthenticated

# ===== Cloud Functions: WordPress Webhook =====
echo "WordPress Webhookをデプロイ中..."
gcloud functions deploy wordpress-webhook \
  --gen2 \
  --runtime python311 \
  --region $REGION \
  --project $PROJECT_ID \
  --source cloud-functions/wordpress-webhook/ \
  --entry-point wordpress_webhook \
  --trigger-http \
  --set-env-vars GCP_PROJECT=$PROJECT_ID,GCP_LOCATION=$REGION,CLOUD_TASKS_QUEUE=sns-posting-queue,POSTING_ENGINE_URL=$POSTING_ENGINE_URL \
  --set-secrets WEBHOOK_SECRET=webhook-secret:latest \
  --allow-unauthenticated

# ===== Cloud Functions: Scheduler Trigger =====
echo "Scheduler Triggerをデプロイ中..."
gcloud functions deploy scheduler-trigger \
  --gen2 \
  --runtime python311 \
  --region $REGION \
  --project $PROJECT_ID \
  --source cloud-functions/scheduler-trigger/ \
  --entry-point scheduler_trigger \
  --trigger-http \
  --set-env-vars GCP_PROJECT=$PROJECT_ID,GCP_LOCATION=$REGION,CLOUD_TASKS_QUEUE=sns-posting-queue,POSTING_ENGINE_URL=$POSTING_ENGINE_URL \
  --no-allow-unauthenticated

SCHEDULER_URL=$(gcloud functions describe scheduler-trigger \
  --region $REGION --project $PROJECT_ID \
  --format "value(serviceConfig.uri)")

# ===== Cloud Scheduler 設定 =====
echo "Cloud Schedulerを設定中..."
gcloud scheduler jobs create http sns-scheduler \
  --location $REGION \
  --project $PROJECT_ID \
  --schedule "*/15 * * * *" \
  --uri $SCHEDULER_URL \
  --http-method POST \
  --oidc-service-account-email sns-poster@$PROJECT_ID.iam.gserviceaccount.com 2>/dev/null || echo "Schedulerは既に存在します"

echo ""
echo "===== デプロイ完了 ====="
echo "投稿エンジン URL: $POSTING_ENGINE_URL"
echo "Web UI URL: $(gcloud run services describe sns-web-ui --region $REGION --project $PROJECT_ID --format 'value(status.url)')"
