import os
import pandas as pd
from glob import glob
from datetime import datetime
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from langchain_core.documents import Document
from supabase import Client, create_client
from dotenv import load_dotenv
from typing import List

load_dotenv()

# Set SUPABASE API
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_API_KEY = os.getenv('SUPABASE_API_KEY')

supabase: Client = create_client(SUPABASE_URL, SUPABASE_API_KEY)

def request_table(table_name, col_name = '*', db = supabase) -> pd.DataFrame:
    """ Get All Rows in supabase table"""
    all_data = []
    page_size = 1000
    page = 0

    while True:
        start_index = page * page_size
        end_index = start_index + page_size - 1

        response = supabase.from_(table_name).select(col_name).range(start_index, end_index).execute()

        data = response.data

        if not data:
            print("[Alert] No Data in table")

        all_data.extend(data)

        # 가져온 데이터가 페이지 크기보다 작으면 마지막 페이지이므로 종료
        if len(data) < page_size:
            print("[Alert] All data get Success")
            break

        page += 1

    df = pd.DataFrame(all_data)

    return df

def text_files_to_docs(path, pattern: str = '*.txt') -> List[Document]:
    """ Load '.txt' files and add metadata """
    text_files = glob(os.path.join(path, pattern))
    today = datetime.today().strftime("%Y-%m-%d")
    
    data = []

    for file in text_files:
        loader = TextLoader(file, encoding = 'utf-8')
        doc = loader.load()[0]                          # Extract Document
        file_name = os.path.basename(file)              # Extract file name
        doc.metadata['file_name'] = file_name           # Add metadata: file_name
        doc.metadata['date'] = today                    # Add metadata: date
        data.append(doc)
    
    return data

def docs_text_split(docs: list, size: int, overlap: int, separator: str = '', db = None) -> List[Document]:
    """
    1. Request DB: latest 'doc_id'
    2. Run Text Split
    3. Insert the latest doc_id into the metadata
    """
    df = request_table(table_name = 'vectorstore', col_name = 'doc_id', db = db)
    
    # Extract latest 'doc_id'
    try:
        df['doc_id'] = df['doc_id'].astype(int)
        max_doc_id = int(df['doc_id'].max())
        start_insert_doc_id = max_doc_id + 1
    except:
        start_insert_doc_id = 1

    # Run Text split
    splitter = RecursiveCharacterTextSplitter(
        chunk_size = size,
        chunk_overlap = overlap,
        separators = separator
    )

    splitted_docs = splitter.split_documents(docs)
    
    # Add a metadata
    for doc in splitted_docs:
        doc.metadata['doc_id'] = 'DOC_' + str(start_insert_doc_id)
        start_insert_doc_id += 1

    return splitted_docs
    
def docs_insert_db(splitted_docs, db):
    """
    1. Takes a Doc object divided into chunks as a parameter
    2. Insert row per document
    """
    dicts_list = []

    for splitted_doc in splitted_docs:
        row = {
            'doc_id': int(splitted_doc.metadata['doc_id'][4:]),
            'source': splitted_doc.metadata['source'],
            'file_name': splitted_doc.metadata['file_name'],
            'date': splitted_doc.metadata['date'],
            'page_content': splitted_doc.page_content
        }

        dicts_list.append(row)
    response = supabase.table('vectorstore').insert(dicts_list).execute()

    return response

def db_to_document(db) -> List[Document]:
    """ Supbase table 'vectorstore' all rows into Document object"""
    df = request_table(
        table_name = 'vectorstore',
        col_name = '*',
        db = db
    )

    # Data Preprocess
    df.drop('id', axis = 1, inplace = True)
    df['date'] = pd.to_datetime(df['date'])

    # DataFrame into Documents
    docs = [
        Document(
            page_content = row['page_content'],
            metadata = {
                'doc_id': f"DOC_{str(row['doc_id'])}",
                'file_name': row['file_name'],
                'source': row['source']
                }
        )
        for row in df.to_dict('records')
    ]

    return docs