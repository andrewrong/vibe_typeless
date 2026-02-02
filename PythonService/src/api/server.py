"""
Typeless ASR and Post-processing Server
FastAPI server for handling ASR requests and text post-processing
"""

import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

# Use relative imports
from .routes import router, postprocess_router, job_router
from .rate_limit import limiter

app = FastAPI(
    title="Typeless Service",
    description="ASR and AI-powered text post-processing service",
    version="0.2.0"
)

# Set up rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Include routers
app.include_router(router)
app.include_router(postprocess_router)
app.include_router(job_router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Typeless Service API", "status": "running"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
