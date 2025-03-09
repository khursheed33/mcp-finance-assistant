from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from src.mcp_server import get_llm_response
from src.database import init_db
import uvicorn

app = FastAPI(title="Personal Finance Assistant")

@app.on_event("startup")
async def startup_event():
    init_db()

class ChatRequest(BaseModel):
    message: str

@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        response = await get_llm_response(request.message)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(".env")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)