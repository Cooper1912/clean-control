import httpx
import asyncio
import os
import json
import re
import uuid
from yookassa import Configuration, Payment
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse




BOT_TOKEN = os.getenv("CLIENT_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID") or 8176375746)

APPROVED_CLEANERS = set()
CLEANER_REQUESTS = {}

ORDERS = []

TARIFFS = {
    "Поддерживающая": 100,
    "Генеральная": 150,
    "После ремонта": 250
}

EXTRAS_PRICES = {
    "Окно": 600,
    "Панорамное окно": 1200,
    "Балкон": 1000,
    "Холодильник": 500,
    "Духовка": 500,
    "Микроволновка": 300,
    "Вытяжка": 300,
    "Шкафы внутри": 1000
}


app = FastAPI()

Configuration.account_id = os.getenv("YOO_KASSA_SHOP_ID")
Configuration.secret_key = os.getenv("YOO_KASSA_SECRET")

@app.get("/", response_class=HTMLResponse)
async def webapp():
    return """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Clean Control</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<script src="https://telegram.org/js/telegram-web-app.js"></script>

<style>
body{margin:0;background:#eef3f8;font-family:-apple-system;}
.header{background:#0a84ff;color:white;padding:20px;text-align:center;font-size:20px;font-weight:600;}
.card{background:white;margin:20px;padding:20px;border-radius:14px;}
input,select{width:100%;padding:14px;margin-top:10px;border-radius:10px;border:1px solid #ddd;font-size:16px;}
.btn{margin-top:15px;background:#0a84ff;color:white;text-align:center;padding:16px;border-radius:12px;font-weight:600;}
.row{display:flex;gap:10px}
.small{flex:1}

.bubbles{
  position: fixed;
  top:0;
  left:0;
  width:100%;
  height:100%;
  pointer-events:none;
  z-index:0;
}

.bubble{
  position:absolute;
  font-size:26px;
  opacity:0.4;
  animation: float 12s infinite linear;
}

@keyframes float{
  0%{ transform: translateY(100vh) rotate(0deg); }
  100%{ transform: translateY(-100vh) rotate(360deg); }
}

/* ===== Screen animations ===== */

.fade-enter {
  opacity: 0;
  transform: translateY(10px);
}

.fade-enter-active {
  opacity: 1;
  transform: translateY(0);
  transition: opacity .25s ease, transform .25s ease;
}

.fade-exit {
  opacity: 1;
}

.fade-exit-active {
  opacity: 0;
  transition: opacity .15s ease;
}

.timeline {
  border-left: 3px solid #d0d7e2;
  padding-left: 14px;
  margin: 10px 0 5px 6px;
}

.timeline-step {
  position: relative;
  margin-bottom: 10px;
  font-size: 14px;
}

.timeline-step::before {
  content: "";
  position: absolute;
  left: -11px;
  top: 4px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #cbd5e1;
}

.timeline-step.done::before {
  background: #22c55e;
}

.timeline-step.current::before {
  background: #facc15;
  box-shadow: 0 0 0 4px rgba(250,204,21,.25);
}

</style>
</head>
<body>
<div class="header">🧼 Clean Control</div>

<div class="bubbles">
  <div class="bubble" style="left:10%;animation-delay:0s">🧽</div>
  <div class="bubble" style="left:30%;animation-delay:4s">🪣</div>
  <div class="bubble" style="left:60%;animation-delay:2s">✨</div>
  <div class="bubble" style="left:80%;animation-delay:6s">🧹</div>
</div>

<div id="screen" class="card"></div>

<script>
function onlyDigits(el){
  el.value = el.value.replace(/\D/g, '')
}

function digitsAndText(el){
  el.value = el.value.replace(/[^a-zA-Zа-яА-Я0-9\s.,\-]/g, '')
}

function onlyText(el){
  el.value = el.value.replace(/[^a-zA-Zа-яА-Я\s\-]/g, '')
}

const API_BASE = window.location.origin
const tg = window.Telegram?.WebApp || null
if (tg) {
  tg.ready()
  tg.expand()
}

const user = tg?.initDataUnsafe?.user || {}
const user_id = user.id || 0

const haptic = window.Telegram?.WebApp?.HapticFeedback || null

function tap(){
  try {
    haptic?.impactOccurred("light")
  } catch (e) {}
}

function animateScreen(html){
  screen.classList.remove("fade-enter", "fade-enter-active")

  screen.classList.add("fade-exit")
  setTimeout(() => {
    screen.classList.add("fade-exit-active")
  }, 10)

  setTimeout(() => {
    screen.innerHTML = html

    screen.classList.remove("fade-exit", "fade-exit-active")
    screen.classList.add("fade-enter")

    requestAnimationFrame(() => {
      screen.classList.add("fade-enter-active")
    })
  }, 150)
}


const screen = document.getElementById("screen")

let order = { extras:{} }
let cachedOrders = []

const TARIFFS = {
  "Поддерживающая":100,
  "Генеральная":150,
  "После ремонта":250
}

const EXTRAS = {
  "Окно":600,
  "Панорамное окно":1200,
  "Балкон":1000,
  "Холодильник":500,
  "Духовка":500,
  "Микроволновка":300,
  "Вытяжка":300,
  "Шкафы внутри":1000
}

function start(){
  clientMenu()
}

function clientMenu(){

  if (window.location.search.includes("paid")) {
  myOrders()
   }

  screen.innerHTML = `
    <h3>${user.first_name || "Здравствуйте"} 👋</h3>

    <div id="lastOrderBlock">
      <i>Загружаем последний заказ…</i>
    </div>

    <div class="btn" onclick="tap(); chooseType()">🧹 Заказать уборку</div>
    <div class="btn" onclick="tap(); myOrders()">📋 Мои заказы</div>
    <div class="btn" onclick="tap(); infoMenu()">ℹ️ Как проходит уборка</div>

    <hr style="margin:16px 0;opacity:.2">

    <div id="cleanerBtn" class="btn" onclick="tap(); cleanerIntro()">
      💼 Стать клинером
    </div>

    <div class="btn" onclick="tap(); supportIntro()">
      🆘 Поддержка
    </div>
  `

  fetch(API_BASE + "/my_orders?user_id=" + user_id)
    .then(r => r.json())
    .then(list => {
      cachedOrders = list || []
      renderLastOrder(cachedOrders)
    })
    .catch(() => {
      renderLastOrder([])
    })

  fetch(API_BASE + "/cleaner/state?user_id=" + user_id)
    .then(r => r.json())
    .then(d => {
      const btn = document.getElementById("cleanerBtn")
      if (!btn) return

      if (d.state === "approved") {
      btn.innerText = "📦 Заказы клинера"
      btn.onclick = () => cleanerAvailable()
      }

      if (d.state === "pending") {
      btn.innerText = "⏳ Заявка на рассмотрении"
      btn.onclick = () => {}
    }
  })
}

function renderLastOrder(list){
  const box = document.getElementById("lastOrderBlock")
  if (!box) return

  if (!list || list.length === 0) {
    box.innerHTML = "<i>У вас пока нет заказов</i>"
    return
  }

  const o = list[list.length - 1]

  box.innerHTML = `
    <div style="background:#f0f7ff;padding:15px;border-radius:12px;margin:15px 0;">
      <b>${o.type}</b><br>
      ${o.address}<br>
      ${o.date} ${o.time}<br>
      <b>${o.price} ₽</b><br>
      <small>Статус: ${humanStatus(o.status)}</small>
      ${o.status === "done" && o.payment_status !== "paid"
  ? `
    <div class="btn" onclick="payOrder(${o.id})">
      💳 Оплатить ${o.price} ₽
    </div>
  `
  : ""
}
      ${renderRating(o)}
    </div>
  `
}

function humanStatus(s){
  return {
    new: "Создан",
    taken: "Клинер назначен",
    on_way: "Клинер выехал",
    cleaning: "Уборка идёт",
    done: "Завершено",
    cancelled: "❌ Отменён",
  }[s] || "—"
}

function renderTimeline(status){
  const steps = [
  ["new", "Создан"],
  ["taken", "Клинер назначен"],
  ["on_way", "Клинер выехал"],
  ["cleaning", "Уборка идёт"],
  ["photos_ready", "Фотоотчёт готов 📸"],
  ["done", "Завершено"]
  ]

  let reached = true
  let html = "<div class='timeline'>"

  for (let [key, label] of steps){
    let cls = "timeline-step"

    if (key === status) {
      cls += " current"
      reached = false
    } else if (reached) {
      cls += " done"
    }

    html += `<div class="${cls}">${label}</div>`
  }

  html += "</div>"
  return html
}



function cleanerIntro(){
  screen.innerHTML = `
    <h3>💼 Работа клинером</h3>

    <div style="margin:15px 0;line-height:1.6">
      🕒 Свободный график<br>
      💰 Оплата за каждый заказ<br>
      📍 Заказы рядом с вами
    </div>

    <div class="btn" onclick="tap(); cleanerEntry()">
      Подать заявку
    </div>

    <div class="btn" onclick="tap(); clientMenu()">
      ← Назад
    </div>
  `
}

function supportIntro(){
  animateScreen(`
    <h3>🆘 Поддержка</h3>

    <div style="margin:15px 0;line-height:1.6">
      Если у вас возникли вопросы по заказу,<br>
      оплате или работе сервиса — напишите нам.
    </div>

    <div class="btn" onclick="tap(); supportForm()">
      Написать в поддержку
    </div>

    <div class="btn" onclick="tap(); clientMenu()">
      ← Назад
    </div>
  `)
}

function infoMenu(){
  screen.innerHTML = `
    <h3>ℹ️ Информация об уборке</h3>

    <div class="btn" onclick="tap(); infoFlow()">🧹 Как проходит уборка</div>
    <div class="btn" onclick="tap(); infoSupport()">🧽 Поддерживающая уборка</div>
    <div class="btn" onclick="tap(); infoGeneral()">✨ Генеральная уборка</div>
    <div class="btn" onclick="tap(); infoExtras()">🧰 Дополнительные услуги</div>
    <div class="btn" onclick="tap(); infoFaq()">❓ Частые вопросы</div>

    <div class="btn" onclick="tap(); clientMenu()">← В меню</div>
  `
}

function infoFlow(){
  screen.innerHTML = `
    <h3>🧹 Как проходит уборка</h3>

    <p>
      1️⃣ Вы оформляете заказ<br>
      2️⃣ Клинер принимает заказ<br>
      3️⃣ Клинер выезжает<br>
      4️⃣ Проводится уборка<br>
      5️⃣ Заказ завершается
    </p>

    <p style="opacity:.7">
      Статус уборки всегда отображается<br>
      в разделе «Мои заказы»
    </p>

    <div class="btn" onclick="tap(); infoMenu()">← Назад</div>
  `
}

function infoSupport(){
  screen.innerHTML = `
    <h3>🧽 Поддерживающая уборка</h3>

    <p>
      Подходит для регулярного поддержания чистоты.
    </p>

    <p>
      ✔️ Полы и плинтусы<br>
      ✔️ Пыль с поверхностей<br>
      ✔️ Кухонные поверхности<br>
      ✔️ Санузел<br>
      ✔️ Зеркала
    </p>

    <p style="opacity:.7">
      Не включает сложные загрязнения
    </p>

    <div class="btn" onclick="tap(); infoMenu()">← Назад</div>
  `
}

function infoGeneral(){
  screen.innerHTML = `
    <h3>✨ Генеральная уборка</h3>

    <p>
      Глубокая уборка всей квартиры.
    </p>

    <p>
      ✔️ Всё из поддерживающей<br>
      ✔️ Труднодоступные места<br>
      ✔️ Удаление стойких загрязнений
    </p>

    <p style="opacity:.7">
      Рекомендуем после долгого перерыва
    </p>

    <div class="btn" onclick="tap(); infoMenu()">← Назад</div>
  `
}

function infoExtras(){
  screen.innerHTML = `
    <h3>🧰 Дополнительные услуги</h3>

    <p>
      🪟 Мытьё окон<br>
      🧊 Холодильник<br>
      🔥 Духовка<br>
      🌀 Вытяжка<br>
      🧺 Шкафы внутри<br>
      🧼 Балкон
    </p>

    <p style="opacity:.7">
      Допы добавляются к заказу
      и влияют на цену
    </p>

    <div class="btn" onclick="tap(); infoMenu()">← Назад</div>
  `
}

function infoFaq(){
  screen.innerHTML = `
    <h3>❓ Частые вопросы</h3>

    <p>
      <b>Нужно ли быть дома?</b><br>
      Нет, можно оставить ключи.
    </p>

    <p>
      <b>Можно ли с животными?</b><br>
      Да, просто укажите это в комментарии.
    </p>

    <p>
      <b>Можно ли оставить пожелания?</b><br>
      Да, при оформлении заказа.
    </p>

    <div class="btn" onclick="tap(); infoMenu()">← Назад</div>
  `
}

function supportForm(){
  screen.innerHTML = `
    <h3>✉️ Сообщение в поддержку</h3>

    <textarea id="supportText"
      placeholder="Опишите проблему или вопрос"
      style="width:100%;height:120px;padding:12px;border-radius:10px;border:1px solid #ddd;font-size:16px"></textarea>

    <div class="btn" onclick="tap(); sendSupport()">
      Отправить
    </div>

    <div class="btn" onclick="tap(); supportIntro()">
      ← Назад
    </div>
  `
}

function cleanerOrders(){
  screen.innerHTML = `
    <h3>📦 Заказы клинера</h3>
    <p>Загружаем…</p>
  `

  fetch(API_BASE + "/cleaner/my_orders?user_id=" + user_id)
    .then(r => r.json())
    .then(list => {
      renderCleanerActive(list)
    })
    .catch(() => {
      screen.innerHTML = `
        <h3>📦 Заказы клинера</h3>
        <p>Ошибка загрузки</p>
        <div class="btn" onclick="tap(); clientMenu()">← В меню</div>
      `
    })
}

function renderCleanerActive(list){
  if(!list || list.length === 0){
    screen.innerHTML = `
      <h3>📦 Активные заказы</h3>
      <p>У вас нет активных заказов</p>
      <div class="btn" onclick="tap(); clientMenu()">← В меню</div>
    `
    return
  }

  const o = list[0]

screen.innerHTML = `
  <h3>🧹 Заказ #${o.id}</h3>

  <b>${o.type}</b><br><br>

  📍 <b>Адрес:</b> ${o.address}<br>
  📐 <b>Метраж:</b> ${o.area} м²<br>
  📅 <b>Дата:</b> ${o.date}<br>
  ⏰ <b>Время:</b> ${o.time}<br><br>

  🧰 <b>Допы:</b><br>
  ${renderExtrasText(o.extras)}<br><br>

  💬 <b>Комментарий клиента:</b><br>
  ${o.comment || "—"}<br><br>

  📞 <b>Телефон клиента:</b><br>
  ${o.phone}<br><br>

  💰 <b>Доход:</b> ${o.cleaner_income} ₽

  <div class="btn" onclick="setStatus(${o.id}, 'on_way')">🚗 Выехал</div>
  <div class="btn" onclick="setStatus(${o.id}, 'cleaning')">🧽 Начал уборку</div>
  <div class="btn" onclick="finishOrder(${o.id})">✅ Завершил</div>

  <hr style="margin:16px 0;opacity:.2">

  <div class="btn" onclick="tap(); clientMenu()">← В меню</div>
`
}

function finishOrder(orderId){
  fetch(API_BASE + "/cleaner/my_orders?user_id=" + user_id)
    .then(r => r.json())
    .then(list => {
      const order = list.find(o => o.id === orderId)
      if(!order) return

      if(!order.photos || !order.photos.after || order.photos.after.length === 0){
        alert("❌ Нельзя завершить заказ без фото ПОСЛЕ")
        return
      }

      setStatus(orderId, "done")
    })
}

function setStatus(orderId, status){
  fetch(API_BASE + "/order/status", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      order_id: orderId,
      status: status
    })
  })
  .then(r => r.json())
  .then(data => {
    if(data.error){
      alert(data.message)
      return
    }
    cleanerOrders()
  })
}

function takeOrder(orderId){
  fetch(API_BASE + "/cleaner/take_order", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      order_id: orderId,
      cleaner_id: user_id
    })
  })
  .then(r => r.json())
  .then(res => {
    if(res.ok){
      alert("✅ Заказ взят")
      cleanerOrders()
    } else {
      alert("❌ Не удалось взять заказ")
    }
  })
}

/* ============ ЗАКАЗ ============ */

function chooseType(){
  screen.innerHTML=`
    <h3>Выберите тип уборки</h3>
    <div class="btn" onclick="tap(); setType('Поддерживающая')">Поддерживающая</div>
    <div class="btn" onclick="tap(); setType('Генеральная')">Генеральная</div>
    <div class="btn" onclick="tap(); setType('После ремонта')">После ремонта</div>
    <div class="btn" onclick="tap(); start()">Назад</div>
  `
}

function setType(t){
  order.type = t
  askContacts()
}

function maskPhone(el){
  let x = el.value.replace(/\\D/g, '').substring(0,11)
  let formatted = '+7'
  if(x.length > 1) formatted += ' (' + x.substring(1,4)
  if(x.length >= 4) formatted += ') ' + x.substring(4,7)
  if(x.length >= 7) formatted += '-' + x.substring(7,9)
  if(x.length >= 9) formatted += '-' + x.substring(9,11)
  el.value = formatted
}

function askContacts(){
  screen.innerHTML=`
    <input id="name"
      placeholder="Имя"
      oninput="onlyText(this)">
    <input id="phone"
      placeholder="+7 (___) ___-__-__"
      inputmode="tel"
      oninput="maskPhone(this)">
      <input id="email"
        placeholder="Email для чека"
        inputmode="email">
    <input id="street"
      placeholder="Улица и дом"
      oninput="digitsAndText(this)">
    <div class="row">
    <input id="entrance" class="small"
      placeholder="Подъезд"
      inputmode="numeric"
      oninput="onlyDigits(this)">

    <input id="floor" class="small"
      placeholder="Этаж"
      inputmode="numeric"
      oninput="onlyDigits(this)">

    <input id="flat" class="small"
      placeholder="Кв"
      inputmode="numeric"
      oninput="onlyDigits(this)">
    </div>
    <input id="date" type="date">
    <select id="time">
        <option value="">Выберите время</option>
        <option>09:00</option>
        <option>10:00</option>
        <option>11:00</option>
        <option>12:00</option>
        <option>13:00</option>
        <option>14:00</option>
        <option>15:00</option>
        <option>16:00</option>
        <option>17:00</option>
        <option>18:00</option>
        <option>19:00</option>
    </select>
    <input id="area"
      placeholder="Метраж м²"
      inputmode="numeric"
      oninput="onlyDigits(this)">
    <textarea id="comment"
  placeholder="Комментарий для клинера (ключи, животные, пожелания)"
  style="width:100%;height:90px;padding:12px;
         border-radius:10px;border:1px solid #ddd;
         font-size:15px;margin-top:10px"></textarea>
    <div class="btn" onclick="tap(); goToExtras()">Далее</div>
    <div class="btn" onclick="tap(); chooseType()">Назад</div>
  `
}

function goToExtras(){
const nameEl = document.getElementById("name")
const phoneEl = document.getElementById("phone")
const emailEl = document.getElementById("email")
const streetEl = document.getElementById("street")
const flatEl = document.getElementById("flat")
const dateEl = document.getElementById("date")
const timeEl = document.getElementById("time")
const areaEl = document.getElementById("area")
const commentEl = document.getElementById("comment")

if(
  !nameEl || !phoneEl || !emailEl || !streetEl || !flatEl || !dateEl || !timeEl || !areaEl ||
  !nameEl.value || !phoneEl.value || !emailEl.value || !streetEl.value || !flatEl.value ||
  !dateEl.value || !timeEl.value || !areaEl.value
){
  alert("Пожалуйста, заполните все поля")
  return
}

if(isNaN(parseInt(areaEl.value)) || parseInt(areaEl.value) <= 0){
  alert("Введите корректный метраж")
  return
}

  order.name = nameEl.value
  order.phone = phoneEl.value
  order.email = emailEl.value.trim()
  order.address = streetEl.value + " кв." + flatEl.value
  order.date = dateEl.value
  order.time = timeEl.value
  order.area = parseInt(areaEl.value || 0)
  order.comment = commentEl ? commentEl.value.trim() : ""
renderExtras()
}

function renderExtras(){
  let html="<h3>Допы</h3>"

  for(let k in EXTRAS){
    order.extras[k] = order.extras[k] || 0
    html += `
      <div style="display:flex;justify-content:space-between;align-items:center;margin:10px 0;">
        <div>${k}</div>
        <div>
          <button onclick="tap(); changeExtra('${k}',-1)">➖</button>
          <span id="count_${k}">${order.extras[k]}</span>
          <button onclick="tap(); changeExtra('${k}',1)">➕</button>
        </div>
      </div>
    `
  }

  html += `<div style="margin-top:15px;font-weight:600;opacity:.6">
  Итоговая стоимость будет показана перед оформлением
</div>`
  html += `<div class="btn" onclick="confirm()">Итог</div>`
  html += `<div class="btn" onclick="askContacts()">Назад</div>`

  screen.innerHTML = html
}

function extras(){
  renderExtras()
}

function confirm(){
  screen.innerHTML = "<h3>Считаем стоимость…</h3>"

  fetch(API_BASE + "/order/preview", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      type: order.type,
      area: order.area,
      extras: order.extras
    })
  })
  .then(r => r.json())
  .then(d => {
    if(d.error){
      alert("Ошибка расчёта стоимости")
      extras()
      return
    }

    order.price = d.price   // ✅ ВАЖНО — сохраняем цену

    screen.innerHTML = `
      <h3>Итого: ${d.price} ₽</h3>

      <div class="btn" onclick="tap(); send()">
        Оформить заказ
      </div>

      <div class="btn" onclick="tap(); extras()">
        Назад
      </div>
    `
  })
}

function changeExtra(name, delta){
  order.extras[name] += delta

  if(order.extras[name] < 0) order.extras[name] = 0
  if(order.extras[name] > 10) order.extras[name] = 10   // защита от 100 окон

  document.getElementById("count_"+name).innerText = order.extras[name]
}

function send(){
  if (send.locked) return
  send.locked = true

  const payload = {
    user_id: user_id,
    type: order.type,
    area: order.area,
    extras: order.extras,

    name: order.name,
    phone: order.phone,
    email: order.email,
    address: order.address,

    date: order.date,
    time: order.time,
    comment: order.comment
  }

  screen.innerHTML = `
    <h3>Оформляем заказ…</h3>
    <p style="opacity:0.6">Считаем стоимость</p>
  `

  fetch(API_BASE + "/order", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  })
  .then(r => r.json())
  .then(data => {
    send.locked = false

    if(data.error){
      alert("Ошибка оформления заказа")
      afterOrderMenu()
      return
    }

    // 👇 ВАЖНО: сервер вернул цену
    order.price = data.price

    cachedOrders.unshift({
      ...order,
      price: data.price,
      status: "new",
      id: data.order_id
    })

    order = { extras:{} }
    afterOrderMenu()
  })
  .catch(() => {
    send.locked = false
    clientMenu()
  })
}

function afterOrderMenu(){
  screen.innerHTML = `
    <h3>Спасибо за заказ 👌</h3>

    <div class="btn" onclick="tap(); chooseType()">Новый заказ</div>
    <div class="btn" onclick="tap(); myOrders()">Мои заказы</div>
  `
}


function myOrders(){
  screen.innerHTML = `
    <h3>Мои заказы</h3>
    <p>Загружаем…</p>
  `

  fetch(API_BASE + "/my_orders?user_id=" + user_id)
    .then(r => r.json())
    .then(list => {
      cachedOrders = list || []
      renderOrdersList(cachedOrders)
    })
    .catch(() => {
      renderOrdersList([])
    })
}

function renderExtrasText(extras){
  if(!extras) return "—"
  let out = []
  for(let k in extras){
    if(extras[k] > 0){
      out.push(`${k}: ${extras[k]}`)
    }
  }
  return out.length ? out.join("<br>") : "—"
}

function renderOrdersList(list){

  if (!list || list.length === 0) {
    screen.innerHTML = `
      <h3>Мои заказы</h3>
      <p>У вас пока нет заказов</p>
      <div class="btn" onclick="tap(); clientMenu()">Назад</div>
    `
    return
  }

  let html = "<h3>Мои заказы</h3>"

  list.forEach(o => {

    const hasPhotos =
      (o.photos?.before?.length || 0) +
      (o.photos?.after?.length || 0) > 0

    const timelineStatus =
      hasPhotos && o.status !== "done"
        ? "photos_ready"
        : o.status

    const canGetPhotos = o.status === "done" && !o.photos_sent

    html += `
      <div style="
        border:1px solid #ddd;
        padding:16px;
        margin:14px 0;
        border-radius:14px;
        background:#fff;
      ">

        <div style="
          display:flex;
          justify-content:space-between;
          align-items:center;
        ">
          <b>${o.type}</b>
          <span style="
            background:#eef3ff;
            padding:4px 10px;
            border-radius:10px;
            font-size:13px;
          ">
            ${humanStatus(o.status)}
          </span>
        </div>

        <div style="margin-top:8px;font-size:14px;opacity:.8">
          📍 ${o.address}<br>
          📅 ${o.date} ${o.time}<br>
          📐 ${o.area} м²
        </div>

        <div style="margin:10px 0;font-weight:600">
          💰 ${o.price} ₽
        </div>

        ${renderTimeline(timelineStatus)}

        ${
          o.payment_status === "paid"
            ? `<div style="margin-top:10px;color:green;font-weight:600">
                 ✅ Оплачено
               </div>`
            : o.status === "done"
              ? `
                <div class="btn" onclick="payOrder(${o.id})">
                  💳 Оплатить уборку ${o.price} ₽
                </div>
              `
              : ""
        }

        ${
          canGetPhotos
            ? `
              <div class="btn" onclick="requestPhotos(${o.id})">
                📸 Получить фото
              </div>
            `
            : `
              <div style="margin-top:12px;opacity:.6">
                📸 Фото уже получены
              </div>
            `
        }

        ${renderRating(o)}

      </div>
    `
  })

  html += `<div class="btn" onclick="tap(); clientMenu()">Назад</div>`

  screen.innerHTML = html
}


/* ===== Клинер ===== */

function cleanerEntry(){
  screen.innerHTML = `
    <h3>Проверяем статус...</h3>
    <p style="opacity:0.6">Пожалуйста, подождите</p>
  `

  fetch(API_BASE + "/cleaner/state?user_id=" + user_id)
    .then(r => r.json())
    .then(d => {
      if(d.state === "approved"){
        screen.innerHTML = `
          <h3>Вы клинер ✅</h3>
          <p>Скоро здесь появятся заказы</p>
          <div class="btn" onclick="tap(); start()">В меню</div>
        `
      } else if(d.state === "pending"){
        screen.innerHTML = `
          <h3>Заявка на рассмотрении</h3>
          <p>Мы проверяем ваши данные</p>
          <div class="btn" onclick="tap(); start()">В меню</div>
        `
      } else {
        cleanerForm()
      }
    })
}

function cleanerForm(){
 screen.innerHTML=`
  <h3>Стать клинером</h3>

  <input id="c_name"
    placeholder="Имя"
    oninput="onlyText(this)">

  <input id="c_phone"
    placeholder="+7 (___) ___-__-__"
    inputmode="tel"
    oninput="maskPhone(this)">

  <input id="c_district"
    placeholder="Район"
    oninput="digitsAndText(this)">

  <input id="c_exp"
    placeholder="Опыт (лет)"
    inputmode="numeric"
    oninput="onlyDigits(this)">

  <textarea id="c_about"
    placeholder="О себе: опыт, инвентарь, авто, районы, чем вы хороши"
    style="
      width:100%;
      height:120px;
      padding:12px;
      margin-top:10px;
      border-radius:10px;
      border:1px solid #ddd;
      font-size:15px;
    "></textarea>

  <div class="btn" onclick="sendCleaner()">Отправить заявку</div>
  <div class="btn" onclick="start()">Назад</div>
 `
}

function sendCleaner(){
if(!c_name.value || !c_phone.value || !c_district.value || !c_exp.value){
  alert("Заполните все поля")
  return
}

if(isNaN(parseInt(c_exp.value))){
  alert("Опыт должен быть числом")
  return
}
 fetch(API_BASE + "/cleaner/apply",{
  method:"POST",
  headers:{"Content-Type":"application/json"},
  body:JSON.stringify({
    user_id:user_id,
    name: c_name.value,
    phone: c_phone.value,
    district: c_district.value,
    experience: c_exp.value,
    about: c_about.value.trim()
  })
 })
 .then(()=>{
   screen.innerHTML="<h3>Заявка отправлена</h3><p>Ожидайте подтверждения</p>"
 })
}

function sendSupport(){
  const textEl = document.getElementById("supportText")
  if(!textEl || !textEl.value.trim()){
    alert("Напишите сообщение")
    return
  }

  fetch(API_BASE + "/support",{
    method:"POST",
    headers:{ "Content-Type":"application/json" },
    body:JSON.stringify({
      user_id: user_id,
      name: user.first_name || "Без имени",
      message: textEl.value
    })
  }).then(()=>{
    screen.innerHTML = `
      <h3>✅ Сообщение отправлено</h3>
      <p>Мы скоро вам ответим</p>
      <div class="btn" onclick="tap(); clientMenu()">В меню</div>
    `
  })
}

function cleanerAvailable(){
  screen.innerHTML = `
    <h3>📦 Доступные заказы</h3>
    <p>Загружаем…</p>
  `

  fetch(API_BASE + "/cleaner/orders?user_id=" + user_id)
    .then(r => r.json())
    .then(list => {
      if(!list || list.length === 0){
        screen.innerHTML = `
          <h3>📦 Доступные заказы</h3>
          <p>Пока нет заказов</p>
          <div class="btn" onclick="tap(); cleanerOrders()">Мои активные</div>
          <div class="btn" onclick="tap(); clientMenu()">← В меню</div>
        `
        return
      }

      let html = "<h3>📦 Доступные заказы</h3>"

      list.forEach(o => {

  const extrasText = renderExtrasText(o.extras)

  html += `
    <div style="
      border:1px solid #ddd;
      padding:14px;
      margin:14px 0;
      border-radius:14px;
      background:#fff;
    ">

      <div style="font-weight:600;font-size:16px">
        🧹 ${o.type}
      </div>

      <div style="margin-top:6px;font-size:14px;opacity:.85">
        📅 ${o.date}<br>
        ⏰ ${o.time}<br>
        📐 ${o.area} м²
      </div>

      <div style="margin-top:8px;font-size:14px">
        🧰 <b>Допы:</b><br>
        ${extrasText}
      </div>

      <div style="margin-top:10px;font-weight:600">
        💰 Доход: ${o.cleaner_income} ₽
      </div>

      <div class="btn" onclick="takeOrder(${o.id})">
        🖐 Взять заказ
      </div>

    </div>
  `
})

      html += `
        <div class="btn" onclick="tap(); cleanerOrders()">Мои активные</div>
        <div class="btn" onclick="tap(); clientMenu()">← В меню</div>
      `
      screen.innerHTML = html
    })
}

function requestPhotos(orderId){
  fetch(API_BASE + "/order/photos", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      order_id: orderId,
      user_id: user_id
    })
  })
  .then(r => r.json())
  .then(() => {
    alert("📸 Фото отправлены в чат")
  })
}

function payOrder(orderId){
  screen.innerHTML = `
    <h3>Переходим к оплате…</h3>
    <p style="opacity:.6">Вы будете перенаправлены</p>
  `

  fetch(API_BASE + "/order/pay", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      order_id: orderId,
      user_id: user_id
    })
  })
  .then(r => r.json())
  .then(res => {

  if (res.confirmation_url) {
    window.location.href = res.confirmation_url
    return
  }

  if (res.error === "already_paid") {
    alert("✅ Заказ уже оплачен")
    myOrders()
    return
  }

  if (res.error === "payment_already_created") {
    alert("⏳ Платёж уже создан, завершите оплату")
    myOrders()
    return
  }

  alert("❌ Не удалось создать платёж")
  myOrders()
})
}

function renderRating(order){
  if (order.status !== "done") return ""
  if (order.rating) {
    return `<div style="margin-top:10px">⭐️ Ваша оценка: ${order.rating}/5</div>`
  }

  let html = "<div style='margin-top:10px'><b>⭐️ Оцените уборку</b><br>"

  for (let i = 1; i <= 5; i++) {
    html += `<span 
      style="font-size:26px;cursor:pointer"
      onclick="rateOrder(${order.id}, ${i})"
    >⭐️</span>`
  }

  html += "</div>"
  return html
}

function rateOrder(orderId, rating){
  fetch(API_BASE + "/order/rate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      order_id: orderId,
      user_id: user_id,
      rating: rating
    })
  })
  .then(r => r.json())
  .then(res => {
    if(res.ok){
      alert("🙏 Спасибо за оценку!")
      myOrders()
    }
  })
}

start()
</script>
</body>
</html>
"""

