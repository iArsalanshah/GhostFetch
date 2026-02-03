import asyncio
import httpx
import time

async def fetch(client, url):
    try:
        response = await client.post("http://localhost:8000/fetch", json={"url": url}, timeout=120)
        return response.status_code, response.json().get("url")
    except Exception as e:
        return 500, str(e)

async def run_load_test(concurrency=5):
    url = "https://example.com"
    async with httpx.AsyncClient() as client:
        tasks = [fetch(client, url) for _ in range(concurrency)]
        start_time = time.time()
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        print(f"Completed {concurrency} requests in {end_time - start_time:.2f} seconds")
        for status, res_url in results:
            print(f"Status: {status}, URL: {res_url}")

if __name__ == "__main__":
    asyncio.run(run_load_test(5))
