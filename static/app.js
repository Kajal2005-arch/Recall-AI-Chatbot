const form = document.getElementById("chat-form");
const input = document.getElementById("user-input");
const messages = document.getElementById("messages");
const typing = document.getElementById("typing");
const errorBox = document.getElementById("error");
const sendButton = document.getElementById("send-button");

function scrollToBottom() { messages.scrollTop = messages.scrollHeight; }

function addMessage(role, text) {
  const welcome = document.getElementById("welcome");
  if (welcome) welcome.remove();

  const article = document.createElement("article");
  article.className = `message ${role === "user" ? "user-message" : "assistant-message"}`;
  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = role === "user" ? "Y" : "R";
  const content = document.createElement("div");
  content.className = "message-content";
  const label = document.createElement("div");
  label.className = "message-label";
  label.textContent = role === "user" ? "You" : "Recall AI";
  const body = document.createElement("div");
  body.className = "message-text";
  body.textContent = text; // textContent prevents user/AI text from becoming HTML.
  content.append(label, body);
  article.append(avatar, content);
  messages.appendChild(article);
  scrollToBottom();
}

async function sendMessage(text) {
  const clean = text.trim();
  if (!clean) return;
  errorBox.classList.add("hidden");
  addMessage("user", clean);
  input.value = "";
  input.style.height = "auto";
  typing.classList.remove("hidden");
  sendButton.disabled = true;
  scrollToBottom();

  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: clean })
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Something went wrong.");
    addMessage("assistant", data.reply);
  } catch (error) {
    errorBox.textContent = error.message || "Unable to contact the server.";
    errorBox.classList.remove("hidden");
  } finally {
    typing.classList.add("hidden");
    sendButton.disabled = false;
    input.focus();
  }
}

form.addEventListener("submit", event => {
  event.preventDefault();
  sendMessage(input.value);
});
input.addEventListener("keydown", event => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});
input.addEventListener("input", () => {
  input.style.height = "auto";
  input.style.height = Math.min(input.scrollHeight, 160) + "px";
});
document.querySelectorAll(".suggestion").forEach(button => {
  button.addEventListener("click", () => sendMessage(button.textContent));
});
document.getElementById("new-chat").addEventListener("click", async () => {
  await fetch("/new-chat", { method: "POST" });
  window.location.reload();
});
scrollToBottom();