@app.get("/cleaner/state")
async def cleaner_state(user_id: int):
    if int(user_id) in APPROVED_CLEANERS:
        return {"state": "approved"}

    if str(user_id) in CLEANER_REQUESTS:
        return {"state": "pending"}

    return {"state": "new"}

@app.get("/cleaner/approve")
async def approve_cleaner(user_id: int):
    APPROVED_CLEANERS.add(int(user_id))
    CLEANER_REQUESTS.pop(str(user_id), None)

    await send_to_admin(f"✅ Клинер {user_id} одобрен")

    return {
        "ok": True,
        "message": "Клинер одобрен. Можно закрыть страницу."
    }

@app.post("/cleaner/apply")
async def cleaner_apply(req: Request):
    data = await req.json()
    uid = str(data["user_id"])

    CLEANER_REQUESTS[uid] = {
        "user_id": uid,
        "name": data["name"],
        "phone": data["phone"],
        "district": data["district"],
        "experience": data["experience"],
        "about": clean_str(data.get("about"), 500)
    }

    text = (
        "🧽 Заявка клинера\n\n"
        f"👤 Имя: {data['name']}\n"
        f"📞 Телефон: {data['phone']}\n"
        f"📍 Район: {data['district']}\n"
        f"🕒 Опыт: {data['experience']} лет\n\n"
        f"📝 О себе:\n{data.get('about','—')}\n\n"
        f"Команды:\n"
        f"/approve_{uid} — ✅ Одобрить\n"
        f"/reject_{uid} — ❌ Отказать\n"
        f"/ask_{uid} — 💬 Задать вопрос"
    )

    async with httpx.AsyncClient() as client:
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Одобрить",
                    callback_data=f"approve_cleaner:{uid}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отказать",
                    callback_data=f"reject_cleaner:{uid}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="💬 Задать вопрос",
                    callback_data=f"ask_cleaner:{uid}"
                )
            ]
        ])

        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(
                f"https://api.telegram.org/bot{ADMIN_BOT_TOKEN}/sendMessage",
                json={
                    "chat_id": ADMIN_ID,
                    "text": text,
                    "reply_markup": kb.model_dump()
                }
            )

    return {"ok": True}

