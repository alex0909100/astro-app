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
  if (view === "chart") renderChart(); if (view === "numbers") renderNumbers(); if (view === "tarot") renderTarot(); if (view === "profile") renderProfile();
  window.scrollTo({top: 0, behavior: "smooth"});
}

function renderChart() {
  const target = $("#view-chart");
  if (!state.chart) { target.innerHTML = `<div class="empty card"><h2>Карта ещё не построена</h2><p>Заполните данные рождения на главной.</p><button class="primary-button" onclick="showView('home')">К форме рождения</button></div>`; return; }
  const planets = state.chart.planets.map((planet) => `<details class="planet-details"><summary class="planet-row"><span>${planet.name}${planet.retrograde ? " ℞" : ""}</span><strong>${planet.sign}</strong><em>${planet.degree.toFixed(1)}° · дом ${planet.house}</em></summary><p><b>Что означает:</b> ${planet.meaning}</p><p><b>Тема дома:</b> ${planet.houseMeaning}</p></details>`).join("");
  const aspects = state.chart.aspects.map((aspect) => `<div class="aspect-row"><span>${aspect.first} — ${aspect.second}</span><strong>${aspect.type}</strong><em>${aspect.orb}°</em></div>`).join("");
  const sections = (state.chart.interpretationSections || []).map((section) => `<article class="interpretation-section"><h3>${escapeHtml(section.title)}</h3><p>${escapeHtml(section.text)}</p></article>`).join("");
  const actions = (state.chart.practicalActions || []).map((action) => `<li>${escapeHtml(action)}</li>`).join("");
  const detailedAspects = (state.chart.interpretationAspects || []).map((aspect) => `<article class="interpretation-section"><h3>${escapeHtml(aspect.title)}</h3><p>${escapeHtml(aspect.text)}</p></article>`).join("");
  target.innerHTML = `<div class="result-header"><p class="eyebrow">ВАША КАРТА ГОТОВА</p><h2>${escapeHtml(state.chart.zodiac)} <span>·</span> ${escapeHtml(state.chart.place)}</h2><p>${state.chart.birthDate} · ${state.chart.birthTime} · система домов ${state.chart.houses.system}</p></div><div class="chart-wheel"><div class="wheel-orbit"><div class="wheel-core">✦<small>${state.chart.zodiac}</small></div></div></div><div class="card guide-card"><div class="section-heading"><span class="step">КАК ЧИТАТЬ</span><h2>Карта простыми словами</h2></div><p><b>Планета</b> — какая жизненная сила проявляется. <b>Знак</b> — каким способом она проявляется. <b>Дом</b> — в какой сфере жизни это заметнее всего. Нажмите на любую планету, чтобы открыть расшифровку.</p></div><div class="card detailed-report"><div class="section-heading"><span class="step">01</span><h2>Ваш персональный разбор</h2></div><p class="report-lead">Ниже — не общий гороскоп, а связное чтение именно ваших положений. Каждый вывод опирается на планету, знак и дом.</p>${sections}<div class="actions-box"><h3>Что попробовать на практике</h3><ol>${actions}</ol></div></div><div class="card"><div class="section-heading"><span class="step">02</span><h2>Планеты, знаки и дома</h2></div>${planets}</div><div class="card"><div class="section-heading"><span class="step">03</span><h2>Аспекты</h2></div>${aspects}${detailedAspects}<p class="explain-text">Аспект показывает, как две жизненные темы взаимодействуют. Соединение усиливает их вместе, тригон даёт лёгкость и поддержку.</p></div>${lockedBlock()}<div class="disclaimer">${state.chart.disclaimer}</div>`;
}

