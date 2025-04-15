from fastapi import FastAPI, status, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import httpx
from pathlib import Path
from src.logger import LoggerFactory
from src.config import settings
from src.api.lifespan import lifespan
from src.api.routes import upload, health, pages, read, root


logger = LoggerFactory.getLogger(__name__)


tags_metadata = [
    {
        "name": "upload",
        "description": "Submit new quiz file to the database",
    },
    {
        "name": "health",
        "description": "Server health stats",
    },
    {
        "name": "read",
        "description": "Read database contents",
    },
    {
        "name": "pages",
        "description": "Development pages",
    },
]

app = FastAPI(lifespan=lifespan, openapi_tags=tags_metadata)

BASE_DIR = Path(__file__).parent.parent

# Mount static files
app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "static")),
    name="static"
)

app.include_router(root.router, prefix="")
app.include_router(upload.router, prefix="/upload")
app.include_router(health.router, prefix="/health")
app.include_router(read.router, prefix="/read")
app.include_router(pages.router, prefix="/pages")


def main():
    uvicorn.run(app, host="0.0.0.0", port=settings.server.port)


if __name__ == "__main__":
    main()