ADMIN_BOT_TOKEN = os.getenv("ADMIN_BOT_TOKEN")

async def send_to_admin(text: str):
    if not ADMIN_BOT_TOKEN:
        print("ADMIN_BOT_TOKEN not set")
        return

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(
                f"https://api.telegram.org/bot{ADMIN_BOT_TOKEN}/sendMessage",
                json={
                    "chat_id": ADMIN_ID,
                    "text": text
                }
            )
    except Exception as e:
        print("Admin telegram error:", e)

async def send_message_to_user(user_id: int, text: str):
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={
                    "chat_id": user_id,
                    "text": text
                }
            )
            data = resp.json()
            return data["result"]["message_id"]
    except Exception as e:
        print("User notify error:", e)
        return None
    
def clean_str(v, max_len=200):
    if not isinstance(v, str):
        return ""
    return v.strip()[:max_len]
    

@app.post("/order")
async def order(req: Request):
    data = await req.json()

    # ===== VALIDATION =====

    # user
    if not data.get("user_id"):
        return {"error": "no_user"}

    # area
    try:
        area = int(data.get("area", 0))
        if area <= 0 or area > 1000:
            raise ValueError
    except:
        return {"error": "invalid_area"}

    # phone
    phone = re.sub(r"\D", "", str(data.get("phone", "")))
    if len(phone) < 10:
        return {"error": "invalid_phone"}

    # strings
    name = clean_str(data.get("name"), 50)
    address = clean_str(data.get("address"), 150)
    comment = clean_str(data.get("comment"), 300)
    email = clean_str(data.get("email"), 100)

    if not email or "@" not in email:
        return {"error": "invalid_email"}

    if not name or not address:
        return {"error": "missing_fields"}

    # type
    cleaning_type = data.get("type")
    if cleaning_type not in TARIFFS:
        return {"error": "invalid_type"}

    # extras
    extras = data.get("extras", {})
    if not isinstance(extras, dict):
        return {"error": "invalid_extras"}

    # ===== PRICE CALCULATION =====

    base_price = area * TARIFFS[cleaning_type]

    extras_sum = 0
    for key, count in extras.items():
        if key not in EXTRAS_PRICES:
            continue
        try:
            c = int(count)
            if c < 0 or c > 10:
                continue
        except:
            continue

        extras_sum += EXTRAS_PRICES[key] * c

    price = base_price + extras_sum

    if price <= 0:
        return {"error": "invalid_price"}

    # ===== ORDER CREATE =====

    order_id = len(ORDERS) + 1

    order_obj = {
        "id": order_id,
        "client_id": int(data["user_id"]),
        "cleaner_id": None,
        "status": "new",

        "type": cleaning_type,
        "name": name,
        "phone": phone,
        "email": email,
        "address": address,
        "date": data.get("date"),
        "time": data.get("time"),
        "area": area,
        "extras": extras,
        "price": price,
        "platform_fee": int(price * 0.20),     # твоя комиссия (пример 20%)
        "cleaner_income": price - int(price * 0.20),

        "payment_status": "unpaid",             # unpaid | waiting | paid
        "payout_status": "locked",              # locked | available | paid

        "comment": comment,
        "rating": None,

        "photos": {
            "before": [],
            "after": []
        },
        "photos_sent": False,    # фото отправлялись или нет
        "receipt": None        # чек
    }

    ORDERS.append(order_obj)

    # ===== NOTIFY ADMIN =====

    asyncio.create_task(send_to_admin(
        f"🧹 Новый заказ #{order_id}\n\n"
        f"Тип: {cleaning_type}\n"
        f"Имя: {name}\n"
        f"Телефон: {phone}\n"
        f"Адрес: {address}\n"
        f"Дата: {data.get('date')} {data.get('time')}\n"
        f"Метраж: {area} м²\n"
        f"Цена клиента: {price} ₽\n"
        f"Доход клинера: {order_obj['cleaner_income']} ₽\n"
        f"Комиссия сервиса: {order_obj['platform_fee']} ₽\n"
        f"Комментарий: {comment or '—'}"
    ))

    return {"ok": True, "order_id": order_id, "price": price}

