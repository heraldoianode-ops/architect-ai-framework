/**
 * index.js — ARS WhatsApp Gateway entry point.
 * Orchestrates webhook, sender, rate limiter, broadcast and internal API.
 */
const express = require("express");
const http = require("http");
const morgan = require("morgan");
const Redis = require("ioredis");

const { handleInbound } = require("./webhook");
const { sendText, sendTemplate, sendButtons } = require("./sender");
const { setupWebSocket, broadcastAll } = require("./broadcast");
const { setRedis, checkRateLimit } = require("./rateLimit");
const { sendWelcomeMenu, sendPropertyCard, sendAppointmentReminder } = require("./templates");

// ─── Config ──────────────────────────────────────────────────────────────────
const PORT = parseInt(process.env.PORT || "3000", 10);
const WA_VERIFY_TOKEN = process.env.WHATSAPP_WEBHOOK_VERIFY_TOKEN || "";

// ─── Redis ───────────────────────────────────────────────────────────────────
const redis = new Redis(process.env.REDIS_URL || "redis://redis:6379/1", {
  lazyConnect: true,
  retryStrategy: (times) => Math.min(times * 200, 3000),
});
redis.connect().catch((e) => console.warn("[redis] connect warning:", e.message));
setRedis(redis);

// ─── App ─────────────────────────────────────────────────────────────────────
const app = express();
const server = http.createServer(app);

// Raw body buffer needed for HMAC verification
app.use(express.json({
  verify: (req, _res, buf) => { req.rawBody = buf; },
}));
app.use(morgan("combined"));

// ─── WebSocket ───────────────────────────────────────────────────────────────
setupWebSocket(server);

// ─── Webhook verification (GET) ──────────────────────────────────────────────
app.get("/webhook", (req, res) => {
  const { "hub.mode": mode, "hub.verify_token": token, "hub.challenge": challenge } = req.query;
  if (mode === "subscribe" && token === WA_VERIFY_TOKEN) {
    console.log("[webhook] Verified by Meta.");
    return res.status(200).send(challenge);
  }
  console.warn("[webhook] Verification failed. Check WHATSAPP_WEBHOOK_VERIFY_TOKEN.");
  res.sendStatus(403);
});

// ─── Inbound messages (POST) ─────────────────────────────────────────────────
app.post("/webhook", async (req, res) => {
  res.sendStatus(200); // always respond immediately to Meta

  const sig = req.headers["x-hub-signature-256"];
  try {
    await handleInbound(req.rawBody, sig);
  } catch (err) {
    console.error("[webhook] Processing error:", err.message);
  }
});

// ─── Internal API — called by FastAPI backend ─────────────────────────────────

// Send text or media
app.post("/send", async (req, res) => {
  const { to, text, type = "text", image_url, caption, template_name, language, components } = req.body;

  if (!to) return res.status(400).json({ error: "Missing 'to'" });

  try {
    let result;
    switch (type) {
      case "template":
        result = await sendTemplate(to, template_name, language || "es_AR", components || []);
        break;
      case "image":
        const { sendImage } = require("./sender");
        result = await sendImage(to, image_url, caption);
        break;
      default:
        if (!text) return res.status(400).json({ error: "Missing 'text'" });
        result = await sendText(to, text);
    }
    res.json({ ok: true, result });
  } catch (err) {
    console.error("[send] Error:", err.response?.data || err.message);
    res.status(502).json({ error: err.message });
  }
});

// Send welcome menu (interactive buttons)
app.post("/send/welcome", async (req, res) => {
  const { to, agency_name } = req.body;
  if (!to) return res.status(400).json({ error: "Missing 'to'" });
  try {
    await sendWelcomeMenu(to, agency_name);
    res.json({ ok: true });
  } catch (err) {
    res.status(502).json({ error: err.message });
  }
});

// Send property card
app.post("/send/property", async (req, res) => {
  const { to, property } = req.body;
  if (!to || !property) return res.status(400).json({ error: "Missing 'to' or 'property'" });
  try {
    await sendPropertyCard(to, property);
    res.json({ ok: true });
  } catch (err) {
    res.status(502).json({ error: err.message });
  }
});

// Send appointment reminder
app.post("/send/reminder", async (req, res) => {
  const { to, time_label, property_title, address } = req.body;
  try {
    await sendAppointmentReminder(to, {
      timeLabel: time_label,
      propertyTitle: property_title,
      address,
    });
    res.json({ ok: true });
  } catch (err) {
    res.status(502).json({ error: err.message });
  }
});

// Broadcast event to all dashboard WebSocket clients
app.post("/broadcast", (req, res) => {
  const { event, data } = req.body;
  if (!event) return res.status(400).json({ error: "Missing 'event'" });
  broadcastAll(event, data || {});
  res.json({ ok: true });
});

// ─── Health ──────────────────────────────────────────────────────────────────
app.get("/health", async (_, res) => {
  const redisOk = await redis.ping().then(() => "ok").catch(() => "error");
  res.json({ status: "ok", service: "ars-gateway", redis: redisOk });
});

// ─── Start ───────────────────────────────────────────────────────────────────
server.listen(PORT, () => {
  console.log(`ARS Gateway listening on :${PORT}`);
  console.log(`FastAPI target: ${process.env.FASTAPI_URL || "http://backend:8000"}`);
  console.log(`WebSocket: ws://0.0.0.0:${PORT}/ws`);
});
