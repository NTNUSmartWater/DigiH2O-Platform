import os, socket
from pathlib import Path
from contextlib import asynccontextmanager
from Functions import dataset_manager
from dotenv import load_dotenv
from redis.asyncio import Redis

# ============== Root directory ================
load_dotenv()
BACKEND_DIR = Path(__file__).parent.parent
env_mode = os.getenv("ENV", "development")
if env_mode == "development":
    PROJECT_STATIC_ROOT = os.getenv("PROJECT_STATIC_ROOT")
    STATIC_DIR_BACKEND = os.getenv("STATIC_DIR_BACKEND")
    STATIC_DIR_FRONTEND = os.getenv("STATIC_DIR_FRONTEND")
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
else:
    PROJECT_STATIC_ROOT = "/app/Delft_Projects"
    STATIC_DIR_BACKEND = "/app/static"
    STATIC_DIR_FRONTEND = "/app/frontend/static"
    REDIS_URL = "redis://redis:6379/0"
DELFT_PATH = os.getenv("DELFT3D_PATH")
GRID_PATH = os.getenv('GRID_PATH')
WINDOWS_AGENT_URL = "http://host.docker.internal:5055/run"

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
        app.state.redis = Redis.from_url(REDIS_URL, decode_responses=True)
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