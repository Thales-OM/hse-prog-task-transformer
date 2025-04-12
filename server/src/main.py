from fastapi import FastAPI
import uvicorn
from src.logger import LoggerFactory
from src.config import settings
from src.api.lifespan import lifespan
from src.api.routes import upload


logger = LoggerFactory.getLogger(__name__)


tags_metadata = [
    {
        "name": "upload",
        "description": "Submit quiz file to update domain configuration in database.",
    },
]

app = FastAPI(lifespan=lifespan, openapi_tags=tags_metadata)

app.include_router(upload.router, prefix="")

def main():
    uvicorn.run(app, host="0.0.0.0", port=settings.)

if __name__ == "__main__":
    main()