import httpx
import asyncio
import os
import json
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse


BOT_TOKEN = os.getenv("CLIENT_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

APPROVED_CLEANERS = set()
CLEANER_REQUESTS = {}

ORDERS = []
PHOTO_CONTEXT = {}


app = FastAPI()

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
const API_BASE = window.location.origin
const tg = window.Telegram?.WebApp || null

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
    </div>
  `
}

function humanStatus(s){
  return {
    new: "Создан",
    taken: "Клинер назначен",
    on_way: "Клинер выехал",
    cleaning: "Уборка идёт",
    done: "Завершено"
  }[s] || "—"
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

  💰 <b>Оплата:</b> ${o.price} ₽<br><br>

  <div class="btn" onclick="setStatus(${o.id}, 'on_way')">🚗 Выехал</div>
  <div class="btn" onclick="setStatus(${o.id}, 'cleaning')">🧽 Начал уборку</div>
  <div class="btn" onclick="finishOrder(${o.id})">✅ Завершил</div>

  <hr style="margin:16px 0;opacity:.2">

  <div class="btn" onclick="uploadPhoto(${o.id}, 'before')">📸 Фото ДО уборки</div>
  <div class="btn" onclick="uploadPhoto(${o.id}, 'after')">📸 Фото ПОСЛЕ уборки</div>

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
  order.rate = TARIFFS[t]
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
    <input id="name" placeholder="Имя">
    <input id="phone" placeholder="+7 (___) ___-__-__" oninput="maskPhone(this)">
    <input id="street" placeholder="Улица и дом">
    <div class="row">
      <input id="entrance" class="small" placeholder="Подъезд">
      <input id="floor" class="small" placeholder="Этаж">
      <input id="flat" class="small" placeholder="Кв">
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
    <input id="area" placeholder="Метраж м²">
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
const streetEl = document.getElementById("street")
const flatEl = document.getElementById("flat")
const dateEl = document.getElementById("date")
const timeEl = document.getElementById("time")
const areaEl = document.getElementById("area")
const commentEl = document.getElementById("comment")

if(
  !nameEl || !phoneEl || !streetEl || !flatEl || !dateEl || !timeEl || !areaEl ||
  !nameEl.value || !phoneEl.value || !streetEl.value || !flatEl.value ||
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
  order.address = streetEl.value + " кв." + flatEl.value
  order.date = dateEl.value
  order.time = timeEl.value
  order.area = parseInt(areaEl.value || 0)
  order.comment = commentEl ? commentEl.value.trim() : ""
  if(!order.rate){
  order.rate = TARIFFS[order.type]
}
renderExtras()
}

function renderExtras(){

    if(!order.rate){
        order.rate = TARIFFS[order.type]
}

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

  html += `<div id="livePrice" style="margin-top:15px;font-weight:600"></div>`
  html += `<div class="btn" onclick="confirm()">Итог</div>`
  html += `<div class="btn" onclick="askContacts()">Назад</div>`

  screen.innerHTML = html
  updateLivePrice()
}

function extras(){
  renderExtras()
}

function confirm(){
  let base = (order.area || 0) * (order.rate || 0)
  let extras=0
  for(let k in order.extras){
    extras+=EXTRAS[k]*(order.extras[k]||0)
  }
  order.price=base+extras

  screen.innerHTML=`
    <h3>Итого: ${order.price} ₽</h3>
    <div class="btn" onclick="tap(); send()">Оформить</div>
    <div class="btn" onclick="tap(); extras()">Назад</div>

  `
}

function changeExtra(name, delta){
  order.extras[name] += delta

  if(order.extras[name] < 0) order.extras[name] = 0
  if(order.extras[name] > 10) order.extras[name] = 10   // защита от 100 окон

  document.getElementById("count_"+name).innerText = order.extras[name]
  updateLivePrice()
}

function updateLivePrice(){

    if(!order.rate){
        order.rate = TARIFFS[order.type]
}
  let base = (order.area || 0) * (order.rate || 0)
  let extras = 0

  for(let k in order.extras){
    extras += EXTRAS[k] * order.extras[k]
  }

  document.getElementById("livePrice").innerText =
    "Текущая сумма: " + (base + extras) + " ₽"
}

function send(){
  if (send.locked) return
  send.locked = true

  order.user_id = user_id

  screen.innerHTML = `
    <h3>Оформляем заказ...</h3>
    <p style="opacity:0.6">Пожалуйста, подождите</p>
  `

  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), 3000) // ⏱ 3 сек

  fetch(API_BASE + "/order", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(order),
  signal: controller.signal
})
.then(async r => {
  const data = await r.json()
  if (data.error) throw new Error(data.error)
  return data
})
.then(() => {
  clearTimeout(timeout)
  send.locked = false

  cachedOrders.unshift({ ...order }) // ← ВАЖНО
  order = { extras:{} }

  renderLastOrder(cachedOrders) // мгновенно
  clientMenu()                  // и потом обновление
})
.catch(() => {
  clearTimeout(timeout)
  send.locked = false
  order = { extras:{} }

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
    html += `
      <div style="border:1px solid #ddd;padding:14px;margin:14px 0;border-radius:12px;">
        <b>${o.type}</b><br><br>

        📍 <b>Адрес:</b> ${o.address}<br>
        📐 <b>Метраж:</b> ${o.area} м²<br>
        📅 <b>Дата:</b> ${o.date}<br>
        ⏰ <b>Время:</b> ${o.time}<br><br>

        🧰 <b>Допы:</b><br>
        ${renderExtrasText(o.extras)}<br><br>

        💬 <b>Комментарий:</b><br>
        ${o.comment || "—"}<br><br>

        💰 <b>Цена:</b> ${o.price} ₽<br>
        📌 <b>Статус:</b> ${humanStatus(o.status)}

        <br><br>

     <div class="btn" onclick="requestPhotos(${o.id}, 'before')">
     📸 Фото  ыДО уборки
     </div>

     <div class="btn" onclick="requestPhotos(${o.id}, 'after')">
     📸 Фото ПОСЛЕ уборки
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
  <input id="c_name" placeholder="Имя">
  <input id="c_phone" placeholder="Телефон">
  <input id="c_district" placeholder="Район">
  <input id="c_exp" placeholder="Опыт (лет)">
  <div class="btn" onclick="sendCleaner()">Отправить заявку</div>
  <div class="btn" onclick="start()">Назад</div>
 `
}

function sendCleaner(){
 fetch(API_BASE + "/cleaner/apply",{
  method:"POST",
  headers:{"Content-Type":"application/json"},
  body:JSON.stringify({
    user_id:user_id,
    name: c_name.value,
    phone: c_phone.value,
    district: c_district.value,
    experience: c_exp.value
  })
 }).then(()=>{
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
        html += `
          <div style="border:1px solid #ddd;padding:12px;margin:12px 0;border-radius:12px;">
            <b>${o.type}</b><br>
            ${o.address}<br>
            ${o.date} ${o.time}<br>
            <b>${o.price} ₽</b>

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

function uploadPhoto(orderId, kind){
  if(!tg){
    alert("Откройте через Telegram")
    return
  }

  tg.sendData(JSON.stringify({
    action: "photo",
    order_id: orderId,
    kind: kind
  }))

  alert(
    kind === "before"
      ? "📸 Отправьте фото ДО уборки в чат"
      : "📸 Отправьте фото ПОСЛЕ уборки в чат"
  )
}

function requestPhotos(orderId, kind){
  if(!tg){
    alert("Откройте через Telegram")
    return
  }

  tg.sendData(JSON.stringify({
    action: "get_photos",
    order_id: orderId,
    kind: kind
  }))

  alert(
    kind === "before"
      ? "📸 Фото ДО уборки придут в чат"
      : "📸 Фото ПОСЛЕ уборки придут в чат"
  )
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

    await send_to_telegram(f"✅ Клинер {user_id} одобрен")

    return {
        "ok": True,
        "message": "Клинер одобрен. Можно закрыть страницу."
    }

@app.post("/cleaner/apply")
async def cleaner_apply(req: Request):
    data = await req.json()
    uid = str(data["user_id"])

    CLEANER_REQUESTS[uid] = data

    text = (
        "🧽 Заявка клинера\n\n"
        f"Имя: {data['name']}\n"
        f"Телефон: {data['phone']}\n"
        f"Район: {data['district']}\n"
        f"Опыт: {data['experience']}\n\n"
        f"Одобрить клинера:\nhttps://clean-control.onrender.com/cleaner/approve?user_id={uid}"
    )

    async with httpx.AsyncClient() as client:
        await client.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": ADMIN_ID, "text": text}
        )

    return {"ok": True}

async def send_to_telegram(text: str):
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={"chat_id": ADMIN_ID, "text": text}
            )
    except Exception as e:
        print("Telegram error:", e)

