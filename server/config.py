import os
 
# --- Database ---------------------------------------------------------------
DATABASE_URL = (
    f"postgresql+psycopg://"
    f"{os.environ['POSTGRES_USER']}:"
    f"{os.environ['POSTGRES_PASSWORD']}@"
    f"{os.environ.get('POSTGRES_HOST', 'localhost')}:"
    f"{os.environ.get('POSTGRES_PORT', '5432')}/"
    f"{os.environ['POSTGRES_DB']}"
)
 
# --- JWT --------------------------------------------------------------------
JWT_SECRET = os.environ["JWT_SECRET"]
if JWT_SECRET == "change-me-generate-your-own":
    # Stops the app from starting with the placeholder from .env.example.
    raise RuntimeError("Set a real JWT_SECRET in your .env file")
 
JWT_ALGORITHM = "HS256"
TOKEN_LIFETIME_MINUTES = 60
 
