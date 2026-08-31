from fastapi import FastAPI
from backend.app.api.health import router as health_router


def create_app() -> FastAPI:
    app = FastAPI(title="Hosfiital API")
    app.include_router(health_router)
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
