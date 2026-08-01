import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://root@localhost:26257/recall?sslmode=disable")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