@app.post("/order/preview")
async def order_preview(req: Request):
    data = await req.json()

    try:
        area = int(data.get("area", 0))
    except:
        return {"error": "bad_area"}

    cleaning_type = data.get("type")
    extras = data.get("extras", {})

    if area <= 0 or cleaning_type not in TARIFFS:
        return {"error": "bad_data"}

    base_price = area * TARIFFS[cleaning_type]
    extras_sum = 0

    for k, c in extras.items():
        if k in EXTRAS_PRICES:
            try:
                c = int(c)
                if 0 <= c <= 10:
                    extras_sum += EXTRAS_PRICES[k] * c
            except:
                pass

    return {"price": base_price + extras_sum}

@app.post("/support")
async def support(req: Request):
    data = await req.json()

    text = (
        "🆘 Поддержка\n\n"
        f"Пользователь: {data.get('name')}\n"
        f"user_id: {data.get('user_id')}\n\n"
        f"{data.get('message')}"
    )

    asyncio.create_task(send_to_admin(text))

    return {"ok": True}

@app.get("/my_orders")
async def my_orders(user_id: int):
    return [
        o for o in ORDERS
        if o.get("client_id") == user_id
    ]

@app.get("/cleaner/orders")
async def cleaner_orders(user_id: int):
    if int(user_id) not in APPROVED_CLEANERS:
        return []

    return [o for o in ORDERS if o["cleaner_id"] is None]

