from fastapi import FastAPI

app = FastAPI(
    title="🎁 Telegram Gift Detector",
    description="Professional gift detection service for Telegram",
    version="1.0.0"
)

@app.get("/")
def read_root():
    return {
        "status": "ok",
        "message": "Telegram Gift Detector is running",
        "version": "1.0.0"
    }

@app.get("/health")
def health_check():
    return {
        "status": "healthy", 
        "service": "Telegram Gift Detector",
        "uptime": "running"
    }

@app.get("/info")
def get_info():
    return {
        "name": "Telegram Gift Detector",
        "version": "1.0.0",
        "description": "Smart Telegram gift detection service",
        "status": "ready for deployment",
        "endpoints": {
            "root": "/",
            "health": "/health",
            "info": "/info",
            "docs": "/docs"
        }
    }

@app.get("/status")
def get_status():
    return {
        "service": "online",
        "deployment": "successful",
        "ready": True
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)