from fastapi import FastAPI
from app.api.routes import router

app = FastAPI(
    title="AI Print Estimator",
    description="Unstructured print order intake and estimation",
    version="1.0.0",
)

@app.get("/")
def health_check():
    return {"status": "AI Print Estimator API is running"}

app.include_router(router)
