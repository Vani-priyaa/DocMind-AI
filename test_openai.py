import os
import asyncio
import pandas as pd
from backend.utils import DataAnalyzer
from dotenv import load_dotenv

load_dotenv()

async def test():
    api_key = os.getenv("OPENAI_API_KEY")
    print(f"Using API key: {api_key}")
    analyzer = DataAnalyzer(api_key)
    try:
        res = await analyzer.analyze_data("hello", {}, [])
        print(res)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test())