@app.post("/cleaner/take_order")
async def take_order(req: Request):
    data = await req.json()

    order_id = data.get("order_id")
    cleaner_id = data.get("cleaner_id")

    if cleaner_id not in APPROVED_CLEANERS:
        return {"error": "not approved"}

    # 1️⃣ Найдём заказ, который пытаются взять
    order_to_take = None
    for o in ORDERS:
        if o["id"] == order_id:
            order_to_take = o
            break

    if not order_to_take:
        return {"error": "order not found"}

    if order_to_take["cleaner_id"] is not None:
        return {"error": "already taken"}

    order_date = order_to_take.get("date")

    # 2️⃣ Считаем, сколько заказов у клинера на эту дату
    orders_today = [
        o for o in ORDERS
        if o.get("cleaner_id") == cleaner_id
        and o.get("date") == order_date
        and o.get("status") != "done"
    ]

    if len(orders_today) >= 4:
        return {
            "error": "limit_reached",
            "message": "❌ Лимит 4 заказа в день"
        }

    # 3️⃣ Назначаем заказ
    order_to_take["cleaner_id"] = cleaner_id
    order_to_take["status"] = "taken"

    await send_to_admin(
        f"🧹 Заказ #{order_id} взят клинером\n"
        f"Клинер: {cleaner_id}\n"
        f"Дата: {order_date}\n"
        f"Заказов сегодня: {len(orders_today)+1}/4"
    )

    return {"ok": True}



