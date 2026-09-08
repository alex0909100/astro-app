const tg = window.Telegram?.WebApp;
tg?.ready(); tg?.expand();
const headers = () => ({ "Content-Type": "application/json", "X-Telegram-Init-Data": tg?.initData || "" });
const $ = (id) => document.getElementById(id);
const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;" }[c]));
async function api(url, options = {}) {
  const response = await fetch(url, {...options, headers: {...headers(), ...(options.headers || {})}});
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Ошибка запроса");
  return data;
}
async function load() {
  try {
    const [stats, users, feedback, admins] = await Promise.all([api("/admin/stats"), api(`/admin/users?search=${encodeURIComponent($("search").value)}`), api("/admin/feedback"), api("/admin/admins")]);
    $("status").textContent = "Доступ администратора подтверждён";
    $("status").className = "notice ok";
    $("total").textContent = stats.totalUsers; $("active").textContent = stats.activeUsers; $("vip").textContent = stats.vipUsers;
    const max = Math.max(...stats.registrations.map((item) => item.count), 1);
    $("registrations").innerHTML = stats.registrations.slice(-14).map((item) => `<div class="bar" title="${item.date}: ${item.count}"><i style="height:${Math.max(8, item.count / max * 100)}%"></i><span>${item.date.slice(5)}</span></div>`).join("");
    $("users").innerHTML = users.users.map((user) => {
      const vip = Boolean(user.isVip);
      return `<tr><td><b>${esc([user.firstName, user.lastName].filter(Boolean).join(" ") || "Без имени")}</b><small>${esc(user.username ? "@"+user.username : user.telegramId || user.userId)}</small></td><td>${esc(user.registeredAt || "—")}<small>Последний вход: ${esc(user.lastActiveAt || "—")} · ${esc(user.lastSource || "—")}</small></td><td><span class="badge ${vip ? "vip" : ""}">${vip ? "VIP" : "нет"}</span></td><td><button onclick="setVip('${esc(user.userId)}',${!vip})">${vip ? "Снять VIP" : "Назначить VIP"}</button></td></tr>`;
    }).join("") || `<tr><td colspan="4">Пользователи не найдены</td></tr>`;
    $("feedback").innerHTML = feedback.messages.slice().reverse().map((item) => `<article class="message"><b>${esc(item.userId)} ${item.username ? "@"+esc(item.username) : ""}</b><small>${esc(item.createdAt)} · ${esc(item.status)}</small><p>${esc(item.message)}</p><button onclick="replyTo('${esc(item.userId)}')">Ответить</button></article>`).join("") || "<p>Сообщений нет.</p>";
    $("admins").innerHTML = admins.admins.map((item) => `<div class="admin-row"><b>${esc(item.telegramId)}</b><small>${esc(item.source)}${item.protected ? " · основной" : ""}</small>${item.protected ? "" : `<button onclick="removeAdmin('${esc(item.telegramId)}')">Удалить</button>`}</div>`).join("");
  } catch (error) { $("status").textContent = error.message; $("status").className = "notice error"; }
}
async function setVip(userId, vip) {
  const days = vip ? prompt("Срок VIP в днях", "30") : "0";
  if (days === null) return;
  const message = prompt("Сообщение пользователю", vip ? "Вам активирован VIP-доступ." : "Ваш VIP-доступ отключён.") || "";
  try { await api("/admin/set-vip", {method:"POST", body:JSON.stringify({userId, vip, days: Number(days), message, notify:true})}); await load(); } catch (error) { alert(error.message); }
}
function replyTo(userId) { $("reply-user").value = userId; $("reply-text").focus(); }
$("refresh").addEventListener("click", load); $("search").addEventListener("input", load);
$("reply-form").addEventListener("submit", async (event) => { event.preventDefault(); try { await api("/admin/feedback", {method:"POST", body:JSON.stringify({userId:$("reply-user").value,message:$("reply-text").value})}); $("reply-text").value = ""; await load(); } catch (error) { alert(error.message); }});
$("admin-form").addEventListener("submit", async (event) => { event.preventDefault(); try { await api("/admin/admins", {method:"POST", body:JSON.stringify({telegramId:$("admin-id").value.trim()})}); $("admin-id").value = ""; await load(); } catch (error) { alert(error.message); }});
async function removeAdmin(telegramId) { if (!confirm(`Удалить администратора ${telegramId}?`)) return; try { await api("/admin/admins/remove", {method:"POST", body:JSON.stringify({telegramId})}); await load(); } catch (error) { alert(error.message); } }
load();
