from langchain_ollama import OllamaLLM
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import CrossEncoderReranker
from langchain_community.cross_encoders import HuggingFaceCrossEncoder
from langchain.retrievers.document_compressors import DocumentCompressorPipeline
from langchain.retrievers.document_compressors import EmbeddingsFilter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from app.routers import llm, db, metrics
from pathlib import Path

@asynccontextmanager
async def lifespan(app: FastAPI):
    """ Server Start >> LLM, Embedding, Vectorstore memory load """
    # Definition LLM, Embedding, Vectorstore
    llm = OllamaLLM(
        model = 'gpt-oss:20b',
        temperature = 0.1
    )

    embedding = HuggingFaceEmbeddings(
        model_name = 'FronyAI/frony-embed-large-ko-v1',
        model_kwargs = {'device': 'mps'},
        encode_kwargs = {'normalize_embeddings': True}
    )

    vectorstore = Chroma(
        embedding_function = embedding,
        collection_name = 'ga_assistant',
        persist_directory = '/Users/dooohn/Project/ga_chatbot/ga_assistant_store'
    )

    retriever = vectorstore.as_retriever(search_kwargs = {'k': 3})

    # Define Cross Encoder
    CrossEncoder = HuggingFaceCrossEncoder(model_name = 'BAAI/bge-reranker-v2-m3')

    # Re-rank Compressor
    re_ranker = CrossEncoderReranker(
    model = CrossEncoder,
    top_n = 2
    )

    # EmbeddingsFilter
    EmbeddingFilter = EmbeddingsFilter(
    embeddings = embedding,
    similarity_threshold = 0.3
    )

    # Compressor Pipeline
    compressor_pipeline = DocumentCompressorPipeline(
        transformers= [re_ranker, EmbeddingFilter]
    )

    # Final retriever
    final_retriever = ContextualCompressionRetriever(
        base_compressor = compressor_pipeline,
        base_retriever = retriever
    )

    print("Resource Load Success.")

    # 의존성 주입
    app.state.llm = llm
    app.state.embedding = embedding
    app.state.vectorstore = vectorstore
    app.state.retriever = final_retriever

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