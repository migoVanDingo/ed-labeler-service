from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlmodel.ext.asyncio.session import AsyncSession
from starlette.responses import RedirectResponse

from app.core.config import settings
from app.db.session import get_session
from app.services.gcs import generate_signed_url
from app.services.label_studio_client import LabelStudioClient

from platform_common.db.dal.annotation_set_dal import AnnotationSetDAL
from platform_common.db.dal.dataset_item_dal import DatasetItemDAL
from platform_common.db.dal.external_annotation_task_dal import ExternalAnnotationTaskDAL
from platform_common.db.dal.external_annotation_project_dal import (
    ExternalAnnotationProjectDAL,
)
from platform_common.db.dal.file_dal import FileDAL
from platform_common.models.external_annotation_project import ExternalAnnotationProject
from platform_common.models.external_annotation_task import ExternalAnnotationTask
from platform_common.utils.string_helpers import slugify

router = APIRouter()


class StartLabelingRequest(BaseModel):
    annotationSetId: str


class StartLabelingResponse(BaseModel):
    externalProjectId: str
    projectUrl: Optional[str]
    tasksCreated: int
    tasksTotal: int


def _default_label_config() -> str:
    return (
        "<View>"
        "<Video name=\"video\" value=\"$video\"/>"
        "<Labels name=\"label\" toName=\"video\">"
        "<Label value=\"Action\"/>"
        "</Labels>"
        "</View>"
    )


def _media_url(dataset_item_id: str) -> str:
    base = settings.PUBLIC_BASE_URL.rstrip("/")
    token = settings.LABEL_STUDIO_MEDIA_TOKEN
    return f"{base}/media/dataset-item/{dataset_item_id}?token={token}"


def _require_label_studio_settings() -> None:
    if not settings.LABEL_STUDIO_BASE_URL or not settings.LABEL_STUDIO_API_KEY:
        raise HTTPException(status_code=500, detail="Label Studio is not configured")


def _verify_shared_secret(request: Request, secret: str) -> bool:
    if not secret:
        return False
    header_secret = request.headers.get("x-label-studio-secret")
    if not header_secret:
        header_secret = request.headers.get("x-webhook-secret")
    query_secret = request.query_params.get("secret")
    return secret in {header_secret, query_secret}


@router.post("/labeling/start", response_model=StartLabelingResponse)
async def start_labeling(
    payload: StartLabelingRequest,
    session: AsyncSession = Depends(get_session),
) -> StartLabelingResponse:
    annotation_set_dal = AnnotationSetDAL(session)
    dataset_item_dal = DatasetItemDAL(session)
    task_dal = ExternalAnnotationTaskDAL(session)
    project_dal = ExternalAnnotationProjectDAL(session)

    annotation_set = await annotation_set_dal.get_by_id(payload.annotationSetId)
    if not annotation_set:
        raise HTTPException(status_code=404, detail="Annotation set not found")

    if not annotation_set.dataset_version_id:
        raise HTTPException(status_code=400, detail="Annotation set has no dataset version")

    dataset_items = await dataset_item_dal.list_by_dataset_version(
        annotation_set.dataset_version_id
    )
    tasks_total = len(dataset_items)

    project_link = await project_dal.get_by_annotation_set(annotation_set.id)

    _require_label_studio_settings()
    client = LabelStudioClient(
        base_url=settings.LABEL_STUDIO_BASE_URL,
        api_key=settings.LABEL_STUDIO_API_KEY,
    )

    if not project_link:
        label_config = settings.LABEL_STUDIO_LABEL_CONFIG or _default_label_config()
        project_name = f"{annotation_set.purpose_key}-{annotation_set.id}"
        project = await client.create_project(project_name, label_config)
        project_id = str(project.get("id"))
        project_url = project.get("url")

        project_link = ExternalAnnotationProject(
            annotation_set_id=annotation_set.id,
            external_project_id=project_id,
            project_url=project_url,
            webhook_secret=settings.LABEL_STUDIO_WEBHOOK_SECRET or None,
            config_json={"label_config": label_config},
            state="ACTIVE",
        )
        project_link = await project_dal.save(project_link)

        if settings.PUBLIC_BASE_URL and settings.LABEL_STUDIO_WEBHOOK_SECRET:
            webhook_url = f"{settings.PUBLIC_BASE_URL.rstrip('/')}/webhooks/labelstudio"
            await client.register_webhook(
                project_id=project_id,
                url=webhook_url,
                secret=settings.LABEL_STUDIO_WEBHOOK_SECRET,
            )

    tasks_created = 0
    for item in dataset_items:
        existing = await task_dal.get_by_dataset_item(annotation_set.id, item.id)
        if existing:
            continue

        task_payload: Dict[str, Any] = {"data": {"video": _media_url(item.id)}}
        external_task_id = await client.create_task(
            project_link.external_project_id,
            task_payload,
        )

        task = ExternalAnnotationTask(
            annotation_set_id=annotation_set.id,
            dataset_item_id=item.id,
            external_task_id=external_task_id,
            state="CREATED",
        )
        await task_dal.save(task)
        tasks_created += 1

    return StartLabelingResponse(
        externalProjectId=project_link.external_project_id,
        projectUrl=project_link.project_url,
        tasksCreated=tasks_created,
        tasksTotal=tasks_total,
    )


@router.get("/media/dataset-item/{dataset_item_id}")
async def media_dataset_item(
    dataset_item_id: str,
    token: Optional[str] = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> RedirectResponse:
    if not settings.LABEL_STUDIO_MEDIA_TOKEN or token != settings.LABEL_STUDIO_MEDIA_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid media token")

    if not settings.GCS_BUCKET:
        raise HTTPException(status_code=500, detail="GCS bucket is not configured")

    dataset_item_dal = DatasetItemDAL(session)
    file_dal = FileDAL(session)

    dataset_item = await dataset_item_dal.get_by_id(dataset_item_id)
    if not dataset_item:
        raise HTTPException(status_code=404, detail="Dataset item not found")

    file_obj = await file_dal.get_by_id(dataset_item.file_id)
    if not file_obj:
        raise HTTPException(status_code=404, detail="File not found")

    normalized_file_id = slugify(file_obj.id)
    object_name = (
        f"curated/datastore/{file_obj.datastore_id}/file/{file_obj.id}/source/{normalized_file_id}"
    )
    signed_url = generate_signed_url(settings.GCS_BUCKET, object_name)
    return RedirectResponse(url=signed_url, status_code=302)


@router.post("/webhooks/labelstudio")
async def label_studio_webhook(request: Request) -> Dict[str, str]:
    secret = settings.LABEL_STUDIO_WEBHOOK_SECRET
    if not _verify_shared_secret(request, secret):
        raise HTTPException(status_code=401, detail="Invalid webhook secret")

    payload = await request.json()
    # TODO: enqueue ingestion/export for annotations
    return {"status": "received", "event": str(payload.get("event", "unknown"))}
