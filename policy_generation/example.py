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
    """
    <?xml version="1.0" encoding="UTF-8"?>
    <Policy xmlns="urn:oasis:names:tc:xacml:3.0:core:schema:wd-17" PolicyId="medi-xpath-test-policy" RuleCombiningAlgId="urn:oasis:names:tc:xacml:1.0:rule-combining-algorithm:first-applicable" Version="1.0">
    <Description>XPath evaluation is done with respect to content elementand check for a matching value. Here content element has been bounded with custom namespace and prefix</Description>
    <PolicyDefaults>
        <XPathVersion>http://www.w3.org/TR/1999/REC-xpath-19991116</XPathVersion>
    </PolicyDefaults>
    <Target>
        <AnyOf>
            <AllOf>
                <Match MatchId="urn:oasis:names:tc:xacml:1.0:function:string-regexp-match">
                <AttributeValue DataType="http://www.w3.org/2001/XMLSchema#string">read</AttributeValue>
                <AttributeDesignator MustBePresent="false" Category="urn:oasis:names:tc:xacml:3.0:attribute-category:action" AttributeId="urn:oasis:names:tc:xacml:1.0:action:action-id" DataType="http://www.w3.org/2001/XMLSchema#string" />
                </Match>
            </AllOf>
        </AnyOf>
    </Target>
    <Rule RuleId="rule1" Effect="Permit">
        <Description>Rule to match value in content element using XPath</Description>
        <Condition>
            <Apply FunctionId="urn:oasis:names:tc:xacml:1.0:function:any-of">
                <Function FunctionId="urn:oasis:names:tc:xacml:1.0:function:string-equal" />
                <Apply FunctionId="urn:oasis:names:tc:xacml:1.0:function:string-one-and-only">
                <AttributeDesignator Category="urn:oasis:names:tc:xacml:1.0:subject-category:access-subject" AttributeId="urn:oasis:names:tc:xacml:1.0:subject:subject-id" DataType="http://www.w3.org/2001/XMLSchema#string" MustBePresent="false" />
                </Apply>
                <AttributeSelector MustBePresent="false" Category="urn:oasis:names:tc:xacml:3.0:attribute-category:resource" Path="//ak:record/ak:patient/ak:patientId/text()" DataType="http://www.w3.org/2001/XMLSchema#string" />
            </Apply>
        </Condition>
    </Rule>
    <Rule RuleId="rule2" Effect="Deny">
        <Description>Deny rule</Description>
    </Rule>
    </Policy>
    """
)
print(json.dumps(output, indent=2))
