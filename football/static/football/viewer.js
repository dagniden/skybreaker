"use strict";
const canvas = document.getElementById("pitch");
const ctx = canvas.getContext("2d");
const play = document.getElementById("play");
const seek = document.getElementById("seek");
const speed = document.getElementById("speed");
const clock = document.getElementById("clock");
const score = document.getElementById("score");
const status = document.getElementById("status");
let replay = null, position = 0, playing = false, previous = null;
const mix = (a, b, weight) => a + (b - a) * weight;
const formatTime = ms => `${Math.floor(ms / 60000)}:${String(Math.floor(ms / 1000) % 60).padStart(2, "0")}`;

function sample(time) {
  const frames = replay.frames;
  let low = 0, high = frames.length - 1;
  while (low < high) {
    const mid = Math.ceil((low + high) / 2);
    if (frames[mid].t <= time) low = mid; else high = mid - 1;
  }
  const a = frames[low], b = frames[Math.min(low + 1, frames.length - 1)];
  const weight = a.r === b.r && b.t > a.t ? Math.max(0, Math.min(1, (time - a.t) / (b.t - a.t))) : 0;
  return { a, b, weight };
}

function field() {
  ctx.fillStyle = "#29671d"; ctx.fillRect(0, 0, 1600, 900);
  ctx.strokeStyle = "#ffffffc9"; ctx.lineWidth = 2;
  ctx.strokeRect(1, 1, 1598, 898);
  ctx.beginPath(); ctx.moveTo(800, 0); ctx.lineTo(800, 900); ctx.stroke();
  ctx.beginPath(); ctx.arc(800, 450, 95, 0, 2 * Math.PI); ctx.stroke();
  for (const x of [0, 1380]) ctx.strokeRect(x, 255, 220, 390);
  for (const x of [0, 1512]) ctx.strokeRect(x, 360, 88, 180);
  ctx.lineWidth = 7;
  for (const x of [3, 1597]) { ctx.beginPath(); ctx.moveTo(x, 360); ctx.lineTo(x, 540); ctx.stroke(); }
}

function render() {
  field();
  if (!replay) return;
  const { a, b, weight } = sample(position);
  a.u.forEach((unit, i) => {
    const next = b.u[i];
    const x = mix(unit[0], next[0], weight), y = mix(unit[1], next[1], weight);
    const team = replay.units[i];
    ctx.fillStyle = team.keeper ? (team.team === 0 ? "#00ffff" : "#ffd700") : (team.team === 0 ? "#1e90ff" : "#ff6347");
    ctx.strokeStyle = a.h === i ? "#fff" : "#14252a"; ctx.lineWidth = a.h === i ? 4 : 2;
    ctx.beginPath(); ctx.arc(x, y, 16, 0, 2 * Math.PI); ctx.fill(); ctx.stroke();
    let dx = mix(unit[2], next[2], weight), dy = mix(unit[3], next[3], weight);
    const length = Math.hypot(dx, dy) || 1; dx /= length; dy /= length;
    ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x + dx * 23, y + dy * 23); ctx.stroke();
  });
  ctx.fillStyle = "#fff"; ctx.strokeStyle = "#14252a"; ctx.lineWidth = 2;
  ctx.beginPath(); ctx.arc(mix(a.b[0], b.b[0], weight), mix(a.b[1], b.b[1], weight), 8, 0, 2 * Math.PI); ctx.fill(); ctx.stroke();
  score.textContent = `${a.s[0]} : ${a.s[1]}`;
  clock.textContent = `${formatTime(position)} / ${formatTime(replay.duration_ms)}`;
  seek.value = String(Math.round(position));
}

function setPlaying(value) { playing = value; previous = null; play.textContent = value ? "Пауза" : "Играть"; }
play.addEventListener("click", () => {
  if (position >= replay.duration_ms) position = 0;
  setPlaying(!playing);
});
seek.addEventListener("input", () => { position = Number(seek.value); previous = null; render(); });
document.addEventListener("keydown", event => {
  if (!replay || /INPUT|SELECT|BUTTON/.test(event.target.tagName)) return;
  if (event.code === "Space") { event.preventDefault(); play.click(); }
  if (event.code === "ArrowLeft" || event.code === "ArrowRight") {
    event.preventDefault(); position = Math.max(0, Math.min(replay.duration_ms, position + (event.code === "ArrowLeft" ? -5000 : 5000))); render();
  }
});
document.addEventListener("visibilitychange", () => { previous = null; });
function tick(now) {
  if (playing && replay && previous !== null) {
    position = Math.min(replay.duration_ms, position + Math.min(now - previous, 250) * Number(speed.value));
    if (position >= replay.duration_ms) setPlaying(false);
  }
  previous = document.hidden ? null : now;
  render(); requestAnimationFrame(tick);
}

async function load() {
  try {
    const response = await fetch(canvas.dataset.replayUrl);
    if (!response.ok) throw new Error("Реплей не найден или срок хранения истёк");
    replay = await response.json();
    if (replay.version !== 1 || !Array.isArray(replay.frames) || replay.frames.length < 2) throw new Error("Неподдерживаемая запись");
    seek.max = String(replay.duration_ms); seek.disabled = false; play.disabled = false;
    status.textContent = "Свободная игра · 6×6 · Просмотр без входа";
    const goals = document.getElementById("goals");
    let last = [0, 0];
    for (const frame of replay.frames) {
      if (frame.s[0] !== last[0] || frame.s[1] !== last[1]) {
        if (goals.textContent === "Пока нет голов") goals.textContent = "";
        const button = document.createElement("button");
        button.textContent = `${formatTime(frame.t)} · ${frame.s[0]}:${frame.s[1]}`;
        button.addEventListener("click", () => { position = Math.max(0, frame.t - 3000); previous = null; render(); });
        goals.appendChild(button); last = frame.s;
      }
    }
  } catch (error) { replay = null; status.textContent = `Ошибка: ${error.message}`; }
}
requestAnimationFrame(tick);
load();
