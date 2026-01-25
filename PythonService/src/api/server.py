"""
Typeless ASR and Post-processing Server
FastAPI server for handling ASR requests and text post-processing
"""

from fastapi import FastAPI
try:
    from .routes import router, postprocess_router
except ImportError:
    # Fallback for running directly
    from routes import router, postprocess_router

app = FastAPI(
    title="Typeless Service",
    description="ASR and AI-powered text post-processing service",
    version="0.1.0"
)

# Include routers
app.include_router(router)
app.include_router(postprocess_router)


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
