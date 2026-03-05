"""
Web UIモジュール
生成した投稿文を確認・コピーできるFlaskベースのダッシュボード
"""

import functools
import os

from flask import Flask, Response, jsonify, render_template_string, request

from storage import load_history, load_today


def _check_auth(username: str, password: str) -> bool:
    """環境変数で設定されたユーザー名・パスワードと照合する"""
    expected_user = os.getenv("DASHBOARD_USER", "admin")
    expected_pass = os.getenv("DASHBOARD_PASSWORD", "")
    if not expected_pass:
        return True  # パスワード未設定時はオープンアクセス
    return username == expected_user and password == expected_pass


def _require_auth(f):
    """HTTP Basic Auth デコレータ"""
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not _check_auth(auth.username, auth.password):
            return Response(
                "認証が必要です",
                401,
                {"WWW-Authenticate": 'Basic realm="SNS Dashboard"'},
            )
        return f(*args, **kwargs)
    return decorated


DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SNS投稿ダッシュボード</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans JP", sans-serif;
            background: #f0f2f5;
            color: #1a1a2e;
        }
        header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px 32px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            box-shadow: 0 2px 12px rgba(0,0,0,0.15);
        }
        header h1 { font-size: 1.4rem; font-weight: 700; }
        header .subtitle { font-size: 0.85rem; opacity: 0.85; margin-top: 2px; }
        .generate-btn {
            background: white;
            color: #764ba2;
            border: none;
            padding: 10px 22px;
            border-radius: 24px;
            font-size: 0.9rem;
            font-weight: 700;
            cursor: pointer;
            transition: transform 0.15s, box-shadow 0.15s;
        }
        .generate-btn:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(0,0,0,0.2); }
        .generate-btn:disabled { opacity: 0.6; cursor: not-allowed; transform: none; }

        .container { max-width: 1200px; margin: 0 auto; padding: 28px 20px; }

        .status-bar {
            background: white;
            border-radius: 12px;
            padding: 16px 24px;
            margin-bottom: 24px;
            display: flex;
            align-items: center;
            gap: 16px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.08);
        }
        .status-indicator {
            width: 10px; height: 10px;
            border-radius: 50%;
            background: #10b981;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.4; }
        }

        .tabs {
            display: flex;
            gap: 8px;
            margin-bottom: 24px;
        }
        .tab-btn {
            padding: 8px 20px;
            border: 2px solid #e2e8f0;
            border-radius: 24px;
            background: white;
            color: #64748b;
            cursor: pointer;
            font-size: 0.9rem;
            font-weight: 600;
            transition: all 0.15s;
        }
        .tab-btn.active {
            background: #667eea;
            border-color: #667eea;
            color: white;
        }
        .tab-btn:hover:not(.active) { border-color: #667eea; color: #667eea; }

        .tab-content { display: none; }
        .tab-content.active { display: block; }

        .platform-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(540px, 1fr));
            gap: 20px;
        }
        .post-card {
            background: white;
            border-radius: 16px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            transition: box-shadow 0.2s;
        }
        .post-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.12); }
        .card-header {
            padding: 14px 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 1px solid #f1f5f9;
        }
        .platform-badge {
            display: flex;
            align-items: center;
            gap: 10px;
            font-weight: 700;
            font-size: 1rem;
        }
        .platform-icon { font-size: 1.4rem; }
        .char-count {
            font-size: 0.78rem;
            color: #94a3b8;
            background: #f8fafc;
            padding: 3px 10px;
            border-radius: 12px;
        }
        .char-count.over { color: #ef4444; background: #fef2f2; }
        .card-body { padding: 18px 20px; }
        .post-content {
            white-space: pre-wrap;
            line-height: 1.75;
            font-size: 0.95rem;
            color: #334155;
            min-height: 80px;
        }
        .card-footer {
            padding: 12px 20px;
            border-top: 1px solid #f1f5f9;
            display: flex;
            gap: 10px;
            justify-content: flex-end;
        }
        .copy-btn {
            padding: 7px 18px;
            border-radius: 8px;
            border: 1.5px solid #667eea;
            background: transparent;
            color: #667eea;
            font-size: 0.85rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.15s;
        }
        .copy-btn:hover { background: #667eea; color: white; }
        .copy-btn.copied { background: #10b981; border-color: #10b981; color: white; }

        .trends-section {
            background: white;
            border-radius: 16px;
            padding: 24px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }
        .trends-section h2 {
            font-size: 1.1rem;
            font-weight: 700;
            margin-bottom: 16px;
            color: #1e293b;
        }
        .trend-tags { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 20px; }
        .trend-tag {
            background: #ede9fe;
            color: #7c3aed;
            padding: 5px 14px;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
        }
        .news-list { list-style: none; }
        .news-item {
            padding: 12px 0;
            border-bottom: 1px solid #f1f5f9;
            font-size: 0.9rem;
        }
        .news-item:last-child { border-bottom: none; }
        .news-source { color: #667eea; font-size: 0.78rem; font-weight: 600; margin-bottom: 3px; }
        .news-title { color: #334155; line-height: 1.5; }

        .history-list { display: flex; flex-direction: column; gap: 16px; }
        .history-card {
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.08);
        }
        .history-date { font-weight: 700; color: #667eea; margin-bottom: 12px; }
        .history-preview {
            font-size: 0.88rem;
            color: #64748b;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }

        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: #94a3b8;
        }
        .empty-state p { margin-top: 12px; font-size: 0.95rem; }

        .loading {
            display: none;
            text-align: center;
            padding: 40px;
            color: #667eea;
            font-weight: 600;
        }
        .loading.show { display: block; }
        .spinner {
            width: 40px; height: 40px;
            border: 4px solid #e2e8f0;
            border-top-color: #667eea;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
            margin: 0 auto 16px;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <header>
        <div>
            <h1>SNS投稿ダッシュボード</h1>
            <div class="subtitle" id="theme-label">読み込み中...</div>
        </div>
        <button class="generate-btn" onclick="generateNow()" id="gen-btn">
            今すぐ生成
        </button>
    </header>

    <div class="container">
        <div class="status-bar">
            <div class="status-indicator"></div>
            <span id="status-text">システム稼働中</span>
            <span style="margin-left:auto; color:#94a3b8; font-size:0.85rem" id="last-updated"></span>
        </div>

        <div class="tabs">
            <button class="tab-btn active" onclick="switchTab('today')">今日の投稿</button>
            <button class="tab-btn" onclick="switchTab('trends')">トレンド情報</button>
            <button class="tab-btn" onclick="switchTab('history')">過去の投稿</button>
        </div>

        <!-- 今日の投稿タブ -->
        <div class="tab-content active" id="tab-today">
            <div class="loading" id="loading">
                <div class="spinner"></div>
                <div>Claude AIが投稿文を生成しています...</div>
                <div style="font-size:0.85rem; color:#94a3b8; margin-top:8px">約30秒かかります</div>
            </div>
            <div class="platform-grid" id="posts-grid"></div>
            <div class="empty-state" id="empty-state" style="display:none">
                <div style="font-size:3rem">✍️</div>
                <p>まだ今日の投稿が生成されていません</p>
                <p>「今すぐ生成」ボタンを押すと生成が始まります</p>
            </div>
        </div>

        <!-- トレンドタブ -->
        <div class="tab-content" id="tab-trends">
            <div class="trends-section" id="trends-content">
                <div class="empty-state">
                    <p>投稿を生成するとトレンド情報が表示されます</p>
                </div>
            </div>
        </div>

        <!-- 履歴タブ -->
        <div class="tab-content" id="tab-history">
            <div class="history-list" id="history-list">
                <div class="empty-state">
                    <p>過去の投稿履歴がありません</p>
                </div>
            </div>
        </div>
    </div>

    <script>
        const PLATFORM_ICONS = {
            x: "𝕏",
            instagram: "📸",
            facebook: "📘",
            linkedin: "💼",
        };

        let currentData = null;

        function switchTab(tab) {
            document.querySelectorAll(".tab-btn").forEach((btn, i) => {
                btn.classList.toggle("active", ["today", "trends", "history"][i] === tab);
            });
            document.querySelectorAll(".tab-content").forEach((el, i) => {
                el.classList.toggle("active", ["tab-today", "tab-trends", "tab-history"][i] === `tab-${tab}`);
            });
            if (tab === "history") loadHistory();
        }

        function copyToClipboard(text, btn) {
            navigator.clipboard.writeText(text).then(() => {
                btn.textContent = "コピー完了!";
                btn.classList.add("copied");
                setTimeout(() => {
                    btn.textContent = "コピー";
                    btn.classList.remove("copied");
                }, 2000);
            });
        }

        function renderPosts(data) {
            currentData = data;
            const grid = document.getElementById("posts-grid");
            const empty = document.getElementById("empty-state");

            if (!data || !data.posts || Object.keys(data.posts).length === 0) {
                grid.innerHTML = "";
                empty.style.display = "block";
                return;
            }

            empty.style.display = "none";
            grid.innerHTML = "";

            for (const [platform, info] of Object.entries(data.posts)) {
                const isOver = info.max_chars !== null && info.char_count > info.max_chars;
                const charLabel = info.max_chars === null
                    ? `${info.char_count} 文字`
                    : `${info.char_count} / ${info.max_chars} 文字`;
                const card = document.createElement("div");
                card.className = "post-card";
                card.innerHTML = `
                    <div class="card-header">
                        <div class="platform-badge">
                            <span class="platform-icon">${PLATFORM_ICONS[platform] || "📝"}</span>
                            <span>${info.platform_name}</span>
                        </div>
                        <span class="char-count ${isOver ? "over" : ""}">
                            ${charLabel}
                        </span>
                    </div>
                    <div class="card-body">
                        <div class="post-content" id="content-${platform}">${escapeHtml(info.content)}</div>
                    </div>
                    <div class="card-footer">
                        <button class="copy-btn" onclick="copyToClipboard(document.getElementById('content-${platform}').textContent, this)">
                            コピー
                        </button>
                    </div>
                `;
                grid.appendChild(card);
            }

            // 更新時刻
            document.getElementById("last-updated").textContent =
                "最終生成: " + new Date(data.generated_at).toLocaleString("ja-JP");
        }

        function renderTrends(data) {
            const container = document.getElementById("trends-content");
            if (!data || !data.trending_data) {
                container.innerHTML = '<div class="empty-state"><p>トレンドデータがありません</p></div>';
                return;
            }

            const trends = data.trending_data.google_trends || [];
            const news = data.trending_data.news_articles || [];

            let html = "";
            if (trends.length > 0) {
                html += `<h2>Googleトレンドキーワード</h2>
                    <div class="trend-tags">
                        ${trends.map(t => `<span class="trend-tag">${escapeHtml(t)}</span>`).join("")}
                    </div>`;
            }
            if (news.length > 0) {
                html += `<h2>参照したニュース</h2>
                    <ul class="news-list">
                        ${news.map(a => `
                            <li class="news-item">
                                <div class="news-source">${escapeHtml(a.source)}</div>
                                <div class="news-title">${escapeHtml(a.title)}</div>
                            </li>
                        `).join("")}
                    </ul>`;
            }
            if (!html) {
                html = '<div class="empty-state"><p>トレンドデータがありません</p></div>';
            }
            container.innerHTML = html;
        }

        function escapeHtml(text) {
            return String(text)
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/"/g, "&quot;");
        }

        async function loadToday() {
            const res = await fetch("/api/today");
            const data = await res.json();
            const theme = data.theme || "";
            const biz = data.business_name || "";
            document.getElementById("theme-label").textContent =
                theme ? `${biz} / テーマ: ${theme}` : "";
            renderPosts(data);
            renderTrends(data);
        }

        async function loadHistory() {
            const res = await fetch("/api/history");
            const history = await res.json();
            const container = document.getElementById("history-list");

            if (history.length === 0) {
                container.innerHTML = '<div class="empty-state"><p>過去の投稿履歴がありません</p></div>';
                return;
            }

            container.innerHTML = history.map(record => {
                const firstPost = Object.values(record.posts || {})[0];
                const preview = firstPost ? firstPost.content : "";
                return `
                    <div class="history-card">
                        <div class="history-date">${record.date}</div>
                        <div style="font-size:0.82rem; color:#94a3b8; margin-bottom:8px">
                            テーマ: ${escapeHtml(record.theme || "")}
                        </div>
                        <div class="history-preview">${escapeHtml(preview)}</div>
                    </div>
                `;
            }).join("");
        }

        async function generateNow() {
            const btn = document.getElementById("gen-btn");
            const loading = document.getElementById("loading");
            const grid = document.getElementById("posts-grid");
            const empty = document.getElementById("empty-state");

            btn.disabled = true;
            btn.textContent = "生成中...";
            loading.classList.add("show");
            grid.innerHTML = "";
            empty.style.display = "none";

            try {
                const res = await fetch("/api/generate", { method: "POST" });
                const data = await res.json();
                if (data.error) {
                    alert("エラー: " + data.error);
                } else {
                    renderPosts(data);
                    renderTrends(data);
                }
            } catch (e) {
                alert("通信エラーが発生しました: " + e.message);
            } finally {
                btn.disabled = false;
                btn.textContent = "今すぐ生成";
                loading.classList.remove("show");
            }
        }

        // 初期読み込み
        loadToday();
    </script>
</body>
</html>
"""


def _run_daily_generation():
    """毎日の投稿生成バッチ処理（APSchedulerから呼び出し）"""
    import os
    from dotenv import load_dotenv
    from generator import generate_posts
    from storage import save_posts
    from trends import fetch_trending_topics

    load_dotenv()
    theme = os.getenv("SNS_THEME", "AIを活用したビジネス効率化")
    business_name = os.getenv("BUSINESS_NAME", "あなたのサービス")

    try:
        trending_data = fetch_trending_topics(theme=theme)
        posts = generate_posts(
            theme=theme,
            business_name=business_name,
            trending_data=trending_data,
        )
        save_posts(
            posts=posts,
            trending_data=trending_data,
            theme=theme,
            business_name=business_name,
        )
        print("[Scheduler] 投稿生成完了")
    except Exception as e:
        print(f"[Scheduler] 生成エラー: {e}")


def create_app() -> Flask:
    app = Flask(__name__)

    # APSchedulerで毎日9:00（JST=UTC+9）に自動生成
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        scheduler = BackgroundScheduler(timezone="Asia/Tokyo")
        schedule_time = os.getenv("SCHEDULE_TIME", "09:00")
        hour, minute = map(int, schedule_time.split(":"))
        scheduler.add_job(_run_daily_generation, "cron", hour=hour, minute=minute)
        scheduler.start()
        print(f"[Scheduler] 毎日 {schedule_time} に自動生成を設定しました")
    except ImportError:
        print("[Scheduler] APSchedulerが見つかりません。自動生成は無効です。")
    except Exception as e:
        print(f"[Scheduler] スケジューラー起動エラー: {e}")

    @app.route("/")
    @_require_auth
    def index():
        return render_template_string(DASHBOARD_HTML)

    @app.route("/api/today")
    @_require_auth
    def api_today():
        from storage import load_today
        data = load_today()
        return jsonify(data or {})

    @app.route("/api/history")
    @_require_auth
    def api_history():
        from storage import load_history
        history = load_history(days=30)
        return jsonify(history)

    @app.route("/api/generate", methods=["POST"])
    @_require_auth
    def api_generate():
        import os
        from dotenv import load_dotenv
        from generator import generate_posts
        from storage import save_posts
        from trends import fetch_trending_topics

        load_dotenv()
        theme = os.getenv("SNS_THEME", "AIを活用したビジネス効率化")
        business_name = os.getenv("BUSINESS_NAME", "あなたのサービス")

        try:
            trending_data = fetch_trending_topics(theme=theme)
            posts = generate_posts(
                theme=theme,
                business_name=business_name,
                trending_data=trending_data,
            )
            save_posts(
                posts=posts,
                trending_data=trending_data,
                theme=theme,
                business_name=business_name,
            )
            from storage import load_today
            return jsonify(load_today() or {})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return app
