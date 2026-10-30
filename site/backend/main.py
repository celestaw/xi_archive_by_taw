import json
import logging
import unicodedata
from pathlib import Path
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from models import ApiError, ArchiveMeta, CollectionDetail, CollectionList, CollectionSummary, Health, PublicCatalogue, PublicCollections, TimelineList, WorkContext, WorkDetail, WorkList, WorkSummary
from timeline import timeline_entry
from work_context import work_context

app = FastAPI(
    title="xi archive API", version="1.0.0",
    description="非公式作品年表。日付は確認できた公開記録であり、作曲日・真の初公開日とは限らない。",
    docs_url="/api/v1/docs", openapi_url="/api/v1/openapi.json", redoc_url=None,
    responses={422: {"model": ApiError}, 500: {"model": ApiError}},
)
data = PublicCatalogue.model_validate_json((Path(__file__).parent / "data/catalogue.json").read_text(encoding="utf-8"))
meta = data.meta
works = data.works
by_id = {w.id: w for w in works}
collection_data = PublicCollections.model_validate_json((Path(__file__).parent / "data/collections.json").read_text(encoding="utf-8"))
collections = collection_data.collections
collections_by_id = {(c.kind, c.id): c for c in collections}


def normalize(value: str) -> str:
    return unicodedata.normalize("NFKC", value).casefold()


def sort_key(work: WorkDetail):
    record = work.earliest_record
    return (record is None or record.date is None, (record.date if record else None) or "9999", work.id)


works.sort(key=sort_key)


@app.exception_handler(StarletteHTTPException)
async def http_error(request: Request, exc: StarletteHTTPException):
    code = "not_found" if exc.status_code == 404 else "invalid_request"
    return JSONResponse(status_code=exc.status_code, content={"error": {"code": code, "message": str(exc.detail)}})


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"error": {"code": "invalid_request", "message": "検索条件を確認してください。"}})


@app.exception_handler(Exception)
async def internal_error(request: Request, exc: Exception):
    logging.getLogger("xi.archive").exception("Unhandled API error", exc_info=exc)
    return JSONResponse(status_code=500, content={"error": {"code": "internal_error", "message": "記録を取得できませんでした。時間をおいてお試しください。"}})


@app.get("/api/v1/health", response_model=Health, operation_id="getHealth")
def health():
    return Health()


@app.get("/api/v1/meta", response_model=ArchiveMeta, operation_id="getMeta")
def get_meta():
    return meta


@app.get("/api/v1/timeline", response_model=TimelineList, operation_id="getTimeline")
def get_timeline():
    return TimelineList(items=[timeline_entry(work) for work in works], checked_on=meta.checked_on)


def collection_list(kind: str):
    selected = [c for c in collections if c.kind == kind]
    selected.sort(key=lambda c: (c.category != "ソロアルバム", not c.release_records or c.release_records[0].date is None,
        (c.release_records[0].date if c.release_records else "") or "9999", normalize(c.title)))
    return CollectionList(items=[CollectionSummary.model_validate(c.model_dump(include=CollectionSummary.model_fields.keys())) for c in selected])


def collection_detail(kind: str, id: str):
    collection = collections_by_id.get((kind, id))
    if collection is None:
        raise HTTPException(404, "該当する収録情報がありません。")
    return collection


@app.get("/api/v1/albums", response_model=CollectionList, operation_id="listAlbums")
def list_albums():
    return collection_list("album")


@app.get("/api/v1/albums/{album_id}", response_model=CollectionDetail, responses={404: {"model": ApiError}}, operation_id="getAlbum")
def get_album(album_id: str):
    return collection_detail("album", album_id)


@app.get("/api/v1/games", response_model=CollectionList, operation_id="listGames")
def list_games():
    return collection_list("game")


@app.get("/api/v1/games/{game_id}", response_model=CollectionDetail, responses={404: {"model": ApiError}}, operation_id="getGame")
def get_game(game_id: str):
    return collection_detail("game", game_id)


@app.get("/api/v1/works", response_model=WorkList, operation_id="listWorks")
def list_works(
    q: Annotated[str, Query(max_length=120)] = "",
    year: Annotated[int | None, Query(ge=1900, le=2100)] = None,
    date_status: Literal["all", "dated", "undated"] = "all",
    attribution: Literal["all", "credited", "unverified"] = "all",
    medium: Annotated[str | None, Query(max_length=200)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 40,
    offset: Annotated[int, Query(ge=0, le=100000)] = 0,
):
    selected = []
    term = normalize(q.strip())
    for work in works:
        record = work.earliest_record
        dated = bool(record and record.date)
        if term and term not in normalize(" ".join([work.title, *(a.title for a in work.aliases)])):
            continue
        if year is not None and (not dated or int(record.date[:4]) != year):
            continue
        if date_status == "dated" and not dated or date_status == "undated" and dated:
            continue
        if attribution != "all" and work.attribution != attribution:
            continue
        if medium is not None and not any(r.medium == medium for r in work.records):
            continue
        selected.append(work)
    return WorkList(
        items=[WorkSummary.model_validate(w.model_dump(include=WorkSummary.model_fields.keys())) for w in selected[offset:offset + limit]],
        total=len(selected), limit=limit, offset=offset,
    )


@app.get("/api/v1/works/{work_id}", response_model=WorkDetail, responses={404: {"model": ApiError}}, operation_id="getWork")
def get_work(work_id: str):
    if work_id not in by_id:
        raise HTTPException(404, "該当する作品の記録がありません。")
    return by_id[work_id]


@app.get("/api/v1/works/{work_id}/context", response_model=WorkContext, responses={404: {"model": ApiError}}, operation_id="getWorkContext")
def get_work_context(work_id: str):
    return work_context(get_work(work_id), collections, by_id)
