from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.routers import llm, db
import ollama
import time

app = FastAPI()

app.include_router(llm.router)  # LLM 관련 라우터
app.include_router(db.router)   # DB 관련 라우터

# 정적 파일 디렉토리 마운트 -> 아이콘 이미지 Load
app.mount("/images", StaticFiles(directory="images"), name="images")
app.mount("/pages", StaticFiles(directory="pages"), name="pages")
app.mount("/js", StaticFiles(directory="js"), name="js")

@app.get('/', summary = "'index.html' load and display", tags = ['index.html'])
async def read_index():
    return FileResponse('./pages/index.html')