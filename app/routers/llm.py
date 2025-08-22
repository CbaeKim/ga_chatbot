from pydantic import BaseModel, field_validator
from dotenv import load_dotenv
from pathlib import Path
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi import APIRouter, Depends, Query, Request
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import CrossEncoderReranker
from langchain_community.cross_encoders import HuggingFaceCrossEncoder
from langchain.retrievers.document_compressors import DocumentCompressorPipeline
from langchain.retrievers.document_compressors import EmbeddingsFilter
from langchain_huggingface import HuggingFaceEmbeddings
from ..dependency.db import connect_supabase
from supabase import Client
from typing import List, Dict, Any, Optional, Union
import time, json, os

# 라우터 객체 설정
router = APIRouter(
    prefix = "/request",  # 웹 페이지 path
    tags = ['Chat Bot']    # API docs에 표시될 태그
)

# Gemini API KEY
load_dotenv()
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Root path
root_path = Path.cwd()

# Pydantic
class ChatRequest(BaseModel):
    """ Validation User input """
    input_text: str                  # User Input Text
    history: Optional[Any] = None    # receive json from javascript

@router.get('/gemini', summary = 'Request Gemini Model')
def request_gemini(input_text: str, model: str = 'gemini-2.5-flash', api_key = GEMINI_API_KEY, request_delay = None):

    # Definition model object
    llm = ChatGoogleGenerativeAI(
        model = model,              # model name
        google_api_key = api_key,   # API KEY
        temperature = 0.5,
        max_output_tokens = 2048
    )

    if request_delay is not None:
        time.sleep(request_delay)

    return llm.invoke(input_text)

def format_docs(docs):
    """ Merge List in string """
    return '\n\n'.join([doc.page_content for doc in docs])

@router.post('/rag_model/lcel', summary = 'Request RAG Model apply LCEL')
def request_rag_lcel(request: Request, chat_request: ChatRequest, model: str = 'gpt-oss:20b', db: Client = Depends(connect_supabase)) -> PlainTextResponse:
    """ LCEL이 적용된 Ollama RAG 모델 """
    input_text = chat_request.input_text
    history = chat_request.history
    if isinstance(history, list):
        if len(history) > 0:
            print(history)
        else:
            print(f"history is empty")

    # 1. Dependency injection: llm, embedding, vectorstore
    llm = request.app.state.llm
    embedding = request.app.state.embedding
    vectorstore = request.app.state.vectorstore

    # 2. Retriever: Contextual Compressor -> Cross Encoder Reranker + EmbeddingsFilter
    retriever = vectorstore.as_retriever(search_kwargs={'k': 2})

    # Define Cross Encoder
    CrossEncoder = HuggingFaceCrossEncoder(model_name = 'BAAI/bge-reranker-v2-m3')
    
    # 2-1. Re-rank Compressor
    re_ranker = CrossEncoderReranker(
    model = CrossEncoder,
    top_n = 2
    )

    # 2-2. EmbeddingsFilter
    EmbeddingFilter = EmbeddingsFilter(
    embeddings = embedding,
    similarity_threshold = 0.3
    )

    # 2-3. Compressor Pipeline
    compressor_pipeline = DocumentCompressorPipeline(
        transformers= [re_ranker, EmbeddingFilter]
    )

    # 2-4. Final retriever
    final_retriever = ContextualCompressionRetriever(
        base_compressor = compressor_pipeline,
        base_retriever = retriever
    )
    
    # 3. Load Prompt text -> loaded_prompt: str
    loaded_prompt = ""

    try:
        file_path = root_path / 'prompt' / 'llm_context.txt'
        with open(file_path, 'r', encoding = 'utf-8') as f:
            loaded_prompt = f.read()    # Load Prompt Text

    except FileNotFoundError:
        print(f"Error: {file_path} not found")

    except Exception as e:
        print(f"Error: {e}")

    # 4. Load Chat History -> history_context: str
    history_context = ""

    try:
        if history and len(history) > 0:
            print(f"Load history: {len(history)}EA")

            history_context = "\n\n[Previous Conversation History]\n"
            # 최근 5개 대화만 사용
            for conv in history[-5:]:
                history_context += f"USER: {conv.get('user', '')}\n"
                history_context += f"AI Response: {conv.get('assistant', '')}\n\n"
        else:
            print("history is None")
            
    except json.JSONDecodeError:
        print(f"Failed parse history, execute empty history")

    # 5. Create Prompt
    prompt_text = loaded_prompt   # Variable name: history_context, context, user_input

    prompt = ChatPromptTemplate.from_template(prompt_text)

    # 7. Retriever Chaining
    def get_input_string(x):
        """ If input type is dictionary """
        if isinstance(x, dict):
            return x['input_text']
        return x
    
    retriever_chain = RunnableLambda(get_input_string) | final_retriever | format_docs

    # 8. Chaining RAG
    rag_chain = (
        # key: llm_context.txt variables, value: value
        {
            'history_context': RunnableLambda(lambda x: history_context),
            'context': retriever_chain,
            'user_input': RunnablePassthrough()
        }
        | prompt
        | llm
        | StrOutputParser()
    )

    response = rag_chain.invoke({'input_text': input_text})

    return PlainTextResponse(content=response, media_type="text/plain")
