import os
from mcp.server.fastmcp import FastMCP
import httpx
from src.database import get_transactions, add_transaction
from openai import AsyncOpenAI
from typing import List, Dict

# Initialize MCP server
mcp = FastMCP("Personal Finance Assistant")
openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_KEY"))  # Replace with your OpenAI API key

# Resource: Expose transaction history
@mcp.resource("transactions://history")
def get_transaction_history() -> str:
    """Returns user's transaction history as a formatted string."""
    transactions = get_transactions()
    return "\n".join([f"{t['date']} - {t['amount']} USD - {t['category']} - {t['description']}" for t in transactions])

# Tool: Calculate total expenses
@mcp.tool()
def calculate_total_expenses() -> float:
    """Calculates total expenses from transaction history."""
    transactions = get_transactions()
    return sum(t["amount"] for t in transactions)

# Tool: Add a new transaction
@mcp.tool()
def log_expense(amount: float, category: str, description: str) -> str:
    """Logs a new expense in the transaction history."""
    add_transaction(amount, category, description)
    return f"Logged expense: {amount} USD - {category} - {description}"

# Tool: Fetch currency exchange rate
@mcp.tool()
async def get_exchange_rate(from_currency: str, to_currency: str) -> float:
    """Fetches real-time exchange rate between two currencies."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"https://api.exchangerate-api.com/v4/latest/{from_currency}")
        data = response.json()
        return data["rates"][to_currency]

# Prompt: Summarize transactions (still available but not hardcoded)
@mcp.prompt()
def summarize_transactions() -> List[Dict]:
    """Prompt to summarize transaction history."""
    transactions = get_transactions()
    total = sum(t["amount"] for t in transactions)
    return [
        {"role": "user", "content": f"Summarize my transactions: Total spent = {total} USD"},
        {"role": "assistant", "content": "Here’s a summary based on your transaction history."}
    ]

# Prompt: Financial advice (still available but not hardcoded)
@mcp.prompt()
def financial_advice(goal: str) -> List[Dict]:
    """Prompt to get financial advice based on a goal."""
    transactions = get_transactions()
    total_spent = sum(t["amount"] for t in transactions)
    return [
        {"role": "user", "content": f"I want to {goal}. My total spending is {total_spent} USD. Advise me."},
        {"role": "assistant", "content": "I’ll provide tailored financial advice."}
    ]

# System prompt describing capabilities
SYSTEM_PROMPT = """
You are a Personal Finance Assistant powered by xAI's Grok 3. Your goal is to help users manage their finances by interpreting their requests and using available tools and resources dynamically. You have access to the following:

### Resources:
- `transactions://history`: Fetches the user's transaction history as a formatted string.

### Tools:
- `calculate_total_expenses()`: Returns the total expenses from the transaction history as a float.
- `log_expense(amount: float, category: str, description: str)`: Logs a new expense and returns a confirmation message.
- `get_exchange_rate(from_currency: str, to_currency: str)`: Fetches the real-time exchange rate between two currencies.

### Prompts:
- `summarize_transactions`: Generates a summary of the user's transaction history.
- `financial_advice(goal: str)`: Provides financial advice based on a specified goal (e.g., "save money").

### Instructions:
1. Interpret the user’s message naturally and decide the best course of action.
2. Use the transaction history (provided in the context) to inform your responses.
3. If a tool or resource is needed, mention it explicitly in your response (e.g., "I’ll use calculate_total_expenses()") and assume the result is available to you.
4. Respond conversationally, combining multiple actions if necessary (e.g., summarizing transactions and giving advice in one go).
5. If the user’s intent is unclear, ask for clarification.

Current date: March 09, 2025.
"""

async def get_llm_response(user_message: str) -> str:
    # Fetch transaction history as context
    transactions = get_transaction_history()

    # Prepare messages for OpenAI
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT + f"\nTransaction history:\n{transactions}"},
        {"role": "user", "content": user_message}
    ]

    # Call OpenAI to handle the request dynamically
    response = await openai_client.chat.completions.create(
        model="gpt-40-mini",  # Or use "gpt-4" if available
        messages=messages,
        max_tokens=500
    )
    
    # Get the LLM’s response
    llm_response = response.choices[0].message.content

    # Post-process to simulate tool calls (since OpenAI doesn’t natively call MCP tools yet)
    if "calculate_total_expenses()" in llm_response:
        total = calculate_total_expenses()
        llm_response = llm_response.replace("calculate_total_expenses()", str(total))
    elif "log_expense(" in llm_response:
        # Extract parameters (rudimentary parsing; improve with regex or structured outputs if needed)
        try:
            parts = llm_response.split("log_expense(")[1].split(")")[0].split(",")
            amount = float(parts[0].strip())
            category = parts[1].strip().strip("'\"")
            description = parts[2].strip().strip("'\"")
            result = log_expense(amount, category, description)
            llm_response = llm_response.replace(f"log_expense({amount}, {category}, {description})", result)
        except Exception as e:
            llm_response += f"\nError logging expense: {str(e)}"
    elif "get_exchange_rate(" in llm_response:
        try:
            parts = llm_response.split("get_exchange_rate(")[1].split(")")[0].split(",")
            from_currency = parts[0].strip().strip("'\"")
            to_currency = parts[1].strip().strip("'\"")
            rate = await get_exchange_rate(from_currency, to_currency)
            llm_response = llm_response.replace(f"get_exchange_rate({from_currency}, {to_currency})", str(rate))
        except Exception as e:
            llm_response += f"\nError fetching exchange rate: {str(e)}"

    return llm_response