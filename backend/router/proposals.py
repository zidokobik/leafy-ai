from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.dependencies.auth import get_current_auth_user
from backend.dependencies.database_session import AsyncDatabaseSession
from backend.schemas.proposals import ProposalRead, ProposalStatus
from backend.schemas.user import AuthenticatedUser
from backend.services import outlets
from backend.services import proposals as proposal_service

router = APIRouter(prefix="/proposals", tags=["proposals"], dependencies=[Depends(get_current_auth_user)])

CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_auth_user)]


def _http_error(error: Exception) -> HTTPException:
	if isinstance(error, proposal_service.ProposalNotFoundError):
		return HTTPException(404, str(error))
	return HTTPException(409, str(error))


ProposalErrors = (proposal_service.ProposalNotFoundError, proposal_service.ProposalConflictError)


@router.get(
	"",
	response_model=list[ProposalRead],
	description="Device run proposals, newest first. Repeat `status` to match several statuses.",
)
async def list_proposals(
	session: AsyncDatabaseSession,
	status: Annotated[list[ProposalStatus] | None, Query()] = None,
	limit: Annotated[int, Query(ge=1, le=100)] = 50,
	offset: Annotated[int, Query(ge=0)] = 0,
):
	return await proposal_service.list_proposals(session, status, limit, offset)


@router.post(
	"/{proposal_id}/approve",
	response_model=ProposalRead,
	description="Approve a pending proposal and switch the device on now. "
	"If the powerboard fails, the proposal is returned with status `failed`.",
)
async def approve_proposal(proposal_id: UUID, session: AsyncDatabaseSession, user: CurrentUser):
	try:
		return await proposal_service.approve(session, proposal_id, user.id)
	except ProposalErrors as error:
		raise _http_error(error) from error


@router.post("/{proposal_id}/reject", response_model=ProposalRead, description="Reject a pending proposal.")
async def reject_proposal(proposal_id: UUID, session: AsyncDatabaseSession, user: CurrentUser):
	try:
		return await proposal_service.reject(session, proposal_id, user.id)
	except ProposalErrors as error:
		raise _http_error(error) from error


@router.post(
	"/{proposal_id}/stop",
	response_model=ProposalRead,
	description="Switch a running device off before its run ends. Returns 502 if the powerboard cannot be reached.",
)
async def stop_proposal(proposal_id: UUID, session: AsyncDatabaseSession, user: CurrentUser):
	try:
		return await proposal_service.stop(session, proposal_id, user.id)
	except ProposalErrors as error:
		raise _http_error(error) from error
	except outlets.PowerboardError as error:
		raise HTTPException(502, str(error)) from error
