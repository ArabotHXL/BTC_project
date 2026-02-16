
(function () {
  const LANG = window.__LANG__ || "en";

  const el = (id) => document.getElementById(id);
  const fmtTs = (ts) => {
    try {
      const d = new Date(ts * 1000);
      return d.toLocaleString();
    } catch (e) {
      return String(ts);
    }
  };

  const TAGS = ["btc", "mining", "etf", "regulation", "macro", "exchange", "hack", "stablecoin", "energy"];

  const state = {
    selectedTags: new Set(),
    lastNews: null,
    lastTrends: null,
    bookmarks: [],
    alerts: [],
  };

  function t(zh, en) {
    return LANG === "zh" ? zh : en;
  }

  function renderTagPills() {
    const c = el("tagPills");
    c.innerHTML = "";
    TAGS.forEach((tag) => {
      const b = document.createElement("button");
      b.className = "btn btn-sm " + (state.selectedTags.has(tag) ? "btn-primary" : "btn-outline-light");
      b.textContent = tag;
      b.addEventListener("click", () => {
        if (state.selectedTags.has(tag)) state.selectedTags.delete(tag);
        else state.selectedTags.add(tag);
        renderTagPills();
        refresh();
      });
      c.appendChild(b);
    });
  }

  async function apiGet(path) {
    const r = await fetch(path, { credentials: "include" });
    if (!r.ok) throw new Error(await r.text());
    return await r.json();
  }

  async function apiJson(path, method, body) {
    const r = await fetch(path, {
      method,
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || {}),
    });
    if (!r.ok) throw new Error(await r.text());
    return await r.json();
  }

  function currentQuery() {
    const windowHours = parseInt(el("windowHours").value || "24", 10);
    const q = (el("q").value || "").trim();
    const tags = Array.from(state.selectedTags.values()).join(",");
    return { windowHours, q, tags };
  }

  function renderBadges(tags) {
    const wrap = document.createElement("span");
    (tags || []).forEach((tag) => {
      const s = document.createElement("span");
      s.className = "badge rounded-pill me-1 badge-tag";
      s.textContent = tag;
      wrap.appendChild(s);
    });
    return wrap;
  }

  function makeBookmarkBtn(item) {
    const btn = document.createElement("button");
    btn.className = "btn btn-outline-light btn-sm";
    btn.innerHTML = '<i class="bi bi-bookmark-plus"></i>';
    btn.title = t("收藏", "Bookmark");
    btn.addEventListener("click", async () => {
      try {
        await apiJson("/api/market-intel/bookmarks", "POST", { item });
        await loadBookmarks();
      } catch (e) {
        alert("Bookmark failed: " + e.message);
      }
    });
    return btn;
  }

  function renderStories(stories) {
    const c = el("stories");
    c.innerHTML = "";

    el("storyCount").textContent = t("事件簇", "Clusters") + ": " + (stories?.length || 0);

    (stories || []).forEach((s) => {
      const card = document.createElement("div");
      card.className = "item-card";

      const top = document.createElement("div");
      top.className = "d-flex justify-content-between gap-2";
      const left = document.createElement("div");
      const title = document.createElement("div");
      title.className = "item-title";
      title.textContent = s.headline || "(no headline)";
      const meta = document.createElement("div");
      meta.className = "item-meta";
      meta.textContent = `${t("来源", "Sources")}: ${(s.sources || []).join(", ")} · ${t("条目", "Items")}: ${(s.items || []).length} · ${t("最新", "Latest")}: ${fmtTs(s.latest_ts || 0)} · ${t("评分", "Score")}: ${Number(s.max_score || 0).toFixed(2)}`;

      left.appendChild(title);
      left.appendChild(meta);
      left.appendChild(renderBadges(s.top_tags || []));

      const right = document.createElement("div");
      right.className = "d-flex align-items-start gap-1";
      // show bookmark for first item
      if (s.items && s.items.length) {
        right.appendChild(makeBookmarkBtn(s.items[0]));
      }

      top.appendChild(left);
      top.appendChild(right);
      card.appendChild(top);

      // show up to 3 links
      const ul = document.createElement("div");
      ul.className = "mt-2 small";
      (s.items || []).slice(0, 3).forEach((it) => {
        const row = document.createElement("div");
        const a = document.createElement("a");
        a.href = it.url;
        a.target = "_blank";
        a.rel = "noopener";
        a.textContent = "• " + (it.title || it.url);
        row.appendChild(a);
        ul.appendChild(row);
      });
      card.appendChild(ul);

      c.appendChild(card);
    });
  }

  function renderNews(items) {
    const c = el("newsList");
    c.innerHTML = "";
    el("newsCount").textContent = t("条目", "Items") + ": " + (items?.length || 0);

    (items || []).forEach((it) => {
      const card = document.createElement("div");
      card.className = "item-card";

      const top = document.createElement("div");
      top.className = "d-flex justify-content-between gap-2";

      const left = document.createElement("div");
      const a = document.createElement("a");
      a.href = it.url;
      a.target = "_blank";
      a.rel = "noopener";
      a.className = "item-title";
      a.textContent = it.title || it.url;

      const meta = document.createElement("div");
      meta.className = "item-meta";
      meta.textContent = `${it.source || "unknown"} · ${fmtTs(it.published_at || 0)} · ${t("评分", "Score")}: ${Number(it.score || 0).toFixed(2)}`;

      const summary = document.createElement("div");
      summary.className = "mt-1";
      summary.style.opacity = "0.9";
      summary.textContent = (it.summary || "").slice(0, 200);

      left.appendChild(a);
      left.appendChild(meta);
      left.appendChild(renderBadges(it.tags || []));
      if (it.summary) left.appendChild(summary);

      const right = document.createElement("div");
      right.className = "d-flex align-items-start gap-1";
      right.appendChild(makeBookmarkBtn(it));

      top.appendChild(left);
      top.appendChild(right);

      card.appendChild(top);
      c.appendChild(card);
    });
  }

  function renderTrends(tr) {
    const tagWrap = el("topTags");
    const kwWrap = el("topKeywords");
    tagWrap.innerHTML = "";
    kwWrap.innerHTML = "";

    (tr.top_tags || []).slice(0, 12).forEach((x) => {
      const s = document.createElement("span");
      s.className = "badge rounded-pill me-1 badge-tag";
      s.textContent = `${x.tag} (${x.count})`;
      tagWrap.appendChild(s);
    });

    (tr.top_keywords || []).slice(0, 24).forEach((x) => {
      const s = document.createElement("span");
      s.className = "badge rounded-pill me-1 badge-keyword";
      s.textContent = `${x.term} (${x.count})`;
      kwWrap.appendChild(s);
    });
  }

  async function refresh() {
    const { windowHours, q, tags } = currentQuery();
    el("metaLine").textContent = t("加载中…", "Loading…");

    const qp = new URLSearchParams();
    qp.set("window_hours", String(windowHours));
    if (q) qp.set("q", q);
    if (tags) qp.set("tags", tags);

    try {
      const [news, trends] = await Promise.all([
        apiGet("/api/market-intel/news?" + qp.toString()),
        apiGet("/api/market-intel/trends?" + qp.toString()),
      ]);
      state.lastNews = news;
      state.lastTrends = trends;

      renderStories(news.stories || []);
      renderNews(news.items || []);
      renderTrends(trends);

      el("metaLine").textContent = `${t("生成时间", "Generated")}: ${fmtTs(news.generated_at || 0)} · ${t("窗口", "Window")}: ${news.window_hours}h · ${t("来源数量", "Sources")}: ${(trends.top_sources || []).length}`;
    } catch (e) {
      console.error(e);
      el("metaLine").textContent = t("加载失败：", "Load failed: ") + e.message;
    }
  }

  async function loadBookmarks() {
    const c = el("bookmarkList");
    c.innerHTML = t("加载中…", "Loading…");
    try {
      const data = await apiGet("/api/market-intel/bookmarks");
      state.bookmarks = data.items || [];
      c.innerHTML = "";
      if (!state.bookmarks.length) {
        c.textContent = t("暂无收藏", "No bookmarks yet");
        return;
      }
      state.bookmarks.slice(0, 50).forEach((b) => {
        const row = document.createElement("div");
        row.className = "d-flex justify-content-between gap-2 item-card";
        const left = document.createElement("div");
        const a = document.createElement("a");
        a.href = b.url;
        a.target = "_blank";
        a.rel = "noopener";
        a.textContent = b.title || b.url;
        const meta = document.createElement("div");
        meta.className = "item-meta";
        meta.textContent = `${b.source || "unknown"} · ${fmtTs(b.published_at || 0)}`;
        left.appendChild(a);
        left.appendChild(meta);

        const btn = document.createElement("button");
        btn.className = "btn btn-outline-danger btn-sm";
        btn.innerHTML = '<i class="bi bi-trash"></i>';
        btn.addEventListener("click", async () => {
          await apiJson("/api/market-intel/bookmarks", "DELETE", { news_id: b.news_id });
          await loadBookmarks();
        });

        row.appendChild(left);
        row.appendChild(btn);
        c.appendChild(row);
      });
    } catch (e) {
      c.textContent = "Bookmarks failed: " + e.message;
    }
  }

  async function loadAlerts() {
    const c = el("alertList");
    c.innerHTML = t("加载中…", "Loading…");
    try {
      const data = await apiGet("/api/market-intel/alerts");
      state.alerts = data.items || [];
      c.innerHTML = "";
      if (!state.alerts.length) {
        c.textContent = t("暂无规则", "No alerts yet");
        return;
      }
      state.alerts.forEach((a) => {
        const row = document.createElement("div");
        row.className = "item-card";
        const top = document.createElement("div");
        top.className = "d-flex justify-content-between gap-2";
        const left = document.createElement("div");
        left.innerHTML = `<div class="item-title">${a.name}</div>
          <div class="item-meta">${t("关键词", "Keywords")}: ${(a.keywords || []).join(", ")} · ${t("标签", "Tags")}: ${(a.tags || []).join(", ")} · ${t("最低分", "Min")}: ${Number(a.min_score || 0).toFixed(1)}</div>`;
        const btn = document.createElement("button");
        btn.className = "btn btn-outline-danger btn-sm";
        btn.innerHTML = '<i class="bi bi-x"></i>';
        btn.addEventListener("click", async () => {
          await apiJson("/api/market-intel/alerts", "DELETE", { id: a.id });
          await loadAlerts();
        });
        top.appendChild(left);
        top.appendChild(btn);
        row.appendChild(top);
        c.appendChild(row);
      });
    } catch (e) {
      c.textContent = "Alerts failed: " + e.message;
    }
  }

  async function addAlert() {
    const name = (el("alertName").value || "").trim() || t("新规则", "New alert");
    const keywords = (el("alertKeywords").value || "").split(",").map((x) => x.trim()).filter(Boolean);
    const tags = (el("alertTags").value || "").split(",").map((x) => x.trim()).filter(Boolean);
    const minScore = parseFloat(el("alertMinScore").value || "0") || 0.0;
    try {
      await apiJson("/api/market-intel/alerts", "POST", { name, keywords, tags, min_score: minScore });
      await loadAlerts();
      el("alertName").value = "";
    } catch (e) {
      alert("Add alert failed: " + e.message);
    }
  }

  async function checkAlertMatches() {
    const out = el("alertMatches");
    out.innerHTML = t("检查中…", "Checking…");
    try {
      const windowHours = parseInt(el("windowHours").value || "24", 10);
      const data = await apiGet(`/api/market-intel/alerts/matches?window_hours=${windowHours}`);
      const matches = data.matches || {};
      let html = "";
      const ids = Object.keys(matches);
      if (!ids.length) {
        out.innerHTML = `<div class="small text-muted">${t("暂无命中", "No matches")}</div>`;
        return;
      }
      ids.forEach((aid) => {
        const items = matches[aid] || [];
        const alertObj = (state.alerts || []).find((x) => String(x.id) === String(aid));
        const name = alertObj ? alertObj.name : ("Alert " + aid);
        html += `<div class="item-card mb-2"><div class="item-title">${name}</div>
          <div class="item-meta">${t("命中", "Matches")}: ${items.length}</div>`;
        items.slice(0, 4).forEach((it) => {
          html += `<div class="small"><a href="${it.url}" target="_blank" rel="noopener">• ${it.title}</a></div>`;
        });
        html += "</div>";
      });
      out.innerHTML = html;
    } catch (e) {
      out.innerHTML = "Match check failed: " + e.message;
    }
  }

  function wire() {
    el("btnRefresh").addEventListener("click", refresh);
    el("btnSearch").addEventListener("click", refresh);
    el("windowHours").addEventListener("change", refresh);

    el("btnLoadBookmarks").addEventListener("click", loadBookmarks);
    el("btnLoadAlerts").addEventListener("click", loadAlerts);
    el("btnAddAlert").addEventListener("click", addAlert);
    el("btnCheckAlerts").addEventListener("click", checkAlertMatches);

    // Enter key triggers search
    el("q").addEventListener("keydown", (e) => {
      if (e.key === "Enter") refresh();
    });
  }

  // init
  renderTagPills();
  wire();
  refresh();
  loadBookmarks();
  loadAlerts();
})();
