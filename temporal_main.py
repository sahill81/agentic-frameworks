# from dataclasses import dataclass
# from temporalio import workflow, activity

# # @dataclass
# # class Params : 
# #     name  : str

# # @activity.defn
# # async def print_name(name : str) :
# #     print(f"Hello {name}") 



# # @workflow.defn
# # class BaseWorkflow :
# #     @workflow.run
# #     async def run(self, name : str) :
# #         return await workflow.execute_activity(
# #             print_name,
# #             Params(name = "sahil")
# #         )

# import asyncio
# import uuid

# from dotenv import load_dotenv
# from temporalio import workflow
# from temporalio.client import Client
# from temporalio.worker import Worker

# from pydantic_ai import Agent
# from pydantic_ai.durable_exec.temporal import (
#     PydanticAIPlugin,
#     PydanticAIWorkflow,
#     TemporalAgent,
# )

# # load_dotenv()


# # agent = Agent(
# #     'gpt-4o',
# #     instructions="You're an expert in geography.",
# #     name='geography',  
# # )

# # temporal_agent = TemporalAgent(agent)  


# # @workflow.defn
# # class GeographyWorkflow(PydanticAIWorkflow):  
# #     __pydantic_ai_agents__ = [temporal_agent]  

# #     @workflow.run
# #     async def run(self, prompt: str) -> str:
# #         result = await temporal_agent.run(prompt)  
# #         return result.output


# # async def main():
# #     client = await Client.connect(  
# #         'localhost:7233',  
# #         plugins=[PydanticAIPlugin()],  
# #     )

# #     async with Worker(  
# #         client,
# #         task_queue='geography',
# #         workflows=[GeographyWorkflow],
# #     ):
# #         output = await client.execute_workflow(  
# #             GeographyWorkflow.run,
# #             args=['What is the capital of Mexico?'],
# #             id=f'geography-{uuid.uuid4()}',
# #             task_queue='geography',
# #         )
# #         print(output)
# #         #> Mexico City (Ciudad de México, CDMX)
# # if __name__ == "__main__" : 
# #     asyncio.run(main())


# from agents import company_name_provider_agent, balance_sheet_agent ,cash_flow_agent, summarizer_agent
# from temporalio.common import RetryPolicy
# from temporalio.workflow import ActivityConfig
# from datetime import timedelta

# load_dotenv()


# temporal_company_name_agent = TemporalAgent(company_name_provider_agent)
# temporal_balance_sheet_agent = TemporalAgent(balance_sheet_agent)
# temporal_cash_flow_agent = TemporalAgent(cash_flow_agent,)       
# temporal_summarizer_agent = TemporalAgent(summarizer_agent)


# @workflow.defn
# class FinancialWorkflow(PydanticAIWorkflow):
#     __pydantic_ai_agents__ = [
#         temporal_company_name_agent,
#         temporal_balance_sheet_agent,
#         temporal_cash_flow_agent,
#         temporal_summarizer_agent
#     ]

#     @workflow.run
#     async def run(self, user_query: str) -> str:
#         company_symbol_result = await temporal_company_name_agent.run(user_query)
#         symbol = company_symbol_result.output.symbol

#         balance_sheet_result = await temporal_balance_sheet_agent.run(f"This is the symbol of the company {symbol}.")
#         try : 
#             cash_flow_result = await temporal_cash_flow_agent.run(f"This is the symbol of the company {symbol}.")
#         except Exception as e:
#             raise RuntimeError(f"Error fetching cash flow: {e}")
#             # cash_flow_result = None

#         summary_input = f"The balance sheet is {balance_sheet_result.output} and the cash flow is {cash_flow_result.output}"
#         summarizer_result = await temporal_summarizer_agent.run(summary_input)

#         return summarizer_result.output
    
# async def main_financial():
#     client = await Client.connect(
#         'localhost:7233',
#         plugins=[PydanticAIPlugin()],
#     )

#     async with Worker(
#         client,
#         task_queue='financial',
#         workflows=[FinancialWorkflow],
#     ):
#         output = await client.execute_workflow(
#             FinancialWorkflow.run,
#             args=['Provide a summary of the balance sheet and the cash flow of Reliance Industries.'],
#             id=f'financial-{uuid.uuid4()}',
#             task_queue='financial',
#         )
#         print(output)

# if __name__ == "__main__" : 
#     asyncio.run(main_financial())