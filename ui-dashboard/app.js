(async function () {
  // 1) Load /health once for status
  try {
    const r = await fetch("/health");
    const h = await r.json();
    document.getElementById("llmEp").textContent = h.llm_endpoint || "—";
    document.getElementById("llmModel").textContent = h.llm_model || "—";
    document.getElementById("whisperModel").textContent =
      h.whisper_model || "—";
    document.getElementById("piperBin").textContent = h.piper_bin || "—";

    const llmBadge = document.getElementById("llmBadge");
    llmBadge.textContent = "LLM: " + (h.llm_ok ? "ready" : "down");
    llmBadge.classList.toggle("ok", !!h.llm_ok);
    llmBadge.classList.toggle("bad", !h.llm_ok);

    const sttBadge = document.getElementById("sttBadge");
    sttBadge.textContent = "Whisper: " + (h.device || "—");
    sttBadge.classList.add("ok");
  } catch (e) {
    const llmBadge = document.getElementById("llmBadge");
    llmBadge.textContent = "LLM: error";
    llmBadge.classList.add("bad");
  }

  // 2) SSE events
  const list = document.getElementById("events");
  function add(ev) {
    const d = ev.data || {};
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
      </div>
      <div class="body">
        ${ev.text ? ev.text : ""}
        ${
          d.ms
            ? `<div style="margin-top:4px;color:#9cb3c9;">⏱ ms: ${JSON.stringify(
                d.ms
              )}</div>`
            : ""
        }
        ${
          d.transcript
            ? `<div style="margin-top:4px;">🗣 <em>${d.transcript}</em></div>`
            : ""
        }
      </div>`;
    list.prepend(el);
  }

  const es = new EventSource("/events");
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
})();
