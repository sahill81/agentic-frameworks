import asyncio
import logging
from agents import company_name_provider_agent, balance_sheet_agent
import logfire


logfire.configure()
logfire.instrument_pydantic_ai()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



async def main() :
    result =  await company_name_provider_agent.run("Whats the company symbol for Reliance digital")
    logger.info(f"result--->${result.output}")


if __name__ == "__main__" : 
    asyncio.run(main())
