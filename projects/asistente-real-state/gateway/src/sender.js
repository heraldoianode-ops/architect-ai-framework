/**
 * sender.js — outbound WhatsApp message factory.
 * Handles text, image, template, interactive (buttons/list) and document.
 * Includes retry logic with exponential backoff.
 */
const axios = require("axios");

const WA_TOKEN = process.env.WHATSAPP_TOKEN || "";
const WA_PHONE_ID = process.env.WHATSAPP_PHONE_NUMBER_ID || "";
const BASE_URL = `https://graph.facebook.com/v21.0/${WA_PHONE_ID}/messages`;

const HEADERS = () => ({
  Authorization: `Bearer ${WA_TOKEN}`,
  "Content-Type": "application/json",
});

// ─── Retry helper ────────────────────────────────────────────────────────────
async function postWithRetry(payload, retries = 3, delayMs = 1000) {
  for (let attempt = 1; attempt <= retries; attempt++) {
    try {
      const resp = await axios.post(BASE_URL, payload, { headers: HEADERS(), timeout: 15000 });
      return resp.data;
    } catch (err) {
      const status = err.response?.status;
      // Don't retry on client errors (4xx) except 429
      if (status && status !== 429 && status < 500 && attempt < retries) {
        throw err;
      }
      if (attempt === retries) throw err;
      const wait = delayMs * Math.pow(2, attempt - 1);
      await new Promise((r) => setTimeout(r, wait));
    }
  }
}

// ─── Text ────────────────────────────────────────────────────────────────────
async function sendText(to, text, previewUrl = false) {
  return postWithRetry({
    messaging_product: "whatsapp",
    recipient_type: "individual",
    to,
    type: "text",
    text: { body: text.slice(0, 4096), preview_url: previewUrl },
  });
}

// ─── Image ───────────────────────────────────────────────────────────────────
async function sendImage(to, imageUrl, caption = "") {
  return postWithRetry({
    messaging_product: "whatsapp",
    recipient_type: "individual",
    to,
    type: "image",
    image: { link: imageUrl, caption: caption.slice(0, 1024) },
  });
}

// ─── Document ────────────────────────────────────────────────────────────────
async function sendDocument(to, docUrl, filename, caption = "") {
  return postWithRetry({
    messaging_product: "whatsapp",
    recipient_type: "individual",
    to,
    type: "document",
    document: { link: docUrl, filename, caption },
  });
}

// ─── Template ────────────────────────────────────────────────────────────────
/**
 * Send a pre-approved WhatsApp template.
 * @param {string} to
 * @param {string} templateName - approved template name in Meta dashboard
 * @param {string} languageCode - e.g. 'es_AR', 'es', 'en_US'
 * @param {Array}  components   - template component parameters
 */
async function sendTemplate(to, templateName, languageCode = "es_AR", components = []) {
  return postWithRetry({
    messaging_product: "whatsapp",
    recipient_type: "individual",
    to,
    type: "template",
    template: {
      name: templateName,
      language: { code: languageCode },
      components,
    },
  });
}

// ─── Interactive — Quick Reply Buttons (max 3) ────────────────────────────────
/**
 * @param {string} to
 * @param {string} bodyText  - message body
 * @param {Array}  buttons   - [{id, title}] max 3 items, title max 20 chars
 * @param {string} headerText - optional header
 * @param {string} footerText - optional footer
 */
async function sendButtons(to, bodyText, buttons, headerText = "", footerText = "") {
  const payload = {
    messaging_product: "whatsapp",
    recipient_type: "individual",
    to,
    type: "interactive",
    interactive: {
      type: "button",
      body: { text: bodyText.slice(0, 1024) },
      action: {
        buttons: buttons.slice(0, 3).map((b) => ({
          type: "reply",
          reply: { id: b.id.slice(0, 256), title: b.title.slice(0, 20) },
        })),
      },
    },
  };
  if (headerText) payload.interactive.header = { type: "text", text: headerText.slice(0, 60) };
  if (footerText) payload.interactive.footer = { text: footerText.slice(0, 60) };
  return postWithRetry(payload);
}

// ─── Interactive — List (max 10 sections, 10 rows each) ──────────────────────
/**
 * @param {string} to
 * @param {string} bodyText
 * @param {string} buttonLabel - list trigger button label (max 20 chars)
 * @param {Array}  sections    - [{title, rows: [{id, title, description?}]}]
 */
async function sendList(to, bodyText, buttonLabel, sections) {
  return postWithRetry({
    messaging_product: "whatsapp",
    recipient_type: "individual",
    to,
    type: "interactive",
    interactive: {
      type: "list",
      body: { text: bodyText.slice(0, 1024) },
      action: {
        button: buttonLabel.slice(0, 20),
        sections: sections.map((s) => ({
          title: s.title?.slice(0, 24),
          rows: s.rows.slice(0, 10).map((r) => ({
            id: r.id.slice(0, 200),
            title: r.title.slice(0, 24),
            description: r.description?.slice(0, 72),
          })),
        })),
      },
    },
  });
}

// ─── Mark message as read ────────────────────────────────────────────────────
async function markRead(messageId) {
  try {
    await axios.post(
      BASE_URL,
      { messaging_product: "whatsapp", status: "read", message_id: messageId },
      { headers: HEADERS(), timeout: 5000 }
    );
  } catch (_) {
    // best-effort
  }
}

module.exports = { sendText, sendImage, sendDocument, sendTemplate, sendButtons, sendList, markRead };
