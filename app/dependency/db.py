from supabase import create_client, Client
from dotenv import load_dotenv
import os

load_dotenv()

url = os.getenv('SUPABASE_URL')
key = os.getenv("SUPABASE_API_KEY")

supabase: Client = create_client(url, key)

def connect_supabase():
    if not url or not key:
        raise ValueError("Supabase URL and Key must be set in environment variables.")
    return supabase