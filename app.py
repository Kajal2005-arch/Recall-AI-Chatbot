import os
import sqlite3
import uuid
from datetime import datetime, timezone

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, session
from groq import Groq

from memory_manager import update_memory, build_context_messages

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "change-this-secret-before-deployment")
DATABASE = os.getenv("DATABASE_PATH", "chat_memory.db")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None


def db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                conversation_id TEXT PRIMARY KEY,
                memory_summary TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(conversation_id) REFERENCES conversations(conversation_id)
            )
        """)


def get_or_create_conversation():
    conversation_id = session.get("conversation_id")
    with db() as conn:
        row = conn.execute(
            "SELECT conversation_id FROM conversations WHERE conversation_id = ?",
            (conversation_id,)
        ).fetchone() if conversation_id else None
        if row:
            return conversation_id

        conversation_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT INTO conversations (conversation_id, memory_summary, created_at) VALUES (?, '', ?)",
            (conversation_id, now)
        )
        session["conversation_id"] = conversation_id
        return conversation_id


def load_messages(conversation_id):
    with db() as conn:
        rows = conn.execute(
            "SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY id",
            (conversation_id,)
        ).fetchall()
    return [{"role": row["role"], "content": row["content"]} for row in rows]


def save_message(conversation_id, role, content):
    with db() as conn:
        conn.execute(
            "INSERT INTO messages (conversation_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (conversation_id, role, content, datetime.now(timezone.utc).isoformat())
        )


def load_summary(conversation_id):
    with db() as conn:
        row = conn.execute(
            "SELECT memory_summary FROM conversations WHERE conversation_id = ?",
            (conversation_id,)
        ).fetchone()
    return row["memory_summary"] if row else ""


def save_summary(conversation_id, summary):
    with db() as conn:
        conn.execute(
            "UPDATE conversations SET memory_summary = ? WHERE conversation_id = ?",
            (summary, conversation_id)
        )


@app.get("/")
def index():
    conversation_id = get_or_create_conversation()
    messages = load_messages(conversation_id)
    return render_template("index.html", messages=messages)


@app.post("/chat")
def chat():
    if not client:
        return jsonify({
            "error": "GROQ_API_KEY is missing. Add it to your .env file and restart the app."
        }), 503

    data = request.get_json(silent=True) or {}
    user_text = str(data.get("message", "")).strip()
    if not user_text:
        return jsonify({"error": "Please enter a message."}), 400
    if len(user_text) > 8000:
        return jsonify({"error": "Message is too long. Please keep it under 8,000 characters."}), 400

    conversation_id = get_or_create_conversation()
    save_message(conversation_id, "user", user_text)

    # Load stored history and compact older turns when necessary.
    history = load_messages(conversation_id)
    summary = load_summary(conversation_id)
    summary, history = update_memory(
        client=client,
        model=GROQ_MODEL,
        conversation_id=conversation_id,
        summary=summary,
        messages=history,
        save_summary_fn=save_summary,
        keep_recent_pairs=4,
    )

    prompt_messages = build_context_messages(summary, history)
    try:
        result = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=prompt_messages,
            temperature=0.5,
            max_completion_tokens=700,
        )
        answer = result.choices[0].message.content or "I couldn't generate a response."
        usage = getattr(result, "usage", None)
        token_info = {
            "prompt_tokens": getattr(usage, "prompt_tokens", None),
            "completion_tokens": getattr(usage, "completion_tokens", None),
        }
    except Exception as exc:
        # Avoid exposing API keys or internal details to the browser.
        app.logger.exception("Groq request failed")
        return jsonify({"error": "The AI request failed. Check your API key, model name, internet connection, and Groq usage limits."}), 502

    save_message(conversation_id, "assistant", answer)
    return jsonify({
        "reply": answer,
        "token_usage": token_info,
        "memory_active": bool(summary),
    })


@app.post("/new-chat")
def new_chat():
    session.pop("conversation_id", None)
    get_or_create_conversation()
    return jsonify({"ok": True})


@app.get("/health")
def health():
    return jsonify({"status": "ok", "groq_configured": bool(client)})


init_db()

if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "false").lower() == "true")
