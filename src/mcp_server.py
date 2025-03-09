import os
from mcp.server.fastmcp import FastMCP
import httpx
from src.database import get_transactions, add_transaction
from openai import AsyncOpenAI
from typing import List, Dict

# Initialize MCP server
mcp = FastMCP("Personal Finance Assistant")
openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_KEY"))

@mcp.resource("transactions://history")
async def get_transaction_history() -> str:
    """Returns user's transaction history as a formatted string."""
    transactions = get_transactions()
    return "\n".join([f"{t['date']} - {t['amount']} USD - {t['category']} - {t['description']}" for t in transactions])

@mcp.tool()
async def calculate_total_expenses() -> float:
    """Calculates total expenses from transaction history."""
    transactions = get_transactions()
    return sum(t["amount"] for t in transactions)

@mcp.tool()
async def log_expense(amount: float, category: str, description: str) -> str:
    """Logs a new expense in the transaction history."""
    add_transaction(amount, category, description)
    return f"Logged expense: {amount} USD - {category} - {description}"

@mcp.tool()
async def get_exchange_rate(from_currency: str, to_currency: str) -> float:
    """Fetches real-time exchange rate between two currencies."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"https://api.exchangerate-api.com/v4/latest/{from_currency}")
        data = response.json()
        return data["rates"][to_currency]

# Improved system prompt with better tool calling instructions
SYSTEM_PROMPT = """
You are a Personal Finance Assistant powered by xAI's Grok 3. Your goal is to help users manage their finances efficiently.

Available Tools and Resources:

1. Transaction History Access:
   - Use: `transactions://history`
   - Returns: Formatted transaction list

2. Financial Tools:
   - `calculate_total_expenses()`
   - `log_expense(amount, category, description)`
   - `get_exchange_rate(from_currency, to_currency)`

Tool Usage Format:
- For calculations: "Let me calculate your total expenses: {await calculate_total_expenses()}"
- For logging: "I'll log that expense: {await log_expense(50.0, 'Food', 'Groceries')}"
- For exchange rates: "The current rate is: {await get_exchange_rate('USD', 'EUR')}"

Instructions:
1. Always use await when calling async tools
2. Format amounts with 2 decimal places
3. Verify input parameters before tool calls
4. Provide clear feedback after each action
5. If multiple tools are needed, call them in sequence

Current date: March 09, 2025
"""

async def get_llm_response(user_message: str) -> str:
    # Fetch transaction history as context
    transactions = await get_transaction_history()

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT + f"\nTransaction history:\n{transactions}"},
        {"role": "user", "content": user_message}
    ]

    # Get LLM response
    response = await openai_client.chat.completions.create(
        model="gpt-4-turbo-preview",
        messages=messages,
        max_tokens=500
    )
    
    llm_response = response.choices[0].message.content

    # Process tool calls with proper async handling
    if "calculate_total_expenses()" in llm_response:
        total = await calculate_total_expenses()
        llm_response = llm_response.replace("calculate_total_expenses()", f"{total:.2f}")
    
    if "log_expense(" in llm_response:
        try:
            # Improved parameter extraction using safer parsing
            import re
            match = re.search(r"log_expense\((.*?)\)", llm_response)
            if match:
                params = [p.strip().strip("'\"") for p in match.group(1).split(",")]
                amount = float(params[0])
                category = params[1]
                description = params[2]
                result = await log_expense(amount, category, description)
                llm_response = llm_response.replace(match.group(0), result)
        except Exception as e:
            llm_response += f"\nError logging expense: {str(e)}"

    if "get_exchange_rate(" in llm_response:
        try:
            import re
            match = re.search(r"get_exchange_rate\((.*?)\)", llm_response)
            if match:
                params = [p.strip().strip("'\"") for p in match.group(1).split(",")]
                rate = await get_exchange_rate(params[0], params[1])
                llm_response = llm_response.replace(match.group(0), f"{rate:.4f}")
        except Exception as e:
            llm_response += f"\nError fetching exchange rate: {str(e)}"

    return llm_response