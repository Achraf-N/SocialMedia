from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.controllers import (
    auth_controller,
    category_controller,
    order_controller,
    product_controller,
    shop_controller,
)
from app.core.config import settings
from app.core.database import create_indexes

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    create_indexes()


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(auth_controller.router, prefix="/api")
app.include_router(shop_controller.router, prefix="/api")
app.include_router(product_controller.router, prefix="/api")
app.include_router(category_controller.router, prefix="/api")
app.include_router(order_controller.router, prefix="/api")
