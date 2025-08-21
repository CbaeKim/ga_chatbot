from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi import APIRouter, Depends, Query, Request
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
from ..dependency.db import connect_supabase
from supabase import Client
import time, json, os

# 라우터 객체 설정
router = APIRouter(
    prefix = "/request",  # 웹 페이지 path
    tags = ['Chat Bot']    # API docs에 표시될 태그
)

load_dotenv(dotenv_path = '../../.env')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

class user_input(BaseModel):
    """ Validation User input """
    input_text: str

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


@router.get('/rag_model/lcel', summary = 'Request RAG Model apply LCEL')
def request_rag_lcel(request: Request, input_text: str, history: str = Query(None), model: str = 'gpt-oss:20b', db: Client = Depends(connect_supabase)) -> PlainTextResponse:
    """ LCEL이 적용된 Ollama RAG 모델 """
    # History Parse & Add history to context
    chat_history = []
    history_context = ""
    
    # Parse Chat history
    if history:
        try:
            chat_history = json.loads(history)
            print(f"Load history: {len(chat_history)}EA")
        except json.JSONDecodeError:
            print(f"Failed parse history, execute empty history")
            chat_history = []
    
    # if exist chat history, add history context
    if chat_history:
        history_context = "\n\n[Previous Conversation History]\n"
        # 최근 5개 대화만 사용
        for conv in chat_history[-5:]:
            history_context += f"사용자: {conv.get('user', '')}\n"
            history_context += f"AI 답변: {conv.get('assistant', '')}\n\n"

    # 1. Dependency injection: llm, embedding, vectorstore
    llm = request.app.state.llm
    embedding = request.app.state.embedding
    vectorstore = request.app.state.vectorstore

    # 2. Retriever
    retriever = vectorstore.as_retriever(search_kwargs={'k': 3})
    
    # 3. Definition Prompt text
    context_text = f"""
    네 이름은 'GA Assistant'야.
    - 직무 : Dooohn Corporation의 총무팀 AI 비서

    사용자는 너에게 Dooohn Corporation에 대한 질문을 할거야.

    [Rules]
    1. 한국어로 답변
    2. 문장 형식은 공손하게 답변하고, 주어진 [Context]를 이용해서만 답변해.
    3. 추가로 답변은 가독성 향상을 위해 Markdown으로 구조화해서 단계적으로 답변해.
    4. 표를 사용할 때는 표 앞뒤에 반드시 빈 줄을 넣어서 올바른 Markdown 형식을 유지해.
    5. URL의 경우 '- 링크 : 링크 삽입' 식으로 명확하게 분리해줘.
    6. [Context]에서 직접적인 답변을 찾을 수 없고, 관련성도 낮다면 '요청하시는 내용의 확인이 어렵습니다.\\n번거로우시겠지만 총무팀에 문의 부탁드립니다.\\n-email: main3373@gmail.com)'로 대답해
    7. [Previous Conversation History]에서 이전 대화 내용을 참고하여 맥락에 맞는 답변을 제공해. (히스토리가 없다면 비어있음)
    
    [Form]
    - 요약 : 질문에 대한 요약 답변
    - 상세 내용 : 질문에 대한 상세 답변
    
    {history_context}
    """

    # 4. Definition Prompt Text
    prompt_text = [
        ('system', '{context_text}'),   # 컨텍스트
    ]
    
    # 5. Add chat history to prompt
    for message in chat_history:
        if message.get('role') == 'user':
            prompt_text.append(('human', message.get('content')))
        elif message.get('role') == 'assistant':
            prompt_text.append(('ai', message.get('content')))

    prompt_text.append(('human', '{input_text}')) # 질문

    # 6. Create Prompt
    prompt = ChatPromptTemplate.from_messages(prompt_text)

    def format_docs(docs):
        """ Merge List in string """
        return '\n\n'.join([doc.page_content for doc in docs])
    
    # 7. Retriever Chaining
    def get_input_string(x):
        """ stream() : Input type is Dictionary"""
        if isinstance(x, dict):
            return x['input_text']
        return x

    retriever_chain = RunnableLambda(get_input_string) | retriever | format_docs

    # 8. Chaining RAG
    # Input >> dict logic >> prompt >> llm >> String Parsing
    rag_chain = (
        # The input to the whole chain is a dictionary: {'input_text': '...'}
        {
            'context_text': retriever_chain,
            'input_text': RunnableLambda(get_input_string)
        }
        | prompt
        | llm
        | StrOutputParser()
    )

    response = rag_chain.invoke({'input_text': input_text})

    return PlainTextResponse(content=response, media_type="text/plain")
