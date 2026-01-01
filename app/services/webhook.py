import httpx
from typing import Dict, Any

async def send_n8n_event(event_type: str, data: Dict[str, Any], n8n_url: str):
    try:
        async with httpx.AsyncClient() as client:
            await client.post(n8n_url, json={"event": event_type, "data": data})
    except Exception as e:
        # You may want to add logging here
        pass

