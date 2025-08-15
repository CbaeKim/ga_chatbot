from pydantic import BaseModel
import ollama, os
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.responses import StreamingResponse
from fastapi import APIRouter, Depends, Query
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_ollama import OllamaLLM
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from ..dependency.db import connect_supabase
from supabase import Client
import time

# 라우터 객체 설정
router = APIRouter(
    prefix = "/request",  # 웹 페이지 path
    tags = ['Chat Bot']    # API docs에 표시될 태그
)

class user_input(BaseModel):
    """ Validation User input """
    input_text: str

@router.post('/', summary = "Language model without RAG applied")
def request_sa(input_text: user_input, model: str = 'gpt-oss:20b') -> JSONResponse:
    """ RAG가 적용되지 않은 일반 Ollama 기반 모델 """
    # Docker 환경에서 Ollama 호스트 설정
    # ollama_client = ollama.Client(host='http://ollama:11434')
    response = ollama.chat(
        model = model,
        messages =[
            {
                'role': 'system',
                'content': """
                1. 너는 기업 전용 AI 비서야.
                2. 항상 한국어로 답변해야 해.
                3. 답변은 항상 가독성 좋게 Markdown으로 구조화해서 단계적으로 답변해.
                    3-1) 앞에 요약을 작성하고, 그 다음에 상세 내용으로 작성
                    3-2) bullet point 목록의 경우 줄바꿈을 한 번만 시행
                    3-3) 예: -항목 1: 설명\n-항목 2: 설명\n결론적으로 이건 ~입니다.
                4. 답변 직전에 모든 '\n\n'을 '\n'으로 변환해.
                5. 확실하지 않은 정보는 '죄송합니다. 학습되지 않은 정보입니다.'라고 답변해.
                6. 맨 끝에 공백은 없애라.
                """
            },
            {
                'role': 'user',
                'content': input_text.input_text
            }
        ]
    )
    return JSONResponse(content = {'message': response['message']['content']})

@router.post('/rag_model', summary = 'Request RAG Model')
def request_rag(input_text: user_input, model: str = 'gpt-oss:20b') -> JSONResponse:
    """ 기본적인 RAG만 적용된 Ollama 모델 """
    # 1. LLM model
    llm = OllamaLLM(model = model, temperature = 0.1)
    # llm = OllamaLLM(model = model, temperature = 0.1, base_url = 'http://ollama:11434')

    # 2. Embedding model
    embedding = OllamaEmbeddings(model = 'bge-m3')
    # embedding = OllamaEmbeddings(model = 'bge-m3', base_url = 'http://ollama:11434')

    # 3. VectorStore
    vectorstore = Chroma(
        embedding_function = embedding,              # 임베딩 모델
        persist_directory = '/Users/dooohn/Project/ga_chatbot/app/company_assistant',
        # persist_directory = '/chroma_db/company_assistant',   # chroma db 경로 (Docker용)
        collection_name = "ga_assistant"
    )

    # 4. Retriever
    retriever = vectorstore.as_retriever(search_kwargs = {'k': 3})

    # 5. prompt
    prompt_text = """
    너는 Dooohn Corporation의 총무팀 AI 비서야.
    사용자는 너에게 Dooohn Corporation에 대한 질문을 할거야.

    [Rules]
    1. 한국어로 답변
    2. 문장 형식은 공손하게 답변하고, 주어진 [Context]를 이용해서만 답변해.
    3. 추가로 답변은 가독성 향상을 위해 Markdown으로 구조화해서 단계적으로 답변해. (단, 표로 답변하지 말 것)
    4. URL의 경우 '- 링크 : 링크 삽입' 식으로 명확하게 분리해줘.
    5. [Context]에서 직접적인 답변을 찾을 수 없고, 관련성도 낮다면 '요청하시는 내용의 확인이 어렵습니다.\n번거로우시겠지만 총무팀에 문의 부탁드립니다.\n-email: main3373@gmail.com)'로 대답해
    
    [Form]
    - 요약 : 질문에 대한 요약 답변
    - 상세 내용 : 질문에 대한 상세 답변

    [Context]: {context}

    [Question] : {input}

    [Answer] : 

    """

    prompt = ChatPromptTemplate.from_template(prompt_text)

    # 6. invoke >> llm & prompt
    combine_docs_chain = create_stuff_documents_chain(llm, prompt)

    # 7. retriever >> vectorstore search & result >> add prompt {context}
    rag_chain = create_retrieval_chain(retriever, combine_docs_chain)

    # 8. Execute Chain
    query = input_text.input_text

    # 키: 프롬프트 텍스트에 입력한 질문 매개변수, 값: 사용자가 입력한 질문
    response = rag_chain.invoke({'input': query})

    # print(f"질문: {response['input']}")
    # print(f"답변: {response['answer']}")
    return JSONResponse(content = {'message': response['answer']})

