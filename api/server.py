from fastapi import FastAPI, Request
from api.routes import frames_router, stats_router
from fastapi.middleware.cors import CORSMiddleware
import time
from starlette.middleware.base import BaseHTTPMiddleware
import logging

# Configure the logging with time
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S %p')

# Create a logger object
logger = logging.getLogger(__name__)


class LogResponseTime(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        # Log the response time (you can customize this part to fit your logging format)
        logger.info(f"Response time for request {request.url}: {process_time:.2f} seconds.")
        return response


class CacheControlMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "max-age=10"  # Apply cache-control globally
        return response


app = FastAPI()

app.include_router(frames_router)
app.include_router(stats_router)

app.add_middleware(LogResponseTime)
app.add_middleware(CacheControlMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)