@app.get("/cleaner/my_orders")
async def cleaner_my_orders(user_id: int):
    return [
        o for o in ORDERS
        if o.get("cleaner_id") == user_id
        and o.get("status") != "done"
    ]

@app.post("/order/status")
async def order_status(req: Request):
    data = await req.json()

    order_id = data["order_id"]
    status = data["status"]

    status_text = {
        "on_way": "🚗 Клинер выехал",
        "cleaning": "🧽 Клинер приступил к уборке",
        "done": "✅ Уборка завершена"
    }.get(status, status)

    for o in ORDERS:
        if o["id"] == order_id:

            if status == "done" and not o["photos"]["after"]:
                return {
                    "error": "no_after_photos",
                    "message": "❌ Загрузите фото ПОСЛЕ уборки"
                }
            
            o["status"] = status

            client_id = o.get("client_id")
            cleaner_id = o.get("cleaner_id")

            # 🔔 Уведомление клиенту
            await send_message_to_user(
                client_id,
                f"{status_text}\n\n"
                f"🧹 Заказ #{order_id}\n"
                f"📍 {o.get('address')}\n"
                f"🕒 {o.get('date')} {o.get('time')}"
            )

            # 🔔 Уведомление админу
            await send_to_admin(
                f"📦 Статус заказа #{order_id}\n"
                f"{status_text}\n"
                f"Клинер: {cleaner_id}"
            )

            return {"ok": True}

    return {"error": "not found"}



