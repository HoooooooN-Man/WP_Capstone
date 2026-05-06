from fastapi import FastAPI
from api.auth.auth import router as auth_router
from api.auth.social import router as social_router
from api.socket.internal_router import router as internal_router
from api.news.newsranking import router as news_router
from api.board.board import router as board_router
from api.users.users import router as users_router
import uvicorn

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Stock Analysis System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 실제 배포 시에는 ["http://localhost:3000"] 처럼 특정 주소만 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(auth_router)
app.include_router(internal_router)
app.include_router(news_router)
app.include_router(board_router)
app.include_router(users_router)
app.include_router(social_router)

@app.get("/")
def root():
    return {"message": "Server is running"}

if __name__ == "__main__":
    # 실행할 때 파일명 'server'와 객체명 'app' 확인
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)