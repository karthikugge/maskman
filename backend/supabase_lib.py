from supabase import create_client, Client
from backend.config import settings

# Initialize Supabase client
# This uses the SUPABASE_URL and SUPABASE_KEY (ideally Service Role Key)
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
