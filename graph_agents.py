# =====================================================================
# AGENT 1: Balance Sheet Agent
# =====================================================================



import asyncio
from dataclasses import dataclass
import os
import time
from dotenv import load_dotenv
from pydantic_ai import Agent, RunContext
import logging
from pydantic_graph import BaseNode, End, Graph, GraphRunContext
import logfire
from langfuse import get_client
load_dotenv()

 
# langfuse = get_client()
# Agent.instrument_all()


logfire.configure()
logfire.instrument_pydantic_ai()



# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


key = os.getenv("OPENAI_API_KEY")
print("key", key)

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
    logger.info(f"🚀 [BALANCE] Started for {symbol} at {start:.2f}")
    await asyncio.sleep(1)
    end_time = time.time()
    logger.info(
        f"FINISH [BALANCE]: {symbol} at {end_time:.2f} "
        f"(Duration: {end_time - start:.2f}s)"
    )
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
    start = time.time()
    logger.info(f"🚀 [CASHFLOW] Started for {symbol} at {start:.2f}")
    await asyncio.sleep(1)
    end_time = time.time()
    logger.info(
        f"FINISH [CASHFLOW]: {symbol} at {end_time:.2f} "
        f"(Duration: {end_time - start:.2f}s)"
    )
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

@dataclass
class CompanyState :
    user_query : str

@dataclass
class FinalResult : 
    response : str

@dataclass
class CashFlow((BaseNode[CompanyState])) : 
    symbol : str
    async def run(self, ctx : GraphRunContext[CompanyState]) -> End[FinalResult] :

        result = await cash_flow_agent.run(f"This is the symbol of the company {self.symbol}.")
        
            
        return End(result.output)

@dataclass
class BalanceSheet((BaseNode[CompanyState])) : 
    symbol : str
    async def run(self, ctx : GraphRunContext[CompanyState]) -> End[FinalResult] :
        # with logfire.span("Fetch balance sheet"):
        result = await balance_sheet_agent.run(f"This is the symbol of the company {self.symbol}.")
        return End(FinalResult(response = result.output))
    



        
@dataclass
class Summarizer(BaseNode[CompanyState]) : 
    balance_sheet_info : str
    cash_flow_info : str
    async def run(self, ctx : GraphRunContext[CompanyState]) -> End[FinalResult] :
        result = await summarizer_agent.run(f"The balance sheet is{self.balance_sheet_info} and the cash flow is {self.cash_flow_info}")
        return End(FinalResult(response = result.output))


@dataclass 
class BalanceSheetAndCashflow(BaseNode[CompanyState]) :
    symbol : str
    async def run(self, ctx : GraphRunContext[CompanyState]) -> Summarizer :
        balance_sheet, cashflow = await asyncio.gather(
                balance_sheet_agent.run(f"This is the symbol of the company {self.symbol}."),
                cash_flow_agent.run(f"This is the symbol of the company {self.symbol}.")
        )
        return Summarizer(balance_sheet,cashflow)


@dataclass
class CompanyNameResolver(BaseNode[CompanyState]) :
    async def run(self, ctx : GraphRunContext[CompanyState] ) -> BalanceSheetAndCashflow: 
        # with logfire.span("Company name resolver"):

        result =  await company_name_provider_agent.run(ctx.state.user_query)
        return BalanceSheetAndCashflow(result.output.symbol)

async def main() :
    state = CompanyState(
        user_query="Whats the balance sheet of Reliance digital"
    )
    g = Graph(nodes=(CompanyNameResolver,BalanceSheetAndCashflow,Summarizer ))

    # result = await g.run(CompanyNameResolver(), state = state)
    async with g.iter(CompanyNameResolver(), state = state) as run :
        async for node in run :
            print("node-------->",node)
    print(run.result)


# asyncio.run(main())