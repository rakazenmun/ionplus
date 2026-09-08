import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS

load_dotenv()

SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")

app = Flask(__name__)
CORS(app)  # Enables cross-origin requests from front-end websites

def run_pipeline():
    print("[Pipeline] Running pipeline check...")

    # Generate dummy input file if not present
    if not os.path.exists("input.json"):
        with open("input.json", "w") as f:
            f.write('{"id": "test_1001", "title": "Important School Update", "author": "Michael Mukai", "body": "Please review the upcoming schedule changes on the official portal."}')

    # Compile and run solution executable
    os.system("g++ solution.cpp -o solution.exe")
    os.system("solution.exe")

    if not os.path.exists("output.txt"):
        print("[Pipeline] Error: output.txt was not generated.")
        return

    with open("output.txt", "r", encoding="utf-8") as f:
        raw_content = f.read().strip()

    if raw_content != "NONE" and "|" in raw_content:
        title, author, body = raw_content.split("|", 2)

        recipients = []
        if os.path.exists("subscribers.txt"):
            with open("subscribers.txt", "r") as f:
                recipients = [line.strip() for line in f if line.strip()]
        
        if not recipients and SENDER_EMAIL:
            recipients = [SENDER_EMAIL]

        msg = EmailMessage()
        msg['Subject'] = f"Ion Announcement: {author}"
        msg['From'] = SENDER_EMAIL
        msg['To'] = SENDER_EMAIL
        
        # HTML Email Body
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px;">
                    <h2 style="color: #0056b3;">{title}</h2>
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

@app.route('/')
def index():
    return jsonify({"status": "active", "service": "IonPlus Backend Server"})

@app.route('/subscribe', methods=['POST'])
def subscribe():
    email = request.form.get('email') or (request.json and request.json.get('email'))
    if email:
        with open("subscribers.txt", "a") as f:
            f.write(email + "\n")
        return jsonify({"message": "Subscribed successfully!"}), 200
    return jsonify({"error": "Invalid email address"}), 400

@app.route('/trigger-check', methods=['GET', 'POST'])
def trigger_check():
    run_pipeline()
    return jsonify({"message": "Pipeline check completed."}), 200

if __name__ == '__main__':
    run_pipeline()
    app.run(host='0.0.0.0', port=5000)