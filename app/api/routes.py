from fastapi import APIRouter, BackgroundTasks, File, Form, Request, UploadFile
from pydantic import BaseModel

router = APIRouter()


# ---------- Request / Response Models ----------


class EstimateRequest(BaseModel):
    input: str
    input_type: str  # text | pdf | image


class EstimateResponse(BaseModel):
    order_id: int
    specs: dict
    pricing: dict
    validation: dict


class StatusUpdateRequest(BaseModel):
    status: str  # pending | review | approved | rejected


# ---------- Endpoints ----------

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.estimator import EstimationError, estimate_pipeline


@router.post("/estimate", response_model=EstimateResponse)
async def estimate_order(
    payload: EstimateRequest,
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = None,
    request: Request = None,
):
    """
    Intake unstructured input → extract → price → validate → store → return JSON
    """
    try:
        result = await estimate_pipeline(payload.input, payload.input_type, db)
        # Trigger webhook in background (n8n integration)
        if background_tasks:
            from app.services.webhook import send_n8n_event

            n8n_url = request.headers.get("x-n8n-webhook-url") if request else None
            if n8n_url:
                background_tasks.add_task(
                    send_n8n_event, "estimate_created", result, n8n_url
                )
        return result
    except EstimationError as e:
        return EstimateResponse(
            order_id=0, specs={}, pricing={}, validation={"error": str(e)}
        )
    except Exception as e:
        return EstimateResponse(
            order_id=0,
            specs={},
            pricing={},
            validation={"error": f"Internal server error: {str(e)}"},
        )


@router.post("/estimate/upload", response_model=EstimateResponse)
async def estimate_order_upload(
    file: UploadFile = File(...),
    input_type: str = Form(...),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = None,
    request: Request = None,
):
    """
    Upload PDF/image for extraction/estimation pipeline.
    """
    try:
        contents = await file.read()
        text = None
        if input_type == "pdf":
            from app.services.extractor import extract_text_from_pdf_async

            text = await extract_text_from_pdf_async(contents)
        elif input_type == "image":
            from app.services.extractor import describe_image_async

            text = await describe_image_async(contents)
        else:
            return EstimateResponse(
                order_id=0,
                specs={},
                pricing={},
                validation={"error": "Unsupported file type for upload."},
            )
        # Use the async pipeline
        result = await estimate_pipeline(text, input_type, db)
        # n8n integration
        if background_tasks:
            from app.services.webhook import send_n8n_event

            n8n_url = request.headers.get("x-n8n-webhook-url") if request else None
            if n8n_url:
                background_tasks.add_task(
                    send_n8n_event, "estimate_uploaded", result, n8n_url
                )
        return result
    except EstimationError as e:
        return EstimateResponse(
            order_id=0, specs={}, pricing={}, validation={"error": str(e)}
        )
    except Exception as e:
        return EstimateResponse(
            order_id=0,
            specs={},
            pricing={},
            validation={"error": f"File upload/pipeline failed: {str(e)}"},
        )


@router.get("/orders/{order_id}")
def get_order(order_id: int, db: Session = Depends(get_db)):
    """
    Fetch order, estimates, and audit trail
    """
    try:
        from app.database import get_latest_estimate, get_order_with_relations

        order = get_order_with_relations(db, order_id)
        if not order:
            return {"error": f"Order with id {order_id} not found"}
        estimate = get_latest_estimate(db, order_id)
        # You may want to serialize using a schema in production
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
def update_order_status(
    order_id: int,
    payload: StatusUpdateRequest,
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = None,
    request: Request = None,
):
    """
    n8n webhook to update order status
    """
    try:
        from app.database import update_order_status

        order = update_order_status(db, order_id, payload.status, actor="api")
        if not order:
            return {"error": f"Order with id {order_id} not found"}
        # Send status update event to n8n
        if background_tasks:
            from app.services.webhook import send_n8n_event

            n8n_url = request.headers.get("x-n8n-webhook-url") if request else None
            if n8n_url:
                background_tasks.add_task(
                    send_n8n_event,
                    "order_status_updated",
                    {"order_id": order_id, "status": order.status},
                    n8n_url,
                )
        return {"success": True, "order_id": order_id, "new_status": order.status}
    except Exception as e:
        return {"error": f"Internal server error: {e}"}
