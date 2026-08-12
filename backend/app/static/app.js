// Passaporto Italiano – Frontend-Logik.
// Bewusst ohne externe Bibliotheken/CDN implementiert (self-hosted, keine
// Drittanbieter-Abhängigkeiten).

const EXERCISE_LABELS = {
  translation: "Übersetzung",
  conjugation: "Konjugation",
  article: "Artikel",
  plural: "Plural",
};

function el(tag, attrs, children) {
  const node = document.createElement(tag);
  Object.entries(attrs || {}).forEach(([k, v]) => {
    if (k === "text") node.textContent = v;
    else node.setAttribute(k, v);
  });
  (children || []).forEach((c) => node.appendChild(c));
  return node;
}

async function fetchJSON(url, options) {
  const res = await fetch(url, options);
  if (!res.ok) throw new Error(`Anfrage fehlgeschlagen (${res.status})`);
  return res.json();
}

// ---------------- Review-Seite ----------------

function initReview() {
  const root = document.getElementById("review-root");
  if (!root) return;
  loadNextExercise(root);
}

async function loadNextExercise(root) {
  root.innerHTML = '<p class="muted">Lade nächste Übung …</p>';
  let payload;
  try {
    payload = await fetchJSON("/review/next");
  } catch (err) {
    root.innerHTML = `<p class="feedback wrong">Fehler beim Laden: ${err.message}</p>`;
    return;
  }

  if (payload.done) {
    root.innerHTML = `<p class="muted">${payload.message || "Für dieses Level ist aktuell nichts fällig oder vorhanden."}</p>`;
    return;
  }

  renderExercise(root, payload);
}

function renderExercise(root, payload) {
  root.innerHTML = "";

  const badge = el("span", { class: "level-badge", text: payload.level });
  const type = el("span", {
    class: "muted",
    text: "  " + (EXERCISE_LABELS[payload.exercise_type] || payload.exercise_type),
  });
  const hintLine = el("div", { class: "exercise-hint", text: payload.hint || "" });
  const question = el("div", { class: "exercise-question", text: payload.question });

  const form = el("form", { class: "inline" });
  const input = el("input", { type: "text", autocomplete: "off", placeholder: "Deine Antwort …" });
  const submitBtn = el("button", { type: "submit", text: "Prüfen" });
  form.appendChild(input);
  form.appendChild(submitBtn);

  const feedbackHolder = el("div", {});
  let answered = false;

  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();

    if (answered) {
      loadNextExercise(root);
      return;
    }

    submitBtn.disabled = true;
    const submission = {
      lexeme_id: payload.lexeme_id,
      exercise_type: payload.exercise_type,
      given_answer: input.value,
      direction: payload.direction || null,
      tense: payload.tense || null,
      person: payload.person || null,
      plural: typeof payload.plural === "boolean" ? payload.plural : null,
    };
    let result;
    try {
      result = await fetchJSON("/review/answer", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(submission),
      });
    } catch (err) {
      feedbackHolder.innerHTML = `<div class="feedback wrong">Fehler: ${err.message}</div>`;
      submitBtn.disabled = false;
      return;
    }

    const box = el("div", { class: "feedback " + (result.correct ? "correct" : "wrong") });
    box.appendChild(
      el("div", { text: result.correct ? "Richtig! ✓" : `Nicht ganz. Richtig wäre: „${result.expected_answer}“` })
    );
    if (result.explanation) {
      box.appendChild(el("div", { class: "explanation", text: result.explanation }));
    }
    feedbackHolder.innerHTML = "";
    feedbackHolder.appendChild(box);

    if (root.dataset.llmEnabled === "true") {
      const context = {
        question: payload.question,
        hint: payload.hint,
        given_answer: input.value,
        expected_answer: result.expected_answer,
        explanation: result.explanation,
        tense: payload.tense_label || payload.tense,
        person: payload.person,
        direction: payload.direction,
      };
      const autoExplain = root.dataset.autoExplain === "true";
      if (!result.correct && autoExplain) {
        feedbackHolder.appendChild(buildAutoExplainWidget(payload.lexeme_id, payload.exercise_type, context));
      } else {
        feedbackHolder.appendChild(buildInlineAskWidget(payload.lexeme_id, payload.exercise_type, context));
      }
    }

    input.disabled = true;
    submitBtn.textContent = "Weiter →";
    submitBtn.disabled = false;
    answered = true;
  });

  root.appendChild(badge);
  root.appendChild(type);
  root.appendChild(hintLine);
  root.appendChild(question);
  root.appendChild(form);
  root.appendChild(feedbackHolder);

  input.focus();
}

// ---------------- Timeline-Seite ----------------

