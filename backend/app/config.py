import os, socket
from contextlib import asynccontextmanager
from Functions import dataset_manager
from dotenv import load_dotenv
from redis.asyncio import Redis

# ============== Root directory ================
load_dotenv()
env_mode = os.getenv("ENV", "development")
if env_mode == "development":
    PROJECT_DES = os.getenv("PROJECT_DES")
    ALLOWED_USERS_PATH = os.path.join(PROJECT_DES, "backend/static/allowed_users.json")
    PROJECT_STATIC_ROOT = os.path.join(PROJECT_DES, "backend/Delft_Projects")
    STATIC_DIR_BACKEND = os.path.join(PROJECT_DES, "backend/static")
    STATIC_DIR_FRONTEND = os.path.join(PROJECT_DES, "frontend/static")
    DELFT_PATH = os.path.join(PROJECT_DES, "backend/x64")
    REDIS_URL = "redis://localhost:6379/0"
else:
    PROJECT_DES = os.getenv("/app")
    ALLOWED_USERS_PATH = os.path.join(PROJECT_DES, "static/allowed_users.json")
    PROJECT_STATIC_ROOT = "/app/Delft_Projects"
    STATIC_DIR_BACKEND = "/app/static"
    STATIC_DIR_FRONTEND = "/app/frontend/static"
    DELFT_PATH = os.path.join(PROJECT_DES, "x64")
    REDIS_URL = "redis://redis:6379/0"
    WINDOWS_AGENT_URL = "http://host.docker.internal:5055/run" 
GRID_PATH = os.getenv('GRID_PATH')


# ============== Redis Client ================
def check_redis_running(host="localhost", port=6379, timeout=1):
    # Check if redis-server is running.
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect((host, port))
        sock.close()
        print("✅ Redis server is running.")
        return True
    except Exception: return False
    
# ============== Lifespan ================
@asynccontextmanager
async def lifespan(app):
    # Dataset
    app.state.dataset_manager = dataset_manager.DatasetManager()
    app.state.env, app.state.project_cache = env_mode, {}
    # Redis
    try:
        app.state.redis = Redis.from_url(REDIS_URL, decode_responses=False)
    except Exception as e:
        print(f"❌ Failed to initialize Redis: {e}")
        app.state.redis = None
    yield
    try:
        app.state.dataset_manager.close()
        if app.state.redis:
            await app.state.redis.close()
    except Exception as e:
        print(f"⚠️ Dataset manager close error: {e}")