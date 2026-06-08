/**
 * broadcast.js — WebSocket broadcast to connected dashboard clients.
 * Events are pushed in real-time to the Next.js dashboard.
 */

const { WebSocketServer } = require("ws");

/** @type {Set<import('ws').WebSocket>} */
const clients = new Set();

/** @type {Map<string, Set<import('ws').WebSocket>>} rooms by agentId */
const agentRooms = new Map();

function setupWebSocket(server) {
  const wss = new WebSocketServer({ server, path: "/ws" });

  wss.on("connection", (ws, req) => {
    clients.add(ws);

    // Client can join a room: send { type: "join", agentId: "..." }
    ws.on("message", (data) => {
      try {
        const msg = JSON.parse(data.toString());
        if (msg.type === "join" && msg.agentId) {
          if (!agentRooms.has(msg.agentId)) agentRooms.set(msg.agentId, new Set());
          agentRooms.get(msg.agentId).add(ws);
          ws._agentId = msg.agentId;
        }
      } catch (_) {}
    });

    ws.on("close", () => {
      clients.delete(ws);
      if (ws._agentId && agentRooms.has(ws._agentId)) {
        agentRooms.get(ws._agentId).delete(ws);
      }
    });

    ws.send(JSON.stringify({ type: "connected", ts: Date.now() }));
  });

  return wss;
}

/** Broadcast an event to ALL connected dashboard clients */
function broadcastAll(event, data) {
  const msg = JSON.stringify({ event, data, ts: Date.now() });
  clients.forEach((ws) => {
    if (ws.readyState === ws.OPEN) ws.send(msg);
  });
}

/** Send an event only to clients in a specific agent's room */
function broadcastToAgent(agentId, event, data) {
  const room = agentRooms.get(agentId);
  if (!room) return;
  const msg = JSON.stringify({ event, data, ts: Date.now() });
  room.forEach((ws) => {
    if (ws.readyState === ws.OPEN) ws.send(msg);
  });
}

/** Notify all agents of an escalation (new conversation needs human attention) */
function notifyEscalation(waContactId, reason, assignedAgentId = null) {
  const payload = { waContactId, reason, assignedAgentId, ts: Date.now() };
  if (assignedAgentId) {
    broadcastToAgent(assignedAgentId, "escalation_required", payload);
  } else {
    broadcastAll("escalation_required", payload);
  }
}

/** Push a new inbound message event to the dashboard */
function notifyInboundMessage(waContactId, text, agentId = null) {
  const payload = { waContactId, text, agentId };
  if (agentId) broadcastToAgent(agentId, "message_received", payload);
  else broadcastAll("message_received", payload);
}

module.exports = { setupWebSocket, broadcastAll, broadcastToAgent, notifyEscalation, notifyInboundMessage };