@app.post("/order/pay")
async def order_pay(req: Request):
    data = await req.json()
    order_id = data.get("order_id")
    user_id = data.get("user_id")

    order = next(
        (o for o in ORDERS if o["id"] == order_id and o["client_id"] == user_id),
        None
    )

    if not order:
        return {"error": "order_not_found"}

    if order["status"] != "done":
        return {"error": "order_not_done"}

    if order["payment_status"] == "paid":
        return {"error": "already_paid"}
    
    if order["payment_status"] == "waiting":
        return {"error": "payment_already_created"}
    
    payment = Payment.create(
    {
        "amount": {
            "value": f"{order['price']}.00",
            "currency": "RUB"
        },

        "confirmation": {
            "type": "redirect",
            "return_url": "https://clean-control.onrender.com/"
        },

        "capture": True,

        "description": f"Уборка квартиры. Заказ №{order_id}",

        "receipt": {
            "customer": {
                "email": order.get("email") or "test@example.com" # или временно test@example.com
            },
            "tax_system_code": 6,  # НПД / самозанятый
            "items": [
                {
                    "description": f"Уборка квартиры, заказ №{order_id}",
                    "quantity": "1.00",
                    "amount": {
                        "value": f"{order['price']}.00",
                        "currency": "RUB"
                    },
                    "vat_code": 1
                }
            ]
        },

        "metadata": {
            "order_id": order_id
        }
    },
    uuid.uuid4()
)

    order["payment_status"] = "waiting"
    order["payment_id"] = payment.id

    return {
        "confirmation_url": payment.confirmation.confirmation_url
    }

@app.post("/yookassa/webhook")
async def yookassa_webhook(req: Request):
    event = await req.json()

    # нас интересует ТОЛЬКО успешная оплата
    if event.get("event") != "payment.succeeded":
        return {"ok": True}

    payment = event["object"]
    order_id = int(payment["metadata"]["order_id"])

    order = next((o for o in ORDERS if o["id"] == order_id), None)
    if not order:
        return {"ok": True}
    