async def send_message_to_user(user_id: int, text: str):
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                    json={
                        "chat_id": user_id,
                        "text": text
                    }
            )
    except Exception as e:
        print("User notify error:", e)

@app.post("/order")
async def order(req: Request):
    data = await req.json()

    order_id = len(ORDERS) + 1

    order_obj = {
        "id": order_id,
        "client_id": data["user_id"],
        "cleaner_id": None,
        "status": "new",
        "comment": data.get("comment", ""),
        "photos": {
            "before": [],
            "after": []
        },
        **data
    }

    ORDERS.append(order_obj)

    text = (
        f"🧹 Новый заказ #{order_id}\n\n"
        f"Тип: {data.get('type')}\n"
        f"Имя: {data.get('name')}\n"
        f"Телефон: {data.get('phone')}\n"
        f"Адрес: {data.get('address')}\n"
        f"Дата: {data.get('date')} {data.get('time')}\n"
        f"Цена: {data.get('price')} ₽\n"
        f"Комментарий: {data.get('comment', '—')}"
    )

    asyncio.create_task(send_to_telegram(text))

    return {"ok": True, "order_id": order_id}

@app.post("/support")
async def support(req: Request):
    data = await req.json()

    text = (
        "🆘 Поддержка\n\n"
        f"Пользователь: {data.get('name')}\n"
        f"user_id: {data.get('user_id')}\n\n"
        f"{data.get('message')}"
    )

    asyncio.create_task(send_to_telegram(text))

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

    await send_to_telegram(
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
            await send_to_telegram(
                f"📦 Статус заказа #{order_id}\n"
                f"{status_text}\n"
                f"Клинер: {cleaner_id}"
            )

            return {"ok": True}

    return {"error": "not found"}

@app.post("/order/photo")
async def order_photo(req: Request):
    data = await req.json()

    order_id = data["order_id"]
    photo_type = data["type"]  # before | after
    file_id = data["file_id"]

    for o in ORDERS:
        if o["id"] == order_id:
            o["photos"][photo_type].append(file_id)
            return {"ok": True}

    return {"error": "order not found"}

@app.post("/webhook")
async def telegram_webhook(request: Request):

    # 1️⃣ ЧИТАЕМ JSON ОДИН РАЗ
    data = await request.json()
    print("📥 WEBHOOK UPDATE:", data)

    # 2️⃣ ДОСТАЁМ MESSAGE
    message = data.get("message", {})
    from_user = message.get("from", {})
    user_id = from_user.get("id")

    # 3️⃣ WEB APP DATA
    web_app_data = message.get("web_app_data")

    if web_app_data:
        print("📦 WebAppData received:", web_app_data)

        try:
            payload = json.loads(web_app_data.get("data", "{}"))
            action = payload.get("action")

            if action == "photo":
                PHOTO_CONTEXT[user_id] = {
                    "order_id": payload.get("order_id"),
                    "kind": payload.get("kind"),
                    "ts": asyncio.get_event_loop().time()
                }

                await send_message_to_user(
                    user_id,
                    f"📸 Контекст принят.\n"
                    f"Отправьте фото "
                    f"{'ДО' if payload.get('kind') == 'before' else 'ПОСЛЕ'} уборки."
                )

                print("✅ PHOTO CONTEXT SET:", PHOTO_CONTEXT[user_id])

            elif action == "get_photos":
                await send_photos_to_user(
                    user_id,
                    payload.get("order_id"),
                    payload.get("kind")
                )

        except Exception as e:
            print("❌ WebAppData error:", e)

    # 4️⃣ ЕСЛИ ЭТО ФОТО
    if "photo" in message:
        await handle_photo(message)

    return {"ok": True}

async def handle_photo(message):
    user_id = message["from"]["id"]

    if user_id not in PHOTO_CONTEXT:
        await send_message_to_user(
            user_id,
            "❌ Фото не привязано к заказу.\n"
            "Сначала нажмите кнопку 📸 Фото ДО/ПОСЛЕ в Mini App."
        )
        print("⚠️ PHOTO WITHOUT CONTEXT:", user_id)
        return

    ctx = PHOTO_CONTEXT.get(user_id)

    # ⏱ Проверка устаревшего контекста (5 минут)
    if asyncio.get_event_loop().time() - ctx.get("ts", 0) > 300:
        PHOTO_CONTEXT.pop(user_id, None)
        await send_message_to_user(
            user_id,
            "⏱ Контекст фото устарел.\n"
            "Пожалуйста, нажмите кнопку загрузки фото ещё раз."
        )
        return

    # Контекст валиден — забираем
    ctx = PHOTO_CONTEXT.pop(user_id)
    order_id = ctx["order_id"]
    kind = ctx["kind"]

    file_id = message["photo"][-1]["file_id"]

    for o in ORDERS:
        if o["id"] == order_id:
            o["photos"][kind].append(file_id)

            await send_to_telegram(
                f"📸 Фото {'ДО' if kind=='before' else 'ПОСЛЕ'}\n"
                f"Заказ #{order_id}\n"
                f"Клинер: {user_id}"
            )

            await send_message_to_user(
                o["client_id"],
                f"📸 Клинер загрузил фото "
                f"{'ДО' if kind=='before' else 'ПОСЛЕ'}\n"
                f"Заказ #{order_id}"
            )

            await send_message_to_user(
                user_id,
                "✅ Фото сохранено.\nВы можете продолжать работу с заказом."
            )
            break

    ctx = PHOTO_CONTEXT.pop(user_id)
    order_id = ctx["order_id"]
    kind = ctx["kind"]

    file_id = message["photo"][-1]["file_id"]

    for o in ORDERS:
        if o["id"] == order_id:
            o["photos"][kind].append(file_id)

            await send_to_telegram(
                f"📸 Фото {'ДО' if kind=='before' else 'ПОСЛЕ'}\n"
                f"Заказ #{order_id}\n"
                f"Клинер: {user_id}"
            )

            await send_message_to_user(
                o["client_id"],
                f"📸 Клинер загрузил фото "
                f"{'ДО' if kind=='before' else 'ПОСЛЕ'}\n"
                f"Заказ #{order_id}"
            )

            await send_message_to_user(
                user_id,
                "✅ Фото сохранено.\nВы можете продолжать работу с заказом."
            )
            break

async def send_photos_to_user(user_id, order_id, kind):
    for o in ORDERS:
        if o["id"] == order_id:
            photos = o["photos"].get(kind, [])

            if not photos:
                await send_message_to_user(
                    user_id,
                    "❌ Фото не найдены"
                )
                return

            async with httpx.AsyncClient() as client:
                for file_id in photos:
                    await client.post(
                        f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
                        json={
                            "chat_id": user_id,
                            "photo": file_id
                        }
                    )
            return