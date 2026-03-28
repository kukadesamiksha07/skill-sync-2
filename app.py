import os
import datetime

from bytez import Bytez
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file
from pymongo import MongoClient
from bson.objectid import ObjectId

# ---------------- Bytez AI Setup ----------------
bytez_sdk = Bytez("fa6f3dc572262e198686d32855a500fd")
ai_model = bytez_sdk.model("google/gemma-3-1b-it")

app = Flask(__name__)
app.secret_key = "your_secret_key_here"

# ---------------- MongoDB Atlas Connection ----------------

client = MongoClient("mongodb+srv://skill_sync_db:admin%40123@cluster0.equbiqh.mongodb.net/skill_sync_db?retryWrites=true&w=majority")

db = client["skill_sync_db"]

# ---------------- ROUTES ----------------

@app.route('/index')
def index():
    user_name = session.get('user_name')  # example if user is logged in
    return render_template('index.html', user_name=user_name)


@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        email = request.form.get('email')
        password = request.form.get('password')

        user = db.users.find_one({
            "email": email,
            "password": password
        })

        if user:
            session['user_id'] = str(user['_id'])
            session['user_name'] = user['name']
            return redirect(url_for('dashboard'))

        return "Invalid credentials", 401

    return render_template('login.html')


@app.route('/register', methods=['POST'])
def register():

    name = request.form.get('name')
    email = request.form.get('email')
    password = request.form.get('password')

    user = {
        "name": name,
        "email": email,
        "password": password
    }

    db.users.insert_one(user)

    return redirect(url_for('login'))


@app.route('/dashboard')
def dashboard():

    if 'user_id' not in session:
        return redirect(url_for('login'))

    mentors = list(db.mentors.find())

    return render_template('dashboard.html', mentors=mentors)


@app.route('/chat')
def chat():

    if 'user_id' not in session:
        return redirect(url_for('login'))

    return render_template('chat.html')


@app.route('/api/get_messages')
def get_messages():

    messages = list(db.messages.find({
        "user_id": session.get('user_id')
    }))

    for msg in messages:
        msg['_id'] = str(msg['_id'])

    return jsonify(messages)

@app.route('/experience')
def experience():

    if 'user_id' not in session:
        return redirect(url_for('login'))

    tasks = list(db.tasks.find({
        "user_id": session['user_id']
    }))

    return render_template('experience.html', tasks=tasks)

from flask import send_file
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib import colors
from reportlab.pdfbase import ttfonts
from reportlab.pdfbase import pdfmetrics
import os, datetime

@app.route('/generate_certificate')
def generate_certificate():

    if 'user_name' not in session:
        return redirect(url_for('login'))

    name = session['user_name']
    file_path = "certificate.pdf"

    # ✅ Register custom font
    font_path = "static/GreatVibes-Regular.ttf"
    if os.path.exists(font_path):
        pdfmetrics.registerFont(ttfonts.TTFont('CustomFont', font_path))

    c = canvas.Canvas(file_path, pagesize=landscape(A4))
    width, height = landscape(A4)

    # 🎨 Background
    c.setFillColorRGB(0.06, 0.1, 0.2)
    c.rect(0, 0, width, height, fill=1)

    # 🟡 Border
    c.setStrokeColor(colors.HexColor("#D4AF37"))
    c.setLineWidth(5)
    c.rect(30, 30, width-60, height-60)

    c.setLineWidth(2)
    c.rect(50, 50, width-100, height-100)

    # 🏆 Title
    c.setFont("Times-Bold", 36)
    c.setFillColor(colors.HexColor("#D4AF37"))
    c.drawCentredString(width/2, height-100, "CERTIFICATE")

    c.setFont("Times-Bold", 22)
    c.drawCentredString(width/2, height-140, "OF COMPLETION")

    # 📜 Subtitle
    c.setFont("Helvetica-Oblique", 16)
    c.setFillColor(colors.white)
    c.drawCentredString(width/2, height-200, "This is to certify that")

    # 👤 NAME (🔥 CUSTOM FONT)
    if os.path.exists(font_path):
        c.setFont("CustomFont", 34)   # 👈 Stylish font
    else:
        c.setFont("Helvetica-Bold", 30)

    c.setFillColor(colors.HexColor("#FFD700"))
    c.drawCentredString(width/2, height-250, name)

    # 📘 Description
    c.setFont("Helvetica", 15)
    c.setFillColor(colors.white)
    c.drawCentredString(
        width/2,
        height-300,
        "has successfully completed the Skill-Sync Mentorship Program"
    )

    # 🏅 STICKER (Transparent PNG)
    seal_path = "static/seal.png"
    if os.path.exists(seal_path):
        c.drawImage(
            seal_path,
            width - 170,
            height/2 - 60,
            width=110,
            height=110,
            mask='auto'   # 👈 IMPORTANT (removes background)
        )

    # ✍ Signature
    c.setStrokeColor(colors.white)
    c.line(120, 120, 280, 120)

    c.setFont("Helvetica-Bold", 12)
    c.drawString(140, 100, "Arjun Mehta")
    c.setFont("Helvetica", 10)
    c.drawString(150, 85, "Lead Mentor")

    # 📅 Date
    date = datetime.datetime.now().strftime("%d %B %Y")
    c.setFont("Helvetica", 12)
    c.drawRightString(width-100, 100, f"Date: {date}")

    c.save()

    return send_file(file_path, as_attachment=True)

