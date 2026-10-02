import os
import sys

sys.path.append(os.path.abspath('.'))
from modelo.supabase_client import SupabaseClient

supabase = SupabaseClient().get_client()
res = supabase.table('reglas').select('*').execute()
for r in res.data:
    print(r)
