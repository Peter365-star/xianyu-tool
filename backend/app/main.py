from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.database import engine, Base
from app.models import Product, HotScore, User, CrawlTask  # noqa: F401

from app.api.auth import router as auth_router
from app.api.categories import router as categories_router
from app.api.crawl import router as crawl_router
from app.api.products import router as products_router

app = FastAPI(title="闲鱼选品工具", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "code": 500},
    )


app.include_router(auth_router)
app.include_router(categories_router)
app.include_router(crawl_router)
app.include_router(products_router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.on_event("startup")
def startup():
    # Create all tables
    Base.metadata.create_all(bind=engine)
    # start scheduler in background
    from app.tasks.scheduler import start_scheduler
    start_scheduler()


@app.on_event("shutdown")
def shutdown():
    from app.tasks.scheduler import shutdown_scheduler
    shutdown_scheduler()
