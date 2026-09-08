const state = { chart: JSON.parse(localStorage.getItem("astroChart") || "null"), userId: localStorage.getItem("astroUserId") || crypto.randomUUID(), subscription: JSON.parse(localStorage.getItem("astroSubscription") || "null") };
localStorage.setItem("astroUserId", state.userId);
const $ = (selector) => document.querySelector(selector);
const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" }[char]));
const telegram = window.Telegram?.WebApp;
telegram?.ready();
telegram?.expand();

document.querySelectorAll(".bottom-nav button").forEach((button) => button.addEventListener("click", () => showView(button.dataset.view)));
$("#profile-button").addEventListener("click", () => showView("profile"));
$("#birth-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = event.currentTarget.querySelector("button");
  const payload = Object.fromEntries(new FormData(event.currentTarget).entries());
  payload.userId = state.userId;
  button.disabled = true; button.innerHTML = "Считаем карту <span>✦</span>";
  try {
    const response = await apiFetch("/api/calculate", { method: "POST", body: JSON.stringify(payload) });
    if (!response.ok) throw new Error((await response.json()).error || "Не удалось выполнить расчёт");
    state.chart = await response.json(); localStorage.setItem("astroChart", JSON.stringify(state.chart));
    await track("chart_created"); renderChart(); showView("chart");
  } catch (error) { alert(error.message); } finally { button.disabled = false; button.innerHTML = "Построить карту <span>→</span>"; }
});

function showView(view) {
  document.querySelectorAll(".view").forEach((item) => item.classList.add("hidden"));
  $(`#view-${view}`).classList.remove("hidden");
  document.querySelectorAll(".bottom-nav button").forEach((button) => button.classList.toggle("active", button.dataset.view === view));
  if (view === "chart") renderChart(); if (view === "numbers") renderNumbers(); if (view === "profile") renderProfile();
  window.scrollTo({top: 0, behavior: "smooth"});
}

function renderChart() {
  const target = $("#view-chart");
  if (!state.chart) { target.innerHTML = `<div class="empty card"><h2>Карта ещё не построена</h2><p>Заполните данные рождения на главной.</p><button class="primary-button" onclick="showView('home')">К форме рождения</button></div>`; return; }
  const planets = state.chart.planets.map((planet) => `<details class="planet-details"><summary class="planet-row"><span>${planet.name}${planet.retrograde ? " ℞" : ""}</span><strong>${planet.sign}</strong><em>${planet.degree.toFixed(1)}° · дом ${planet.house}</em></summary><p><b>Что означает:</b> ${planet.meaning}</p><p><b>Тема дома:</b> ${planet.houseMeaning}</p></details>`).join("");
  const aspects = state.chart.aspects.map((aspect) => `<div class="aspect-row"><span>${aspect.first} — ${aspect.second}</span><strong>${aspect.type}</strong><em>${aspect.orb}°</em></div>`).join("");
  target.innerHTML = `<div class="result-header"><p class="eyebrow">ВАША КАРТА ГОТОВА</p><h2>${escapeHtml(state.chart.zodiac)} <span>·</span> ${escapeHtml(state.chart.place)}</h2><p>${state.chart.birthDate} · ${state.chart.birthTime} · система домов ${state.chart.houses.system}</p></div><div class="chart-wheel"><div class="wheel-orbit"><div class="wheel-core">✦<small>${state.chart.zodiac}</small></div></div></div><div class="card guide-card"><div class="section-heading"><span class="step">КАК ЧИТАТЬ</span><h2>Карта простыми словами</h2></div><p><b>Планета</b> — какая жизненная сила проявляется. <b>Знак</b> — каким способом она проявляется. <b>Дом</b> — в какой сфере жизни это заметнее всего. Нажмите на любую планету, чтобы открыть расшифровку.</p></div><div class="card"><div class="section-heading"><span class="step">02</span><h2>Планеты, знаки и дома</h2></div>${planets}</div><div class="card"><div class="section-heading"><span class="step">03</span><h2>Аспекты</h2></div>${aspects}<p class="explain-text">Аспект показывает, как две жизненные темы взаимодействуют. Соединение усиливает их вместе, тригон даёт лёгкость и поддержку.</p></div><div class="card interpretation"><div class="section-heading"><span class="step">✦</span><h2>Интерпретация</h2></div><p>${escapeHtml(state.chart.interpretation)}</p></div>${lockedBlock()}<div class="disclaimer">${state.chart.disclaimer}</div>`;
}

