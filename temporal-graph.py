import asyncio
from dataclasses import dataclass
from datetime import timedelta
import time
from typing import Dict, Any
from dotenv import load_dotenv
from pydantic_ai import Agent, RunContext
from temporalio import workflow, activity
from temporalio.client import Client
from temporalio.worker import Worker
from pydantic_ai.durable_exec.temporal import PydanticAIPlugin
from pydantic_ai.durable_exec.temporal import (
    PydanticAIPlugin,
    PydanticAIWorkflow,
    TemporalAgent,
)
from pydantic_graph import BaseNode, Graph, End, GraphRunContext

load_dotenv()


@dataclass
class CompanySymbol:
    symbol: str

@dataclass
class FinancialData:
    data: Dict[str, Any]

@dataclass
class CompanyState:
    user_query: str

@dataclass
class FinalResult:
    response: str


company_name_provider_agent = Agent(
    model="gpt-4o",
    name="company_name_provider_agent",
    system_prompt="Get the company symbol from the query.",
    output_type=CompanySymbol,
)

@company_name_provider_agent.tool
async def get_company_name(ctx: RunContext[None], company_name: str):
    return CompanySymbol(symbol="RELIANCE.NS")

balance_sheet_agent = Agent(
    model="gpt-4o",
    name="balance_sheet_agent",
    system_prompt="Return the balance sheet data. Use the tool provided.",
    output_type=FinancialData 
)

@balance_sheet_agent.tool
async def get_balance_sheet(ctx: RunContext[None], symbol: str) -> dict:
    return {
        "type": "balance_sheet",
        "symbol": symbol,
        "assets": 352755000000,
        "liabilities": 125481000000,
    }

cash_flow_agent = Agent(
    model="gpt-4o",
    name="cash_flow_agent",
    system_prompt="Return the cash flow data. Use the tool provided.",
    output_type=FinancialData
)

@cash_flow_agent.tool
async def get_cash_flow(ctx: RunContext[None], symbol: str) -> dict:
    return {
        "type": "cash_flow",
        "symbol": symbol,
        "operating_cash_flow": 110543000000,
        "free_cash_flow": 95838000000,
    }

summarizer_agent = Agent(
    model="gpt-4o",
    name="summarizer_agent",
    system_prompt="Summarize the provided financial information into a brief paragraph."
)

temporal_company_name_agent = TemporalAgent(company_name_provider_agent)
temporal_balance_sheet_agent = TemporalAgent(balance_sheet_agent)
temporal_cash_flow_agent = TemporalAgent(cash_flow_agent,)       
temporal_summarizer_agent = TemporalAgent(summarizer_agent)

# =====================================================================
# PYDANTIC GRAPH NODES
# =====================================================================

@dataclass
class CompanyNameResolver(BaseNode[CompanyState]):
    async def run(self, ctx: GraphRunContext[CompanyState]) -> "BalanceSheetAndCashflow":
        result = await temporal_company_name_agent.run(ctx.state.user_query)
        return BalanceSheetAndCashflow(symbol=result.output.symbol)

@dataclass
class BalanceSheetAndCashflow(BaseNode[CompanyState]):
    symbol: str
    
    async def run(self, ctx: GraphRunContext[CompanyState]) -> "Summarizer":
        balance, cashflow = await asyncio.gather(
            temporal_balance_sheet_agent.run(f"Get balance sheet for {self.symbol}"),
            temporal_cash_flow_agent.run(f"Get cash flow for {self.symbol}")
        )
        return Summarizer(
            balance_sheet_info=str(balance.output.data),
            cash_flow_info=str(cashflow.output.data)
        )

@dataclass
class Summarizer(BaseNode[CompanyState]):
    balance_sheet_info: str
    cash_flow_info: str
    
    async def run(self, ctx: GraphRunContext[CompanyState]) -> End[FinalResult]:
        result = await temporal_summarizer_agent.run(
            f"Balance Sheet: {self.balance_sheet_info}, Cash Flow: {self.cash_flow_info}"
        )
        return End(FinalResult(response=result.output))

# =====================================================================
# WORKFLOW (Orchestration with PydanticGraph)
# =====================================================================

@workflow.defn
class FinancialGraphWorkflow(PydanticAIWorkflow):
    
    __pydantic_ai_agents__ = [
        temporal_company_name_agent,
        temporal_balance_sheet_agent,
        temporal_cash_flow_agent,
        temporal_summarizer_agent,
    ]

    @workflow.run
    async def run(self, user_query: str) -> str:
        # Create the initial state
        state = CompanyState(user_query=user_query)
        
        # Build the graph
        g = Graph(
            nodes=(CompanyNameResolver, BalanceSheetAndCashflow, Summarizer)
        )
        
        # Execute the graph within the Temporal workflow
        workflow.logger.info(f"Starting graph execution for query: {user_query}")
        
        async with g.iter(CompanyNameResolver(), state=state) as run:
            async for node in run:
                workflow.logger.info(f"Executed node: {type(node).__name__}")
        
        workflow.logger.info("Graph execution completed")
        return run.result.response

# =====================================================================
# MAIN
# =====================================================================

async def main():
    client = await Client.connect("localhost:7233", plugins=[PydanticAIPlugin()])
    
    async with Worker(
        client,
        task_queue="financial-graph-1",
        workflows=[FinancialGraphWorkflow],
        activities=[],
    ):
        print("Worker started. Running PydanticGraph via Temporal...")
        result = await client.execute_workflow(
            FinancialGraphWorkflow.run,
            "Whats the balance sheet and cash flow of Reliance digital",
            id=f"financial-graph-{int(time.time())}",
            task_queue="financial-graph-1",
        )
        print(f"Final Result: {result}")

if __name__ == "__main__":
    import sys
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())