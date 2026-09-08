import os
import json
import smtplib
from email.message import EmailMessage

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request, redirect, session, render_template, url_for
from flask_cors import CORS

load_dotenv()

SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")

ION_CLIENT_ID = os.getenv("ION_CLIENT_ID")
ION_CLIENT_SECRET = os.getenv("ION_CLIENT_SECRET")
ION_REDIRECT_URI = os.getenv("ION_REDIRECT_URI")  # e.g. https://ionplus.wnbase.com/callback

ION_AUTHORIZE_URL = "https://ion.tjhsst.edu/oauth/authorize/"
ION_TOKEN_URL = "https://ion.tjhsst.edu/oauth/token/"
ION_PROFILE_URL = "https://ion.tjhsst.edu/api/profile"

SUBSCRIBERS_FILE = "subscribers.json"  # { "ion_username": ["email1", "email2"] }

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")  # required for session cookies
CORS(app, supports_credentials=True)


# subscribers

def load_subscribers():
    if not os.path.exists(SUBSCRIBERS_FILE):
        return {}
    with open(SUBSCRIBERS_FILE, "r") as f:
        return json.load(f)


def save_subscribers(data):
    with open(SUBSCRIBERS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def all_subscribed_emails():
    """Flat list of every email across every user, for the announcement pipeline."""
    data = load_subscribers()
    emails = set()
    for email_list in data.values():
        emails.update(email_list)
    return list(emails)


# announcements

def run_pipeline():
    print("[Pipeline] Running pipeline check...")

    if not os.path.exists("input.json"):
        with open("input.json", "w") as f:
            f.write('{"id": "test_1001", "title": "Important School Update", "author": "Michael Mukai", "body": "Please review the upcoming schedule changes on the official portal."}')

    os.system("g++ solution.cpp -o solution.exe")
    os.system("solution.exe")

    if not os.path.exists("output.txt"):
        print("[Pipeline] Error: output.txt was not generated.")
        return

    with open("output.txt", "r", encoding="utf-8") as f:
        raw_content = f.read().strip()

    if raw_content != "NONE" and "|" in raw_content:
        title, author, body = raw_content.split("|", 2)

        recipients = all_subscribed_emails()
        if not recipients and SENDER_EMAIL:
            recipients = [SENDER_EMAIL]

        msg = EmailMessage()
        msg['Subject'] = f"Ion Announcement: {author}"
        msg['From'] = SENDER_EMAIL
        msg['To'] = SENDER_EMAIL

        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px;">
                    <h2 style="color: #003057;">{title}</h2>
                    <p style="font-size: 14px; color: #666;"><strong>Author:</strong> {author}</p>
                    <hr style="border: 0; border-top: 1px solid #ccc;">
                    <p style="font-size: 16px;">{body}</p>
                </div>
            </body>
        </html>
        """

        msg.set_content(f"Announcement from {author}:\n\nTitle: {title}\n\n{body}")
        msg.add_alternative(html_content, subtype='html')

        print(f"[Pipeline] Dispatching email to {len(recipients)} recipient(s)...")
        try:
            with smtplib.SMTP_SSL("smtp.zoho.com", 465) as server:
                server.login(SENDER_EMAIL, SENDER_PASSWORD)
                server.send_message(msg, to_addrs=recipients)
            print("[Pipeline] Email dispatched successfully.")
        except Exception as e:
            print(f"[Pipeline] Failed to send email: {e}")
    else:
        print("[Pipeline] No new announcements detected.")


# ion oauth

@app.route('/login')
def login():
    params = {
        "response_type": "code",
        "client_id": ION_CLIENT_ID,
        "redirect_uri": ION_REDIRECT_URI,
        "scope": "read",
    }
    query = "&".join(f"{k}={requests.utils.quote(str(v))}" for k, v in params.items())
    return redirect(f"{ION_AUTHORIZE_URL}?{query}")


@app.route('/callback')
def callback():
    code = request.args.get("code")
    if not code:
        return "Missing authorization code from Ion.", 400

    token_response = requests.post(ION_TOKEN_URL, data={
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": ION_REDIRECT_URI,
        "client_id": ION_CLIENT_ID,
        "client_secret": ION_CLIENT_SECRET,
    })

    if token_response.status_code != 200:
        return f"Failed to exchange code for token: {token_response.text}", 400

    token_data = token_response.json()
    access_token = token_data["access_token"]

    profile_response = requests.get(
        ION_PROFILE_URL,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    if profile_response.status_code != 200:
        return f"Failed to fetch Ion profile: {profile_response.text}", 400

    profile = profile_response.json()
    ion_username = profile.get("ion_username")
    if not ion_username:
        return "Ion profile did not return a username.", 400

    # keep username
    session["ion_username"] = ion_username

    return redirect(url_for("dashboard"))


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for("index"))


def current_user():
    return session.get("ion_username")


# pages

@app.route('/')
def index():
    return render_template("index.html")


@app.route('/dashboard')
def dashboard():
    username = current_user()
    if not username:
        return redirect(url_for("login"))

    data = load_subscribers()
    my_emails = data.get(username, [])
    return render_template("dashboard.html", username=username, emails=my_emails)


# subscription API

@app.route('/api/subscribe', methods=['POST'])
def subscribe():
    username = current_user()
    if not username:
        return jsonify({"error": "Not signed in with Ion."}), 401

    email = request.form.get('email') or (request.json and request.json.get('email'))
    if not email:
        return jsonify({"error": "Invalid email address"}), 400

    data = load_subscribers()
    emails = data.setdefault(username, [])
    if email not in emails:
        emails.append(email)
        save_subscribers(data)

    return jsonify({"message": "Subscribed successfully!", "emails": emails}), 200


@app.route('/api/unsubscribe', methods=['POST'])
def unsubscribe():
    username = current_user()
    if not username:
        return jsonify({"error": "Not signed in with Ion."}), 401

    email = request.form.get('email') or (request.json and request.json.get('email'))
    if not email:
        return jsonify({"error": "Invalid email address"}), 400

    data = load_subscribers()
    emails = data.get(username, [])
    if email in emails:
        emails.remove(email)
        save_subscribers(data)

    return jsonify({"message": "Removed.", "emails": emails}), 200


@app.route('/trigger-check', methods=['GET', 'POST'])
def trigger_check():
    run_pipeline()
    return jsonify({"message": "Pipeline check completed."}), 200


if __name__ == '__main__':
    run_pipeline()
    app.run(host='0.0.0.0', port=5000)