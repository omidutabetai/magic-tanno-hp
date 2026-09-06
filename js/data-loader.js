(() => {
  const DATA_FILES = {
    members: "data/members.json",
    timeline: "data/timeline.json",
    works: "data/works.json",
  };

  function showError(containerId, message, { append = false } = {}) {
    const el = document.getElementById(containerId);
    if (!el) return;
    const p = document.createElement("p");
    p.className = "data-load-error";
    p.textContent = message;
    if (append) {
      el.appendChild(p);
    } else {
      el.replaceChildren(p);
    }
  }

  function renderMembers(members) {
    const container = document.getElementById("members-list");
    if (!container) return;
    container.innerHTML = "";

    for (const member of members) {
      const card = document.createElement("div");
      card.className = "member-card";

      const h3 = document.createElement("h3");
      h3.textContent = member.name;
      card.appendChild(h3);

      for (const role of member.roles || []) {
        const span = document.createElement("span");
        span.className = "role-tag";
        span.textContent = role;
        card.appendChild(span);
      }

      const p = document.createElement("p");
      p.textContent = member.description;
      card.appendChild(p);

      const contacts = member.contacts || [];
      if (contacts.length > 0) {
        const h4 = document.createElement("h4");
        h4.textContent = "Contact";
        card.appendChild(h4);

        const ul = document.createElement("ul");
        for (const contact of contacts) {
          const li = document.createElement("li");
          if (contact.url) {
            const a = document.createElement("a");
            a.href = contact.url;
            a.target = "_blank";
            a.rel = "noopener";
            a.textContent = `${contact.label}: ${contact.value}`;
            li.appendChild(a);
          } else {
            li.textContent = `${contact.label}: ${contact.value}`;
          }
          ul.appendChild(li);
        }
        card.appendChild(ul);
      }

      container.appendChild(card);
    }
  }

  function renderTimeline(entries) {
    const container = document.getElementById("timeline-list");
    if (!container) return;
    container.innerHTML = "";

    for (const entry of entries) {
      const li = document.createElement("li");
      li.className = "timeline-event";

      const time = document.createElement("time");
      time.className = "timeline-date";
      time.setAttribute("datetime", entry.datetime);
      time.textContent = entry.displayDate;
      li.appendChild(time);

      const body = document.createElement("div");
      body.className = "timeline-body";

      const h3 = document.createElement("h3");
      h3.className = "timeline-title";
      h3.textContent = entry.title;
      body.appendChild(h3);

      const p = document.createElement("p");
      p.className = "timeline-content";
      p.textContent = entry.description;
      body.appendChild(p);

      li.appendChild(body);
      container.appendChild(li);
    }
  }

  function renderWorks(works) {
    const container = document.getElementById("works-list");
    if (!container) return;
    // Not cleared: the Air-LiDAR exhibit item is hardcoded here (not a 頒布物, so not in works.json)
    // and JSON-driven entries are appended alongside it.

    for (const work of works) {
      const item = document.createElement("div");
      item.className = "work";

      const tag = document.createElement("span");
      tag.className = work.type === "新刊" ? "tag" : "tag kikanshi";
      tag.textContent = work.event ? `${work.type} / ${work.event}` : work.type;
      item.appendChild(tag);

      const inner = document.createElement("div");

      const series = document.createElement("div");
      series.className = "series";
      series.textContent = `${work.author} 著`;
      inner.appendChild(series);

      const h3 = document.createElement("h3");
      h3.textContent = work.title;
      inner.appendChild(h3);

      const p = document.createElement("p");
      p.textContent = work.description;
      inner.appendChild(p);

      item.appendChild(inner);
      container.appendChild(item);
    }
  }

  async function loadAndRender() {
    let members, timeline, works;
    try {
      [members, timeline, works] = await Promise.all([
        fetch(DATA_FILES.members).then((r) => r.json()),
        fetch(DATA_FILES.timeline).then((r) => r.json()),
        fetch(DATA_FILES.works).then((r) => r.json()),
      ]);
    } catch (err) {
      const message =
        "コンテンツの読み込みに失敗しました。ローカルサーバー経由（例: npx serve .）で開いてください。";
      showError("members-list", message);
      showError("timeline-list", message);
      // append rather than replace: works-list also holds the hardcoded Air-LiDAR exhibit entry
      showError("works-list", message, { append: true });
      console.error("Failed to load data/*.json:", err);
      return;
    }

    renderMembers(members);
    renderTimeline(timeline);
    renderWorks(works);
  }

  document.addEventListener("DOMContentLoaded", loadAndRender);
})();
