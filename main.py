from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from scraper import StealthScraper
import uvicorn

app = FastAPI(title="Stealth Fetcher API", description="API for fetching content from hard-to-scrape sites.")
scraper = StealthScraper()

class FetchRequest(BaseModel):
    url: str

@app.on_event("startup")
async def startup_event():
    print("Starting Playwright browser...")
    await scraper.start()
    print("Browser started.")

@app.on_event("shutdown")
async def shutdown_event():
    print("Stopping Playwright browser...")
    await scraper.stop()
    print("Browser stopped.")

@app.post("/fetch")
async def fetch_endpoint(request: FetchRequest):
    """
    Fetch content from a URL using a headless browser with stealth techniques.
    Returns the content converted to Markdown.
    """
    try:
        content = await scraper.fetch(request.url)
        if content == "Failed to fetch content.":
             raise HTTPException(status_code=400, detail="Failed to fetch content from the provided URL.")
        return {"url": request.url, "markdown": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
