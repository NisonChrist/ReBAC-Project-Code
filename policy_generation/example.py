import json
import os
from dotenv import load_dotenv
from openai import OpenAI
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


def translate_statement(text: str) -> dict[str, str]:
    system_prompt_path = Path(
        "policy_generation/input/prompts/system_prompt_for_xacml.txt"
    )
    system_prompt = system_prompt_path.read_text(encoding="utf-8")
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


output = translate_statement(
    # "A user working on a project can read the project schedule."
    """
    <Request xmlns="urn:oasis:names:tc:xacml:3.0:core:schema:wd-17" CombinedDecision="false" ReturnPolicyIdList="false">
        <Attributes Category="urn:oasis:names:tc:xacml:3.0:attribute-category:action">
            <Attribute AttributeId="urn:oasis:names:tc:xacml:1.0:action:action-id" IncludeInResult="false">
                <AttributeValue DataType="http://www.w3.org/2001/XMLSchema#string">read</AttributeValue>
            </Attribute>
        </Attributes>
        <Attributes Category="urn:oasis:names:tc:xacml:1.0:subject-category:access-subject">
            <Attribute AttributeId="urn:oasis:names:tc:xacml:1.0:subject:subject-id" IncludeInResult="false">
                <AttributeValue DataType="http://www.w3.org/2001/XMLSchema#string">admin</AttributeValue>
            </Attribute>
        </Attributes>
        <Attributes Category="urn:oasis:names:tc:xacml:3.0:attribute-category:resource">
            <Attribute AttributeId="urn:oasis:names:tc:xacml:1.0:resource:resource-id" IncludeInResult="false">
                <AttributeValue DataType="http://www.w3.org/2001/XMLSchema#string">http://localhost:8280/services/echo/</AttributeValue>
            </Attribute>
        </Attributes>
        <Attributes Category="urn:oasis:names:tc:xacml:3.0:group">
            <Attribute AttributeId="group" IncludeInResult="false">
                <AttributeValue DataType="http://www.w3.org/2001/XMLSchema#string">admin</AttributeValue>
                <AttributeValue DataType="http://www.w3.org/2001/XMLSchema#string">business</AttributeValue>
            </Attribute>
        </Attributes>
    </Request>
    """
)
print(json.dumps(output, indent=2))
