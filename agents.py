
import asyncio
from dataclasses import dataclass
import os
import time
from dotenv import load_dotenv
from pydantic_ai import Agent, RunContext
load_dotenv()


@dataclass
class CompanySymbol :
    symbol : str

company_name_provider_agent = Agent(
    model = "gpt-4o",
    name = "company_name_provider_agent",
    system_prompt=f"""You are a company name provider agent. You will be provided with a user financial query. Your job is to get the company that is in scope and return its comapany symbol.""",
    output_type=CompanySymbol,
    instrument=True

)

@company_name_provider_agent.tool
async def get_company_name(ctx: RunContext[None],company_name : str) :
    return CompanySymbol(symbol="RELIANCE.NS")

balance_sheet_agent = Agent(
    model="gpt-4o",
    name = "balance_sheet_agent",
    system_prompt="You fetch balance sheet data for a given company symbol.",
    instrument=True

)

@balance_sheet_agent.tool
async def get_balance_sheet(ctx: RunContext[None], symbol: str) -> dict:
    start = time.time()
    await asyncio.sleep(1)
    end_time = time.time()

    return {
        "type": "balance_sheet",
        "symbol": symbol,
        "assets": 352755000000,
        "liabilities": 125481000000,
    }


# =====================================================================
# AGENT 2: Cash Flow Agent
# =====================================================================

cash_flow_agent = Agent(
    model="gpt-4o",
    name = "cash_flow_agent",
    system_prompt="You fetch cash flow data for a given company symbol.",
)

@cash_flow_agent.tool
async def get_cash_flow(ctx: RunContext[None], symbol: str) -> dict:
    raise RuntimeError("Manual cash flow failure for retry")

    start = time.time()
    await asyncio.sleep(1)
    end_time = time.time()

    return {
        "type": "cash_flow",
        "symbol": symbol,
        "operating_cash_flow": 110543000000,
        "free_cash_flow": 95838000000,
    }

summarizer_agent = Agent(
    model="gpt-4o",
    name = "summarizer_agent",
    system_prompt="You are a summarizer agent. You will recieve company balance sheet and cash flow financial information. Your job is to create a brief summary for that information"
)