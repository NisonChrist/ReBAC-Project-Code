import json
import os
from dotenv import load_dotenv
from openai import OpenAI
import pandas as pd
from pathlib import Path


API_KEY: str | None | RuntimeError = (
    os.getenv("DEEPSEEK_API_KEY")
    if load_dotenv(dotenv_path=".env")
    else RuntimeError(".env file NOT found!")
)

# For type checking
assert isinstance(API_KEY, str)

client = OpenAI(
    api_key=API_KEY,
    base_url="https://api.deepseek.com",
)


def translate2datalog(xacml_str: str) -> dict[str, str]:
    system_prompt_path = Path(
        "policy_generation/input/prompts/system_prompt_for_xacml.txt"
    )
    system_prompt = system_prompt_path.read_text(encoding="utf-8")
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": xacml_str,
            },
        ],
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content or "{}"
    parsed = json.loads(content)

    return {
        "datalog_subjects": parsed.get("datalog_subjects", ""),
        "datalog_objects": parsed.get("datalog_objects", ""),
        "datalog_relationships": parsed.get("datalog_relationships", ""),
        "datalog_actions": parsed.get("datalog_actions", ""),
    }


input_xacml_dir = Path("policy_generation/input/xacml/xacBench-datasets")
output_xacml_dir = Path("policy_generation/output/xacml/xacBench")
output_xacml_dir.mkdir(parents=True, exist_ok=True)

for xacml_file in input_xacml_dir.glob("*.csv"):
    df = pd.read_csv(xacml_file)

    datalog_subjects_list = []
    datalog_objects_list = []
    datalog_relationships_list = []
    datalog_actions_list = []

    for _, row in df.iterrows():
        xacml_str = row["xacml"]
        datalog_parts = translate2datalog(xacml_str)

        datalog_subjects_list.append(datalog_parts["datalog_subjects"])
        datalog_objects_list.append(datalog_parts["datalog_objects"])
        datalog_relationships_list.append(datalog_parts["datalog_relationships"])
        datalog_actions_list.append(datalog_parts["datalog_actions"])

    df["datalog_subjects"] = datalog_subjects_list
    df["datalog_objects"] = datalog_objects_list
    df["datalog_relationships"] = datalog_relationships_list
    df["datalog_actions"] = datalog_actions_list

    output_file_path = output_xacml_dir / xacml_file.name
    df.to_csv(output_file_path, index=False)
