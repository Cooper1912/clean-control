import httpx
import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

BOT_TOKEN = "8414415084:AAHJfqYcMWd6_5EoGDJHXf2jpo52Lve-cv4"
ADMIN_ID = 8176375746
APPROVED_CLEANERS = set()
CLEANER_REQUESTS = {}

USER_ORDERS = {}
USER_ORDERS_DATA = {}

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
const API_BASE = "https://aleta-retrogressive-miserly.ngrok-free.dev"
const tg = window.Telegram?.WebApp || null

const user = tg?.initDataUnsafe?.user || {}
const user_id = user.id || 0

const haptic = window.Telegram?.WebApp?.HapticFeedback || null

function tap(){
  try {
    haptic?.impactOccurred("light")
  } catch (e) {}
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
    <div class="btn">🏠 Мои адреса</div>

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
      if(d.state === "approved"){
        const btn = document.getElementById("cleanerBtn")
        if(btn) btn.style.display = "none"
      }
    })
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
  screen.innerHTML = `
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

function renderLastOrder(list){
  const box = document.getElementById("lastOrderBlock")
  if (!box) return

  if (!list || list.length === 0) {
    box.innerHTML = "<i>У вас пока нет заказов</i>"
    return
  }

  const o = list[list.length - 1]

  box.style.opacity = 1
  box.innerHTML = `
    <div style="background:#f0f7ff;padding:15px;border-radius:12px;margin:15px 0;">
      <b>${o.type}</b><br>
      ${o.address}<br>
      ${o.date} ${o.time}<br>
      <b>${o.price} ₽</b>
    </div>
  `
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
      <div style="border:1px solid #ddd;padding:10px;margin:10px 0;border-radius:10px;">
        <b>${o.type}</b><br>
        ${o.address}<br>
        ${o.date} ${o.time}<br>
        <b>${o.price} ₽</b>
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

start()
</script>
</body>
</html>
"""

@app.get("/cleaner/state")
async def cleaner_state(user_id: int):
    if user_id in APPROVED_CLEANERS:
        return {"state": "approved"}

    if str(user_id) in CLEANER_REQUESTS:
        return {"state": "pending"}

    return {"state": "new"}

@app.post("/cleaner/approve")
async def approve_cleaner(req: Request):
    data = await req.json()
    uid = int(data["user_id"])

    APPROVED_CLEANERS.add(uid)
    CLEANER_REQUESTS.pop(str(uid), None)

    return {"ok": True}

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
        f"Одобрить: /approve_{uid}"
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

@app.post("/order")
async def order(req: Request):
    data = await req.json()

    uid = str(data.get("user_id", "unknown"))
    USER_ORDERS_DATA.setdefault(uid, [])

    if len(USER_ORDERS_DATA[uid]) >= 2:
        return {"error": "limit"}

    USER_ORDERS_DATA[uid].append(data)

    text = (
        "🧹 Новый заказ\n\n"
        f"Тип: {data.get('type')}\n"
        f"Имя: {data.get('name')}\n"
        f"Телефон: {data.get('phone')}\n"
        f"Адрес: {data.get('address')}\n"
        f"Дата: {data.get('date')} {data.get('time')}\n"
        f"Метраж: {data.get('area')} м²\n"
        f"Цена: {data.get('price')} ₽"
    )

    # 🔥 ЖЁСТКИЙ FIRE-AND-FORGET (НЕ БЛОКИРУЕТ ЗАКАЗ)
    asyncio.create_task(send_to_telegram(text))

    return {"ok": True}

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
    return USER_ORDERS_DATA.get(str(user_id), [])

import os
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher
from aiogram.types import Update

BOT_TOKEN = os.getenv("CLIENT_BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

app = FastAPI()


@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update(**data)
    await dp.feed_update(bot, update)
    return {"ok": True}