import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv
from flask import Flask, jsonify, request

load_dotenv()

SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")

app = Flask(__name__)

def run_pipeline():
    print("[Pipeline] Fetching data from Ion API...")

    # Mock API response file write for testing if input.json doesn't exist
    if not os.path.exists("input.json"):
        with open("input.json", "w") as f:
            f.write('{"id": "test_1001", "title": "Important School Update", "author": "Michael Mukai", "body": "Please review the upcoming schedule changes on the official portal."}')

    # Compile and run solution.cpp
    os.system("g++ solution.cpp -o solution.exe")
    os.system("solution.exe")

    if not os.path.exists("output.txt"):
        print("[Pipeline] Error: output.txt not found.")
        return

    with open("output.txt", "r", encoding="utf-8") as f:
        raw_content = f.read().strip()

    if raw_content != "NONE" and "|" in raw_content:
        title, author, body = raw_content.split("|", 2)

        if os.path.exists("subscribers.txt"):
            with open("subscribers.txt", "r") as f:
                recipients = [line.strip() for line in f if line.strip()]
        else:
            recipients = [SENDER_EMAIL]

        msg = EmailMessage()
        
        # Dynamic Subject line based on author
        msg['Subject'] = f"Ion announcement: {author}"
        msg['From'] = SENDER_EMAIL
        msg['To'] = SENDER_EMAIL
        msg['Reply-To'] = SENDER_EMAIL
        msg['Bcc'] = ", ".join(recipients)

        # Plain text fallback
        msg.set_content(f"Announcement from {author}:\n\n{title}\n\n{body}")

        # Formatted HTML Email Body with TJHSST Header
        html_content = f"""
        <!DOCTYPE html>
        <html>
          <body style="font-family: Arial, sans-serif; background-color: #f4f6f9; padding: 20px; color: #333;">
            <div style="max-width: 580px; margin: 0 auto; background: #ffffff; border-radius: 8px; border: 1px solid #e2e8f0; overflow: hidden;">
              
              <!-- Header with TJHSST Crest -->
              <div style="background-color: #002855; padding: 20px; text-align: center;">
                <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/8/8e/Thomas_Jefferson_High_School_for_Science_and_Technology_Crest.png/240px-Thomas_Jefferson_High_School_for_Science_and_Technology_Crest.png" 
                     alt="TJHSST Crest" 
                     style="width: 70px; height: auto; margin-bottom: 8px;">
                <h2 style="color: #ffffff; margin: 0; font-size: 18px; font-weight: 600;">Thomas Jefferson High School</h2>
                <p style="color: #cbd5e1; margin: 4px 0 0 0; font-size: 13px;">Ion Announcement System</p>
              </div>

              <!-- Content Body -->
              <div style="padding: 24px;">
                <div style="margin-bottom: 16px;">
                  <strong style="font-size: 16px; color: #0f172a; display: block;">{author}</strong>
                  <span style="font-size: 12px; color: #64748b;">Ion Announcement Author</span>
                </div>

                <h3 style="color: #1e293b; margin-top: 0; margin-bottom: 12px; font-size: 18px;">{title}</h3>
                
                <div style="font-size: 14px; line-height: 1.6; color: #334155; white-space: pre-line; background: #f8fafc; padding: 16px; border-radius: 6px; border-left: 4px solid #002855;">
                  {body}
                </div>

                <div style="margin-top: 24px; text-align: center;">
                  <a href="https://ion.tjhsst.edu" 
                     style="display: inline-block; background-color: #002855; color: #ffffff; text-decoration: none; padding: 10px 20px; border-radius: 5px; font-weight: bold; font-size: 13px;">
                     Open in Ion
                  </a>
                </div>
              </div>

            </div>
          </body>
        </html>
        """

        msg.add_alternative(html_content, subtype='html')

        print(f"[Pipeline] Sending email: '{msg['Subject']}' to {len(recipients)} recipient(s)...")
        with smtplib.SMTP_SSL("smtp.zoho.com", 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)

        print("[Pipeline] Email sent successfully!")
    else:
        print("[Pipeline] No new announcements found.")

@app.route('/')
def index():
    return "IonPlus Server Running"

if __name__ == '__main__':
    run_pipeline()
    app.run(port=5000)