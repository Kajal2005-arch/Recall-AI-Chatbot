# Recall — Memory-Aware Groq + CrewAI Chatbot

A Flask chatbot assignment demonstrating:
- Groq Chat Completions API for answers
- CrewAI agent/task orchestration to compact older conversation messages into memory
- SQLite persistence for conversation history and summaries
- Token optimization by sending a summary plus only the latest four user/assistant pairs
- A responsive browser-based chat interface

## 1. Requirements

Use Python 3.10 or newer (Python 3.11 is a good choice). You need internet access and a Groq API key.

## 2. Setup on Windows (VS Code / PowerShell)

```powershell
mkdir groq_crewai_flask_chatbot
# Extract this project ZIP into that folder, then:
cd groq_crewai_flask_chatbot
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Open `.env` and replace `put_your_groq_api_key_here` with your own key. Do not share the key or upload `.env` to GitHub.

If PowerShell blocks activation, run this once for the current terminal only:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## 3. Run the app

```powershell
python app.py
```

Open `http://127.0.0.1:5000` in your browser. Keep the terminal running while you use the site.

Check the server status at `http://127.0.0.1:5000/health`.

## 4. Demonstrate memory accumulation

1. Ask: "My project is called GreenSteps and it helps students track recycling."
2. Continue chatting for more than four user/assistant exchanges so the old messages are summarized.
3. Ask: "What is my project called, and what does it do?"
4. The assistant should answer from the compact memory if the summary captured those details.

The app keeps the original messages in SQLite. It does not delete the original history when creating a summary.

## 5. How token optimization works

Without optimization, a request may resend the entire conversation history every turn. This project instead sends:
- a fixed system instruction,
- a compact summary of older messages (once created),
- the latest four user/assistant pairs.

This reduces prompt size for long conversations. The exact savings depend on the conversation and summary length. The code reports Groq prompt/completion token usage in the API response, which can be inspected in browser developer tools.

CrewAI is attempted first for summarization. If CrewAI is unavailable or fails because of model/provider configuration, the app falls back to a direct Groq summarization call. This keeps the chatbot functional, but for assignment evaluation confirm CrewAI is installed and the server log shows no CrewAI summarization error.

## 6. Important notes

- The conversation store is a local SQLite database and the Flask session cookie identifies the conversation. This is a learning/demo implementation, not a production multi-user system.
- Use a strong random `FLASK_SECRET_KEY` for deployment.
- Never commit API keys.
- Model names can change. If Groq reports that the configured model is unavailable, choose a currently available chat model from the Groq Console and update `GROQ_MODEL`. For CrewAI's provider routing, the same model name is prefixed with `groq/` in `memory_manager.py`.
- CrewAI may make additional API calls when older messages need summarizing, so the memory step itself consumes tokens. The optimization goal is to reduce repeated long-history tokens over later turns, not to make summarization free.
