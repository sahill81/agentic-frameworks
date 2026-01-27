import asyncio
import os
import time
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pydantic_ai import Agent, ModelSettings, RunContext
from pydantic_ai.tools import Tool
import logging

load_dotenv()

key = os.getenv("OPENAI_API_KEY")
print("key", key)
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# Request/Response Models
# ============================================================================

class AgentRequest(BaseModel):
    """Request model for the agent endpoint."""
    company: str
    query: str


class AgentResponse(BaseModel):
    """Response model for the agent endpoint."""
    status: str
    result: dict


# ============================================================================
# Tool Definitions (Three Basic Tools)
# ============================================================================

async def get_balance_sheet(symbol: str) -> dict:
    """
    Fetch balance sheet data for a given company symbol.
    
    Args:
        symbol: Company ticker symbol (e.g., 'AAPL')
        
    Returns:
        Dictionary containing balance sheet data
    """
    start = time.time()
    logger.info(f"🚀 Started balance sheet for {symbol} at {start:.2f}")
    logger.info(f"Fetching balance sheet for {symbol}")
    await asyncio.sleep(1)  # Simulate API call
    end_time = time.time()
    logger.info(f"FINISH: Balance Sheet for {symbol} at {end_time:.2f} (Duration: {end_time - start:.2f}s)")
    return {
        "type": "balance_sheet",
        "symbol": symbol,
        "assets": 352755000000,
        "liabilities": 125481000000,
    }


async def get_cash_flow(symbol: str) -> dict:
    """
    Fetch cash flow data for a given company symbol.
    
    Args:
        symbol: Company ticker symbol (e.g., 'AAPL')
        
    Returns:
        Dictionary containing cash flow data
    """
    start = time.time()
    logger.info(f"🚀 Started cash flow for {symbol} at {start:.2f}")
    logger.info(f"Fetching cash flow for {symbol}")
    await asyncio.sleep(1)  # Simulate API call
    end_time = time.time()
    logger.info(f"FINISH: Cash Flow for {symbol} at {end_time:.2f} (Duration: {end_time - start:.2f}s)")
    return {
        "type": "cash_flow",
        "symbol": symbol,
        "operating_cash_flow": 110543000000,
        "free_cash_flow": 95838000000,
    }




# ============================================================================
# Parallel Wrapper Tool 
# ============================================================================

async def get_all_data_parallel(symbol: str, query: str) -> dict:
    """
    Fetch all financial data and news in parallel using asyncio.gather.
    
    This tool demonstrates parallel execution of multiple async operations,
    which is more efficient than calling them sequentially.
    
    Args:
        symbol: Company ticker symbol
        query: News search query
        
    Returns:
        Dictionary containing all data from parallel calls
    """
    logger.info(f"Fetching all data in parallel for {symbol} with query: {query}")
    
    # Execute all three tools in parallel
    balance, cash_flow, news = await asyncio.gather(
        get_balance_sheet(symbol),
        get_cash_flow(symbol),
    )
    
    return {
        "balance_sheet": balance,
        "cash_flow": cash_flow,
        "news": news,
        "parallel_execution": True,
    }


# ============================================================================
# PydanticAI Agent Setup
# ============================================================================

# Create agent with parallel tool calls enabled
from agents import cash_flow_agent, balance_sheet_agent

main_agent = Agent("gpt-4o", model_settings=ModelSettings(parallel_tool_calls=True))

@main_agent.tool
async def delegate_balance(ctx: RunContext[None], symbol: str):
    return await balance_sheet_agent.run(f"Get balance sheet for {symbol}")

@main_agent.tool
async def delegate_cashflow(ctx: RunContext[None], symbol: str):
    return await cash_flow_agent.run(f"Get cash flow for {symbol}")



# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(title="PydanticAI Parallel Agent", version="1.0.0")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/run-agent", response_model=AgentResponse)
async def run_agent(request: AgentRequest) -> AgentResponse:
    """
    Run the PydanticAI agent with parallel tool calls.
    
    Args:
        request: AgentRequest containing company symbol and query
        
    Returns:
        AgentResponse with the result from the agent
        
    Raises:
        HTTPException: If agent execution fails
    """
    try:
        # logger.info(f"Received request: company={request.company}, query={request.query}")
        
        # Construct prompt for the agent
        prompt = f"""
        You are a financial data retrieval agent.

        Your task:
        - Get the balance sheet data for {request.company} or the cash flow data for {request.company} according to the user query.

        Rules:
        - Use the provided tool as needed.
        """

        
        # Run the agent
        logger.info("Running agent with parallel tool calls enabled")
        # Run the agent
        result = await main_agent.run(user_prompt=request.query,instructions=prompt)

        # # Inspect intermediate steps
        # for message in result.new_messages():
        #     print(f"DEBUG: {message}") 

        # Specifically looking for tool calls
        for message in result.new_messages():
            logger.info("-----------------intermediatery call of the llm-----------------")
            if hasattr(message, 'parts'):
                for part in message.parts:
                    if part.part_kind == 'tool-call':
                        logger.info(f"Tool Called: {part.tool_name} with args: {part.args}")
                    elif part.part_kind == 'tool-return':
                        logger.info(f"Tool Result: {part.content}")  
                    elif part.part_kind == "text"  :
                        logger.info(f"Text Result: {part.content}")   
                    else : 
                        logger.info(f"Reslut contains none of these types actual type is: {part.part_kind}")   

            logger.info("-----------------intermediatery call of the llm end")
        logger.info("Agent execution completed successfully")
        
        
        
        return AgentResponse(
            status="success",
            result={
                "company": request.company,
                "query": request.query,
                "agent_response": result.data if hasattr(result, 'data') else str(result),
                "parallel_execution": True,
            }
        )
    
    except Exception as e:
        logger.error(f"Error running agent: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Agent execution failed: {str(e)}")
    


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
