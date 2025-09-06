(async function () {
  const $ = (id) => document.getElementById(id);

  // --- Health badge updater ---
  async function refreshHealth() {
    try {
      const r = await fetch("/health", { cache: "no-store" });
      const h = await r.json();

      $("#llmEp").textContent = h.llm_endpoint || "—";
      $("#llmModel").textContent = h.llm_model || "—";
      $("#whisperModel").textContent = h.whisper_model || "—";
      $("#piperBin").textContent = h.piper_bin || "—";

      const llmBadge = $("#llmBadge");
      llmBadge.textContent = "LLM: " + (h.llm_ok ? "ready" : "down");
      llmBadge.classList.toggle("ok", !!h.llm_ok);
      llmBadge.classList.toggle("bad", !h.llm_ok);

      const sttBadge = $("#sttBadge");
      sttBadge.textContent = "Whisper: " + (h.device || "—");
      sttBadge.classList.add("ok"); // device string already indicates CPU/GPU
    } catch (e) {
      const llmBadge = $("#llmBadge");
      llmBadge.textContent = "LLM: error";
      llmBadge.classList.remove("ok");
      llmBadge.classList.add("bad");
      // optional: console.error(e);
    }
  }
  await refreshHealth();
  setInterval(refreshHealth, 4000);

  // --- Event rendering ---
  const list = $("#events");
  function chip(k, v) {
    return `<span class="chip"><b>${k}</b> ${v}</span>`;
  }
  function add(ev) {
    const d = ev.data || {};
    const ms = d.ms || {};
    const persona = d.persona ? ` <span class="chip">${d.persona}</span>` : "";
    const timing = Object.keys(ms).length
      ? `<div class="timing">${[
          "stt" in ms ? chip("stt", ms.stt) : "",
          "llm" in ms ? chip("llm", ms.llm) : "",
          "tts" in ms ? chip("tts", ms.tts) : "",
          "total" in ms ? chip("total", ms.total) : "",
        ]
          .filter(Boolean)
          .join("")}</div>`
      : "";

    const transcript = d.transcript
      ? `<div class="soft">🗣 <em>${d.transcript}</em></div>`
      : "";

    const el = document.createElement("div");
    el.className = "ev";
    el.innerHTML = `
      <div class="head">
        <span class="type">${ev.type}</span>
        <span>•</span>
        <span>${new Date(ev.ts).toLocaleTimeString()}</span>
        ${
          ev.call_id
            ? `<span>•</span><code>${ev.call_id.slice(0, 8)}</code>`
            : ""
        }
        ${persona}
      </div>
      <div class="body">
        ${ev.text ? ev.text : ""}
        ${transcript}
        ${timing}
      </div>`;
    list.prepend(el);
  }

  // --- SSE wiring ---
  const es = new EventSource("/events");

  // Listen to our named event types (emitted by the server)
  ["phone_start", "stt_start", "stt_done", "call_end"].forEach((t) => {
    es.addEventListener(t, (e) => {
      try {
        add(JSON.parse(e.data));
      } catch {}
    });
  });

  // Fallback for any other event types
  es.onmessage = (m) => {
    try {
      add(JSON.parse(m.data));
    } catch {}
  };

  es.addEventListener("open", () =>
    add({
      type: "client",
      ts: new Date().toISOString(),
      text: "🔌 connected to /events",
    })
  );

  es.addEventListener("error", () =>
    add({
      type: "client",
      ts: new Date().toISOString(),
      text: "⚠️ event stream error",
    })
  );

  // Clean up on navigation
  window.addEventListener("beforeunload", () => es.close());
})();
