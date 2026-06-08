const express = require("express");
const crypto = require("crypto");
const axios = require("axios");
const morgan = require("morgan");
const { WebSocketServer } = require("ws");
const http = require("http");

const app = express();
const server = http.createServer(app);

// ─── WebSocket server (real-time dashboard updates) ──────────────────────────
const wss = new WebSocketServer({ server, path: "/ws" });
const wsClients = new Set();

wss.on("connection", (ws) => {
  wsClients.add(ws);
  ws.on("close", () => wsClients.delete(ws));
});

function broadcast(event, data) {
  const msg = JSON.stringify({ event, data, ts: Date.now() });
  wsClients.forEach((ws) => {
    if (ws.readyState === ws.OPEN) ws.send(msg);
  });
}

// ─── Middleware ──────────────────────────────────────────────────────────────
app.use(morgan("combined"));
app.use(express.json());

const FASTAPI_URL = process.env.FASTAPI_URL || "http://backend:8000";
const WA_TOKEN = process.env.WHATSAPP_TOKEN || "";
const WA_PHONE_ID = process.env.WHATSAPP_PHONE_NUMBER_ID || "";
const WA_VERIFY_TOKEN = process.env.WHATSAPP_WEBHOOK_VERIFY_TOKEN || "";
const WA_APP_SECRET = process.env.WHATSAPP_APP_SECRET || "";

// ─── HMAC signature verification ────────────────────────────────────────────
function verifySignature(req) {
  const sig = req.headers["x-hub-signature-256"];
  if (!sig || !WA_APP_SECRET) return false;
  const expected = "sha256=" + crypto
    .createHmac("sha256", WA_APP_SECRET)
    .update(JSON.stringify(req.body))
    .digest("hex");
  return crypto.timingSafeEqual(Buffer.from(sig), Buffer.from(expected));
}

// ─── Webhook verification (GET) ──────────────────────────────────────────────
app.get("/webhook", (req, res) => {
  const { "hub.mode": mode, "hub.verify_token": token, "hub.challenge": challenge } = req.query;
  if (mode === "subscribe" && token === WA_VERIFY_TOKEN) {
    console.log("Webhook verified.");
    return res.status(200).send(challenge);
  }
  res.sendStatus(403);
});

// ─── Incoming messages (POST) ────────────────────────────────────────────────
app.post("/webhook", async (req, res) => {
  // Always respond 200 immediately to Meta
  res.sendStatus(200);

  if (!verifySignature(req)) {
    console.warn("Invalid HMAC signature — request ignored.");
    return;
  }

  try {
    const entry = req.body?.entry?.[0];
    const changes = entry?.changes?.[0]?.value;
    const messages = changes?.messages;

    if (!messages?.length) return;

    for (const msg of messages) {
      const waId = msg.from;
      const text = msg.text?.body || "";
      const msgType = msg.type;

      if (msgType !== "text") {
        // TODO: handle image/audio/document types
        continue;
      }

      console.log(`Inbound WA [${waId}]: ${text}`);
      broadcast("message_received", { waId, text });

      // Forward to FastAPI agent orchestrator
      const response = await axios.post(`${FASTAPI_URL}/agent/whatsapp`, {
        wa_contact_id: waId,
        message: text,
        message_id: msg.id,
        timestamp: msg.timestamp,
      }, { timeout: 30000 });

      const reply = response.data?.reply;
      if (reply) {
        await sendMessage(waId, reply);
        broadcast("message_sent", { waId, reply });
      }
    }
  } catch (err) {
    console.error("Webhook processing error:", err.message);
  }
});

// ─── Send WhatsApp message ───────────────────────────────────────────────────
async function sendMessage(to, text) {
  await axios.post(
    `https://graph.facebook.com/v21.0/${WA_PHONE_ID}/messages`,
    {
      messaging_product: "whatsapp",
      recipient_type: "individual",
      to,
      type: "text",
      text: { body: text, preview_url: false },
    },
    {
      headers: {
        Authorization: `Bearer ${WA_TOKEN}`,
        "Content-Type": "application/json",
      },
    }
  );
}

// ─── Internal API (called by FastAPI backend) ────────────────────────────────
app.post("/send", async (req, res) => {
  const { to, text, type = "text" } = req.body;
  if (!to || !text) return res.status(400).json({ error: "Missing to or text" });
  try {
    await sendMessage(to, text);
    res.json({ ok: true });
  } catch (err) {
    console.error("Send error:", err.response?.data || err.message);
    res.status(500).json({ error: err.message });
  }
});

app.get("/health", (_, res) => res.json({ status: "ok", service: "ars-gateway" }));

// ─── Start ───────────────────────────────────────────────────────────────────
const PORT = process.env.PORT || 3000;
server.listen(PORT, () => {
  console.log(`ARS Gateway listening on :${PORT}`);
  console.log(`FastAPI target: ${FASTAPI_URL}`);
  console.log(`WebSocket: ws://localhost:${PORT}/ws`);
});
