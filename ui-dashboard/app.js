// ui-dashboard/app.js
(function () {
  const $ = (sel) => document.querySelector(sel);
  const list = $("#events");
  const calls = new Map(); // call_id -> {root, header, body, times, persona, digits}
  let activeId = null; // temporary card id before server assigns a call_id

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
        <code class="cid">${String(call_id).slice(0, 8)}</code>
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
      persona: persona || "unknown",
      digits: "",
      times: { stt: null, llm: null, tts: null, total: null },

      setPersona(name) {
        this.persona = name || "unknown";
        header.querySelector(".persona").textContent = `• ${this.persona}${
          this.digits ? "  #" + this.digits : ""
        }`;
      },

      addDigit(d) {
        this.digits += String(d);
        header.querySelector(
          ".persona"
        ).textContent = `• ${this.persona}  #${this.digits}`;
      },

      setTranscript(text, ms) {
        body.querySelector(".transcript").textContent = text || "";
        this.times.stt = ms ?? this.times.stt;
        header.querySelector(".stt").textContent = `STT: ${prettyMs(
          this.times.stt
        )}`;
      },

      // Append final reply instead of replacing (so greeting/filler lines remain)
      setReply(text, used, ms) {
        const cont = body.querySelector(".reply");
        const line = document.createElement("div");
        line.textContent = text || "";
        cont.appendChild(line);
        this.times.llm = ms ?? this.times.llm;
        header.querySelector(".llm").textContent = `LLM: ${prettyMs(
          this.times.llm
        )}${used ? "" : " (fallback)"}`;
      },

      // Generic appender (for greeting / filler lines)
      appendReply(text) {
        const cont = body.querySelector(".reply");
        const line = document.createElement("div");
        line.textContent = text || "";
        cont.appendChild(line);
      },

      setTTS(ms) {
        this.times.tts = ms ?? this.times.tts;
        header.querySelector(".tts").textContent = `TTS: ${prettyMs(
          this.times.tts
        )}`;
      },

      setTotal(ms) {
        this.times.total = ms ?? this.times.total;
        header.querySelector(".total").textContent = `Total: ${prettyMs(
          this.times.total
        )}`;
      },

      note(text) {
        body.querySelector(".note").textContent = text || "";
      },
    };

    obj.setPersona(persona);
    calls.set(call_id, obj);
    return obj;
  }

  function ensureCard(call_id, personaMaybe) {
    if (!call_id) return null;
    if (!calls.has(call_id)) {
      return makeCallCard(call_id, personaMaybe || "unknown");
    }
    return calls.get(call_id);
  }

  // Keep a temporary active card when no call_id is present yet
  function ensureActiveCard(ev, personaMaybe) {
    const cid = ev.call_id || activeId || `pending-${Date.now()}`;
    if (!activeId) activeId = cid; // lock until end of call
    return ensureCard(cid, personaMaybe);
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

      // Mark UI opened (tolerate either 'type' or 'event' on server)
      fetch("/event", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          type: "dashboard_open",
          event: "dashboard_open",
          text: "UI opened",
        }),
      }).catch(() => {});
    } catch {
      const llmBadge = $("#llmBadge");
      llmBadge.textContent = "LLM: error";
      llmBadge.classList.add("bad");
    }
  })();

  // 2) Handle incoming events
  function handle(raw) {
    const type = raw.type || raw.event || "message";
    const data = raw.data || {};
    const ts = raw.ts || Date.now();

    // Remove placeholder if present
    const empty = document.getElementById("empty");
    if (empty) empty.remove();

    switch (type) {
      case "phone_start": {
        const card = ensureActiveCard(raw, data.persona);
        if (card) {
          card.setPersona(data.persona || "unknown");
          card.note("Handset lifted — dial a 3-digit code…");
        }
        break;
      }
      case "dial_digit": {
        const card = ensureActiveCard(raw);
        if (card) {
          if (typeof data.d !== "undefined") card.addDigit(data.d);
          card.note(`Dialing… ${card.digits}`);
        }
        break;
      }
      case "ringback": {
        const card = ensureActiveCard(raw);
        if (card) card.note("Ringback…");
        break;
      }
      case "answer": {
        const card = ensureActiveCard(raw);
        if (card) {
          const s = (data && data.sound) || "answer";
          card.note(s === "receiver_lift" ? "📞 Answered" : "📎 Click");
        }
        break;
      }
      case "greet": {
        const card = ensureActiveCard(raw);
        if (card) {
          const msg = data.caption || data.text || "Hello.";
          card.appendReply(`👋 ${msg}`);
          card.note("Greeting played.");
        }
        break;
      }
      case "record_start": {
        const card = ensureActiveCard(raw);
        if (card) card.note("Recording… speak now.");
        break;
      }
      case "record_done": {
        const card = ensureActiveCard(raw);
        if (card) card.note(`Recorded ${data.sec ?? "?"}s — transcribing…`);
        break;
      }
      case "stt_start": {
        const card = ensureActiveCard(raw);
        if (card) card.note("Transcribing…");
        break;
      }
      case "stt_done": {
        const card = ensureActiveCard(raw);
        if (card) {
          card.setTranscript(data.transcript || "", data.ms);
          card.note("");
        }
        break;
      }
      case "filler_start": {
        const card = ensureActiveCard(raw);
        if (card) {
          const msg = data.caption || data.text || "Thinking…";
          card.appendReply(`… ${msg}`);
          card.note("Thinking…");
        }
        break;
      }
      case "filler_stop": {
        const card = ensureActiveCard(raw);
        if (card) card.note("");
        break;
      }
      case "llm_start": {
        const card = ensureActiveCard(raw);
        if (card) card.note("Generating…");
        break;
      }
      case "llm_done": {
        const card = ensureActiveCard(raw);
        if (card) {
          card.setReply(data.reply || "", !!data.used, data.ms);
          card.note("");
        }
        break;
      }
      case "tts_start": {
        const card = ensureActiveCard(raw);
        if (card) card.note("Speaking…");
        break;
      }
      case "tts_done": {
        const card = ensureActiveCard(raw);
        if (card) {
          card.setTTS(data.ms);
          card.note("");
        }
        break;
      }
      case "call_end": {
        const card = ensureActiveCard(raw);
        if (card) {
          card.setTotal(data.total_ms);
          card.note(data.reason ? `Completed (${data.reason})` : "Completed");
        }
        // clear activeId so the next call makes a new card
        activeId = null;
        break;
      }
      default: {
        // For test/unknown events, log a simple line
        const el = document.createElement("div");
        el.className = "ev";
        el.innerHTML = `
          <div class="head">
            <span class="type">${type}</span>
            <span>•</span>
            <span>${new Date(ts).toLocaleTimeString()}</span>
          </div>
          <div class="body">${raw.text || ""}</div>`;
        list.prepend(el);
      }
    }
  }

  // 3) Subscribe to all named SSE events
  const es = new EventSource("/events");
  const TYPES = [
    "phone_start",
    "dial_digit",
    "ringback",
    "answer",
    "greet",
    "record_start",
    "record_done",
    "stt_start",
    "stt_done",
    "filler_start",
    "filler_stop",
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
