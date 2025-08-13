from ..dependency.db import connect_supabase
from fastapi import Depends, Request, APIRouter
from pydantic import BaseModel
from supabase import Client

router = APIRouter(
    prefix = "/db",         # 웹 페이지 path
    tags = ['Supabase']     # API docs에 표시될 태그
)

class user_input(BaseModel):
    """ Validation User input """
    input_text: str
    chat_response: str

def get_ip(request: Request):
    """ Get User IP Address """
    forwarded_ip = request.headers.get('x-forwarded-for')
    if forwarded_ip:
        return forwarded_ip.split(',')[0].strip()
    else:
        return request.client.host

@router.post('/insert_row', summary = "request & insert chatting log", tags = ['Supabase'])
async def request(data: user_input, user_ip: str = Depends(get_ip), db: Client = Depends(connect_supabase)):    
    # Insert Input Log
    insert_data = {
        'user_id': 'public',
        'ip_address': user_ip,
        'content': data.input_text,
        'response': data.chat_response
    }
    try:
        resopnse = db.from_('chat_logs').insert(insert_data).execute()
        print("[Row Insert] Success.")
    except Exception as e:
        print(f"[Row Insert] Error: {e}")