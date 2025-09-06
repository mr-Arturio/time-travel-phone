// ui/app.js
(function () {
  const log = (...a) => console.log("[ui]", ...a);

  const $ = (id) => document.getElementById(id);
  const setText = (id, txt) => {
    const el = $(id);
    if (el) el.textContent = txt;
  };
  const setBadge = (id, label, ok) => {
    const el = $(id);
    if (!el) return;
    el.textContent = label;
    el.classList.toggle("ok", !!ok);
    el.classList.toggle("bad", !ok);
  };

  async function refreshHealth() {
    try {
      const r = await fetch("/health", { cache: "no-store" });
      const h = await r.json();
      setText("llmEp", h.llm_endpoint || "—");
      setText("llmModel", h.llm_model || "—");
      setText("whisperModel", h.whisper_model || "—");
      setText("piperBin", h.piper_bin || "—");
      setBadge("llmBadge", "LLM: " + (h.llm_ok ? "ready" : "down"), h.llm_ok);
      setBadge("sttBadge", "Whisper: " + (h.device || "—"), true);
    } catch (e) {
      setBadge("llmBadge", "LLM: error", false);
      log("health error", e);
    }
  }

  function add(ev) {
    const list = $("events");
    if (!list) return;
    const d = ev.data || {};
    const el = document.createElement("div");
    el.className = "ev";
    const ts = ev.ts ? new Date(ev.ts).toLocaleTimeString() : "";
    el.innerHTML = `
      <div class="head">
        <span class="type">${ev.type}</span>
        <span>•</span><span>${ts}</span>
        ${ev.call_id ? `<span>•</span><code>${ev.call_id.slice(0, 8)}</code>` : ""}
      </div>
      <div class="body">
        ${ev.text ? ev.text : ""}
        ${d.ms ? `<div style="margin-top:4px;color:#9cb3c9;">⏱ ms: ${JSON.stringify(d.ms)}</div>` : ""}
        ${d.transcript ? `<div style="margin-top:4px;">🗣 <em>${d.transcript}</em></div>` : ""}
      </div>`;
    list.prepend(el);
  }

  function startSSE() {
    const es = new EventSource("/events");
    es.onmessage = (m) => {
      try { add(JSON.parse(m.data)); }
      catch (e) { log("SSE parse error", e, m.data); }
    };
    es.addEventListener("open", () =>
      add({ type: "client", ts: new Date().toISOString(), text: "🔌 connected to /events" })
    );
    es.addEventListener("error", () =>
      add({ type: "client", ts: new Date().toISOString(), text: "⚠️ event stream error" })
    );
    window.addEventListener("beforeunload", () => es.close());
  }

  // kick it off
  refreshHealth();
  setInterval(refreshHealth, 5000);
  startSSE();

  // optional: log that the dashboard opened (exercise the /event POST)
  fetch("/event", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ type: "dashboard_open", text: "UI opened" }),
  }).catch(() => {});
})();
