"""
SNS投稿自動生成アプリ - メインスクリプト
毎日指定時刻に最新トレンドを取得してSNS投稿文を自動生成する

使い方:
    # スケジューラーとして起動（毎日自動実行）
    python main.py

    # 今すぐ1回実行
    python main.py --now

    # Webダッシュボードのみ起動
    python main.py --web
"""

import argparse
import os
import sys
import time
from datetime import datetime

import schedule
from dotenv import load_dotenv

from generator import generate_posts
from storage import save_posts
from trends import fetch_trending_topics

load_dotenv()


def run_generation():
    """トレンド取得 → 投稿文生成 → 保存を実行する"""
    theme = os.getenv("SNS_THEME", "AIを活用したビジネス効率化")
    business_name = os.getenv("BUSINESS_NAME", "あなたのサービス")

    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 投稿文の生成を開始します")
    print(f"  テーマ: {theme}")
    print(f"  ビジネス名: {business_name}")

    # Step 1: トレンド・ニュース取得
    print("  [1/3] 最新トレンド・ニュースを取得中...")
    trending_data = fetch_trending_topics(theme=theme)

    trends_count = len(trending_data.get("google_trends", []))
    news_count = len(trending_data.get("news_articles", []))
    print(f"       Googleトレンド: {trends_count}件、ニュース: {news_count}件")

    # Step 2: 投稿文生成
    print("  [2/3] Claude AIで投稿文を生成中...")
    posts = generate_posts(
        theme=theme,
        business_name=business_name,
        trending_data=trending_data,
    )
    print(f"       {len(posts)}プラットフォーム分の投稿文を生成しました")

    # Step 3: 保存
    print("  [3/3] 投稿文を保存中...")
    file_path = save_posts(
        posts=posts,
        trending_data=trending_data,
        theme=theme,
        business_name=business_name,
    )
    print(f"       保存完了: {file_path}")

    # 結果の表示
    print("\n" + "=" * 60)
    print("生成された投稿文")
    print("=" * 60)
    for platform, data in posts.items():
        print(f"\n【{data['platform_name']}】 ({data['char_count']}文字)")
        print("-" * 40)
        print(data["content"])

    print("\n" + "=" * 60)
    print("投稿文の生成が完了しました。Webダッシュボードで確認できます。")

    return posts


def start_scheduler():
    """スケジューラーを起動して毎日自動実行する"""
    schedule_time = os.getenv("SCHEDULE_TIME", "09:00")

    print(f"スケジューラーを起動しました（毎日 {schedule_time} に実行）")
    print("Webダッシュボードは http://localhost:5000 で確認できます")
    print("停止するには Ctrl+C を押してください\n")

    schedule.every().day.at(schedule_time).do(run_generation)

    while True:
        schedule.run_pending()
        time.sleep(60)


def main():
    parser = argparse.ArgumentParser(description="SNS投稿自動生成アプリ")
    parser.add_argument("--now", action="store_true", help="今すぐ1回実行")
    parser.add_argument("--web", action="store_true", help="Webダッシュボードのみ起動")
    args = parser.parse_args()

    # APIキーの確認
    if not os.getenv("GROQ_API_KEY"):
        print("エラー: GROQ_API_KEY が設定されていません。")
        print(".env ファイルを作成して GROQ_API_KEY を設定してください。")
        sys.exit(1)

    if args.now:
        run_generation()
    elif args.web:
        from web_ui import create_app
        app = create_app()
        port = int(os.getenv("WEB_PORT", 5000))
        app.run(host="0.0.0.0", port=port, debug=False)
    else:
        # デフォルト: スケジューラー + Web UIを両方起動
        import threading
        from web_ui import create_app

        # Web UIをバックグラウンドで起動
        app = create_app()
        port = int(os.getenv("WEB_PORT", 5000))
        web_thread = threading.Thread(
            target=lambda: app.run(host="0.0.0.0", port=port, debug=False),
            daemon=True,
        )
        web_thread.start()

        # スケジューラーをメインスレッドで起動
        start_scheduler()


if __name__ == "__main__":
    main()
