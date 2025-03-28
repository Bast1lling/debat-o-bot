import os
import json
from typing import Dict, Any, Generator, Union
from dotenv import load_dotenv
from openai import OpenAI
from openai.types.responses import ResponseTextDeltaEvent
from pydantic import BaseModel
from langchain_core.prompts import PromptTemplate
from config import model

user_dir = os.path.expanduser("~")
env_path = os.path.join(user_dir, ".env")
if os.path.exists(env_path):
    load_dotenv(env_path)

api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)


def generate_structured_response(
    input: str,
    schema: BaseModel,
    instructions: str = None,
    model: str = model,
    stream: bool = False,
) -> Union[Dict[str, Any], Generator[Dict[str, Any], None, None]]:
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
        stream=stream,
    )
    if stream:
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
    else:
        with open("output.txt", "w") as file:
            file.write(response.output_text)
        return json.loads(response.output_text)


def generate_simple_response(
    input: str, instructions: str = None, model: str = model, stream: bool = False
) -> Union[str, Generator[str, None, None]]:
    response = client.responses.create(
        model=model, input=input, instructions=instructions, stream=stream
    )
    if stream:
        for chunk in response:
            if isinstance(chunk, ResponseTextDeltaEvent):
                yield chunk.delta
    else:
        return response.output_text


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