async function initTimeline() {
  const seriesRoot = document.getElementById("timeline-series");
  const levelRoot = document.getElementById("timeline-levels");
  const summaryRoot = document.getElementById("timeline-summary");
  if (!seriesRoot && !levelRoot && !summaryRoot) return;

  let data;
  try {
    data = await fetchJSON("/stats/timeline?days=60");
  } catch (err) {
    if (summaryRoot) summaryRoot.innerHTML = `<p class="feedback wrong">Fehler: ${err.message}</p>`;
    return;
  }

  if (summaryRoot) {
    summaryRoot.innerHTML = "";
    const stats = [
      ["Fällig jetzt", data.due_now],
      ["Antworten gesamt", data.total_reviews],
      ["Trefferquote", data.total_reviews ? data.overall_accuracy + " %" : "–"],
    ];
    stats.forEach(([label, value]) => {
      summaryRoot.appendChild(
        el("div", { class: "stat-box" }, [
          el("div", { class: "value", text: String(value) }),
          el("div", { class: "label", text: label }),
        ])
      );
    });
  }

  if (seriesRoot) {
    seriesRoot.innerHTML = "";
    if (!data.daily_series.length) {
      seriesRoot.innerHTML = '<p class="muted">Noch keine Übungen in diesem Zeitraum.</p>';
    } else {
      const max = Math.max(...data.daily_series.map((d) => d.total), 1);
      data.daily_series.forEach((d) => {
        const heightPct = Math.max(4, Math.round((d.total / max) * 100));
        const bar = el("div", {
          class: "bar" + (d.accuracy < 60 ? " low" : ""),
          style: `height:${heightPct}%`,
          title: `${d.date}: ${d.correct}/${d.total} richtig (${d.accuracy}%)`,
        });
        seriesRoot.appendChild(bar);
      });
    }
  }

  if (levelRoot) {
    levelRoot.innerHTML = "";
    const maxMastered = Math.max(...Object.values(data.mastered_by_level), 1);
    Object.entries(data.mastered_by_level).forEach(([level, count]) => {
      const pct = Math.round((count / maxMastered) * 100);
      levelRoot.appendChild(
        el("div", { class: "row" }, [
          el("span", { class: "lvl", text: level }),
          el("div", { class: "track" }, [el("div", { class: "fill", style: `width:${pct}%` })]),
          el("span", { class: "count", text: String(count) }),
        ])
      );
    });
  }
}

// ---------------- KI-Rückfragen (gemeinsam für Review-Button & Chat-Seite) ----------------

async function askStart(lexemeId, exerciseType, context) {
  return fetchJSON("/ask/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ lexeme_id: lexemeId, exercise_type: exerciseType, context: context || null }),
  });
}

async function askSend(threadId, message) {
  return fetchJSON("/ask/message", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ thread_id: threadId, message }),
  });
}

function renderChatMessages(container, messages) {
  container.innerHTML = "";
  if (!messages.length) {
    container.appendChild(el("p", { class: "muted", text: "Stell ruhig eine Frage – z. B. „Warum genau diese Form?“" }));
    return;
  }
  messages.forEach((m) => {
    container.appendChild(
      el("div", { class: "chat-bubble " + (m.role === "user" ? "chat-user" : "chat-assistant") }, [
        el("div", { text: m.content }),
      ])
    );
  });
  container.scrollTop = container.scrollHeight;
}

// Wird bei falscher Antwort automatisch aufgerufen (kein Klick/Tippen nötig):
// lädt sofort eine KI-Erklärung und erlaubt danach weitere Rückfragen.
function buildAutoExplainWidget(lexemeId, exerciseType, context) {
  const wrap = el("div", { class: "ask-widget" });
  const heading = el("div", { class: "muted", text: "🤖 KI-Erklärung:" });
  const messagesBox = el("div", { class: "chat-messages small" });
  const form = el("form", { class: "inline", style: "margin-top:0.5rem;" });
  const input = el("input", { type: "text", placeholder: "Noch eine Rückfrage …", autocomplete: "off" });
  const sendBtn = el("button", { type: "submit", text: "Senden" });
  form.appendChild(input);
  form.appendChild(sendBtn);

  messagesBox.innerHTML = '<p class="muted">… erklärt gerade …</p>';

  let threadId = null;

  (async () => {
    try {
      const data = await askStart(lexemeId, exerciseType, context);
      threadId = data.thread_id;
      const result = await askSend(threadId, "Warum genau ist meine Antwort falsch? Kurz erklären.");
      renderChatMessages(messagesBox, result.messages);
    } catch (err) {
      messagesBox.innerHTML = `<p class="feedback wrong">Fehler: ${err.message}</p>`;
    }
  })();

  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const text = input.value.trim();
    if (!text || !threadId) return;
    input.value = "";
    sendBtn.disabled = true;
    messagesBox.appendChild(el("div", { class: "chat-bubble chat-user" }, [el("div", { text })]));
    messagesBox.appendChild(el("p", { class: "muted", text: "… denkt nach …" }));
    try {
      const data = await askSend(threadId, text);
      renderChatMessages(messagesBox, data.messages);
    } catch (err) {
      messagesBox.innerHTML += `<p class="feedback wrong">Fehler: ${err.message}</p>`;
    }
    sendBtn.disabled = false;
    input.focus();
  });

  wrap.appendChild(heading);
  wrap.appendChild(messagesBox);
  wrap.appendChild(form);
  return wrap;
}

