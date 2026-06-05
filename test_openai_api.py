import os
import asyncio
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv

load_dotenv()

async def test_openai():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("No API key found")
        return
    
    try:
        llm = ChatOpenAI(model="gpt-4o", openai_api_key=api_key)
        res = await llm.ainvoke([HumanMessage(content="Hello, say 'Test OK'")])
        print(f"Response: {res.content}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_openai())
