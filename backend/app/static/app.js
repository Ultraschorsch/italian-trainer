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

document.addEventListener("DOMContentLoaded", () => {
  initReview();
  initTimeline();
});