function buildInlineAskWidget(lexemeId, exerciseType, context) {
  const wrap = el("div", { class: "ask-widget" });
  const toggleBtn = el("button", { type: "button", class: "secondary", text: "Warum genau? KI fragen" });
  const panel = el("div", { style: "display:none; margin-top:0.8rem;" });
  const messagesBox = el("div", { class: "chat-messages small" });
  const form = el("form", { class: "inline" });
  const input = el("input", { type: "text", placeholder: "Deine Frage …", autocomplete: "off" });
  const sendBtn = el("button", { type: "submit", text: "Senden" });
  form.appendChild(input);
  form.appendChild(sendBtn);
  panel.appendChild(messagesBox);
  panel.appendChild(form);

  let threadId = null;
  let opened = false;

  toggleBtn.addEventListener("click", async () => {
    if (opened) {
      panel.style.display = panel.style.display === "none" ? "block" : "none";
      return;
    }
    opened = true;
    panel.style.display = "block";
    messagesBox.innerHTML = '<p class="muted">Lade Chat …</p>';
    try {
      const data = await askStart(lexemeId, exerciseType, context);
      threadId = data.thread_id;
      renderChatMessages(messagesBox, data.messages);
    } catch (err) {
      messagesBox.innerHTML = `<p class="feedback wrong">Fehler: ${err.message}</p>`;
    }
  });

  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const text = input.value.trim();
    if (!text || !threadId) return;
    input.value = "";
    sendBtn.disabled = true;
    messagesBox.appendChild(el("div", { class: "chat-bubble chat-user" }, [el("div", { text })]));
    messagesBox.appendChild(el("p", { class: "muted", text: "… denkt nach …" }));
    try {
      const data = await askSend(threadId, text);
      renderChatMessages(messagesBox, data.messages);
    } catch (err) {
      messagesBox.innerHTML += `<p class="feedback wrong">Fehler: ${err.message}</p>`;
    }
    sendBtn.disabled = false;
    input.focus();
  });

  wrap.appendChild(toggleBtn);
  wrap.appendChild(panel);
  return wrap;
}

// ---------------- Chat-Seite (/chat) ----------------

function initAskPage() {
  const searchInput = document.getElementById("vocab-search");
  if (!searchInput) return;

  const resultsBox = document.getElementById("vocab-results");
  const chatCard = document.getElementById("chat-card");
  const chatTitle = document.getElementById("chat-title");
  const chatMessages = document.getElementById("chat-messages");
  const chatForm = document.getElementById("chat-form");
  const chatInput = document.getElementById("chat-input");

  let debounceTimer = null;
  let currentThreadId = null;

  searchInput.addEventListener("input", () => {
    clearTimeout(debounceTimer);
    const q = searchInput.value.trim();
    if (q.length < 2) {
      resultsBox.innerHTML = "";
      return;
    }
    debounceTimer = setTimeout(async () => {
      let results;
      try {
        results = await fetchJSON("/vocab/search?q=" + encodeURIComponent(q));
      } catch (err) {
        resultsBox.innerHTML = `<p class="feedback wrong">Fehler: ${err.message}</p>`;
        return;
      }
      resultsBox.innerHTML = "";
      if (!results.length) {
        resultsBox.appendChild(el("p", { class: "muted", text: "Keine Treffer." }));
        return;
      }
      results.forEach((r) => {
        const link = el("a", { href: "#", text: `${r.italian} — ${r.german} (${r.level})` });
        link.addEventListener("click", async (ev) => {
          ev.preventDefault();
          chatCard.style.display = "block";
          chatTitle.textContent = `${r.italian} — ${r.german}`;
          chatMessages.innerHTML = '<p class="muted">Lade Chat …</p>';
          try {
            const data = await askStart(r.id, null, null);
            currentThreadId = data.thread_id;
            renderChatMessages(chatMessages, data.messages);
          } catch (err) {
            chatMessages.innerHTML = `<p class="feedback wrong">Fehler: ${err.message}</p>`;
          }
        });
        resultsBox.appendChild(link);
      });
    }, 300);
  });

  chatForm.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const text = chatInput.value.trim();
    if (!text || !currentThreadId) return;
    chatInput.value = "";
    chatMessages.appendChild(el("div", { class: "chat-bubble chat-user" }, [el("div", { text })]));
    chatMessages.appendChild(el("p", { class: "muted", text: "… denkt nach …" }));
    try {
      const data = await askSend(currentThreadId, text);
      renderChatMessages(chatMessages, data.messages);
    } catch (err) {
      chatMessages.innerHTML += `<p class="feedback wrong">Fehler: ${err.message}</p>`;
    }
    chatInput.focus();
  });
}

document.addEventListener("DOMContentLoaded", () => {
  initReview();
  initTimeline();
  initAskPage();
});
