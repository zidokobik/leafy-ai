"""All signed-in users share access. Review is not exposed as an agent tool."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import ValidationError

from backend.db_models.ai_decisions import AIDecision
from backend.db_models.command_requests import CommandRequest
from backend.db_models.safety_rules import SafetyRule
from backend.dependencies.auth import get_current_auth_user
from backend.dependencies.database_session import AsyncDatabaseSession
from backend.schemas.ai_decisions import AIDecisionCreate, AIDecisionRead
from backend.schemas.command_requests import (
	CommandRequestCreate,
	CommandRequestRead,
	CommandReviewRequest,
	CommandStatus,
)
from backend.schemas.safety_rules import SafetyRuleRead, SafetyRuleWrite
from backend.schemas.user import AuthenticatedUser
from backend.services import safety
from backend.services import safety_records as records

router = APIRouter(tags=["safety"], dependencies=[Depends(get_current_auth_user)])
Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]


async def _respond(operation):
	try:
		return await operation
	except safety.SafetyNotFoundError as error:
		raise HTTPException(404, str(error)) from error
	except safety.SafetyConflictError as error:
		raise HTTPException(409, str(error)) from error
	except ValidationError as error:
		raise HTTPException(422, "Invalid or expired request parameters.") from error


@router.get("/safety-rules", response_model=list[SafetyRuleRead])
async def list_rules(
	session: AsyncDatabaseSession, device_id: UUID | None = None, limit: Limit = 50, offset: Offset = 0
):
	return await records.list_rules(session, device_id, limit, offset)


@router.post("/safety-rules", response_model=SafetyRuleRead, status_code=201)
async def create_rule(payload: SafetyRuleWrite, session: AsyncDatabaseSession):
	return await _respond(records.save_rule(session, **payload.model_dump()))


@router.get("/safety-rules/{rule_id}", response_model=SafetyRuleRead)
async def get_rule(rule_id: UUID, session: AsyncDatabaseSession):
	return await _respond(records.get_record(session, SafetyRule, rule_id))


@router.put("/safety-rules/{rule_id}", response_model=SafetyRuleRead)
async def update_rule(rule_id: UUID, payload: SafetyRuleWrite, session: AsyncDatabaseSession):
	return await _respond(records.save_rule(session, rule_id=rule_id, **payload.model_dump()))


@router.delete("/safety-rules/{rule_id}", status_code=204)
async def delete_rule(rule_id: UUID, session: AsyncDatabaseSession):
	await _respond(records.delete_rule(session, rule_id))


@router.get("/ai-decisions", response_model=list[AIDecisionRead])
async def list_decisions(
	session: AsyncDatabaseSession, schedule_id: UUID | None = None, limit: Limit = 50, offset: Offset = 0
):
	return await records.list_decisions(session, schedule_id, limit, offset)


@router.post("/ai-decisions", response_model=AIDecisionRead, status_code=201)
async def create_decision(payload: AIDecisionCreate, session: AsyncDatabaseSession):
	return await _respond(records.create_decision(session, **payload.model_dump()))


@router.get("/ai-decisions/{decision_id}", response_model=AIDecisionRead)
async def get_decision(decision_id: UUID, session: AsyncDatabaseSession):
	return await _respond(records.get_record(session, AIDecision, decision_id))


@router.get("/command-requests", response_model=list[CommandRequestRead])
async def list_commands(
	session: AsyncDatabaseSession,
	device_id: UUID | None = None,
	decision_id: UUID | None = None,
	status: CommandStatus | None = None,
	limit: Limit = 50,
	offset: Offset = 0,
):
	return await records.list_commands(session, device_id, decision_id, status, limit, offset)


@router.post("/command-requests", response_model=CommandRequestRead, status_code=201)
async def create_command(payload: CommandRequestCreate, session: AsyncDatabaseSession):
	return await _respond(safety.create_command_request(session, **payload.model_dump()))


@router.get("/command-requests/{request_id}", response_model=CommandRequestRead)
async def get_command(request_id: UUID, session: AsyncDatabaseSession):
	return await _respond(records.get_record(session, CommandRequest, request_id))


@router.post(
	"/command-requests/{request_id}/review",
	response_model=CommandRequestRead,
	description="Approve or reject as the signed-in user. Rechecks safety; never executes hardware.",
)
async def review_command(
	request_id: UUID,
	payload: CommandReviewRequest,
	session: AsyncDatabaseSession,
	current_user: Annotated[AuthenticatedUser, Depends(get_current_auth_user)],
):
	return await _respond(safety.review_command_request(session, request_id, current_user.id, payload.action))
