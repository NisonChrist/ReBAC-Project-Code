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


input_xacml_dir = Path("policy_generation/input/xacml")
output_xacml_dir = Path("policy_generation/output/xacml")
output_xacml_dir.mkdir(parents=True, exist_ok=True)

# Recursively find all XML files
xml_files = list(input_xacml_dir.rglob("*.xml"))
print(f"Found {len(xml_files)} XML files to process")

for xml_file in xml_files:
    # get relative path to maintain directory structure
    relative_path = xml_file.relative_to(input_xacml_dir)
    output_subdir = output_xacml_dir / relative_path.parent
    output_subdir.mkdir(parents=True, exist_ok=True)

    print(f"\nProcessing {relative_path}...")
    try:
        xacml_str = xml_file.read_text(encoding="utf-8")
        json_res = translate2datalog(xacml_str)
        json_res["xacml"] = xacml_str

        df = pd.DataFrame([json_res])
        if "xacml" in df.columns:
            cols = ["xacml"] + [c for c in df.columns if c != "xacml"]
            df = df[cols]

        output_csv_path = output_subdir / f"{xml_file.stem}.csv"
        df.to_csv(output_csv_path, index=False)
        print(f"✓ Saved to {output_csv_path.relative_to(output_xacml_dir.parent)}")
    except Exception as e:
        print(f"✗ Error processing {relative_path}: {e}")

print(f"\nAll files processed. Output saved to {output_xacml_dir}")
