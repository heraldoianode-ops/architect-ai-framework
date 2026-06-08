/**
 * webhook.js — inbound WhatsApp message handler.
 * Validates HMAC, routes by message type, calls FastAPI agent, handles interactive replies.
 */
const axios = require("axios");
const crypto = require("crypto");
const { sendText, sendButtons, markRead } = require("./sender");
const { sendWelcomeMenu } = require("./templates");
const { checkRateLimit, isEscalated } = require("./rateLimit");
const { notifyInboundMessage, notifyEscalation } = require("./broadcast");

const WA_APP_SECRET = process.env.WHATSAPP_APP_SECRET || "";
const FASTAPI_URL = process.env.FASTAPI_URL || "http://backend:8000";

// ─── HMAC signature verification ─────────────────────────────────────────────
function verifySignature(rawBody, signature) {
  if (!signature || !WA_APP_SECRET) return false;
  const expected = "sha256=" + crypto
    .createHmac("sha256", WA_APP_SECRET)
    .update(rawBody)
    .digest("hex");
  try {
    return crypto.timingSafeEqual(Buffer.from(signature), Buffer.from(expected));
  } catch (_) {
    return false;
  }
}

// ─── Extract messages from Meta payload ──────────────────────────────────────
function extractMessages(body) {
  return body?.entry?.[0]?.changes?.[0]?.value?.messages || [];
}

function extractContacts(body) {
  return body?.entry?.[0]?.changes?.[0]?.value?.contacts || [];
}

// ─── Call FastAPI agent ───────────────────────────────────────────────────────
async function callAgent(waId, text, messageId, timestamp) {
  const resp = await axios.post(
    `${FASTAPI_URL}/agent/whatsapp`,
    { wa_contact_id: waId, message: text, message_id: messageId, timestamp },
    { timeout: 45000 }
  );
  return resp.data; // { reply, escalated }
}

// ─── Interactive reply decoder ────────────────────────────────────────────────
function decodeInteractiveReply(msg) {
  if (msg.type === "interactive") {
    const btn = msg.interactive?.button_reply;
    const row = msg.interactive?.list_reply;
    if (btn) return { id: btn.id, text: btn.title };
    if (row) return { id: row.id, text: row.title };
  }
  return null;
}

// ─── Main handler ─────────────────────────────────────────────────────────────
async function handleInbound(rawBody, signature) {
  const body = JSON.parse(rawBody.toString());

  if (!verifySignature(rawBody, signature)) {
    console.warn("[webhook] Invalid HMAC — request ignored");
    return;
  }

  const messages = extractMessages(body);
  if (!messages.length) return;

  for (const msg of messages) {
    const waId = msg.from;
    const msgId = msg.id;

    // Mark as read immediately
    markRead(msgId).catch(() => {});

    // Rate limiting
    const allowed = await checkRateLimit(waId);
    if (!allowed) {
      await sendText(waId, "Por favor, esperá un momento antes de enviar más mensajes.");
      continue;
    }

    // Escalation check — if escalated, notify agent dashboard and stay silent
    const escalated = await isEscalated(waId);
    if (escalated) {
      notifyInboundMessage(waId, msg.text?.body || "[media]");
      console.log(`[webhook] Escalated conversation from ${waId} — bot silent`);
      continue;
    }

    let userText = "";

    // Decode by message type
    switch (msg.type) {
      case "text":
        userText = msg.text?.body || "";
        break;

      case "interactive": {
        const reply = decodeInteractiveReply(msg);
        if (!reply) continue;
        // Map button IDs to natural language for the agent
        const buttonMap = {
          buscar_propiedad: "Quiero buscar una propiedad para comprar o alquilar",
          vender_propiedad: "Quiero vender o alquilar mi propiedad",
          hablar_agente: "Quiero hablar con un agente",
        };
        userText = buttonMap[reply.id] || reply.text;
        break;
      }

      case "image":
        userText = `[El cliente envió una imagen${msg.image?.caption ? `: ${msg.image.caption}` : ""}]`;
        break;

      case "document":
        userText = `[El cliente envió un documento: ${msg.document?.filename || "archivo"}]`;
        break;

      case "location":
        userText = `[El cliente compartió su ubicación: lat ${msg.location?.latitude}, lng ${msg.location?.longitude}]`;
        break;

      default:
        console.log(`[webhook] Unhandled message type: ${msg.type} from ${waId}`);
        continue;
    }

    if (!userText) continue;

    notifyInboundMessage(waId, userText);
    console.log(`[webhook] Inbound [${waId}]: ${userText.slice(0, 80)}`);

    try {
      const { reply, escalated: nowEscalated } = await callAgent(
        waId, userText, msgId, msg.timestamp
      );

      if (nowEscalated) {
        notifyEscalation(waId, "Escalado por el agente IA");
        // Don't send bot reply when just escalated
        continue;
      }

      if (reply) {
        await sendText(waId, reply);
        notifyInboundMessage(waId, `[BOT] ${reply}`);
      }
    } catch (err) {
      console.error(`[webhook] Agent error for ${waId}:`, err.message);
      await sendText(waId, "Disculpá, hubo un problema. Intentá de nuevo o escribí AGENTE para hablar con una persona.");
    }
  }
}

module.exports = { handleInbound, verifySignature };
