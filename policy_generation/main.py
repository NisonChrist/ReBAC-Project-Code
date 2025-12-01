import os
from typing import TypedDict
from dotenv import load_dotenv
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam
import json


class LLMConfig(TypedDict):
    MODEL_NAME: str
    BASE_URL: str
    API_KEY: str


class PathConfig(TypedDict):
    DATA_PATH: str
    OUTPUT_PATH: str
    SYSTEM_PROMPT_PATH: str


class Config(TypedDict):
    LLM: LLMConfig
    NATURAL_LANGUAGE_STATEMENTS: PathConfig
    XACML: PathConfig


API_KEY: str | None | RuntimeError = (
    os.getenv("DEEPSEEK_API_KEY")
    if load_dotenv(dotenv_path=".env")
    else RuntimeError(".env file NOT found!")
)

# For type checking
assert isinstance(API_KEY, str)

CONFIG: Config = {
    "LLM": {
        "MODEL_NAME": "deepseek-chat",
        "BASE_URL": "https://api.deepseek.com",
        "API_KEY": API_KEY,
        # "TEMPERATURE": 1,
    },
    "NATURAL_LANGUAGE_STATEMENTS": {
        "DATA_PATH": "./policy_generation/input/litroacp/data_acp/",
        "OUTPUT_PATH": "./policy_generation/output/litroacp/",
        "SYSTEM_PROMPT_PATH": "./policy_generation/prompts/system_prompt_for_natural_language_statements.txt",
    },
    "XACML": {
        "DATA_PATH": "./policy_generation/input/xacml/",
        "OUTPUT_PATH": "./policy_generation/output/xacml/",
        "SYSTEM_PROMPT_PATH": "./policy_generation/prompts/system_prompt_for_xacml.txt",
    },
}

print(CONFIG)

CLIENT = OpenAI(
    api_key=CONFIG["LLM"]["API_KEY"],
    base_url=CONFIG["LLM"]["BASE_URL"],
)

# Read each jsonl file in the directory one by one
nl_file_list: list[str] = []
for filename in os.listdir(CONFIG["NATURAL_LANGUAGE_STATEMENTS"]["DATA_PATH"]):
    nl_file_list.append(CONFIG["NATURAL_LANGUAGE_STATEMENTS"]["DATA_PATH"] + filename)
    # print(CONFIG["NATURAL_LANGUAGE_STATEMENTS"]["DATA_PATH"] + filename)

for file_path in nl_file_list:
    with open(file_path, "r") as file:
        print(f"------ Reading file: {file_path} ------")
        for line in file:
            json_obj = json.loads(line)
            print(json_obj["text"])
            user_prompt = json_obj["text"]
            messages: list[ChatCompletionMessageParam] = [
                {
                    "role": "system",
                    "content": open(
                        CONFIG["NATURAL_LANGUAGE_STATEMENTS"]["SYSTEM_PROMPT_PATH"], "r"
                    ).read(),
                },
                {"role": "user", "content": user_prompt},
            ]
            response = CLIENT.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                response_format={"type": "json_object"},
            )
            json_res = response.choices[0].message.content
            print(json.dumps(json_res or ""))



# --- IGNORE ---

# user_prompt = "Employees ranked as professors or tenured assistant professors can select from, insert into, and delete from graduate admission related tables in the database."

# messages: list[ChatCompletionMessageParam] = [
#     {"role": "system", "content": system_prompt},
#     {"role": "user", "content": user_prompt},
# ]

# response = CLIENT.chat.completions.create(
#     model="deepseek-chat", messages=messages, response_format={"type": "json_object"}
# )

# json_res = response.choices[0].message.content

# print(json.dumps(json_res or ""))
