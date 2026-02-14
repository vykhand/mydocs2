"""FastAPI application factory."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from lightodm import MongoConnection

from mydocs.backend.routes.cases import router as cases_router
from mydocs.backend.routes.documents import router as documents_router
from mydocs.backend.routes.search import router as search_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize MongoDB connection
    conn = MongoConnection()
    await conn.get_async_client()
    yield
    # Shutdown: close connections
    conn.close_connection()


def create_app() -> FastAPI:
    application = FastAPI(
        title="mydocs",
        description="AI-powered document parsing and information extraction",
        version="0.1.0",
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(cases_router)
    application.include_router(documents_router)
    application.include_router(search_router)

    @application.get("/health")
    async def health():
        return {"status": "ok"}

    @application.exception_handler(RequestValidationError)
    async def validation_exception_handler(request, exc):
        return JSONResponse(
            status_code=422,
            content={
                "detail": str(exc),
                "error_code": "VALIDATION_ERROR",
                "status_code": 422,
            },
        )

    @application.exception_handler(Exception)
    async def generic_exception_handler(request, exc):
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "error_code": "INTERNAL_ERROR",
                "status_code": 500,
            },
        )

    return application


app = create_app()
