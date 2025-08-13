import ollama, os
from langchain_community.document_loaders import TextLoader
from langchain_core.documents import Document
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Set Gemini API KEY
genai.configure(api_key = os.getenv('GEMINI_API_KEY'))

def request_gem(text: str, prompt: str, model: str = 'gemini-2.5-flash') -> str:
    """ Get Reponse from Gemini """
    client = genai.GenerativeModel(model)

    contents = [
        {
            'role': 'user',
            'parts': [f'{prompt}\n\n요청사항: {text}']
        }
    ]

    response = client.generate_content(
        contents = contents
    )

    return response.text

def request_sa(text: str, model: str = 'gpt-oss:20b') -> str:
    """ Get Reponse sentimental-analysis """
    response = ollama.chat(
        model = 'gpt-oss:20b',
        messages =[
            {
                'role': 'system',
                'content': """
                1. 텍스트 감성분석 전문가야.
                2. 주식 뉴스 기사 감성분석을 수행해줘.
                3. 답변의 자유도는 절대 아래의 예시폼에서 벗어나서는 안 돼
                ```json{'positive': 0.6, 'negative': 0.4}```
                4. 답변을 주기 전에 네 답변을 한 번 더 검증 후 답변해줘.
                """
            },
            {
                'role': 'user',
                'content': text
            }
        ]
    )
    return response['message']['content']

def text_embedding(text, model: str = 'bge-m3') -> list:
    """ Single Text embedding for RAG """
    response = ollama.embeddings(
        model = 'bge-m3',   # 모델명
        prompt = text       # 임베딩 텍스트
    )
    
    return response['embedding']

def texts_embedding(text_data, model: str = 'bge-m3'):
    """ Multi Text iterrable data embedding for RAG """
    # input type : Document Object
    if isinstance(text_data[0], Document):
        embedding_results = []
        for i in range(len(text_data)):
            embedding_results.append(text_embedding(text_data[i].page_content))
        return embedding_results
    
    # input type : str List
    elif isinstance(text_data[0], str):
        responses = [text_embedding(text, model) for text in text_data]
        return responses
    
def load_parent_directory():
    """ load the parent directory to access libraries """
    try:
        # envirionment '*.ipynb'
        current_dir = os.getcwd()
        parent_dir = os.path.dirname(current_dir)
        sys.path.append(parent_dir)
        return print("Success: '*.ipynb'")
    except:
        # environment '*.py'
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)
        sys.path.append(parent_dir)
        return print("Success: '*.py'")