"use strict";

const ui = JSON.parse(document.querySelector("#localized-ui")?.textContent || "{}");
const locale = document.documentElement.lang || "en";
const rtl = document.documentElement.dir === "rtl";

const menuToggle = document.querySelector(".menu-toggle");
const sidebar = document.querySelector("#sidebar");
const appShell = document.querySelector(".app-shell");
const mobileNavigation = window.matchMedia("(max-width: 760px)");

function setNavigation(open, restoreFocus = false) {
  if (!sidebar || !menuToggle) return;
  const expanded = mobileNavigation.matches && open;
  document.body.classList.toggle("nav-open", expanded);
  menuToggle.setAttribute("aria-expanded", String(expanded));
  sidebar.inert = mobileNavigation.matches && !expanded;
  appShell.inert = expanded;
  if (expanded) sidebar.querySelector("button, a")?.focus();
  else if (restoreFocus) menuToggle.focus();
}

menuToggle?.addEventListener("click", () => {
  const expanded = menuToggle.getAttribute("aria-expanded") === "true";
  setNavigation(!expanded);
});
document.addEventListener("keydown", (event) => {
  if (!document.body.classList.contains("nav-open")) return;
  if (event.key === "Escape") setNavigation(false, true);
  if (event.key === "Tab") {
    const links = sidebar.querySelectorAll("a[href], button:not([disabled])");
    const first = links[0], last = links[links.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }
});
document.querySelector(".sidebar-close")?.addEventListener("click", () => setNavigation(false, true));
mobileNavigation.addEventListener("change", () => setNavigation(false));
setNavigation(false);

document.querySelector("#use-ai-draft")?.addEventListener("click", () => {
  const composer = document.querySelector("#reply-composer textarea");
  if (composer.value.trim() && !window.confirm(ui.replace_draft)) return;
  composer.value = JSON.parse(document.querySelector("#ai-draft").textContent);
  // Loading a draft never submits a form or changes note visibility.
  composer.focus();
  composer.scrollIntoView({ behavior: "smooth", block: "center" });
});

const labels = ui.labels;
const analytics = document.querySelector("#analytics-data");
if (analytics) {
  const data = JSON.parse(analytics.textContent);
  document.querySelectorAll("[data-chart]").forEach((chart) => {
    const dimension = chart.dataset.chart;
    const records = data[`by_${dimension}`];
    Object.entries(labels[dimension]).forEach(([key, label]) => {
      const count = records.find((record) => record[dimension] === key)?.count || 0;
      const row = document.createElement("div");
      row.className = "breakdown-row";
      const title = document.createElement("span");
      title.textContent = label;
      const number = document.createElement("strong");
      number.textContent = count.toLocaleString(locale);
      const track = document.createElement("div");
      track.className = "bar-track";
      const bar = document.createElement("span");
      bar.className = `bar-${key}`;
      bar.style.width = `${data.total ? (count / data.total) * 100 : 0}%`;
      track.append(bar);
      row.append(title, number, track);
      chart.append(row);
    });
  });
}

const chartCanvas = document.querySelector("#activity-chart");
if (chartCanvas) {
  const series = JSON.parse(document.querySelector("#activity-data").textContent);
  const dates = Array.from({ length: 14 }, (_, index) => {
    const date = new Date();
    date.setUTCHours(0, 0, 0, 0);
    date.setUTCDate(date.getUTCDate() - 13 + index);
    return date.toISOString().slice(0, 10);
  });
  const values = dates.map((date) => series.find((item) => item.day === date)?.count || 0);
  function drawActivity() {
    const bounds = chartCanvas.getBoundingClientRect();
    const ratio = window.devicePixelRatio || 1;
    chartCanvas.width = bounds.width * ratio;
    chartCanvas.height = bounds.height * ratio;
    const ctx = chartCanvas.getContext("2d");
    ctx.scale(ratio, ratio);
    const width = bounds.width, height = bounds.height;
    const left = rtl ? 12 : 32, right = rtl ? 32 : 12, top = 16, bottom = 28;
    const chartWidth = width - left - right, chartHeight = height - top - bottom;
    const max = Math.max(4, ...values);
    const ceiling = Math.ceil(max / 4) * 4;
    ctx.font = '11px "Segoe UI", sans-serif';
    ctx.textBaseline = "middle";
    for (let step = 0; step <= 4; step++) {
      const y = top + (chartHeight * step) / 4;
      ctx.strokeStyle = "#edf0ed";
      ctx.beginPath(); ctx.moveTo(left, y); ctx.lineTo(width - right, y); ctx.stroke();
      ctx.fillStyle = "#84908a"; ctx.textAlign = rtl ? "left" : "right";
      ctx.fillText((ceiling - (ceiling * step) / 4).toLocaleString(locale), rtl ? width - right + 10 : left - 10, y);
    }
    const gap = chartWidth / 14;
    values.forEach((value, index) => {
      const barHeight = (value / ceiling) * chartHeight;
      ctx.fillStyle = index === 13 ? "#1c6b56" : "#aed4c5";
      ctx.beginPath();
      const position = rtl ? 13 - index : index;
      ctx.roundRect(left + position * gap + gap * 0.2, top + chartHeight - barHeight, gap * 0.6, barHeight, [3, 3, 0, 0]);
      ctx.fill();
      if (index % 3 === 0 || index === 13) {
        const date = new Date(`${dates[index]}T00:00:00Z`);
        ctx.fillStyle = "#84908a"; ctx.textAlign = "center";
        ctx.fillText(date.toLocaleDateString(locale, { month: "short", day: "numeric", timeZone: "UTC" }), left + position * gap + gap / 2, height - 10);
      }
    });
  }
  new ResizeObserver(drawActivity).observe(chartCanvas);
}