@app.route('/feedback')
def feedback():

    if 'user_id' not in session:
        return redirect(url_for('login'))

    return render_template('feedback.html')


@app.route('/portfolio')
def final_portfolio():

    if 'user_id' not in session:
        return redirect(url_for('login'))

    projects = list(db.projects.find({
        "user_id": session['user_id']
    }))

    if not projects:
        projects = list(db.projects.find())  # fallback

    for project in projects:
        project['_id'] = str(project['_id'])

    return render_template('final.html', projects=projects)


# ---------------- API ----------------

@app.route('/api/send_message', methods=['POST'])
def send_message():

    data = request.json
    user_text = data.get('text')

    # Save user message
    db.messages.insert_one({
        "user_id": session.get('user_id'),
        "text": user_text,
        "sender": "user",
        "timestamp": datetime.datetime.utcnow()
    })

    # 🔥 SIMPLE AI / MENTOR REPLY LOGIC
    if "flask" in user_text.lower():
        reply = "Great question! Flask is a backend framework used to build APIs and web apps."
    elif "help" in user_text.lower():
        reply = "Sure! Tell me exactly where you're stuck, I’ll guide you step by step."
    elif "project" in user_text.lower():
        reply = "Nice! Working on projects is the best way to learn. What are you building?"
    else:
        reply = "That's interesting! Can you explain a bit more?"

    # Save mentor reply
    db.messages.insert_one({
        "user_id": session.get('user_id'),
        "text": reply,
        "sender": "mentor",
        "timestamp": datetime.datetime.utcnow()
    })

    return jsonify({
        "status": "success",
        "reply": reply
    })


def extract_reply(output):
    """Extract the assistant's text reply from Bytez SDK output."""
    if isinstance(output, str):
        return output
    if isinstance(output, dict):
        if "content" in output:
            return extract_reply(output["content"])
        if "generated_text" in output:
            return extract_reply(output["generated_text"])
        return str(output)
    if isinstance(output, list):
        # Find the last assistant message, or fall back to last item
        for item in reversed(output):
            if isinstance(item, dict) and item.get("role") == "assistant":
                return item.get("content", str(item))
        # If no assistant role found, try the last item
        return extract_reply(output[-1]) if output else "No response."
    return str(output)

@app.route('/api/get_reply', methods=['POST'])
def get_reply():
    data = request.get_json()
    user_text = data.get("text")

    if not user_text:
        return jsonify({"reply": "Please enter a message."})

    try:
        results = ai_model.run([{"role": "user", "content": user_text}])
        print("Raw Bytez output:", results.output)  # debug

        if results.error:
            print("AI error:", results.error)
            reply = f"⚠️ AI error: {results.error}"
        else:
            output = results.output
            reply = extract_reply(output)


    except Exception as e:
        print("AI error:", e)
        reply = f"⚠️ AI is not responding properly: {e}"

    return jsonify({"reply": reply})

@app.route('/api/complete_task', methods=['POST'])
def complete_task():

    task_name = request.json.get('task_id')

    db.tasks.update_one(
        {
            "user_id": session.get('user_id'),
            "name": task_name
        },
        {
            "$set": {
                "status": "completed",
                "completed_at": datetime.datetime.utcnow()
            }
        }
    )

    return jsonify({"status": "updated"})


@app.route('/logout')
def logout():

    session.clear()

    return redirect(url_for('index'))


# ---------------- RUN APP ----------------

if __name__ == '__main__':
    app.run(debug=True)