"""
ReAct Agent — core of the PropTech AI assistant.
Pattern: Reasoning + Acting via Tool Use (LangChain AgentExecutor).
Default LLM: Ollama local (zero token cost).
External LLM: only for authorized agents when allow_external=True.
"""
import structlog
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import HumanMessage, AIMessage

from app.core.llm import get_llm
from app.core.redis import get_session, set_session
from app.agents.tools.search_properties import search_properties
from app.agents.tools.get_client_history import get_client_history
from app.agents.tools.schedule_event import schedule_event
from app.agents.tools.send_whatsapp import send_whatsapp_message, escalate_to_human

log = structlog.get_logger()

# ─── Tool registry ────────────────────────────────────────────────────────────
BASE_TOOLS = [
    search_properties,
    get_client_history,
    schedule_event,
    send_whatsapp_message,
    escalate_to_human,
]

# ─── System prompt ────────────────────────────────────────────────────────────
REACT_PROMPT = PromptTemplate.from_template("""Sos un asistente inmobiliario profesional para una agencia de bienes raíces.
Tu trabajo es ayudar a compradores, vendedores y agentes de manera eficiente y amable.

Tenés acceso a las siguientes herramientas:
{tools}

Siempre seguí este formato:

Pregunta: la pregunta que tenés que responder
Pensamiento: pensá paso a paso qué debés hacer
Acción: la acción a tomar, debe ser una de [{tool_names}]
Entrada de acción: la entrada para la acción
Observación: el resultado de la acción
... (este ciclo Pensamiento/Acción/Entrada/Observación puede repetirse N veces)
Pensamiento: ya sé qué responder
Respuesta final: la respuesta final al usuario

REGLAS:
- Siempre consultá el historial del cliente ANTES de responder (get_client_history).
- Si no podés resolver la consulta, escalá a un agente humano (escalate_to_human).
- Respondé siempre en español, de manera natural y profesional.
- No inventes precios, disponibilidad ni datos de propiedades — usá las herramientas.
- Para agendar, confirmá todos los datos antes de crear el evento.

Historial de conversación:
{chat_history}

Pregunta: {input}
{agent_scratchpad}""")


# ─── Agent factory ────────────────────────────────────────────────────────────
def build_agent(agent_name: str | None = None) -> AgentExecutor:
    llm = get_llm(agent_name)
    agent = create_react_agent(llm, BASE_TOOLS, REACT_PROMPT)
    return AgentExecutor(
        agent=agent,
        tools=BASE_TOOLS,
        verbose=True,
        max_iterations=6,
        handle_parsing_errors=True,
        return_intermediate_steps=False,
    )


# ─── Main entry point (called by /agent/whatsapp endpoint) ───────────────────
async def run_whatsapp_agent(wa_contact_id: str, user_message: str) -> str:
    """
    Process an inbound WhatsApp message through the ReAct agent.
    Maintains conversation window memory in Redis (k=10).
    """
    log.info("agent.run_start", wa_id=wa_contact_id, msg_len=len(user_message))

    # Load session memory from Redis
    session = await get_session(wa_contact_id)
    chat_history_text = _format_history(session)

    agent_executor = build_agent()

    try:
        result = await agent_executor.ainvoke({
            "input": user_message,
            "chat_history": chat_history_text,
        })
        reply = result.get("output", "No pude procesar tu consulta. Intentá de nuevo.")
    except Exception as e:
        log.error("agent.run_error", wa_id=wa_contact_id, error=str(e))
        reply = "Ocurrió un error procesando tu mensaje. Un agente te contactará pronto."

    # Update session memory in Redis
    session.append({"role": "user", "content": user_message})
    session.append({"role": "assistant", "content": reply})
    await set_session(wa_contact_id, session[-10:])  # keep last k=10

    log.info("agent.run_complete", wa_id=wa_contact_id, reply_len=len(reply))
    return reply


def _format_history(session: list[dict]) -> str:
    if not session:
        return "Sin historial previo."
    lines = []
    for msg in session[-6:]:  # inject last 6 messages into prompt
        role = "Usuario" if msg["role"] == "user" else "Asistente"
        lines.append(f"{role}: {msg['content']}")
    return "\n".join(lines)