@router.get('/rag_model/lcel', summary = 'Request RAG Model apply LCEL')
def request_rag_lcel(input_text: str, model: str = 'gpt-oss:20b', db: Client = Depends(connect_supabase)) -> PlainTextResponse:
    """ LCEL이 적용된 Ollama RAG 모델 """
    # 1. LLM model
    llm = OllamaLLM(
        model = model,
        temperature = 0.1,
        # base_url = 'http://ollama:11434'  # Docker Server
    )

    # 2. Embedding model
    embedding = OllamaEmbeddings(model = 'bge-m3')
    # embedding = OllamaEmbeddings(model = 'bge-m3', base_url = 'http://ollama:11434')

    # 3. VectorStore
    vectorstore = Chroma(
        embedding_function = embedding,              # 임베딩 모델
        persist_directory = '/Users/dooohn/Project/ga_chatbot/app/company_assistant',
        # persist_directory = '/chroma_db/company_assistant',   # chroma db 경로 (Docker용)
        collection_name = "ga_assistant"
    )

    # 4. Retriever
    retriever = vectorstore.as_retriever(search_kwargs = {'k': 3})

    # 5. Context Text Definition
    context_text = """
    너는 Dooohn Corporation의 총무팀 AI 비서야.
    사용자는 너에게 Dooohn Corporation에 대한 질문을 할거야.

    [Rules]
    1. 한국어로 답변
    2. 문장 형식은 공손하게 답변하고, 주어진 [Context]를 이용해서만 답변해.
    3. 추가로 답변은 가독성 향상을 위해 Markdown으로 구조화해서 단계적으로 답변해.
    4. 표를 사용할 때는 표 앞뒤에 반드시 빈 줄을 넣어서 올바른 Markdown 형식을 유지해.
    5. URL의 경우 '- 링크 : 링크 삽입' 식으로 명확하게 분리해줘.
    6. [Context]에서 직접적인 답변을 찾을 수 없고, 관련성도 낮다면 '요청하시는 내용의 확인이 어렵습니다.\\n번거로우시겠지만 총무팀에 문의 부탁드립니다.\\n-email: main3373@gmail.com)'로 대답해
    
    [Form]
    - 요약 : 질문에 대한 요약 답변
    - 상세 내용 : 질문에 대한 상세 답변
    """
    
    # Definition Prompt Text
    prompt_text = [
        ('system', '{context_text}'),   # 컨텍스트
        ('human', '{input_text}')       # 질문
    ]

    # 1. Create Prompt
    prompt = ChatPromptTemplate.from_messages(prompt_text)

    def format_docs(docs):
        """ Merge List in string """
        return '\n\n'.join([doc.page_content for doc in docs])
    
    # 2. Retriever Chaining
    def get_input_string(x):
        """ stream() : Input type is Dictionary"""
        if isinstance(x, dict):
            return x['input_text']
        return x

    retriever_chain = RunnableLambda(get_input_string) | retriever | format_docs

    # 3. Chaining RAG
    # Input >> dict logic >> prompt >> llm >> String Parsing
    rag_chain = (
        # The input to the whole chain is a dictionary: {'input_text': '...'}
        {
            'context_text': retriever_chain,
            'input_text' : RunnableLambda(get_input_string)
        }
        | prompt
        | llm
        | StrOutputParser()
    )

    response = rag_chain.invoke(input_text)

    return PlainTextResponse(content=response, media_type="text/plain")