function renderNumbers() {
  const chart = state.chart;
  const meanings = Object.entries(chart?.numberMeanings || {}).map(([key, item]) => `<details class="meaning-row"><summary><b>${item.title}</b><span>+</span></summary><p>${item.text}</p></details>`).join("");
  $("#view-numbers").innerHTML = chart ? `<div class="result-header"><p class="eyebrow">НУМЕРОЛОГИЯ</p><h2>Ваши ключи</h2><p>Дата ${chart.birthDate}${chart.nameNumber ? ` · ${escapeHtml(chart.place)}` : ""}</p></div><div class="stats-grid"><article class="stat-card accent"><small>ЧИСЛО ЖИЗНЕННОГО ПУТИ</small><strong>${chart.lifePath}</strong><p>Главный вектор опыта</p></article><article class="stat-card"><small>ЧИСЛО ДУШИ</small><strong>${chart.soulNumber}</strong><p>Внутренняя мотивация</p></article></div>${chart.nameNumber ? `<div class="card"><div class="section-heading"><span class="step">ИМЯ</span><h2>Число имени</h2></div><div class="big-number">${chart.nameNumber}</div><p>Звучание имени раскрывает способ проявления себя.</p></div>` : ""}<div class="card"><div class="section-heading"><span class="step">МАТРИЦА</span><h2>Квадрат Пифагора</h2></div><p class="explain-text">Количество цифр показывает, насколько заметно качество числа в дате. Ноль означает, что качество раскрывается через осознанную практику, а не автоматически.</p><div class="matrix">${Object.entries(chart.matrix).map(([key, value]) => `<div class="matrix-cell"><small>${key}</small><strong>${value || "—"}</strong></div>`).join("")}</div></div><div class="card"><div class="section-heading"><span class="step">СПРАВКА</span><h2>Что означает каждая цифра</h2></div>${meanings}</div><div class="disclaimer">${chart.disclaimer}</div>` : `<div class="empty card"><h2>Откройте свои числа</h2><p>Сначала постройте натальную карту.</p></div>`;
}

function renderProfile() {
  $("#view-profile").innerHTML = `<div class="result-header"><p class="eyebrow">ПРОФИЛЬ</p><h2>Ваше пространство</h2><p>ID: ${state.userId.slice(0, 8)}…</p></div><div class="card subscription-card"><div class="section-heading"><span class="step">✦</span><h2>${state.subscription ? "Подписка активна" : "Полный доступ"}</h2></div><p>${state.subscription ? `Доступ до ${new Date(state.subscription.expiresAt).toLocaleDateString("ru-RU")}.` : "Ежедневный прогноз, утренняя подсказка и все отчёты без ограничений."}</p>${state.subscription ? `<span class="pill">АКТИВНА</span>` : `<button class="primary-button" id="subscribe-button">Оформить · 300 Stars</button>`}</div><div class="card"><div class="section-heading"><span class="step">♡</span><h2>Совместимость</h2></div><p class="muted">Сравните число жизненного пути двух людей.</p><div class="compatibility-form"><input id="compat-date" type="date"><button class="secondary-button" id="compat-button">Сравнить карты →</button></div><div id="compat-result"></div></div><div class="card"><div class="section-heading"><span class="step">⚙</span><h2>Приватность</h2></div><p class="muted">Данные хранятся локально в демо-режиме. В production профиль шифруется и привязывается к Telegram.</p><button class="secondary-button danger" id="delete-button">Удалить все данные</button></div><div class="disclaimer">${state.chart?.disclaimer || "Вся информация носит развлекательный характер и не является профессиональной консультацией."}</div>`;
  $("#subscribe-button")?.addEventListener("click", subscribe); $("#delete-button").addEventListener("click", deleteData); $("#compat-button").addEventListener("click", compareCompatibility);
}

