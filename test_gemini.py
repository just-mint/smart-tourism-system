import os
import asyncio
import httpx
from dotenv import load_dotenv

load_dotenv(".env")
api_key = os.getenv("GEMINI_API_KEY")
print(f"API Key: {api_key}")

async def test():
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    payload = {"contents": [{"parts": [{"text": "Hello"}]}]}
    async with httpx.AsyncClient(timeout=10.0) as client:
        res = await client.post(url, json=payload)
        print(res.status_code)
        print(res.text)

asyncio.run(test())
