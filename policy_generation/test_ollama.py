# from enum import Enum
from string import Template

import pandas as pd

# from typing import Literal, TypedDict
from ollama import chat


class LLM:
    def __init__(self, model: str, temperature: float):
        self.model = model
        self.temperature = temperature

    def generate(self, prompt: str) -> str | None:
        response = chat(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            options={"temperature": self.temperature},
        )
        return response.message.content


llm = LLM("deepseek-v3.1:671b-cloud", 0)

natural_language_statements: str = (
    "The drug desired to be prescribed is checked against the patient's drug allergies."
)
prompt_template_for_natural_languages = Template("""
Convert the following natural language access control policy statements into a Datalog format:
${natural_language_statements}
Do not include any explanations, only provide the Datalog representation. The Datalog should be complete and accurate, reflecting all the details mentioned in the natural language statements. Focus on the main components such as subjects, objects, actions, and relationships.
""")
datalog_from_natural_languages = llm.generate(
    prompt_template_for_natural_languages.substitute(
        natural_language_statements=natural_language_statements
    )
)
print(datalog_from_natural_languages)
