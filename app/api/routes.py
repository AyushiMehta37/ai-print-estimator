from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Request, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db, get_latest_estimate, get_order_with_relations, update_order_status
from app.services.estimator import EstimationError, estimate_pipeline
from app.services.extractor import describe_image_async, extract_text_from_pdf_async
from app.services.webhook import send_n8n_event

router = APIRouter()


class EstimateRequest(BaseModel):
    input: str
    input_type: str


class EstimateResponse(BaseModel):
    order_id: int
    specs: dict
    pricing: dict
    validation: dict


class StatusUpdateRequest(BaseModel):
    status: str


def _get_n8n_url(request: Request) -> str | None:
    """Extract n8n webhook URL from request headers."""
    return request.headers.get("x-n8n-webhook-url") if request else None


def _trigger_webhook(background_tasks: BackgroundTasks, event: str, data: dict, n8n_url: str):
    """Trigger n8n webhook in background."""
    if background_tasks and n8n_url:
        background_tasks.add_task(send_n8n_event, event, data, n8n_url)


@router.post("/estimate", response_model=EstimateResponse)
async def estimate_order(
    payload: EstimateRequest,
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = None,
    request: Request = None,
):
    """Process text input for print order estimation."""
    try:
        result = await estimate_pipeline(payload.input, payload.input_type, db)
        _trigger_webhook(background_tasks, "estimate_created", result, _get_n8n_url(request))
        return result
    except EstimationError as e:
        return EstimateResponse(order_id=0, specs={}, pricing={}, validation={"error": str(e)})
    except Exception as e:
        return EstimateResponse(order_id=0, specs={}, pricing={}, validation={"error": f"Internal server error: {str(e)}"})


@router.post("/estimate/upload", response_model=EstimateResponse)
async def estimate_order_upload(
    file: UploadFile = File(...),
    input_type: str = Form(...),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = None,
    request: Request = None,
):
    """Process uploaded PDF/image files for estimation."""
    try:
        contents = await file.read()

        if input_type == "pdf":
            text = await extract_text_from_pdf_async(contents)
        elif input_type == "image":
            text = await describe_image_async(contents)
        else:
            return EstimateResponse(order_id=0, specs={}, pricing={}, validation={"error": "Unsupported file type"})

        result = await estimate_pipeline(text, input_type, db)
        _trigger_webhook(background_tasks, "estimate_uploaded", result, _get_n8n_url(request))
        return result
    except EstimationError as e:
        return EstimateResponse(order_id=0, specs={}, pricing={}, validation={"error": str(e)})
    except Exception as e:
        return EstimateResponse(order_id=0, specs={}, pricing={}, validation={"error": f"File upload failed: {str(e)}"})


@router.get("/orders/{order_id}")
def get_order(order_id: int, db: Session = Depends(get_db)):
    """Retrieve complete order details and audit trail."""
    try:
        order = get_order_with_relations(db, order_id)
        if not order:
            return {"error": f"Order {order_id} not found"}

        estimate = get_latest_estimate(db, order_id)
        return {
            "order_id": order.id,
            "status": order.status,
            "specs": order.extracted_specs,
            "validation": order.validation_flags,
            "estimate": estimate.pricing if estimate else None,
            "audit": [
                {
                    "action": a.action,
                    "actor": a.actor,
                    "created_at": a.created_at.isoformat(),
                    "notes": a.notes,
                }
                for a in order.audits
            ],
        }
    except Exception as e:
        return {"error": f"Internal server error: {e}"}


@router.post("/orders/{order_id}/status")
def update_order_status_endpoint(
    order_id: int,
    payload: StatusUpdateRequest,
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = None,
    request: Request = None,
):
    """Update order status via n8n webhook."""
    try:
        order = update_order_status(db, order_id, payload.status, actor="api")
        if not order:
            return {"error": f"Order {order_id} not found"}

        _trigger_webhook(
            background_tasks,
            "order_status_updated",
            {"order_id": order_id, "status": order.status},
            _get_n8n_url(request)
        )
        return {"success": True, "order_id": order_id, "new_status": order.status}
    except Exception as e:
        return {"error": f"Internal server error: {e}"}
