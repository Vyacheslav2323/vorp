import psycopg2
import psycopg2.pool
from typing import Optional
import os

class DatabasePool:
    def __init__(self):
        self.pool = None
    
    def init_pool(self) -> bool:
        db_url = os.getenv('DATABASE_URL')
        if db_url:
            try:
                self.pool = psycopg2.pool.ThreadedConnectionPool(
                    minconn=1,
                    maxconn=10,
                    dsn=db_url
                )
                print("✓ Database connected (via DATABASE_URL)", flush=True)
                return True
            except Exception as e:
                print(f"db_init_error (url): {e}", flush=True)
        
        try:
            self.pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=10,
                host=os.getenv('DB_HOST', 'localhost'),
                port=os.getenv('DB_PORT', '5432'),
                database=os.getenv('DB_NAME', 'lexipark'),
                user=os.getenv('DB_USER', 'postgres'),
                password=os.getenv('DB_PASSWORD', 'lexipark2024')
            )
            print("✓ Database connected to local PostgreSQL", flush=True)
            return True
        except Exception as e:
            print(f"db_init_error: {e}", flush=True)
            return False
    
    def get_connection(self) -> Optional[psycopg2.extensions.connection]:
        if not self.pool:
            return None
        try:
            return self.pool.getconn()
        except Exception:
            return None
    
    def return_connection(self, conn: psycopg2.extensions.connection):
        if self.pool and conn:
            self.pool.putconn(conn)

db_pool = DatabasePool()

