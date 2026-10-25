import asyncio
import os
import sys
import json

from dotenv import load_dotenv
from google import genai
from google.genai import types

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY is missing from your .env file.")

gemini = genai.Client(api_key=api_key)


def convert_mcp_tools(mcp_tools):
    """Convert MCP tools into Gemini function declarations."""

    declarations = []

    for tool in mcp_tools:
        parameters = tool.inputSchema or {
            "type": "object",
            "properties": {},
        }

        declarations.append(
            types.FunctionDeclaration(
                name=tool.name,
                description=tool.description or tool.name,
                parameters_json_schema=parameters,
            )
        )

    return types.Tool(function_declarations=declarations)


async def main():
    print("\n===================================")
    print("       WorkSphere MCP AI")
    print("===================================")

    server_params = StdioServerParameters(
        command=sys.executable,
        args=["server.py"],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:

            await session.initialize()

            tools_result = await session.list_tools()
            mcp_tools = tools_result.tools

            print("\nConnected to WorkSphere MCP!")
            print("\nAvailable MCP tools:")

            for tool in mcp_tools:
                print(f"- {tool.name}")

            gemini_tools = [convert_mcp_tools(mcp_tools)]

            print("\nAsk WorkSphere anything!")
            print("Type 'exit' to stop.\n")

            while True:
                prompt = input("You: ").strip()

                if prompt.lower() in ("exit", "quit"):
                    print("WorkSphere: Goodbye, Pookie! 💗")
                    break

                if not prompt:
                    continue

                try:
                    response = await gemini.aio.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            tools=gemini_tools,
                            temperature=0.2,
                        ),
                    )

                    # Execute Gemini's requested MCP tool calls.
                    while response.function_calls:
                        function_responses = []

                        for function_call in response.function_calls:
                            tool_name = function_call.name
                            arguments = dict(function_call.args or {})

                            print(f"\nRunning MCP tool: {tool_name}")

                            result = await session.call_tool(
                                tool_name,
                                arguments=arguments,
                            )

                            result_data = []

                            for content in result.content:
                                if hasattr(content, "text"):
                                    result_data.append(content.text)
                                else:
                                    result_data.append(str(content))

                            function_responses.append(
                                types.Part.from_function_response(
                                    name=tool_name,
                                    response={
                                        "result": "\n".join(result_data),
                                        "isError": result.isError,
                                    },
                                )
                            )

                        response = await gemini.aio.models.generate_content(
                            model="gemini-2.5-flash",
                            contents=[
                                types.Content(
                                    role="user",
                                    parts=[types.Part.from_text(text=prompt)],
                                ),
                                response.candidates[0].content,
                                types.Content(
                                    role="user",
                                    parts=function_responses,
                                ),
                            ],
                            config=types.GenerateContentConfig(
                                tools=gemini_tools,
                                temperature=0.2,
                            ),
                        )

                    print(
                        "\nWorkSphere:",
                        response.text or "No text response received.",
                        "\n",
                    )

                except Exception as error:
                    print(f"\nError: {error}\n")


if __name__ == "__main__":
    asyncio.run(main())