function renderNumbers() {
  const chart = state.chart;
  const meanings = Object.entries(chart?.numberMeanings || {}).map(([key, item]) => `<details class="meaning-row"><summary><b>${item.title}</b><span>+</span></summary><p>${item.text}</p></details>`).join("");
  $("#view-numbers").innerHTML = chart ? `<div class="result-header"><p class="eyebrow">НУМЕРОЛОГИЯ</p><h2>Ваши ключи</h2><p>Дата ${chart.birthDate}${chart.nameNumber ? ` · ${escapeHtml(chart.place)}` : ""}</p></div><div class="stats-grid"><article class="stat-card accent"><small>ЧИСЛО ЖИЗНЕННОГО ПУТИ</small><strong>${chart.lifePath}</strong><p>Главный вектор опыта</p></article><article class="stat-card"><small>ЧИСЛО ДУШИ</small><strong>${chart.soulNumber}</strong><p>Внутренняя мотивация</p></article></div>${chart.nameNumber ? `<div class="card"><div class="section-heading"><span class="step">ИМЯ</span><h2>Число имени</h2></div><div class="big-number">${chart.nameNumber}</div><p>Звучание имени раскрывает способ проявления себя.</p></div>` : ""}<div class="card"><div class="section-heading"><span class="step">МАТРИЦА</span><h2>Квадрат Пифагора</h2></div><p class="explain-text">Количество цифр показывает, насколько заметно качество числа в дате. Ноль означает, что качество раскрывается через осознанную практику, а не автоматически.</p><div class="matrix">${Object.entries(chart.matrix).map(([key, value]) => `<div class="matrix-cell"><small>${key}</small><strong>${value || "—"}</strong></div>`).join("")}</div></div><div class="card"><div class="section-heading"><span class="step">СПРАВКА</span><h2>Что означает каждая цифра</h2></div>${meanings}</div><div class="disclaimer">${chart.disclaimer}</div>` : `<div class="empty card"><h2>Откройте свои числа</h2><p>Сначала постройте натальную карту.</p></div>`;
}

function renderTarot() {
  const target = $("#view-tarot");
  target.innerHTML = `<div class="result-header"><p class="eyebrow">ТАРО · ОСОЗНАННЫЙ РАСКЛАД</p><h2>Задайте вопрос картам</h2><p>Карты помогают увидеть взаимосвязи, но не выносят приговоров.</p></div><div id="tarot-arcana-container">${renderTarotArcana()}</div><div class="card tarot-form"><div class="section-heading"><span class="step">01</span><h2>Схема и тема</h2></div><label>Тип расклада<select id="tarot-spread"></select></label><div id="tarot-topics" class="tarot-topics"><span class="muted">Загрузка тем…</span></div><label>Ваш вопрос<textarea id="tarot-question" rows="4" placeholder="Сформулируйте вопрос конкретно и про себя"></textarea></label><button class="primary-button" id="tarot-draw">Перемешать и вытянуть карты <span>✦</span></button><p class="hint">Бесплатно доступен 1 расклад в день. Подписка снимает дневной лимит.</p></div><div id="tarot-day" class="card"></div><div id="tarot-result"></div><div class="disclaimer">Карты Таро — инструмент для размышления, а не окончательный приговор. Всё в ваших руках.</div>`;
  if (state.chart?.birthDate) fetch(`/api/tarot/arcana?birthDate=${encodeURIComponent(state.chart.birthDate)}`).then((response) => response.json()).then((data) => { state.chart.personalArcana = data.personalArcana; $("#tarot-arcana-container").innerHTML = renderTarotArcana(data.personalArcana); });
  fetch("/api/tarot/topics").then((response) => response.json()).then((data) => {
    $("#tarot-spread").innerHTML = Object.entries(data.spreads).map(([id, spread]) => `<option value="${id}">${escapeHtml(spread.title)} · ${escapeHtml(spread.description)}</option>`).join("");
    $("#tarot-topics").innerHTML = data.topics.map((topic, index) => `<button class="tarot-topic ${index === 0 ? "selected" : ""}" data-topic="${topic.id}" data-question="${escapeHtml(topic.question)}">${escapeHtml(topic.title)}</button>`).join("");
    document.querySelectorAll(".tarot-topic").forEach((button) => button.addEventListener("click", () => {
      document.querySelectorAll(".tarot-topic").forEach((item) => item.classList.remove("selected")); button.classList.add("selected");
      $("#tarot-question").value = button.dataset.question;
    }));
    $("#tarot-question").value = data.topics[0].question;
    fetch(`/api/tarot/card-of-day?userId=${encodeURIComponent(state.userId)}`).then((response) => response.json()).then((day) => { $("#tarot-day").innerHTML = `<div class="section-heading"><span class="step">✦</span><h2>Карта дня · ${escapeHtml(day.card.name)}</h2></div><p>${escapeHtml(day.card.fullUpright)}</p><p class="muted">${escapeHtml(day.message)}</p>`; });
    loadTarotHistory();
  });
  $("#tarot-draw").addEventListener("click", drawTarot);
}

