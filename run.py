import os
import json
import time
import secrets
import smtplib
from email.message import EmailMessage

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS

load_dotenv()

senderEmail = os.getenv("SENDER_EMAIL")
senderPassword = os.getenv("SENDER_PASSWORD")

ionClientId = os.getenv("ION_CLIENT_ID")
ionClientSecret = os.getenv("ION_CLIENT_SECRET")
ionRedirectUri = os.getenv("ION_REDIRECT_URI")

authUrl = "https://ion.tjhsst.edu/oauth/authorize/"
tokenUrl = "https://ion.tjhsst.edu/oauth/token/"
profileUrl = "https://ion.tjhsst.edu/api/profile"

subsFile = "subscribers"
tokensFile = "tokens"

tokenLifetime = 60 * 60 * 24 * 7

app = Flask(__name__)
CORS(app)


upstashUrl = os.getenv("UPSTASH_URL")
upstashToken = os.getenv("UPSTASH_TOKEN")


def upstashHeaders():
    return {"Authorization": f"Bearer {upstashToken}"}


def loadJson(key):
    res = requests.get(f"{upstashUrl}/get/{key}", headers=upstashHeaders())
    result = res.json().get("result")
    if not result:
        return {}
    return json.loads(result)


def saveJson(key, data):
    payload = json.dumps(data)
    requests.post(f"{upstashUrl}/set/{key}", headers=upstashHeaders(), data=payload.encode())


def usernameFromToken(token):
    tokens = loadJson(tokensFile)
    entry = tokens.get(token)
    if not entry:
        return None
    if time.time() - entry["created"] > tokenLifetime:
        del tokens[token]
        saveJson(tokensFile, tokens)
        return None
    return entry["username"]


def getTokenFromRequest():
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return None


def allEmails():
    subs = loadJson(subsFile)
    out = set()
    for lst in subs.values():
        out.update(lst)
    return list(out)


def runPipeline():
    print("checking for new announcements...")

    if not os.path.exists("input.json"):
        with open("input.json", "w") as f:
            f.write('{"id": "test_1001", "title": "Important School Update", "author": "Michael Mukai", "body": "Please review the upcoming schedule changes on the official portal."}')

    os.system("g++ solution.cpp -o solution.exe")
    os.system("solution.exe")

    if not os.path.exists("output.txt"):
        print("no output.txt, something broke in solution.cpp?")
        return

    with open("output.txt", encoding="utf-8") as f:
        raw = f.read().strip()

    if raw == "NONE" or "|" not in raw:
        print("nothing new")
        return

    title, author, body = raw.split("|", 2)
    recipients = allEmails()
    if not recipients and senderEmail:
        recipients = [senderEmail]

    msg = EmailMessage()
    msg["Subject"] = f"Ion Announcement: {author}"
    msg["From"] = senderEmail
    msg["To"] = senderEmail

    html = f"""
    <html><body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
      <div style="max-width:600px;margin:0 auto;padding:20px;border:1px solid #e0e0e0;border-radius:8px;">
        <h2 style="color:#003057;">{title}</h2>
        <p style="font-size:14px;color:#666;"><strong>Author:</strong> {author}</p>
        <hr style="border:0;border-top:1px solid #ccc;">
        <p style="font-size:16px;">{body}</p>
      </div>
    </body></html>
    """
    msg.set_content(f"{author}: {title}\n\n{body}")
    msg.add_alternative(html, subtype="html")

    try:
        with smtplib.SMTP_SSL("smtp.zoho.com", 465) as server:
            server.login(senderEmail, senderPassword)
            server.send_message(msg, to_addrs=recipients)
        print(f"sent to {len(recipients)} people")
    except Exception as e:
        print("email send failed:", e)


@app.route("/login")
def login():
    params = {
        "response_type": "code",
        "client_id": ionClientId,
        "redirect_uri": ionRedirectUri,
        "scope": "read",
    }
    qs = "&".join(f"{k}={requests.utils.quote(str(v))}" for k, v in params.items())
    return f'<a href="{authUrl}?{qs}">continue to ion</a>', 200, {"Content-Type": "text/html"}


@app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return "no code from ion", 400

    tokenRes = requests.post(tokenUrl, data={
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": ionRedirectUri,
        "client_id": ionClientId,
        "client_secret": ionClientSecret,
    })
    if tokenRes.status_code != 200:
        return f"token exchange failed: {tokenRes.text}", 400

    accessToken = tokenRes.json()["access_token"]

    profileRes = requests.get(profileUrl, headers={"Authorization": f"Bearer {accessToken}"})
    if profileRes.status_code != 200:
        return f"couldn't get profile: {profileRes.text}", 400

    username = profileRes.json().get("ion_username")
    if not username:
        return "no ion_username in profile response", 400

    siteToken = secrets.token_urlsafe(32)
    tokens = loadJson(tokensFile)
    tokens[siteToken] = {"username": username, "created": time.time()}
    saveJson(tokensFile, tokens)

    return f'<script>location.href = "https://ionplus.wnbase.com/dashboard.html?token={siteToken}";</script>'


@app.route("/api/me")
def me():
    username = usernameFromToken(getTokenFromRequest())
    if not username:
        return jsonify({"error": "not signed in"}), 401
    return jsonify({"username": username})


@app.route("/api/subscribe", methods=["POST"])
def subscribe():
    username = usernameFromToken(getTokenFromRequest())
    if not username:
        return jsonify({"error": "not signed in"}), 401

    email = request.json.get("email") if request.json else None
    if not email:
        return jsonify({"error": "no email given"}), 400

    subs = loadJson(subsFile)
    emails = subs.setdefault(username, [])
    if email not in emails:
        emails.append(email)
        saveJson(subsFile, subs)

    return jsonify({"emails": emails})


@app.route("/api/unsubscribe", methods=["POST"])
def unsubscribe():
    username = usernameFromToken(getTokenFromRequest())
    if not username:
        return jsonify({"error": "not signed in"}), 401

    email = request.json.get("email") if request.json else None
    if not email:
        return jsonify({"error": "no email given"}), 400

    subs = loadJson(subsFile)
    emails = subs.get(username, [])
    if email in emails:
        emails.remove(email)
        saveJson(subsFile, subs)

    return jsonify({"emails": emails})


@app.route("/trigger-check", methods=["GET", "POST"])
def triggerCheck():
    runPipeline()
    return jsonify({"message": "done"})


if __name__ == "__main__":
    runPipeline()
    app.run(host="0.0.0.0", port=5000)