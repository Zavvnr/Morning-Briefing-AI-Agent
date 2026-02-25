import asyncio

from requests import session
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    server_params = StdioServerParameters(
        command="python",
        args=["mcp_server.py"]
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()


            # List all tools the server provides
            tools_response = await session.list_tools()
            print("Available tools:")
            for tool in tools_response.tools:
                print(f" - {tool.name}: {tool.description}")

            # List all resources
            resources_response = await session.list_resources()
            print("\nAvailable resources:")
            for res in resources_response.resources:
                print(f" - {res.uri}: {res.description}")

            # Introspect prompts
            prompts_response = await session.list_prompts()
            print("\nAvailable prompts:")
            for p in prompts_response.prompts:
                print(f" - {p.name}: {p.description}")
                
                
            async with MCPServerStdio(params=server_params) as mcp_server:
                # Create the agent and provide the MCP server
                agent = Agent(
                name="Shopping Assistant",
                instructions="Look at the MCP server's available tools and resources to help manage the morning briefings.",
                model="gpt-4.1",
                mcp_servers=[mcp_server]  # List of MCP servers available
            )

            # Run the agent with a query
            result = await asyncio.Runner.run(agent, "Give me my to-do list for the day based on the morning briefing tools available on the MCP server.")
        
        # Print the final output
        print(result.final_output)

    
if __name__ == "__main__":
    print("---------Agent is running---------")

    asyncio.run(main())
