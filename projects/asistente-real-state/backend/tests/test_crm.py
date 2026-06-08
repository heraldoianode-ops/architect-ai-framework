"""
test_crm.py — L2 unit tests for Node 3.3: CRM Kanban, FTS, interactions, stage transitions.
All DB calls are mocked with AsyncMock.
"""
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from app.models.client import Client, LeadStage, LEAD_STAGE_ORDER
from app.models.interaction import Interaction, InteractionType


# ─── LeadStage order ────────────────────────────────────────────────────────────
class TestLeadStageOrder:
    def test_order_starts_with_nuevo(self):
        assert LEAD_STAGE_ORDER[0] == LeadStage.nuevo

    def test_order_ends_before_cerrado(self):
        # cerrado is terminal — no next stage after it in LEAD_STAGE_ORDER
        assert LeadStage.cerrado == LEAD_STAGE_ORDER[-1]

    def test_perdido_not_in_order(self):
        # perdido is a side-exit, not a funnel step
        assert LeadStage.perdido not in LEAD_STAGE_ORDER

    def test_advance_from_nuevo(self):
        idx = LEAD_STAGE_ORDER.index(LeadStage.nuevo)
        assert LEAD_STAGE_ORDER[idx + 1] == LeadStage.contactado

    def test_advance_from_propuesta(self):
        idx = LEAD_STAGE_ORDER.index(LeadStage.propuesta)
        assert LEAD_STAGE_ORDER[idx + 1] == LeadStage.negociacion

    def test_no_next_after_cerrado(self):
        idx = LEAD_STAGE_ORDER.index(LeadStage.cerrado)
        assert idx == len(LEAD_STAGE_ORDER) - 1


# ─── _scope_query logic (pure unit) ──────────────────────────────────────────────
class TestScopeQuery:
    def _make_user(self, role):
        from app.models.user import User, UserRole
        u = MagicMock(spec=User)
        u.id = uuid.uuid4()
        u.role = UserRole(role)
        return u

    def test_agent_scope_applied(self):
        from app.routers.crm import _scope_query
        from sqlalchemy import select
        user = self._make_user("agente_real_state")
        stmt = _scope_query(select(Client), user)
        # The whereclause should reference agent_id
        compiled = str(stmt.compile())
        assert "agent_id" in compiled

    def test_admin_no_scope(self):
        from app.routers.crm import _scope_query
        from sqlalchemy import select
        user = self._make_user("administrador")
        stmt_unscoped = select(Client)
        stmt_scoped = _scope_query(stmt_unscoped, user)
        # Admin query should be unchanged (no extra WHERE)
        assert str(stmt_scoped.compile()) == str(stmt_unscoped.compile())


# ─── Stage transition ───────────────────────────────────────────────────────────
async def _run_update_stage(client_stage, new_stage):
    from app.routers.crm import update_stage
    from app.routers.crm import StageTransitionIn
    from app.models.user import User, UserRole

    client = MagicMock(spec=Client)
    client.id = uuid.uuid4()
    client.lead_stage = client_stage
    client.updated_at = datetime.now(timezone.utc)

    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.role = UserRole.agente_real_state

    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = client
    db.execute = AsyncMock(return_value=mock_result)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    body = StageTransitionIn(stage=new_stage)

    with patch("app.routers.crm._get_client_or_404", AsyncMock(return_value=client)):
        result = await update_stage(client.id, body, db, user)
    return result, db


@pytest.mark.asyncio
async def test_stage_transition_updates_client():
    client, db = await _run_update_stage(LeadStage.nuevo, LeadStage.contactado)
    assert client.lead_stage == LeadStage.contactado
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_same_stage_no_commit():
    """No DB write if stage unchanged."""
    from app.routers.crm import update_stage, StageTransitionIn
    from app.models.user import User, UserRole

    client = MagicMock(spec=Client)
    client.id = uuid.uuid4()
    client.lead_stage = LeadStage.contactado

    user = MagicMock(spec=User)
    user.role = UserRole.agente_real_state

    db = AsyncMock()
    body = StageTransitionIn(stage=LeadStage.contactado)

    with patch("app.routers.crm._get_client_or_404", AsyncMock(return_value=client)):
        result = await update_stage(client.id, body, db, user)

    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_advance_stage_raises_at_end():
    from fastapi import HTTPException
    from app.routers.crm import advance_stage
    from app.models.user import User, UserRole

    client = MagicMock(spec=Client)
    client.id = uuid.uuid4()
    client.lead_stage = LeadStage.cerrado  # already terminal

    user = MagicMock(spec=User)
    user.role = UserRole.agente_real_state

    db = AsyncMock()

    with patch("app.routers.crm._get_client_or_404", AsyncMock(return_value=client)):
        with pytest.raises(HTTPException) as exc_info:
            await advance_stage(client.id, db, user)

    assert exc_info.value.status_code == 400


# ─── add_interaction ────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_add_interaction_creates_record():
    from app.routers.crm import add_interaction, InteractionIn
    from app.models.user import User, UserRole

    client_id = uuid.uuid4()
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.role = UserRole.agente_real_state

    db = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()

    body = InteractionIn(interaction_type=InteractionType.note, content="Primera llamada exitosa")

    with patch("app.routers.crm._get_client_or_404", AsyncMock(return_value=MagicMock())):
        with patch("app.routers.crm.Interaction") as MockInteraction:
            mock_instance = MagicMock()
            MockInteraction.return_value = mock_instance
            await add_interaction(client_id, body, db, user)

    db.add.assert_called_once()
    db.commit.assert_awaited_once()


# ─── InteractionType coverage ──────────────────────────────────────────────────
class TestInteractionType:
    @pytest.mark.parametrize("itype", list(InteractionType))
    def test_all_types_are_strings(self, itype):
        assert isinstance(itype.value, str)

    def test_whatsapp_type_exists(self):
        assert InteractionType.whatsapp in InteractionType

    def test_visit_type_exists(self):
        assert InteractionType.visit in InteractionType
