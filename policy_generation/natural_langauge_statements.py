import json
import os
from dotenv import load_dotenv
from openai import OpenAI
import pandas as pd
from pathlib import Path

acre_acp_path = Path("policy_generation/input/litroacp/data_acp/acre_acp.jsonl")
acre_acp_records = [
    {
        "natural_language_statements": json.loads(line).get("text", ""),
        "datalog_subjects": "",
        "datalog_objects": "",
        "datalog_relationships": "",
        "datalog_actions": "",
    }
    for line in acre_acp_path.read_text(encoding="utf-8").splitlines()
    if line.strip()
]
acre_acp_df = pd.DataFrame(acre_acp_records)
print(acre_acp_df.head())

collected_acp_path = Path(
    "policy_generation/input/litroacp/data_acp/collected_acp.jsonl"
)
collected_acp_records = [
    {
        "natural_language_statements": json.loads(line).get("text", ""),
        "datalog_subjects": "",
        "datalog_objects": "",
        "datalog_relationships": "",
        "datalog_actions": "",
    }
    for line in collected_acp_path.read_text(encoding="utf-8").splitlines()
    if line.strip()
]
collected_acp_df = pd.DataFrame(collected_acp_records)
print(collected_acp_df.head())

cyber_acp_path = Path("policy_generation/input/litroacp/data_acp/cyber_acp.jsonl")
cyber_acp_records = [
    {
        "natural_language_statements": json.loads(line).get("text", ""),
        "datalog_subjects": "",
        "datalog_objects": "",
        "datalog_relationships": "",
        "datalog_actions": "",
    }
    for line in cyber_acp_path.read_text(encoding="utf-8").splitlines()
    if line.strip()
]
cyber_acp_df = pd.DataFrame(cyber_acp_records)
print(cyber_acp_df.head())

ibm_acp_path = Path("policy_generation/input/litroacp/data_acp/ibm_acp.jsonl")
ibm_acp_records = [
    {
        "natural_language_statements": json.loads(line).get("text", ""),
        "datalog_subjects": "",
        "datalog_objects": "",
        "datalog_relationships": "",
        "datalog_actions": "",
    }
    for line in ibm_acp_path.read_text(encoding="utf-8").splitlines()
    if line.strip()
]
ibm_acp_df = pd.DataFrame(ibm_acp_records)
print(ibm_acp_df.head())

t2p_acp_path = Path("policy_generation/input/litroacp/data_acp/t2p_acp.jsonl")
t2p_acp_records = [
    {
        "natural_language_statements": json.loads(line).get("text", ""),
        "datalog_subjects": "",
        "datalog_objects": "",
        "datalog_relationships": "",
        "datalog_actions": "",
    }
    for line in t2p_acp_path.read_text(encoding="utf-8").splitlines()
    if line.strip()
]
t2p_acp_df = pd.DataFrame(t2p_acp_records)
print(t2p_acp_df.head())


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

# system_prompt = """
# You are an access control policy-translation assistant. Your task is to translate access control policies (expressed in natural language statements) into a Datalog-based Intermediate Representation (IR) that is suitable for mapping into different Relationship-Based Access Control (ReBAC) models. The user will provide some exam text. Please translate the "natural language statements" into Datalog and output them in JSON format.

# EXAMPLE INPUT:
# The drug desired to be prescribed is checked against the patient's drug allergies.

# EXAMPLE JSON OUTPUT:
# {
#     "natural_language_statements": "The drug desired to be prescribed is checked against the patient's drug allergies.",
#     "datalog_subjects": "Patient(P), Prescriber(D).",
#     "datalog_objects": "Drug(DR).",
#     "datalog_relationships": "has_allergy(P, DR) :- Patient(P), Drug(DR).",
#     "datalog_actions": "can_prescribe(D, P, DR) :- Prescriber(D), Patient(P), Drug(DR), not has_allergy(P, DR).",
# }
# """

# user_prompt = "Employees ranked as professors or tenured assistant professors can select from, insert into, and delete from graduate admission related tables in the database."

# response = client.chat.completions.create(
#     model="deepseek-chat",
#     messages=[
#         {"role": "system", "content": system_prompt},
#         {"role": "user", "content": user_prompt},
#     ],
#     response_format={"type": "json_object"},
# )

# json_res = response.choices[0].message.content

# print(json.dumps(json_res or ""))

system_prompt_path = Path(
    "policy_generation/input/prompts/system_prompt_for_natural_language_statements.txt"
)
system_prompt = system_prompt_path.read_text(encoding="utf-8")


def translate_statement(text: str) -> dict[str, str]:
    if not text.strip():
        return {
            "datalog_subjects": "",
            "datalog_objects": "",
            "datalog_relationships": "",
            "datalog_actions": "",
        }

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
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


def enrich_dataframe(name: str, df: pd.DataFrame) -> pd.DataFrame:
    print(f"Processing {name} ({len(df)} rows)")
    enrichments = df["natural_language_statements"].apply(
        lambda text: pd.Series(translate_statement(text))
    )
    df[
        [
            "datalog_subjects",
            "datalog_objects",
            "datalog_relationships",
            "datalog_actions",
        ]
    ] = enrichments
    print(df.head())
    return df


acre_acp_df = enrich_dataframe("acre_acp", acre_acp_df)
collected_acp_df = enrich_dataframe("collected_acp", collected_acp_df)
cyber_acp_df = enrich_dataframe("cyber_acp", cyber_acp_df)
ibm_acp_df = enrich_dataframe("ibm_acp", ibm_acp_df)
t2p_acp_df = enrich_dataframe("t2p_acp", t2p_acp_df)
acre_acp_df.to_csv("policy_generation/output/litroacp/acre_acp.csv", index=False)
collected_acp_df.to_csv(
    "policy_generation/output/litroacp/collected_acp.csv", index=False
)
cyber_acp_df.to_csv("policy_generation/output/litroacp/cyber_acp.csv", index=False)
ibm_acp_df.to_csv("policy_generation/output/litroacp/ibm_acp.csv", index=False)
t2p_acp_df.to_csv("policy_generation/output/litroacp/t2p_acp.csv", index=False)
print("All done.")
