import os
import json
from typing import Dict, Any, Generator
from dotenv import load_dotenv
from openai import OpenAI
from openai.types.responses import ResponseTextDeltaEvent
from pydantic import BaseModel
from langchain_core.prompts import PromptTemplate
from config import model, save_responses
from datetime import datetime

user_dir = os.path.expanduser("~")
env_path = os.path.join(user_dir, ".env")
if os.path.exists(env_path):
    load_dotenv(env_path)

api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)


def _save_response(system_prompt: str, response_text: str, prefix: str = "response") -> None:
    """Helper function to save response to a file."""
    # Create responses directory if it doesn't exist
    responses_dir = os.path.join("output", "responses")
    system_dir = os.path.join("output", "system_prompts")
    os.makedirs(responses_dir, exist_ok=True)
    os.makedirs(system_dir, exist_ok=True)
    
    # Generate timestamped filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{prefix}_{timestamp}.txt"
    filepath = os.path.join(responses_dir, filename)
    system_filepath = os.path.join(system_dir, filename)

    # Save the response
    with open(filepath, "w") as file:
        file.write(response_text)
    with open(system_filepath, "w") as file:
        file.write(system_prompt)
    print(f"Response saved to {filepath}")


def generate_structured_response(
    input: str,
    schema: BaseModel,
    instructions: str = None,
    model: str = model,
    save_response: bool = save_responses,
) -> Dict[str, Any]:
    """Generate a structured response without streaming."""
    print("Generating structured response")
    response = client.responses.create(
        model=model,
        input=input,
        instructions=instructions,
        text={
            "format": {
                "type": "json_schema",
                "name": "BidResponse",
                "schema": schema.model_json_schema(),
            }
        },
        stream=False,
    )
    print("Response generated")
    
    if save_response:
        _save_response(response.output_text, "structured_response")
    
    return json.loads(response.output_text)


def stream_structured_response(
    input: str,
    schema: BaseModel,
    instructions: str = None,
    model: str = model,
) -> Generator[Dict[str, Any], None, None]:
    """Stream a structured response."""
    print("Starting structured response stream")
    response = client.responses.create(
        model=model,
        input=input,
        instructions=instructions,
        text={
            "format": {
                "type": "json_schema",
                "name": "BidResponse",
                "schema": schema.model_json_schema(),
            }
        },
        stream=True,
    )
    
    complete_response = ""
    count = 0
    for chunk in response:
        if isinstance(chunk, ResponseTextDeltaEvent):
            for char in chunk.delta:
                complete_response += char
                try:
                    yield json.loads(complete_response + "]}")
                    print(count)
                    count += 1
                except:
                    continue


def generate_simple_response(
    input: str, 
    instructions: str = None, 
    model: str = model,
    save_response: bool = save_responses,
) -> str:
    """Generate a simple response without streaming."""
    response = client.responses.create(
        model=model,
        input=input,
        instructions=instructions,
        stream=False
    )
    
    if save_response:
        _save_response(response.output_text, "simple_response")
    
    return response.output_text


def stream_simple_response(
    input: str, 
    instructions: str = None, 
    model: str = model,
) -> Generator[str, None, None]:
    """Stream a simple response."""
    response = client.responses.create(
        model=model,
        input=input,
        instructions=instructions,
        stream=True
    )
    
    for chunk in response:
        if isinstance(chunk, ResponseTextDeltaEvent):
            yield chunk.delta


prompts_dir_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts")


def load_prompt_template(
    prompt_name: str, input_variables: list[str]
) -> PromptTemplate:
    with open(os.path.join(prompts_dir_path, prompt_name), "r") as file:
        return PromptTemplate(template=file.read(), input_variables=input_variables)


def load_prompt(prompt_name: str, input_dict: Dict[str, Any]) -> str:
    return load_prompt_template(prompt_name, input_dict.keys()).format(**input_dict)


def load_txt_file(file_name: str) -> Dict[str, Any]:
    with open(os.path.join(prompts_dir_path, file_name), "r") as file:
        return json.loads(file.read())
