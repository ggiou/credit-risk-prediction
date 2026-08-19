"""FastAPI 애플리케이션을 생성하고 내부 예측 라우터를 등록한다."""

from fastapi import FastAPI

from app.api.prediction import router as prediction_router


def create_app() -> FastAPI:
    """신용카드 연체 위험 AI 서버 애플리케이션을 생성한다."""

    # 문서 경로는 내부 개발 확인용이며 운영 네트워크에서는 외부에 노출하지 않는다.
    application = FastAPI(
        title="신용카드 연체 위험 AI 서버",
        version="0.1.0",
        docs_url="/internal/docs",
        openapi_url="/internal/openapi.json",
    )
    application.include_router(prediction_router)
    return application


app = create_app()

