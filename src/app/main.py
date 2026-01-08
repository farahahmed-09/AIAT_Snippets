from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from src.app.core.config import settings
from src.app.api.routes import sessions, snippets

app = FastAPI(title=settings.PROJECT_NAME,
              openapi_url=f"{settings.API_V1_STR}/openapi.json")

# Set all origins enabled
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(
    sessions.router, prefix=settings.API_V1_STR, tags=["sessions"])
app.include_router(
    snippets.router, prefix=settings.API_V1_STR, tags=["snippets"])

# Static Files for output
app.mount("/output", StaticFiles(directory=settings.OUTPUT_DIR), name="output")


@app.get("/")
def root():
    return {"message": "Welcome to SmartCut AI API"}