# если уже обработан — ничего не делаем
    if order.get("payment_status") == "paid":
        return {"ok": True}

    order["payment_status"] = "paid"
    order["payout_status"] = "available"

    await send_to_admin(
        f"💰 Оплата получена\n"
        f"Заказ #{order_id}\n"
        f"Сумма: {order['price']} ₽"
    )

    return {"ok": True}

@app.post("/order/photos")
async def order_photos(req: Request):
    data = await req.json()

    order_id = data.get("order_id")
    user_id = data.get("user_id")

    if not order_id or not user_id:
        return {"error": "bad_request"}

    # 1️⃣ ищем заказ
    order = next((o for o in ORDERS if o["id"] == order_id), None)
    if not order:
        return {"error": "order_not_found"}

    # 2️⃣ проверяем доступ
    if order.get("client_id") != user_id:
        return {"error": "no_access"}
    
    if order.get("photos_sent"):
        return {"error": "already_sent"}

    # 3️⃣ собираем альбом
    media = []

    for file_id in order["photos"].get("before", []):
        media.append({
            "type": "photo",
            "media": file_id
        })

    for file_id in order["photos"].get("after", []):
        media.append({
            "type": "photo",
            "media": file_id
        })

    if not media:
        await send_message_to_user(
            user_id,
            "❌ Фото по этому заказу пока нет"
        )
        return {"ok": False}

    # 4️⃣ подпись у первого фото
    media[0]["caption"] = (
        f"🧼 Фотоотчёт по уборке\n"
        f"Заказ #{order_id}\n\n"
        f"Сначала ДО → затем ПОСЛЕ"
    )

    # 5️⃣ отправляем альбом
    async with httpx.AsyncClient(timeout=5) as client:
        await client.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMediaGroup",
            json={
                "chat_id": user_id,
                "media": media
            }
        )
        order["photos_sent"] = True

    return {"ok": True, "sent": len(media)}

@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    print("📥 WEBHOOK UPDATE:", data)

    message = data.get("message")
    if not message:
        return {"ok": True}

    if message.get("photo") or message.get("document"):
        await handle_simple_photo(message)

    return {"ok": True}

async def handle_simple_photo(message):
    user_id = message["from"]["id"]
    caption = (message.get("caption") or "").lower()

    match = re.search(r"\b(\d+)\b", caption)
    if not match:
        await send_message_to_user(
            user_id,
            "❌ Укажите номер заказа.\nПример: ДО 17"
        )
        return

    order_id = int(match.group(1))

    if "до" in caption:
        kind = "before"
    elif "после" in caption:
        kind = "after"
    else:
        await send_message_to_user(
            user_id,
            "❌ Укажите ДО или ПОСЛЕ.\nПример: ПОСЛЕ 17"
        )
        return

    if message.get("photo"):
        file_id = message["photo"][-1]["file_id"]
    elif message.get("document"):
        file_id = message["document"]["file_id"]
    else:
        return

    for o in ORDERS:
        if o["id"] == order_id:
            o["photos"][kind].append(file_id)

            await send_message_to_user(
                user_id,
                f"✅ Фото {'ДО' if kind=='before' else 'ПОСЛЕ'} сохранено\nЗаказ #{order_id}"
            )
            return

    await send_message_to_user(user_id, "❌ Заказ не найден")

@app.post("/order/rate")
async def rate_order(req: Request):
    data = await req.json()

    order_id = data.get("order_id")
    user_id = data.get("user_id")
    rating = data.get("rating")

    if not order_id or not user_id or not rating:
        return {"error": "bad_request"}

    for o in ORDERS:
        if o["id"] == order_id and o["client_id"] == user_id:
            if o["status"] != "done":
                return {"error": "not_done"}

            o["rating"] = int(rating)

            await send_to_admin(
                f"⭐️ Оценка заказа #{order_id}\n"
                f"Оценка: {rating}/5\n"
                f"Клинер: {o.get('cleaner_id')}"
            )

            return {"ok": True}

    return {"error": "order_not_found"}

@app.post("/admin/cancel_order")
async def admin_cancel_order(req: Request):
    data = await req.json()
    order_id = data.get("order_id")
    reason = data.get("reason", "Отменено администратором")

    order = next((o for o in ORDERS if o["id"] == order_id), None)
    if not order:
        return {"error": "order_not_found"}

    if order["status"] == "done":
        return {"error": "already_done"}

    order["status"] = "cancelled"

    client_id = order.get("client_id")
    cleaner_id = order.get("cleaner_id")

    # клиенту
    await send_message_to_user(
        client_id,
        f"❌ Ваш заказ #{order_id} отменён администратором.\n"
        f"Причина: {reason}"
    )

    # клинеру
    if cleaner_id:
        await send_message_to_user(
            cleaner_id,
            f"❌ Заказ #{order_id} отменён администратором.\n"
            f"Вы освобождены от выполнения."
        )

    await send_to_admin(f"❌ Заказ #{order_id} отменён администратором")

    return {"ok": True}

@app.post("/admin/unassign_order")
async def admin_unassign_order(req: Request):
    data = await req.json()
    order_id = data.get("order_id")

    order = next((o for o in ORDERS if o["id"] == order_id), None)
    if not order:
        return {"error": "order_not_found"}

    cleaner_id = order.get("cleaner_id")
    if not cleaner_id:
        return {"error": "no_cleaner_assigned"}

    order["cleaner_id"] = None
    order["status"] = "new"

    await send_message_to_user(
        cleaner_id,
        f"🔄 Заказ #{order_id} снят администратором.\n"
        f"Заказ снова доступен другим клинерам."
    )

    await send_to_admin(
        f"🔄 Заказ #{order_id} снят с клинера {cleaner_id}"
    )

    return {"ok": True}

@app.get("/admin/orders")
async def admin_orders():
    return [
        {
            "id": o["id"],
            "status": o["status"],
            "price": o["price"],
            "cleaner_id": o.get("cleaner_id")
        }
        for o in ORDERS
        if o["status"] not in ("done", "cancelled")
    ]

@app.get("/admin/cleaners")
async def admin_cleaners():
    out = []

    for cid in APPROVED_CLEANERS:
        out.append({
            "id": cid,
            "name": "—",
            "status": "approved"
        })

    for cid, data in CLEANER_REQUESTS.items():
        out.append({
            "id": int(cid),
            "name": data.get("name", "—"),
            "status": "pending"
        })

    return out
