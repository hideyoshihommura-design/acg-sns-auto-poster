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
            <button class="tab-btn" onclick="switchTab('wordpress')">WordPress記事</button>
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

        <!-- WordPress記事タブ -->
        <div class="tab-content" id="tab-wordpress">
            <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:20px;">
                <div style="font-size:0.9rem; color:#64748b;">WordPressの新着記事を取得してSNS投稿文を生成・投稿できます</div>
                <div style="display:flex; gap:10px;">
                    <button class="generate-btn" style="background:#10b981; color:white; font-size:0.85rem; padding:8px 18px;" onclick="checkWordpress()">
                        新着記事を確認
                    </button>
                    <button class="generate-btn" style="background:#3b82f6; color:white; font-size:0.85rem; padding:8px 18px;" onclick="processNewArticles()">
                        新着を全て投稿
                    </button>
                </div>
            </div>
            <div id="wp-articles-list">
                <div class="empty-state">
                    <div style="font-size:3rem">📰</div>
                    <p>「新着記事を確認」ボタンを押してください</p>
                </div>
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
                btn.classList.toggle("active", ["today", "wordpress", "trends", "history"][i] === tab);
            });
            document.querySelectorAll(".tab-content").forEach((el, i) => {
                el.classList.toggle("active", ["tab-today", "tab-wordpress", "tab-trends", "tab-history"][i] === `tab-${tab}`);
            });
            if (tab === "history") loadHistory();
            if (tab === "trends") loadTrends();
            if (tab === "wordpress") checkWordpress();
        }

        // --- WordPress記事関連 ---

        async function checkWordpress() {
            const container = document.getElementById("wp-articles-list");
            container.innerHTML = '<div class="loading show"><div class="spinner"></div><div>WordPress新着記事を確認中...</div></div>';
            try {
                const res = await fetch("/api/wordpress/articles");
                const data = await res.json();
                renderWordpressArticles(data);
            } catch (e) {
                container.innerHTML = '<div class="empty-state"><p>取得エラー: ' + escapeHtml(e.message) + '</p></div>';
            }
        }

        function renderWordpressArticles(data) {
            const container = document.getElementById("wp-articles-list");
            const articles = data.articles || [];
            const siteConfigured = data.site_configured;

            if (!siteConfigured) {
                container.innerHTML = `<div class="empty-state">
                    <div style="font-size:2rem">⚙️</div>
                    <p style="margin-top:12px;font-weight:600;">WordPress URLが未設定です</p>
                    <p style="margin-top:8px;font-size:0.85rem;color:#94a3b8;">
                        .env ファイルに <code>WP_SITE_URL=https://yoursite.com</code> を設定してください
                    </p>
                </div>`;
                return;
            }

            if (!data.api_available) {
                container.innerHTML = `<div class="empty-state">
                    <div style="font-size:2rem">⚠️</div>
                    <p style="margin-top:12px;font-weight:600;">WordPress REST APIにアクセスできません</p>
                    <p style="margin-top:8px;font-size:0.85rem;color:#94a3b8;">
                        WordPress管理画面 → 設定 → パーマリンク設定 を保存し直してAPIを有効化してください
                    </p>
                </div>`;
                return;
            }

            if (articles.length === 0) {
                container.innerHTML = '<div class="empty-state"><div style="font-size:2rem">✅</div><p style="margin-top:12px;">新着未投稿記事はありません</p></div>';
                return;
            }

            container.innerHTML = articles.map(a => {
                const pubDate = a.published ? new Date(a.published).toLocaleString("ja-JP") : "";
                const imgHtml = a.featured_image_url
                    ? `<img src="${escapeHtml(a.featured_image_url)}" style="width:80px;height:60px;object-fit:cover;border-radius:6px;flex-shrink:0;" onerror="this.style.display='none'">`
                    : `<div style="width:80px;height:60px;background:#f1f5f9;border-radius:6px;display:flex;align-items:center;justify-content:center;color:#94a3b8;font-size:1.4rem;flex-shrink:0;">📷</div>`;
                return `
                <div class="post-card" style="margin-bottom:16px;">
                    <div class="card-body" style="display:flex;gap:16px;align-items:flex-start;">
                        ${imgHtml}
                        <div style="flex:1;min-width:0;">
                            <div style="font-weight:700;font-size:0.95rem;margin-bottom:4px;">${escapeHtml(a.title)}</div>
                            <div style="font-size:0.82rem;color:#94a3b8;margin-bottom:8px;">${pubDate}</div>
                            <div style="font-size:0.88rem;color:#64748b;line-height:1.5;">${escapeHtml(a.excerpt || a.content_preview || "")}</div>
                        </div>
                    </div>
                    <div class="card-footer">
                        <button class="copy-btn" style="border-color:#667eea;color:#667eea;"
                            onclick="generateFromArticle(${a.id}, '${escapeHtml(a.title).replace(/'/g, "\\'")}', this)">
                            投稿文を生成して投稿
                        </button>
                        <span style="font-size:0.78rem;color:#94a3b8;margin-left:auto;">${a.featured_image_url ? "📷 画像あり" : "📷 画像なし（Instagram除く）"}</span>
                    </div>
                </div>`;
            }).join("");
        }

        async function generateFromArticle(articleId, articleTitle, btn) {
            btn.disabled = true;
            btn.textContent = "生成・投稿中...";
            try {
                const res = await fetch("/api/wordpress/process-one", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({article_id: articleId}),
                });
                const data = await res.json();
                if (data.error) {
                    alert("エラー: " + data.error);
                    btn.disabled = false;
                    btn.textContent = "投稿文を生成して投稿";
                } else {
                    btn.textContent = "✅ 投稿完了";
                    btn.style.background = "#10b981";
                    btn.style.color = "white";
                    btn.style.borderColor = "#10b981";
                    // 結果表示
                    const results = data.post_results || {};
                    const lines = Object.entries(results).map(([p, r]) =>
                        `${p}: ${r.success ? "✅成功" : "❌" + r.error}`
                    );
                    if (lines.length > 0) {
                        const msg = document.createElement("div");
                        msg.style.cssText = "font-size:0.78rem;color:#64748b;margin-top:8px;";
                        msg.textContent = lines.join("  /  ");
                        btn.parentElement.appendChild(msg);
                    }
                }
            } catch (e) {
                alert("通信エラー: " + e.message);
                btn.disabled = false;
                btn.textContent = "投稿文を生成して投稿";
            }
        }

        async function processNewArticles() {
            if (!confirm("未投稿の新着記事を全て生成・投稿します。よろしいですか？")) return;
            const btn = event.target;
            btn.disabled = true;
            btn.textContent = "処理中...";
            try {
                const res = await fetch("/api/wordpress/process-all", {method: "POST"});
                const data = await res.json();
                if (data.error) {
                    alert("エラー: " + data.error);
                } else {
                    alert(`処理完了: ${data.processed}件の記事を処理しました`);
                    checkWordpress();
                }
            } catch (e) {
                alert("通信エラー: " + e.message);
            } finally {
                btn.disabled = false;
                btn.textContent = "新着を全て投稿";
            }
        }

        // --- SNS投稿ボタン（今日の投稿タブ） ---

        async function postToPlatform(platform, btn) {
            if (!confirm(`${platform.toUpperCase()} に投稿します。よろしいですか？`)) return;
            btn.disabled = true;
            btn.textContent = "投稿中...";
            try {
                const res = await fetch("/api/post", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({platform}),
                });
                const data = await res.json();
                const result = data[platform] || data;
                if (result.success) {
                    btn.textContent = "✅ 投稿済み";
                    btn.style.background = "#10b981";
                    btn.style.color = "white";
                    btn.style.borderColor = "#10b981";
                } else {
                    btn.textContent = "❌ 失敗";
                    btn.style.borderColor = "#ef4444";
                    btn.style.color = "#ef4444";
                    alert("投稿エラー: " + (result.error || "不明なエラー"));
                    btn.disabled = false;
                }
            } catch (e) {
                alert("通信エラー: " + e.message);
                btn.disabled = false;
                btn.textContent = "SNS投稿する";
            }
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
                        <button class="copy-btn" style="border-color:#10b981; color:#10b981;" id="post-btn-${platform}"
                            onclick="postToPlatform('${platform}', this)">
                            SNS投稿する
                        </button>
                    </div>
                `;
                grid.appendChild(card);
            }

            // 更新時刻
            document.getElementById("last-updated").textContent =
                "最終生成: " + new Date(data.generated_at).toLocaleString("ja-JP");
        }

        async function loadTrends() {
            const container = document.getElementById("trends-content");
            container.innerHTML = '<div class="loading show"><div class="spinner"></div><div>トレンド情報を取得中...</div></div>';
            try {
                const res = await fetch("/api/trends");
                const data = await res.json();
                renderTrends(data);
            } catch (e) {
                container.innerHTML = '<div class="empty-state"><p>トレンド取得に失敗しました: ' + escapeHtml(e.message) + '</p></div>';
            }
        }

        function renderTrends(data) {
            const container = document.getElementById("trends-content");
            // /api/trends は直接 {google_trends, news_articles, fetched_at} を返す
            // /api/today 経由は data.trending_data の下に入っている
            const trends_data = (data && data.google_trends !== undefined) ? data : (data && data.trending_data ? data.trending_data : null);
            if (!trends_data) {
                container.innerHTML = '<div class="empty-state"><p>トレンドデータがありません</p></div>';
                return;
            }

            const trends = trends_data.google_trends || [];
            const news = trends_data.news_articles || [];
            const fetchedAt = trends_data.fetched_at
                ? new Date(trends_data.fetched_at).toLocaleString("ja-JP")
                : null;

            let html = `<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;">
                <span style="font-size:0.82rem;color:#94a3b8;">
                    ${fetchedAt ? "取得時刻: " + fetchedAt : ""}
                </span>
                <button onclick="loadTrends()" style="padding:5px 14px;border-radius:8px;border:1.5px solid #667eea;background:transparent;color:#667eea;font-size:0.82rem;font-weight:600;cursor:pointer;">
                    ↻ 再取得
                </button>
            </div>`;

            if (trends.length > 0) {
                html += `<h2>Googleトレンドキーワード</h2>
                    <div class="trend-tags">
                        ${trends.map(t => `<span class="trend-tag">${escapeHtml(t)}</span>`).join("")}
                    </div>`;
            }
            if (news.length > 0) {
                html += `<h2>参照したニュース</h2>
                    <ul class="news-list">
                        ${news.map(a => {
                            let pubStr = "";
                            if (a.published) {
                                try {
                                    pubStr = new Date(a.published).toLocaleDateString("ja-JP");
                                } catch(e) { pubStr = a.published; }
                            }
                            return `
                            <li class="news-item">
                                <div class="news-source">${escapeHtml(a.source)}${pubStr ? " &nbsp;·&nbsp; " + pubStr : ""}</div>
                                <div class="news-title">${escapeHtml(a.title)}</div>
                            </li>`;
                        }).join("")}
                    </ul>`;
            }
            if (trends.length === 0 && news.length === 0) {
                html += '<div class="empty-state"><p>トレンドデータがありません</p></div>';
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

    @app.route("/api/trends")
    @_require_auth
    def api_trends():
        from trends import fetch_trending_topics
        try:
            data = fetch_trending_topics()
            return jsonify(data)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

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

    @app.route("/api/post", methods=["POST"])
    @_require_auth
    def api_post():
        """今日生成済みの投稿文を指定プラットフォームに投稿する"""
        from poster import post_to_x, post_to_facebook, post_to_instagram
        from storage import load_today

        data = request.get_json() or {}
        platform = data.get("platform")

        today_data = load_today()
        if not today_data or not today_data.get("posts"):
            return jsonify({"error": "今日の投稿文がありません。先に生成してください。"}), 400

        posts = today_data["posts"]

        if platform == "x":
            content = posts.get("x", {}).get("content", "")
            if not content:
                return jsonify({"error": "X用の投稿文がありません"}), 400
            result = post_to_x(content)
        elif platform == "facebook":
            content = posts.get("facebook", {}).get("content", "")
            if not content:
                return jsonify({"error": "Facebook用の投稿文がありません"}), 400
            result = post_to_facebook(content)
        elif platform == "instagram":
            content = posts.get("instagram", {}).get("content", "")
            if not content:
                return jsonify({"error": "Instagram用の投稿文がありません"}), 400
            image_url = today_data.get("wordpress_image_url")
            result = post_to_instagram(content, image_url=image_url)
        else:
            return jsonify({"error": f"未対応のプラットフォーム: {platform}"}), 400

        return jsonify({platform: result})

    @app.route("/api/wordpress/articles")
    @_require_auth
    def api_wordpress_articles():
        """WordPress新着未投稿記事の一覧を返す"""
        from wordpress import get_new_articles, check_api_available

        site_url = os.getenv("WP_SITE_URL", "")
        if not site_url:
            return jsonify({"site_configured": False, "api_available": False, "articles": []})

        api_available = check_api_available(site_url)
        if not api_available:
            return jsonify({"site_configured": True, "api_available": False, "articles": []})

        articles = get_new_articles(
            site_url=site_url,
            category_slug=os.getenv("WP_NEWS_CATEGORY_SLUG") or None,
            recent_hours=int(os.getenv("WP_CHECK_HOURS", "48")),
        )
        return jsonify({"site_configured": True, "api_available": True, "articles": articles})

    @app.route("/api/wordpress/process-one", methods=["POST"])
    @_require_auth
    def api_wordpress_process_one():
        """指定した記事IDの投稿文を生成してSNSに投稿する"""
        from wordpress import fetch_recent_articles, save_posted_id
        from generator import generate_posts
        from poster import post_all
        from trends import fetch_trending_topics

        data = request.get_json() or {}
        article_id = data.get("article_id")
        if not article_id:
            return jsonify({"error": "article_id が指定されていません"}), 400

        site_url = os.getenv("WP_SITE_URL", "")
        if not site_url:
            return jsonify({"error": "WP_SITE_URL が設定されていません"}), 400

        # 記事を取得
        articles = fetch_recent_articles(
            site_url=site_url,
            recent_hours=72,  # 少し広めに
            max_items=20,
            wp_username=os.getenv("WP_USERNAME") or None,
            wp_app_password=os.getenv("WP_APP_PASSWORD") or None,
        )
        article = next((a for a in articles if a["id"] == article_id), None)
        if not article:
            return jsonify({"error": f"記事ID {article_id} が見つかりません"}), 404

        try:
            # トレンド取得 + 投稿文生成（WordPress記事情報を追加コンテキストとして渡す）
            theme = os.getenv("SNS_THEME", "AIを活用したビジネス効率化")
            business_name = os.getenv("BUSINESS_NAME", "あなたのサービス")
            trending_data = fetch_trending_topics(theme=theme)

            # WordPress記事がある日はその記事だけで生成（外部ニュースは使わない）
            trending_data["news_articles"] = [{
                "title": article["title"],
                "summary": article["excerpt"] or article["content_preview"],
                "source": "自社サイトNEWS",
                "score": 100,
                "category": "自社",
            }]
            trending_data["google_trends"] = []
            trending_data["wp_article_url"] = article["url"]
            trending_data["wp_article_title"] = article["title"]

            posts = generate_posts(
                theme=theme,
                business_name=business_name,
                trending_data=trending_data,
            )

            # SNSに投稿
            image_url = article.get("featured_image_url")
            post_results = post_all(posts, image_url=image_url)

            # 少なくとも1つ成功したら投稿済みとして記録
            any_success = any(r.get("success") for r in post_results.values())
            if any_success:
                save_posted_id(article_id)

            return jsonify({
                "article_id": article_id,
                "article_title": article["title"],
                "post_results": post_results,
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/wordpress/process-all", methods=["POST"])
    @_require_auth
    def api_wordpress_process_all():
        """未投稿の新着記事を全て処理する（Cloud Schedulerからも呼ばれる）"""
        from wordpress import get_new_articles, save_posted_id
        from generator import generate_posts
        from poster import post_all
        from trends import fetch_trending_topics

        site_url = os.getenv("WP_SITE_URL", "")
        if not site_url:
            return jsonify({"error": "WP_SITE_URL が設定されていません"}), 400

        articles = get_new_articles(
            site_url=site_url,
            category_slug=os.getenv("WP_NEWS_CATEGORY_SLUG") or None,
            recent_hours=int(os.getenv("WP_CHECK_HOURS", "48")),
        )

        processed = 0
        results = []

        # トレンドは一度だけ取得
        theme = os.getenv("SNS_THEME", "AIを活用したビジネス効率化")
        business_name = os.getenv("BUSINESS_NAME", "あなたのサービス")

        try:
            base_trending = fetch_trending_topics(theme=theme)
        except Exception:
            base_trending = {"google_trends": [], "news_articles": []}

        for article in articles[:5]:  # 一度に最大5件
            try:
                # WordPress記事がある日はその記事だけで生成（外部ニュースは使わない）
                trending_data = {
                    "google_trends": [],
                    "news_articles": [{
                        "title": article["title"],
                        "summary": article["excerpt"] or article["content_preview"],
                        "source": "自社サイトNEWS",
                        "score": 100,
                        "category": "自社",
                    }],
                }

                posts = generate_posts(
                    theme=theme,
                    business_name=business_name,
                    trending_data=trending_data,
                )
                post_results = post_all(posts, image_url=article.get("featured_image_url"))

                any_success = any(r.get("success") for r in post_results.values())
                if any_success:
                    save_posted_id(article["id"])
                    processed += 1

                results.append({
                    "article_id": article["id"],
                    "article_title": article["title"],
                    "post_results": post_results,
                })
            except Exception as e:
                results.append({"article_id": article["id"], "error": str(e)})

        return jsonify({"processed": processed, "total_new": len(articles), "results": results})

    return app
