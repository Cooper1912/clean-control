import requests

BOT_TOKEN = "8526483891:AAEBaUB0RDKMJ4u12_ynz7WjB_lGI4ZqlUs"

def set_menu_button():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setChatMenuButton"

    payload = {
        "menu_button": {
            "type": "web_app",
            "text": "🧼 Clean Control",
            "web_app": {
                "url": "https://clean-control.onrender.com"
            }
        }
    }

    r = requests.post(url, json=payload)
    print(r.text)

set_menu_button()