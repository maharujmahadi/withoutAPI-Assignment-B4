"""Agent integration for Mistral API with tool calling.

This module defines a strict system prompt and an execution loop that ensures the LLM
invokes the deterministic tools `calculate_vulnerability_score` and
`estimate_retrofit_cost` to generate a final report.

The implementation is intentionally simple and robust: it executes any tool calls made by the
model and feeds the tool outputs back to the model until the model returns a final message.
"""

from __future__ import annotations

import os
import json
from typing import Any, Dict, List, Optional, Tuple

import requests

from tools import calculate_vulnerability_score, estimate_retrofit_cost


MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"


def get_api_key() -> str:
    key = os.environ.get("MISTRAL_API_KEY") or "cQwUVAjWVPgxsPAlGyaehrQKykV9CItF"
    if not key:
        raise EnvironmentError(
            "MISTRAL_API_KEY is not set. Set it in your environment (or in a .env file) to use the agent."  # noqa: E501
        )
    return key


def _get_tool_definitions() -> List[Dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "calculate_vulnerability_score",
                "description": (
                    "Compute a vulnerability risk tier for a building based on soil zone, "
                    "construction year, soft story condition, and structure type. "
                    "Returns detailed scoring information."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "soil_type": {
                            "type": "string",
                            "description": "Soil/zone classification for Dhaka (Zone 1, Zone 2, Zone 3).",
                        },
                        "construction_year": {
                            "type": "integer",
                            "description": "The building construction year (e.g., 1995).",
                        },
                        "soft_story": {
                            "type": "string",
                            "description": "Whether the ground floor is open/piloti or solid (e.g., 'open ground floor').",
                        },
                        "structure_type": {
                            "type": "string",
                            "description": "Structural system (e.g., 'RC Soft Story', 'URM', 'RC Infilled').",
                        },
                    },
                    "required": [
                        "soil_type",
                        "construction_year",
                        "soft_story",
                        "structure_type",
                    ],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "estimate_retrofit_cost",
                "description": (
                    "Provide a rough retrofit cost estimate based on a selected intervention type, "
                    "a quantity (in meters or sqm depending on the method), zone, and number of floors."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "intervention_type": {
                            "type": "string",
                            "description": "Selected retrofit method (e.g., 'Shear Walls (with footing)', 'Column Jacketing (with footing)', 'Deep foundation retrofitting').",
                        },
                        "quantity": {
                            "type": "number",
                            "description": "Quantity of work per floor (e.g., meters of columns, sqm of walls).",
                        },
                        "zone": {
                            "type": "string",
                            "description": "Soil/zone classification (Zone 1/Zone 2/Zone 3).",
                        },
                        "num_floors": {
                            "type": "integer",
                            "description": "Number of floors (including ground floor) used for escalation in cost calculations.",
                        },
                    },
                    "required": [
                        "intervention_type",
                        "quantity",
                        "zone",
                        "num_floors",
                    ],
                },
            },
        },
    ]


def _run_mistral_request(
    messages: List[Dict[str, Any]],
    tools: Optional[List[Dict[str, Any]]] = None,
    tool_choice: str = "auto",
) -> Dict[str, Any]:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {get_api_key()}",
    }

    payload: Dict[str, Any] = {
        "model": "mistral-large-latest",  # Use a model that supports tool calling
        "messages": messages,
        "temperature": 0.2,
    }

    if tools is not None:
        payload["tools"] = tools
        payload["tool_choice"] = tool_choice

    response = requests.post(MISTRAL_API_URL, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    return response.json()


def _execute_tool_call(name: str, arguments: Dict[str, Any]) -> Tuple[str, Any]:
    """Execute the deterministic python tool and return a tool response string."""
    if name == "calculate_vulnerability_score":
        result = calculate_vulnerability_score(
            soil_type=arguments.get("soil_type", ""),
            construction_year=int(arguments.get("construction_year", 0)),
            soft_story=arguments.get("soft_story", ""),
            structure_type=arguments.get("structure_type", ""),
        )
        return (
            name,
            {
                "zone": result.zone,
                "zone_points": result.zone_points,
                "year": result.year,
                "year_points": result.year_points,
                "soft_story": result.soft_story,
                "soft_story_points": result.soft_story_points,
                "structure_type": result.structure_type,
                "structure_points": result.structure_points,
                "total_score": result.total_score,
                "risk_tier": result.risk_tier,
            },
        )

    if name == "estimate_retrofit_cost":
        result = estimate_retrofit_cost(
            intervention_type=arguments.get("intervention_type", ""),
            quantity=float(arguments.get("quantity", 0)),
            zone=arguments.get("zone", "Zone 2"),
            num_floors=int(arguments.get("num_floors", 2)),
        )
        return (
            name,
            {
                "intervention_type": result.intervention_type,
                "zone": result.zone,
                "quantity": result.quantity,
                "unit": result.unit,
                "num_floors": result.num_floors,
                "estimated_cost_tk": result.estimated_cost_tk,
                "details": result.details,
            },
        )

    raise ValueError(f"Unknown tool called: {name}")


def run_building_consultant(user_message: str) -> str:
    """Run the agent loop and return the final report text."""

    system_prompt = (
        "You are a rigorous structural vulnerability consultant focused on Dhaka city (Bangladesh). "
        "You must NEVER invent scoring or cost results yourself; instead, you must call the provided tools and use their deterministic output. "
        "When a user describes a building, you MUST do the following in this order: "
        "(1) extract the required parameters (zone, construction year, soft story condition, structure type, quantity of work, number of floors), "
        "(2) call the function calculate_vulnerability_score with those parameters, "
        "(3) based on the returned risk tier, choose a fitting retrofit intervention and call estimate_retrofit_cost (zone, quantity, and floors must be consistent with the building description), "
        "(4) generate a final human-readable report that cites the research tables and clearly explains how the score and cost were derived. "
        "If any required parameter is missing or unclear, ask the user a clarifying question instead of guessing."
    )

    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    tools = _get_tool_definitions()

    # First pass to let the model request a tool call.
    response = _run_mistral_request(messages, tools=tools, tool_choice="auto")
    choice = response["choices"][0]
    message = choice["message"]

    # If the model decided to call a tool, run it and feed the result back.
    tool_calls = message.get("tool_calls")
    if tool_calls:
        for tool_call in tool_calls:
            name = tool_call["function"]["name"]
            arguments_raw = tool_call["function"]["arguments"]
            # Arguments are a JSON string
            try:
                arguments = json.loads(arguments_raw)
            except Exception:
                arguments = {}

            _, tool_response = _execute_tool_call(name, arguments)

            # Add tool response back into conversation
            messages.append(message)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": json.dumps(tool_response),
                }
            )
        # Ask the model to write the final report.
        messages.append(
            {
                "role": "user",
                "content": (
                    "Please provide a final human-readable report that includes the vulnerability score, "
                    "recommended retrofit method, cost estimate, and safety advice citing the research tables."
                ),
            }
        )

        final_resp = _run_mistral_request(messages, tools=tools, tool_choice="none")
        final_msg = final_resp["choices"][0]["message"]
        return final_msg.get("content", "")

    # If no tool call was made, just return the generation.
    return message.get("content", "")
