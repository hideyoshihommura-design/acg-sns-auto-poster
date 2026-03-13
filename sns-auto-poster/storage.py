"""
投稿データの保存・読み込みモジュール
DATABASE_URL が設定されている場合はPostgreSQLを使用し、
未設定の場合はJSONファイルにフォールバックする
"""

import json
import os
from datetime import date, datetime
from pathlib import Path


# --- PostgreSQL ヘルパー ---

def _get_db_url() -> str | None:
    return os.getenv("DATABASE_URL")


def _get_conn():
    import psycopg2
    url = _get_db_url()
    return psycopg2.connect(url)


def _init_db():
    """テーブルが存在しない場合は作成する"""
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS sns_posts (
                    id SERIAL PRIMARY KEY,
                    record_date DATE NOT NULL,
                    generated_at TIMESTAMP NOT NULL,
                    theme TEXT,
                    business_name TEXT,
                    posts JSONB,
                    trending_data JSONB
                )
            """)
        conn.commit()


# --- JSONファイル ヘルパー ---

def get_output_dir() -> Path:
    output_dir = Path(os.getenv("OUTPUT_DIR", "./output"))
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


# --- 共通API ---

def save_posts(posts: dict, trending_data: dict, theme: str, business_name: str):
    """生成した投稿文を保存する"""
    today = date.today()
    now = datetime.now()

    if _get_db_url():
        _init_db()
        with _get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO sns_posts (record_date, generated_at, theme, business_name, posts, trending_data)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        today,
                        now,
                        theme,
                        business_name,
                        json.dumps(posts, ensure_ascii=False),
                        json.dumps({
                            "google_trends": trending_data.get("google_trends", []),
                            "news_articles": trending_data.get("news_articles", []),
                            "fetched_at": trending_data.get("fetched_at", ""),
                        }, ensure_ascii=False),
                    ),
                )
            conn.commit()
        return "database"
    else:
        # JSONファイルへのフォールバック
        file_path = get_output_dir() / f"{today.isoformat()}.json"
        existing_data = {}
        if file_path.exists():
            with open(file_path, encoding="utf-8") as f:
                existing_data = json.load(f)
        record = {
            "date": today.isoformat(),
            "generated_at": now.isoformat(),
            "theme": theme,
            "business_name": business_name,
            "posts": posts,
            "trending_data": {
                "google_trends": trending_data.get("google_trends", []),
                "news_articles": trending_data.get("news_articles", []),
                "fetched_at": trending_data.get("fetched_at", ""),
            },
        }
        existing_data[now.strftime("%H%M%S")] = record
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(existing_data, f, ensure_ascii=False, indent=2)
        return file_path


def load_history(days: int = 30) -> list[dict]:
    """過去の投稿履歴を日付降順で返す（1日1件・最新のみ）"""
    if _get_db_url():
        _init_db()
        with _get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT DISTINCT ON (record_date)
                        record_date, generated_at, theme, business_name, posts, trending_data
                    FROM sns_posts
                    ORDER BY record_date DESC, generated_at DESC
                    LIMIT %s
                    """,
                    (days,),
                )
                rows = cur.fetchall()
        return [
            {
                "date": row[0].isoformat(),
                "generated_at": row[1].isoformat(),
                "theme": row[2],
                "business_name": row[3],
                "posts": row[4],
                "trending_data": row[5],
            }
            for row in rows
        ]
    else:
        output_dir = get_output_dir()
        records = []
        for file_path in sorted(output_dir.glob("*.json"), reverse=True)[:days]:
            try:
                with open(file_path, encoding="utf-8") as f:
                    day_data = json.load(f)
                if day_data:
                    latest_key = sorted(day_data.keys())[-1]
                    records.append(day_data[latest_key])
            except Exception:
                continue
        return records


def load_today() -> dict | None:
    """今日の最新投稿を返す"""
    today = date.today()

    if _get_db_url():
        _init_db()
        with _get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT record_date, generated_at, theme, business_name, posts, trending_data
                    FROM sns_posts
                    WHERE record_date = %s
                    ORDER BY generated_at DESC
                    LIMIT 1
                    """,
                    (today,),
                )
                row = cur.fetchone()
        if not row:
            return None
        return {
            "date": row[0].isoformat(),
            "generated_at": row[1].isoformat(),
            "theme": row[2],
            "business_name": row[3],
            "posts": row[4],
            "trending_data": row[5],
        }
    else:
        file_path = get_output_dir() / f"{today.isoformat()}.json"
        if not file_path.exists():
            return None
        try:
            with open(file_path, encoding="utf-8") as f:
                day_data = json.load(f)
            if day_data:
                latest_key = sorted(day_data.keys())[-1]
                return day_data[latest_key]
        except Exception:
            return None
