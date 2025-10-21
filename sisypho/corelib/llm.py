"""
Core library for interacting with the LLM.
"""

import json
import os
from typing import Dict, Any, Union, Type
import requests

def _convert_to_json_schema(output_schema: Dict[str, Type]) -> Dict[str, Any]:
    """
    Convert a simple type dictionary to JSON schema format.
    
    Args:
        output_schema: Dictionary mapping field names to Python types
        
    Returns:
        Proper JSON schema dictionary
    """
    # Type mapping from Python types to JSON schema types
    type_mapping = {
        str: "string",
        int: "integer", 
        float: "number",
        bool: "boolean",
        list: "array",
        dict: "object"
    }
    
    properties = {}
    required = []
    
    for field_name, field_type in output_schema.items():
        if field_type in type_mapping:
            properties[field_name] = {
                "type": type_mapping[field_type],
                "description": f"The {field_name.replace('_', ' ')}"
            }
            required.append(field_name)
        else:
            # Fallback for unknown types
            properties[field_name] = {
                "type": "string",
                "description": f"The {field_name.replace('_', ' ')}"
            }
            required.append(field_name)
    
    return {
        "title": "Response",
        "description": "Response schema",
        "type": "object",
        "properties": properties,
        "required": required
    }

def llm_call(system_prompt: str, user_prompt: str, output_schema: Union[Dict[str, Type], Dict[str, Any]], enable_web_search: bool = False) -> Dict[str, Any]:
    """
    Call the LLM.

    Args:
        system_prompt: The system prompt to use.
        user_prompt: The user prompt to use.
        output_schema: The output schema to use. Can be either a simple type dictionary 
                      like {"field": str} or a full JSON schema.
        enable_web_search: Whether to enable web search tools.

    Returns:
        The response from the LLM.

    Examples:
        >>> llm_call(
        ...     system_prompt="Determine whether the user prefers chocolate or vanilla.",
        ...     user_prompt="I prefer chocolate over vanilla generally.",
        ...     output_schema={"preferred_flavor": str},
        ... )
        {'preferred_flavor': 'chocolate'}
    """
    
    # Check if this is a simple type dictionary and convert to JSON schema
    if output_schema and isinstance(output_schema, dict):
        # Check if it's a simple type dictionary (values are Python types)
        if all(isinstance(v, type) for v in output_schema.values()):
            output_schema = _convert_to_json_schema(output_schema)
    
    userId = os.environ.get("SISYPHO_USER_ID")
    authHeaders = os.environ.get("SISYPHO_AUTH_HEADERS")
    baseUrl = os.environ.get("SISYPHO_ENDPOINT")
    if authHeaders is None or baseUrl is None:
        raise ValueError("Auth headers or base url not set in environment variables")

    headers = json.loads(authHeaders)
    headers['Content-Type'] = "application/json"
    response = requests.post(baseUrl + "/api/corelib/llm_call/" + userId, json={"system_prompt": system_prompt, "user_prompt": user_prompt, "output_schema": output_schema, "enable_web_search": enable_web_search}, headers=headers)
    if response.status_code != 200:
        raise RuntimeError("llm call api failed with", response.status_code, response.content)
    return response.json()
