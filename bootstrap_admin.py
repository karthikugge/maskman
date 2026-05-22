import asyncio
import uuid
from backend.supabase_lib import supabase
from backend.api.security import get_password_hash

async def bootstrap():
    print("Bootstrapping initial CEO SuperAdmin via Supabase SDK...")
    
    # Check if any admin exists
    try:
        response = supabase.table("admin_users").select("email").limit(1).execute()
        if response.data:
            print(f"Admins already exist in Supabase: {response.data[0]['email']}")
            return

        # Create initial CEO superadmin
        admin = {
            "id": str(uuid.uuid4()),
            "username": "kart123",
            "email": "uggekarthik96@gmail.com",
            "hashed_password": get_password_hash("Karthik@123"),
            "full_name": "Karthik CEO",
            "designation": "CEO",
            "role": "superadmin",
            "is_active": True
        }
        
        res = supabase.table("admin_users").insert(admin).execute()
        
        if res.data:
            print("CEO SuperAdmin created successfully in Supabase!")
            print("Email: uggekarthik96@gmail.com")
            print("Pass:  Karthik@123")
        else:
            print("Failed to create admin.")
            
    except Exception as e:
        print(f"Error during bootstrap: {e}")

if __name__ == "__main__":
    asyncio.run(bootstrap())