async function drawTarot() {
  const button = $("#tarot-draw"); const topic = document.querySelector(".tarot-topic.selected");
  button.disabled = true; button.innerHTML = "Колода перемешивается <span>✦</span>";
  const response = await apiFetch("/api/tarot/spread", {method: "POST", body: JSON.stringify({userId: state.userId, topicId: topic?.dataset.topic, spreadType: $("#tarot-spread").value, question: $("#tarot-question").value, birthDate: state.chart?.birthDate})});
  const data = await response.json();
  button.disabled = false; button.innerHTML = "Перемешать и вытянуть 3 карты <span>✦</span>";
  if (!response.ok) {
    const isLimit = data.error === "daily_tarot_limit";
    $("#tarot-result").innerHTML = `<div class="card locked"><h2>${isLimit ? "Расклад на сегодня уже использован" : "Расклад недоступен"}</h2><p>${escapeHtml(data.message || "Не удалось выполнить расклад.")}</p>${isLimit ? '<button class="primary-button" onclick="showView(\'profile\')">Открыть подписку</button>' : ""}</div>`;
    return;
  }
  const arcanaAfterSpread = data.personalArcana ? `<div class="card tarot-arcana-after"><div class="section-heading"><span class="step">04</span><h2>Ваши персональные Арканы в этом раскладе</h2></div><p class="tarot-arcana-intro">Это не предсказание, а личный контекст: он помогает понять, почему тема расклада может быть для вас значимой.</p>${Object.entries({personality:"Личность",destiny:"Судьба",additional:"Социальная реализация"}).map(([key, title]) => `<article class="tarot-after-item"><strong>${title}: ${data.personalArcana[key].number} · ${escapeHtml(data.personalArcana[key].name)}</strong><p>${escapeHtml(data.personalArcana[key].description)}</p><p class="tarot-arcana-meaning"><b>Краткое значение карты:</b> ${escapeHtml(data.personalArcana[key].drawnMeaning)}</p></article>`).join("")}</div>` : "";
  $("#tarot-result").innerHTML = `<div class="tarot-spread"><div class="section-heading"><span class="step">02</span><h2>${escapeHtml(data.spread.title)} · ${escapeHtml(data.topic.title)}</h2></div><p class="tarot-question">«${escapeHtml(data.question)}»</p><div class="tarot-cards">${data.cards.map((card) => `<article class="tarot-card"><div class="tarot-card-inner"><div class="tarot-back">✦<small>ASTRO TAROT</small></div><div class="tarot-front"><span>${card.reversed ? "↺" : "✦"}</span><strong>${escapeHtml(card.name)}</strong><small>${card.reversed ? "ПЕРЕВЁРНУТАЯ" : "ПРЯМАЯ"}</small></div></div><h3>${escapeHtml(card.position)}</h3><p class="muted">${escapeHtml(card.positionPrompt)}</p><p>${escapeHtml(card.interpretation)}</p></article>`).join("")}</div><div class="card tarot-summary"><div class="section-heading"><span class="step">03</span><h2>Общий итог</h2></div><p>${escapeHtml(data.summary)}</p><p class="muted">${data.disclaimer}</p></div>${arcanaAfterSpread}<button class="secondary-button" onclick="shareTarot()">Поделиться раскладом ↗</button></div>`;
}

