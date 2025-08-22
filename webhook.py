from flask import Flask, request, jsonify
import gspread
from oauth2client.service_account import ServiceAccountCredentials

app = Flask(__name__)

# --- Config Google Sheets (uguale al tuo Streamlit) ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("creds.json", scope)
client = gspread.authorize(creds)
sheet = client.open_by_key("1Wf8A8BkTPJGrQmJca35_Spsbj1HJxmZoLffkreqGkrM").sheet1  

# --- Endpoint per la verifica iniziale di Meta ---
@app.route("/webhook", methods=["GET"])
def verify():
    verify_token = "1234"  # scegli tu una stringa
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == verify_token:
        return challenge, 200
    else:
        return "Error", 403

# --- Endpoint che riceve i messaggi WhatsApp ---
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    if "entry" in data:
        for entry in data["entry"]:
            for change in entry["changes"]:
                value = change["value"]
                if "messages" in value:
                    for message in value["messages"]:
                        testo = message["text"]["body"] if "text" in message else ""
                        numero = message["from"]

                        # Scrivi su Google Sheets
                        sheet.append_row(["Spesa WhatsApp", "", testo, f"da {numero}"])

                        print(f"Nuovo messaggio da {numero}: {testo}")

    return jsonify(success=True)

if __name__ == "__main__":
    app.run(port=5000, debug=True)
