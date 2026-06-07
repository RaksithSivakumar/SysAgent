import logging
import sys
from typing import Dict, Any, Optional, Iterator
import google.generativeai as genai
from google.generativeai.types import Tool

from sysagent.config import Config, get_api_key, print_key_missing_instructions
from sysagent.security.sandbox import SandboxedCollector
from sysagent.collectors import register_all_collectors
from sysagent.agent.tools import build_tools
from sysagent.agent.prompts import SYSTEM_PROMPT

logger = logging.getLogger("sysagent.agent.core")

class GeminiAgent:
    def __init__(self, config: Optional[Config] = None, sandbox: Optional[SandboxedCollector] = None):
        self.config = config or Config.load()
        
        # Setup sandbox and register all collectors
        if sandbox is None:
            self.sandbox = SandboxedCollector(self.config)
            register_all_collectors(self.sandbox)
            # Add full report registration directly
            self.sandbox.register_collector("get_full_report", self.sandbox.get_full_report)
        else:
            self.sandbox = sandbox

        self.api_key = get_api_key()
        self.chat = None
        self.model = None

        if not self.api_key:
            # Missing API key warning - handled during REPL or command execution
            logger.warning("No Gemini API key was found in environment or keyring.")
        else:
            self.initialize_session()

    def initialize_session(self) -> None:
        """Initializes the Google Gemini client and chat context."""
        try:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(
                model_name=self.config.model,
                system_instruction=SYSTEM_PROMPT,
                tools=build_tools(),
            )
            # Disable automatic function calling so we control the execution in the sandbox
            self.chat = self.model.start_chat(enable_automatic_function_calling=False)
            logger.info(f"Gemini chat session initialized with model: {self.config.model}")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini GenerativeModel: {e}")
            self.chat = None

    def agentic_loop(self, user_message: str) -> Iterator[str]:
        """
        Runs the main agent loop with Gemini. Resolves tool calls requested by Gemini
        iteratively, yields text responses, and logs metrics.
        """
        if not self.api_key:
            print_key_missing_instructions()
            yield "Setup required: Please configure your GEMINI_API_KEY first."
            return

        if not self.chat:
            self.initialize_session()
            if not self.chat:
                yield "Failed to establish a connection with Google Gemini API."
                return

        logger.info(f"Sending message to Gemini: {user_message}")
        try:
            response = self.chat.send_message(user_message)
        except Exception as e:
            logger.error(f"Gemini connection error: {e}")
            yield f"API Error: Failed to communicate with Gemini. Check your API key and connection. ({e})"
            return

        while True:
            # Make sure candidates and parts are present
            if not response.candidates or not response.candidates[0].content.parts:
                yield "Error: Received empty response from model."
                break

            parts = response.candidates[0].content.parts
            
            # Filter all function call requests
            function_calls = [p.function_call for p in parts if hasattr(p, 'function_call') and p.function_call.name]
            
            if function_calls:
                response_parts = []
                for call in function_calls:
                    fn_name = call.name
                    fn_args = dict(call.args)
                    
                    logger.info(f"Gemini requested tool execution: {fn_name} with args {fn_args}")
                    yield f"\n*[SysAgent is running tool `{fn_name}`...]*\n"
                    
                    # Execute tool via Sandbox
                    result = self.sandbox.call_tool(fn_name, fn_args)
                    
                    # Build response part
                    response_parts.append(
                        genai.protos.Part(
                            function_response=genai.protos.FunctionResponse(
                                name=fn_name,
                                response={"result": result}
                            )
                        )
                    )
                
                # Send all tool execution results back to Gemini in one turn
                try:
                    response = self.chat.send_message(response_parts)
                except Exception as e:
                    logger.error(f"Failed to return tool results to Gemini: {e}")
                    yield f"Error: Tool execution feedback failed: {e}"
                    break
            else:
                # Gemini returned final text
                texts = [p.text for p in parts if hasattr(p, 'text') and p.text]
                final_text = "".join(texts)
                yield final_text
                break