function lockedBlock() { return state.subscription ? `<div class="forecast-actions"><button class="secondary-button" onclick="loadForecast('day')">Сегодня</button><button class="secondary-button" onclick="loadForecast('week')">Неделя</button><button class="secondary-button" onclick="loadForecast('month')">Месяц</button></div><div id="forecast"></div><button class="secondary-button" onclick="shareChart()">Поделиться картой ↗</button>` : `<div class="locked card"><span>✦</span><h2>Раскройте полный прогноз</h2><p>День, неделя, месяц, любовь, деньги, карьера и совместимость доступны по подписке.</p><button class="primary-button" onclick="showView('profile')">Открыть доступ</button></div>`; }
async function loadForecast(period = "day") { const response = await fetch(`/api/forecast/${period}`); const data = await response.json(); $("#forecast").innerHTML = `<div class="card forecast"><p class="eyebrow">ПРОГНОЗ · ${period.toUpperCase()} · УДАЧА ${data.luck}/10</p><p>${data.text}</p>${Object.entries(data.areas || {}).map(([area, text]) => `<p><b>${area}:</b> ${text}</p>`).join("")}<small>${data.disclaimer}</small></div>`; }
async function shareChart() { const text = `Моя космическая карта в Astro App: ${state.chart.zodiac}, число пути ${state.chart.lifePath}.`; if (navigator.share) await navigator.share({title: "Моя карта Astro App", text}); else await navigator.clipboard.writeText(text); }
async function subscribe() {
  if (telegram?.initData) {
    const invoiceResponse = await apiFetch("/api/invoice", {method: "POST", body: JSON.stringify({userId: state.userId})});
    const invoice = await invoiceResponse.json();
    telegram.openInvoice(invoice.invoiceUrl, (status) => { if (status === "paid") activateSubscription(); });
    return;
  }
  await activateSubscription();
}
async function activateSubscription() { const response = await apiFetch("/api/subscribe", {method: "POST", body: JSON.stringify({userId: state.userId, plan: "monthly"})}); state.subscription = await response.json(); localStorage.setItem("astroSubscription", JSON.stringify(state.subscription)); await track("subscription_started"); renderProfile(); }
async function compareCompatibility() { const secondDate = $("#compat-date").value; if (!state.chart || !secondDate) return alert("Выберите дату рождения второго человека."); const response = await fetch("/api/compatibility", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({first: {birthDate: state.chart.birthDate}, second: {birthDate: secondDate}})}); const data = await response.json(); $("#compat-result").innerHTML = `<div class="compat-result"><strong>${data.score}%</strong><p>${data.summary}</p><small>${data.disclaimer}</small></div>`; }
async function deleteData() { if (!confirm("Удалить все данные профиля?")) return; await fetch("/api/account", {method: "DELETE", headers: {"Content-Type": "application/json"}, body: JSON.stringify({userId: state.userId})}); localStorage.clear(); location.reload(); }
async function track(name) { apiFetch("/api/analytics", {method: "POST", body: JSON.stringify({name, userId: state.userId})}).catch(() => {}); }
function apiFetch(url, options = {}) { options.headers = {...options.headers, "Content-Type": "application/json"}; if (telegram?.initData) options.headers["X-Telegram-Init-Data"] = telegram.initData; return fetch(url, options); }
if (state.chart) { $("#daily-text").textContent = "Ваша карта готова — загляните в раздел «Карта»."; }