function renderTarotArcana(arcana = state.chart?.personalArcana) {
  if (!arcana) return `<div class="card tarot-arcana-empty"><div class="section-heading"><span class="step">АРКАНЫ</span><h2>Ваши персональные Арканы</h2></div><p>Постройте натальную карту, чтобы рассчитать Арканы только по дате рождения и использовать их в раскладах.</p><button class="secondary-button" onclick="showView('home')">Ввести дату рождения →</button></div>`;
  const items = [
    ["personality", "Аркан Личности", "характер и способ проявлять себя"],
    ["destiny", "Аркан Судьбы", "предназначение и общий жизненный тон"],
    ["additional", "Дополнительный Аркан", "социальная реализация"],
  ];
  return `<section class="card tarot-arcana-block"><div class="section-heading"><span class="step">АРКАНЫ</span><h2>Ваши персональные Арканы</h2></div><p class="tarot-arcana-intro">Расчёт выполнен только по дате рождения <b>${escapeHtml(state.chart.birthDate)}</b>. Аркан Судьбы задаёт общий тон интерпретации раскладов, но не определяет единственный исход.</p><div class="tarot-arcana-list">${items.map(([key, title, subtitle]) => `<article class="tarot-arcana-item"><div class="tarot-arcana-number">${arcana[key].number}</div><div><p class="tarot-arcana-label">${title}</p><h3>${escapeHtml(arcana[key].name)}</h3><p class="tarot-arcana-subtitle">${subtitle}</p><p>${escapeHtml(arcana[key].description)}</p><p class="tarot-arcana-meaning"><b>Если выпала:</b> ${escapeHtml(arcana[key].drawnMeaning)}</p><div class="tarot-arcana-sides"><span><b>Свет</b>${escapeHtml(arcana[key].light)}</span><span><b>Тень</b>${escapeHtml(arcana[key].shadow)}</span></div></div></article>`).join("")}</div><p class="hint">Арканы помогают задавать направление для размышления. Свобода выбора остаётся за вами.</p></section>`;
}

async function loadTarotHistory() { const response = await fetch(`/api/tarot/history?userId=${encodeURIComponent(state.userId)}`); const data = await response.json(); const target = $("#tarot-day"); if (data.history?.length) target.insertAdjacentHTML("beforeend", `<details class="tarot-history"><summary>История раскладов · ${data.history.length}</summary>${data.history.slice().reverse().map((item) => `<p><b>${escapeHtml(item.spread.topic.title)}</b><br><span class="muted">${escapeHtml(item.spread.question)}</span></p>`).join("")}</details>`); }

async function shareTarot() { const text = "Мой расклад Таро в Astro App помогает посмотреть на ситуацию с другой стороны."; if (navigator.share) await navigator.share({title: "Мой расклад Таро", text}); else await navigator.clipboard.writeText(text); }

function renderProfile() {
  const arcana = state.chart?.personalArcana;
  $("#view-profile").innerHTML = `<div class="result-header"><p class="eyebrow">ПРОФИЛЬ</p><h2>Ваше пространство</h2><p>ID: ${state.userId.slice(0, 8)}…</p></div>${arcana ? `<div class="card"><div class="section-heading"><span class="step">АРКАНЫ</span><h2>Ваши ключи Таро</h2></div><div class="arcana-grid">${Object.entries({personality:"Личности",destiny:"Судьбы",additional:"Дополнительный"}).map(([key, title]) => `<article><small>${title}</small><strong>${arcana[key].number} · ${escapeHtml(arcana[key].name)}</strong><p>${escapeHtml(arcana[key].description)}</p><em>Свет: ${escapeHtml(arcana[key].light)} · Тень: ${escapeHtml(arcana[key].shadow)}</em></article>`).join("")}</div></div>` : ""}<div class="card subscription-card"><div class="section-heading"><span class="step">✦</span><h2>${state.subscription ? "Подписка активна" : "Полный доступ"}</h2></div><p>${state.subscription ? `Доступ до ${new Date(state.subscription.expiresAt).toLocaleDateString("ru-RU")}.` : "Доступ к расширенным раскладам и ежедневным картам."}</p>${state.subscription ? `<span class="pill">АКТИВНА</span>` : `<button class="primary-button" id="subscribe-button">Оформить · 300 Stars</button>`}</div><div class="card"><div class="section-heading"><span class="step">♡</span><h2>Совместимость</h2></div><p class="muted">Сравните число жизненного пути двух людей.</p><div class="compatibility-form"><input id="compat-date" type="date"><button class="secondary-button" id="compat-button">Сравнить карты →</button></div><div id="compat-result"></div></div><div class="card"><div class="section-heading"><span class="step">⚙</span><h2>Приватность</h2></div><p class="muted">Данные хранятся локально в демо-режиме. В production профиль шифруется и привязывается к Telegram.</p><button class="secondary-button danger" id="delete-button">Удалить все данные</button></div><div class="disclaimer">${state.chart?.disclaimer || "Вся информация носит развлекательный характер и не является профессиональной консультацией."}</div>`;
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
