import time
import pandas as pd
from typing import List, Dict
from dotenv import load_dotenv
from fastapi import APIRouter
from langchain.evaluation import load_evaluator, EvaluatorType, EmbeddingDistance
from langchain_openai import ChatOpenAI
from sentence_transformers import CrossEncoder
from korouge_score import rouge_scorer

load_dotenv()

router = APIRouter(
    prefix = "/metrics",    # 웹 페이지 path
    tags = ['Metrics']      # API docs에 표시될 태그
)

# Evaluator Object
embedding_evaluator = load_evaluator(
    evaluator = EvaluatorType.EMBEDDING_DISTANCE,               # 임베딩 거리 기반 평가
    distance_metric = EmbeddingDistance.COSINE,                 # 거리 측정 : 코사인 거리 기반
    llm = ChatOpenAI(model = 'gpt-4o-mini', temperature = 0.3)  # 추론에 사용될 LLM
)

# Cross Encoder Model
cross_encoder = CrossEncoder('BAAI/bge-reranker-v2-m3')

@router.get('/embedding_distance', summary = 'Embedding Evaluator: COSINE Distance')
async def evaluate_embedding(df, query_col: str, label_col: str, chain, time_delay = None) -> dict:
    """
    설명: Query(feature), Label이 있는 데이터프레임을 읽어 모델에 Query를 입력 후 생성한 답변을 평가

    - df : Pandas DataFrame
    - query_col : 쿼리가 저장된 컬럼
    - label_col : 쿼리에 대한 정답이 담긴 컬럼
    - evaluator : 평가 객체
    - chain : RAG Chain
    """

    scores = []

    for i in range(len(df)):
        # Extract query & label
        query = df.iloc[i][query_col]
        label = df.iloc[i][label_col]

        # Execute prediction
        predict = chain.invoke(query)

        # Calculate score
        score = embedding_evaluator.evaluate_strings(prediction = predict, reference = label)
        extracted_score = round(score['score'], 5)
        
        # Floating point processing
        if extracted_score == 0.0:
            extracted_score = 0.0

        scores.append(extracted_score)
        
        # API TPM Limit
        if time_delay is not None:
            time.sleep(time_delay)
    
    scores_dict = {'score': scores}

    return scores_dict

@router.get('/cross_encoder', summary = 'Evaluate Cross Encoder')
async def evaluate_cross_encoder(label: str, predict: str):
    """ Calculate cross encoder similarity score in Single Text """
    cross_encoder = CrossEncoder('BAAI/bge-reranker-v2-m3')

    sentence_pairing = [[label, predict]]

    scores = cross_encoder.predict(sentence_pairing)

    return scores[0]

@router.get('/Rouge', summary = 'Calculate Rouge Metrics')
def calculate_rouge_similarity(label: str, predict: str, rouge_types: List[str] = ['rouge1', 'rouge2', 'rougeL']) -> Dict[str, float]:
    """
    Rouge Metric을 계산
    - Rouge-1 : 단어 수준의 일치도 (문맥, 단어 순서 고려 X)
    - Rouge-2 : 단어의 쌍 일치도 (단어 순서(문맥)를 일부 반영)
    - Rouge-L : 문장의 구조, 흐름 일치도 (단어의 순서 고려 O, 연속성 고려 X)
    """
    
    # Validate input 'rouge_types'
    valid_rouge_types = set(['rouge1', 'rouge2', 'rougeL'])
    rouge_types = [input_rouge for input_rouge in rouge_types if input_rouge in valid_rouge_types]

    if not rouge_types:
        raise ValueError("Invalid ROUGE type")
    
    # Definition Rouge Calculator
    scorer = rouge_scorer.RougeScorer(rouge_types, use_stemmer = True)

    # Calculate Rouge metrics
    scores = scorer.score(label, predict)

    return {rouge_type: scores[rouge_type]for rouge_type in rouge_types}