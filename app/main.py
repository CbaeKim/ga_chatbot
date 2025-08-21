from langchain_ollama import OllamaLLM
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from app.routers import llm, db, metrics

@asynccontextmanager
async def lifespan(app: FastAPI):
    """ Server Start >> LLM, Embedding, Vectorstore memory load """
    # Definition LLM, Embedding, Vectorstore
    llm = OllamaLLM(model = 'gpt-oss:20b', temperature = 0.1)
    embedding = OllamaEmbeddings(model = 'bge-m3')
    vectorstore = Chroma(
        embedding_function = embedding,
        collection_name = 'ga_assistant',
        persist_directory = '/Users/dooohn/Project/ga_chatbot/app/company_assistant'
    )
    print("Resource Load Success.")

    # 의존성 주입
    app.state.llm = llm
    app.state.embedding = embedding
    app.state.vectorstore = vectorstore

    yield
    print("Server Down.")
    del llm, embedding, vectorstore

app = FastAPI(lifespan = lifespan)

app.include_router(llm.router)      # LLM 관련 라우터
app.include_router(db.router)       # DB 관련 라우터
app.include_router(metrics.router)  # Metrics 관련 라우터

# 정적 파일 디렉토리 마운트 -> 아이콘 이미지 Load
app.mount("/images", StaticFiles(directory="images"), name="images")
app.mount("/pages", StaticFiles(directory="pages"), name="pages")
app.mount("/js", StaticFiles(directory="js"), name="js")

@app.get('/', summary = "'index.html' load and display", tags = ['index.html'])
async def read_index():
    return FileResponse('./pages/index.html')