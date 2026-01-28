from dataclasses import dataclass
from datetime import timedelta
import asyncio
import time
from dotenv import load_dotenv
from temporalio import workflow, activity
from temporalio.client import Client
from temporalio.worker import Worker
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel
from pydantic_graph import BaseNode, Graph, End, GraphRunContext, GraphRunResult
from pydantic_ai.durable_exec.temporal import TemporalAgent, PydanticAIWorkflow, PydanticAIPlugin


load_dotenv()

# =====================================================================
# PYDANTIC AI MODELS
# =====================================================================
@dataclass
class CompanySymbol:
    symbol: str

@dataclass
class FinancialData:
    type: str
    symbol: str
    data: dict

# =====================================================================
# STATE & RESULTS
# =====================================================================
@dataclass
class CompanyState:
    user_query: str

@dataclass
class FinalResult:
    response: str

# =====================================================================
# AGENTS (Same as before)
# =====================================================================
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

# Wrap agents with Temporal
temporal_company_agent = TemporalAgent(company_name_provider_agent)
temporal_balance_agent = TemporalAgent(balance_sheet_agent)
temporal_cashflow_agent = TemporalAgent(cash_flow_agent)
temporal_summarizer_agent = TemporalAgent(summarizer_agent)

# =====================================================================
# PYDANTIC GRAPH NODES
# =====================================================================
@dataclass
class CompanyNameResolver(BaseNode[CompanyState]):
    async def run(self, ctx: GraphRunContext[CompanyState]) -> "BalanceSheetAndCashflow":
        result = await temporal_company_agent.run(ctx.state.user_query)
        return BalanceSheetAndCashflow(symbol=result.output.symbol)

@dataclass
class BalanceSheetAndCashflow(BaseNode[CompanyState]):
    symbol: str
    
    async def run(self, ctx: GraphRunContext[CompanyState]) -> "Summarizer":
        balance, cashflow = await asyncio.gather(
            temporal_balance_agent.run(f"This is the symbol of the company {self.symbol}."),
            temporal_cashflow_agent.run(f"This is the symbol of the company {self.symbol}.")
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
            f"The balance sheet is {self.balance_sheet_info} and the cash flow is {self.cash_flow_info}"
        )
        return End(FinalResult(response=result.output))

# =====================================================================
# ACTIVITY: Execute graph (wraps non-deterministic uuid.uuid4 calls)
# =====================================================================
@activity.defn
async def execute_graph_activity(user_query: str) -> str:
    """
    Wraps the entire graph execution as an activity.
    This isolates the non-deterministic uuid.uuid4() calls used by PydanticGraph.
    """
    state = CompanyState(user_query=user_query)
    g = Graph(nodes=(CompanyNameResolver, BalanceSheetAndCashflow, Summarizer))
    
    result : GraphRunResult = await g.run(CompanyNameResolver(), state=state)
    return result.output

# =====================================================================
# TEMPORAL WORKFLOW WITH PYDANTIC GRAPH
# =====================================================================
@workflow.defn
class FinancialGraphWorkflow(PydanticAIWorkflow):
    """
    This workflow executes the PydanticGraph via an activity wrapper.
    The activity isolates non-deterministic operations (uuid.uuid4) from the workflow.
    """
    
    __pydantic_ai_agents__ = [
        temporal_company_agent,
        temporal_balance_agent,
        temporal_cashflow_agent,
        temporal_summarizer_agent,
    ]

    @workflow.run
    async def run(self, user_query: str) -> str:
        workflow.logger.info(f"Starting graph execution for query: {user_query}")
        
        # Execute the graph as an activity to avoid non-deterministic uuid.uuid4 calls
        result = await workflow.execute_activity(
            execute_graph_activity,
            user_query,
            start_to_close_timeout=timedelta(minutes=5),
        )
        
        workflow.logger.info("Graph execution completed")
        return result

# =====================================================================
# MAIN EXECUTION
# =====================================================================
async def main():
    """
    This is how you run it - clean and simple!
    The graph structure is preserved while getting Temporal's durability.
    """
    client = await Client.connect("localhost:7233", plugins=[PydanticAIPlugin()])
    
    # Start worker
    async with Worker(
        client,
        task_queue="financial-graph-queue-2",
        workflows=[FinancialGraphWorkflow],
        activities=[execute_graph_activity],
    ):
        print("Worker started. Executing PydanticGraph via Temporal...")
        
        # Execute the workflow - this runs your graph with durability!
        result = await client.execute_workflow(
            FinancialGraphWorkflow.run,
            "Whats the balance sheet and cash flow of Reliance digital",
            id=f"financial-graph-{int(time.time())}",
            task_queue="financial-graph-queue-2",
        )
        
        print(f"\n{'='*60}")
        print(f"Final Result: {result}")
        print(f"{'='*60}\n")

# =====================================================================
# STANDALONE GRAPH EXECUTION (without Temporal, for testing)
# =====================================================================
async def run_graph_standalone():
    """
    You can still run the graph standalone for testing/development
    """
    state = CompanyState(
        user_query="Whats the balance sheet and cash flow of Reliance digital"
    )
    g = Graph(nodes=(CompanyNameResolver, BalanceSheetAndCashflow, Summarizer))
    
    result = await g.run(CompanyNameResolver(), state=state)
    print(f"Standalone Result: {result.response}")

if __name__ == "__main__":
    import sys
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # Run with Temporal
    asyncio.run(main())
    
    # Or run standalone for testing
    # asyncio.run(run_graph_standalone())