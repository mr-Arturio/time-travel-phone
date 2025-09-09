// ui-dashboard/app.js
(function () {
  const $ = (sel) => document.querySelector(sel);
  const list = $("#events");
  const calls = new Map(); // call_id -> {root, header, body, times}

  function prettyMs(ms) {
    if (ms == null) return "—";
    return `${ms} ms`;
  }

  function makeCallCard(call_id, persona = "unknown") {
    const root = document.createElement("div");
    root.className = "call";
    root.dataset.callId = call_id;

    const header = document.createElement("div");
    header.className = "call-h";
    header.innerHTML = `
      <div class="left">
        <span class="badge">CALL</span>
        <code class="cid">${call_id.slice(0, 8)}</code>
        <span class="persona"></span>
      </div>
      <div class="right">
        <span class="stt">STT: —</span>
        <span class="llm">LLM: —</span>
        <span class="tts">TTS: —</span>
        <span class="total strong">Total: —</span>
      </div>
    `;

    const body = document.createElement("div");
    body.className = "call-b";
    body.innerHTML = `
      <div class="row">
        <div class="label">Transcript</div>
        <div class="value transcript"></div>
      </div>
      <div class="row">
        <div class="label">Reply</div>
        <div class="value reply"></div>
      </div>
      <div class="row small gray">
        <div class="value note"></div>
      </div>
    `;

    root.appendChild(header);
    root.appendChild(body);
    list.prepend(root);

    const obj = {
      root,
      header,
      body,
      times: { stt: null, llm: null, tts: null, total: null },
      setPersona(name) {
        header.querySelector(".persona").textContent = `• ${name}`;
      },
      setTranscript(text, ms) {
        body.querySelector(".transcript").textContent = text || "";
        this.times.stt = ms ?? this.times.stt;
        header.querySelector(".stt").textContent = `STT: ${prettyMs(this.times.stt)}`;
      },
      setReply(text, used, ms) {
        body.querySelector(".reply").textContent = text || "";
        this.times.llm = ms ?? this.times.llm;
        header.querySelector(".llm").textContent = `LLM: ${prettyMs(this.times.llm)}${used ? "" : " (fallback)"}`;
      },
      setTTS(ms) {
        this.times.tts = ms ?? this.times.tts;
        header.querySelector(".tts").textContent = `TTS: ${prettyMs(this.times.tts)}`;
      },
      setTotal(ms) {
        this.times.total = ms ?? this.times.total;
        header.querySelector(".total").textContent = `Total: ${prettyMs(this.times.total)}`;
      },
      note(text) {
        body.querySelector(".note").textContent = text || "";
      },
    };

    calls.set(call_id, obj);
    return obj;
  }

  function ensureCard(call_id, personaMaybe) {
    if (!call_id) return null; // ignore test/dashboard events
    if (!calls.has(call_id)) {
      return makeCallCard(call_id, personaMaybe || "unknown");
    }
    return calls.get(call_id);
  }

  // 1) Load /health once for status bar
  (async function initHealth() {
    try {
      const r = await fetch("/health");
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
      sttBadge.classList.add("ok");

      // Mark UI opened (for your curl window / history)
      fetch("/event", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ type: "dashboard_open", text: "UI opened" }),
      }).catch(() => {});
    } catch {
      const llmBadge = $("#llmBadge");
      llmBadge.textContent = "LLM: error";
      llmBadge.classList.add("bad");
    }
  })();

  // 2) Handle incoming events
  function handle(ev) {
    // Remove placeholder if present
    const empty = document.getElementById("empty");
    if (empty) empty.remove();

    const data = ev.data || {};
    switch (ev.type) {
      case "phone_start": {
        const card = ensureCard(ev.call_id, data.persona);
        if (card) card.setPersona(data.persona || "unknown");
        break;
      }
      case "stt_start": {
        const card = ensureCard(ev.call_id);
        if (card) card.note("Transcribing…");
        break;
      }
      case "stt_done": {
        const card = ensureCard(ev.call_id);
        if (card) {
          card.setTranscript(data.transcript || "", data.ms);
          card.note("");
        }
        break;
      }
      case "llm_start": {
        const card = ensureCard(ev.call_id);
        if (card) card.note("Generating…");
        break;
      }
      case "llm_done": {
        const card = ensureCard(ev.call_id);
        if (card) {
          card.setReply(data.reply || "", !!data.used, data.ms);
          card.note("");
        }
        break;
      }
      case "tts_start": {
        const card = ensureCard(ev.call_id);
        if (card) card.note("Speaking…");
        break;
      }
      case "tts_done": {
        const card = ensureCard(ev.call_id);
        if (card) {
          card.setTTS(data.ms);
          card.note("");
        }
        break;
      }
      case "call_end": {
        const card = ensureCard(ev.call_id);
        if (card) {
          card.setTotal(data.total_ms);
          card.note("Completed");
        }
        break;
      }
      default: {
        // For test/dashboard events, just log a small line at the top
        const el = document.createElement("div");
        el.className = "ev";
        el.innerHTML = `
          <div class="head">
            <span class="type">${ev.type}</span>
            <span>•</span>
            <span>${new Date(ev.ts).toLocaleTimeString()}</span>
          </div>
          <div class="body">${ev.text || ""}</div>`;
        list.prepend(el);
      }
    }
  }

  // 3) Subscribe to all named SSE events
  const es = new EventSource("/events");
  const TYPES = [
    "phone_start",
    "stt_start",
    "stt_done",
    "llm_start",
    "llm_done",
    "tts_start",
    "tts_done",
    "call_end",
    "test",
    "dashboard_open",
  ];
  TYPES.forEach((t) =>
    es.addEventListener(t, (m) => {
      try {
        handle(JSON.parse(m.data));
      } catch (e) {
        console.error("bad event", t, e);
      }
    })
  );
  // Fallback if server ever sends default 'message' events
  es.onmessage = (m) => {
    try {
      handle(JSON.parse(m.data));
    } catch {}
  };
  es.addEventListener("open", () => {
    const el = document.createElement("div");
    el.className = "ev";
    el.innerHTML = `<div class="body">🔌 connected to /events</div>`;
    list.prepend(el);
  });
  es.addEventListener("error", () => {
    const el = document.createElement("div");
    el.className = "ev";
    el.innerHTML = `<div class="body">⚠️ event stream error</div>`;
    list.prepend(el);
  });
})();
