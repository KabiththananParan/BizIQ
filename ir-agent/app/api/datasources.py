"""app/api/datasources.py — CRUD endpoints for Data Sources (scoped to the caller)."""

from fastapi import APIRouter, Depends, HTTPException, Response

from app.models import datasource as repo
from app.schemas import DataSourceCreate, DataSourceOut, DataSourceUpdate
from app.services.auth import AuthUser, verify_token
from app.services.ir_engine import invalidate

router = APIRouter(prefix="/datasources", tags=["Data Sources"])


def _not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="Data source not found")


@router.post("", response_model=DataSourceOut, status_code=201)
def create_datasource(payload: DataSourceCreate, user: AuthUser = Depends(verify_token)):
    row = repo.create(user.user_id, payload.name, payload.description,
                      payload.content, payload.source_type)
    invalidate(user.user_id)
    return row


@router.get("", response_model=list[DataSourceOut])
def list_datasources(user: AuthUser = Depends(verify_token)):
    return repo.list_all(user.user_id)


@router.get("/{datasource_id}", response_model=DataSourceOut)
def get_datasource(datasource_id: int, user: AuthUser = Depends(verify_token)):
    row = repo.get(datasource_id, user.user_id)
    if row is None:
        raise _not_found()
    return row


@router.put("/{datasource_id}", response_model=DataSourceOut)
def update_datasource(datasource_id: int, payload: DataSourceUpdate,
                      user: AuthUser = Depends(verify_token)):
    fields = payload.model_dump(exclude_unset=True)
    if "description" in fields and fields["description"] is None:
        fields["description"] = ""          # explicit null -> empty string
    row = repo.update(datasource_id, user.user_id, fields)  # other nulls are ignored
    if row is None:
        raise _not_found()
    invalidate(user.user_id)
    return row


@router.delete("/{datasource_id}", status_code=204)
def delete_datasource(datasource_id: int, user: AuthUser = Depends(verify_token)):
    if not repo.delete(datasource_id, user.user_id):
        raise _not_found()
    invalidate(user.user_id)
    return Response(status_code=204)
