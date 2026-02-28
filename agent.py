import asyncio
import os
import sys

from agents import Agent, Runner
from agents.mcp.server import MCPServerStdio
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

async def main():
    server_params = {
        "command": sys.executable,
        "args": ["mcp_server.py"],
        "env": os.environ.copy(),
    }
    try:
        async with MCPServerStdio(params=server_params) as mcp_server:
            # Create the agent and provide the MCP server
            agent = Agent(
                name="Shopping Assistant",
                instructions="Look at the MCP server's available tools and resources to help manage the morning briefings.",
                model="gpt-4.1",
                mcp_servers=[mcp_server]  # List of MCP servers available
            )

            # Run the agent with a query
            result = await Runner.run(agent, "Give me my to-do list for the day based on the morning briefing tools available on the MCP server.")
        
            # Print the final output
            print(result.final_output)
    except Exception as e:
        print(f"An error occurred: {e}")
        raise

    
if __name__ == "__main__":
    print("---------Agent is running---------")

    asyncio.run(main())