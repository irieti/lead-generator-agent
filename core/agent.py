"""
Autonomous agent loop.

Sends a task to Claude with all tools available.
Claude decides which tools to call and in what order.
The loop continues until Claude stops calling tools (end_turn).
"""

from __future__ import annotations

import json
from typing import Any, AsyncGenerator

import anthropic

from core.config import settings
from core.executor import execute_tool
from core.config_loader import get_config
from core.prompts import build_system_prompt
from core.tool_definitions import TOOL_DEFINITIONS
from core.logging import get_logger

logger = get_logger("agent")

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)


async def run_agent(
    task: str,
    mode: str = "auto",
    max_iterations: int = 50,
) -> AsyncGenerator[dict[str, Any], None]:

    # Build the initial user message
    user_message = f"Mode: {mode.upper()}\n\nTask: {task}"

    conversation: list[dict] = [{"role": "user", "content": user_message}]

    logger.info("agent.start", mode=mode, task=task[:100])
    yield {"type": "start", "mode": mode, "task": task}

    for iteration in range(max_iterations):
        logger.info("agent.iteration", iteration=iteration)

        # Call Claude
        response = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=4096,
            system=build_system_prompt(get_config()),
            tools=TOOL_DEFINITIONS,
            messages=conversation,
        )

        # Collect all content blocks from this response
        assistant_content = []

        for block in response.content:
            if block.type == "text" and block.text.strip():
                logger.info("agent.thinking", text=block.text[:200])
                yield {"type": "thinking", "content": block.text}
                assistant_content.append({"type": "text", "text": block.text})

            elif block.type == "tool_use":
                tool_name = block.name
                tool_inputs = block.input
                tool_use_id = block.id

                logger.info("agent.tool_call", tool=tool_name, inputs=tool_inputs)
                yield {"type": "tool_call", "tool": tool_name, "inputs": tool_inputs}

                assistant_content.append(
                    {
                        "type": "tool_use",
                        "id": tool_use_id,
                        "name": tool_name,
                        "input": tool_inputs,
                    }
                )

                # Execute the tool
                result_str = await execute_tool(tool_name, tool_inputs)
                result_data = json.loads(result_str)

                logger.info("agent.tool_result", tool=tool_name)
                yield {"type": "tool_result", "tool": tool_name, "result": result_data}

                # Append assistant message + tool result to conversation
                conversation.append({"role": "assistant", "content": assistant_content})
                conversation.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": tool_use_id,
                                "content": result_str,
                            }
                        ],
                    }
                )

                # Reset assistant_content for next iteration
                assistant_content = []
                break  # process one tool at a time, then re-invoke Claude

        else:
            # No tool_use block found — Claude is done
            if assistant_content:
                conversation.append({"role": "assistant", "content": assistant_content})

            if response.stop_reason == "end_turn":
                final_text = " ".join(
                    block.text for block in response.content if block.type == "text"
                )
                logger.info("agent.done", iterations=iteration + 1)
                yield {
                    "type": "done",
                    "output": final_text,
                    "iterations": iteration + 1,
                }
                return

        if response.stop_reason == "end_turn" and not any(
            b.type == "tool_use" for b in response.content
        ):
            final_text = " ".join(
                block.text for block in response.content if block.type == "text"
            )
            logger.info("agent.done", iterations=iteration + 1)
            yield {"type": "done", "output": final_text, "iterations": iteration + 1}
            return

    # Hit max iterations
    logger.warning("agent.max_iterations_reached", max=max_iterations)
    yield {"type": "error", "message": f"Max iterations ({max_iterations}) reached"}
