/**
 * templates.js — pre-built WhatsApp template builders for common flows.
 * All templates must be pre-approved in the Meta Business dashboard before use.
 * Template names here match what's registered in Meta.
 */
const { sendTemplate, sendButtons, sendText } = require("./sender");

/**
 * Send appointment confirmation with date/time/place.
 * Template: ars_appointment_confirmation
 */
async function sendAppointmentConfirmation(to, { agentName, date, time, address, propertyTitle }) {
  return sendTemplate(to, "ars_appointment_confirmation", "es_AR", [
    {
      type: "body",
      parameters: [
        { type: "text", text: agentName },
        { type: "text", text: date },
        { type: "text", text: time },
        { type: "text", text: propertyTitle || address },
        { type: "text", text: address },
      ],
    },
  ]);
}

/**
 * Send appointment reminder (24h or 1h before).
 * Template: ars_appointment_reminder
 */
async function sendAppointmentReminder(to, { timeLabel, propertyTitle, address }) {
  return sendTemplate(to, "ars_appointment_reminder", "es_AR", [
    {
      type: "body",
      parameters: [
        { type: "text", text: timeLabel },   // "24 horas" or "1 hora"
        { type: "text", text: propertyTitle || address },
        { type: "text", text: address },
      ],
    },
  ]);
}

/**
 * Send new property match notification to a buyer.
 * Template: ars_new_property_match
 */
async function sendPropertyMatch(to, { neighborhood, propertyType, price, currency, rooms }) {
  return sendTemplate(to, "ars_new_property_match", "es_AR", [
    {
      type: "body",
      parameters: [
        { type: "text", text: `${propertyType} en ${neighborhood}` },
        { type: "text", text: `${currency} ${Number(price).toLocaleString("es-AR")}` },
        { type: "text", text: String(rooms || "?") },
      ],
    },
  ]);
}

/**
 * Send interactive welcome menu for new contacts.
 * Uses interactive buttons (no template approval needed for session messages).
 */
async function sendWelcomeMenu(to, agencyName = "la agencia") {
  return sendButtons(
    to,
    `Hola 👋 Bienvenido/a a ${agencyName}. ¿En qué te puedo ayudar?`,
    [
      { id: "buscar_propiedad", title: "🏠 Buscar propiedad" },
      { id: "vender_propiedad", title: "💰 Vender/alquilar" },
      { id: "hablar_agente",    title: "👤 Hablar con agente" },
    ],
    "",
    "Respondé con el número o tocá una opción"
  );
}

/**
 * Send a property card as text + optional image.
 */
async function sendPropertyCard(to, property) {
  const lines = [
    `🏠 *${property.title || property.address}*`,
    `📍 ${property.neighborhood || property.city}`,
    `💵 ${property.currency} ${Number(property.price).toLocaleString("es-AR")} | ${property.operation_type}`,
    `📐 ${property.sqm_covered || "?"} m² cub. · ${property.bedrooms || "?"} dorm. · ${property.bathrooms || "?"} baños`,
    property.amenities?.length ? `✨ ${property.amenities.slice(0, 4).join(" · ")}` : "",
    `\nID: ${String(property.id).slice(0, 8)} — Respondé para más info o para agendar visita.`,
  ].filter(Boolean).join("\n");

  await sendText(to, lines);
}

module.exports = {
  sendAppointmentConfirmation,
  sendAppointmentReminder,
  sendPropertyMatch,
  sendWelcomeMenu,
  sendPropertyCard,
};
