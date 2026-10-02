// Scheme New Tab - colors come from ~/.config/current_theme/chromium.theme
// (1st line bg, 2nd line text), with colors.json written by
// chromium-scheme-apply.py as fallback.

const THEME_FILE = "file:///home/sk/.config/current_theme/chromium.theme";
const HEX_RE = /^#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})$/;
// last-resort defaults = colors at build time
const EMBEDDED = { bg: "#16242d", text: "#d6e2ee" };

function normalize(v) {
  v = v.trim();
  if (!v.startsWith("#")) v = "#" + v;
  if (!HEX_RE.test(v)) throw new Error("bad color " + v);
  if (v.length === 4) v = "#" + [...v.slice(1)].map((c) => c + c).join("");
  return v.toLowerCase();
}

function apply(bg, text) {
  const r = document.documentElement.style;
  r.setProperty("--bg", bg);
  r.setProperty("--text", text);
  document.getElementById("colors").textContent = `bg ${bg} · text ${text}`;
}

async function fromFile() {
  const res = await fetch(THEME_FILE, { cache: "no-store" });
  if (!res.ok) throw new Error("file fetch " + res.status);
  const lines = (await res.text()).split(/\r?\n/);
  return { bg: normalize(lines[0] || ""), text: normalize(lines[1] || "") };
}

async function fromJson() {
  // cache-buster: force a fresh read of the unpacked extension file
  const res = await fetch(
    chrome.runtime.getURL("colors.json") + "?t=" + Date.now(),
    { cache: "no-store" });
  if (!res.ok) throw new Error("json fetch " + res.status);
  const data = await res.json();
  return { bg: normalize(data.bg), text: normalize(data.text) };
}

async function refresh() {
  for (const source of [fromFile, fromJson]) {
    try {
      const { bg, text } = await source();
      apply(bg, text);
      return;
    } catch (e) {
      console.warn("scheme-newtab:", source.name, "failed:", e.message);
    }
  }
  apply(EMBEDDED.bg, EMBEDDED.text);
}

function tick() {
  const now = new Date();
  document.getElementById("clock").textContent =
    now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  document.getElementById("date").textContent =
    now.toLocaleDateString(undefined,
      { weekday: "long", day: "numeric", month: "long" });
}

document.getElementById("search").addEventListener("submit", (e) => {
  const q = e.target.q.value.trim();
  if (!q) e.preventDefault();
});

tick();
setInterval(tick, 1000);
refresh();
setInterval(refresh, 15000);
document.addEventListener("visibilitychange", () => {
  if (!document.hidden) refresh();
});
