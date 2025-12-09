import csv
from pathlib import Path
import re
import os

import pandas as pd


def parse_term(term):
    term = term.strip()
    if not term:
        return term
    if term.startswith("'") and term.endswith("'"):
        return term
    if term.startswith('"') and term.endswith('"'):
        return term
    if term.replace(".", "", 1).isdigit():
        return term
    # Check if it is a variable (starts with uppercase or is just a word)
    # In this dataset, variables seem to be identifiers.
    return f"?{term}"


def parse_predicate(pred_str):
    is_negated = False
    pred_str = pred_str.strip()
    if pred_str.startswith("not "):
        is_negated = True
        pred_str = pred_str[4:].strip()

    # Check for infix operators =, >=, <=, >, <, !=
    # Regex for infix: term operator term
    # We need to be careful not to match inside parentheses of a predicate
    # e.g. func(A=B) - though Datalog usually doesn't have that.
    # But (G = 'height') might be passed here if we strip parens?
    # Let's try to match standard predicate first.

    match = re.match(r"(\w+)\((.*)\)", pred_str)
    if match:
        name = match.group(1)
        args_str = match.group(2)
        # Naive split by comma, but we should respect nested parens if any (e.g. function calls)
        args = []
        current = ""
        depth = 0
        for char in args_str:
            if char == "(":
                depth += 1
                current += char
            elif char == ")":
                depth -= 1
                current += char
            elif char == "," and depth == 0:
                args.append(current.strip())
                current = ""
            else:
                current += char
        if current:
            args.append(current.strip())

        new_args = [parse_term(arg) for arg in args]
        formatted = f"{name}({','.join(new_args)})"
        if is_negated:
            formatted = f"not {formatted}"
        return formatted

    # Check for infix operators
    infix_match = re.match(r"(.+?)\s*(=|>=|<=|>|<|!=|in)\s*(.+)", pred_str)
    if infix_match:
        left = infix_match.group(1)
        op = infix_match.group(2)
        right = infix_match.group(3)
        # If left contains '(', it might be a predicate that failed the first check?
        # No, because first check matches \w+(...)
        return f"{parse_term(left)} {op} {parse_term(right)}"

    # Handle (A ; B) - Disjunction or grouped expression
    if pred_str.startswith("(") and pred_str.endswith(")"):
        content = pred_str[1:-1]
        # Recursively parse?
        # If it contains ';', it's disjunction.
        if ";" in content:
            parts = content.split(";")
            parsed_parts = [parse_predicate(p) for p in parts]
            return f"({' ; '.join(parsed_parts)})"
        else:
            return f"({parse_predicate(content)})"

    return pred_str


def convert_datalog_to_carminati(csv_path):
    results = []
    if not os.path.exists(csv_path):
        print(f"File not found: {csv_path}")
        return []

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            action = row.get("datalog_actions", "")
            if not action:
                continue

            # Remove newlines
            action = action.replace("\n", " ")

            # Split Head :- Body
            if ":-" in action:
                parts = action.split(":-")
                head_str = parts[0].strip()
                body_str = parts[1].strip()
                if body_str.endswith("."):
                    body_str = body_str[:-1]

                # Parse Head
                head_formatted = parse_predicate(head_str)

                # Parse Body
                body_preds = []
                current = ""
                depth = 0
                for char in body_str:
                    if char == "(":
                        depth += 1
                        current += char
                    elif char == ")":
                        depth -= 1
                        current += char
                    elif char == "," and depth == 0:
                        body_preds.append(current.strip())
                        current = ""
                    else:
                        current += char
                if current:
                    body_preds.append(current.strip())

                formatted_body_preds = []
                for pred in body_preds:
                    formatted_body_preds.append(parse_predicate(pred))

                # Construct SWRL
                # Body => Head
                swrl = f"{' ∧ '.join(formatted_body_preds)} => {head_formatted}"
                results.append(f"{swrl}")
            else:
                # Fact?
                pass

    return results


def translate(input_path: Path, output_path: Path):
    # acre_acp_input_path = Path(
    #     "/Users/ziv/Desktop/ReBAC-Project-Code/policy_generation/output/litroacp/acre_acp.csv"
    # )
    acre_acp_input_path = input_path
    acre_acp_swrl_rules = convert_datalog_to_carminati(acre_acp_input_path)
    for rule in acre_acp_swrl_rules:
        print(rule)
    # save to csv file
    # output_path = Path(
    #     "/Users/ziv/Desktop/ReBAC-Project-Code/policy_translation/output/carminati/acre_acp.csv"
    # )
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["carminati"])
        for rule in acre_acp_swrl_rules:
            writer.writerow([rule])
    # merge the output csv file with input csv file using pandas
    acre_acp_input_df = pd.read_csv(acre_acp_input_path)
    acre_acp_output_df = pd.read_csv(output_path)
    acre_acp_merged_df = pd.concat([acre_acp_input_df, acre_acp_output_df], axis=1)
    acre_acp_merged_output_path = output_path
    acre_acp_merged_df.to_csv(acre_acp_merged_output_path, index=False)
    print(f"Merged output saved to {acre_acp_merged_output_path}")


if __name__ == "__main__":
    # Natural Language
    acre_acp_input_path = Path("policy_generation/output/litroacp/acre_acp.csv")
    acre_acp_output_path = Path("policy_translation/output/carminati/acre_acp.csv")
    translate(acre_acp_input_path, acre_acp_output_path)
    collected_acp_input_path = Path(
        "policy_generation/output/litroacp/collected_acp.csv"
    )
    collected_acp_output_path = Path(
        "policy_translation/output/carminati/collected_acp.csv"
    )
    translate(collected_acp_input_path, collected_acp_output_path)
    cyber_acp_input_path = Path("policy_generation/output/litroacp/cyber_acp.csv")
    cyber_acp_output_path = Path("policy_translation/output/carminati/cyber_acp.csv")
    translate(cyber_acp_input_path, cyber_acp_output_path)
    ibm_acp_input_path = Path("policy_generation/output/litroacp/ibm_acp.csv")
    ibm_acp_output_path = Path("policy_translation/output/carminati/ibm_acp.csv")
    translate(ibm_acp_input_path, ibm_acp_output_path)
    t2p_acp_input_path = Path("policy_generation/output/litroacp/t2p_acp.csv")
    t2p_acp_output_path = Path("policy_translation/output/carminati/t2p_acp.csv")
    translate(t2p_acp_input_path, t2p_acp_output_path)

    # XACML
    xacml2_1_input_path = Path("policy_generation/output/xacml/xacBench/xacml2_1.csv")
    xacml2_1_output_path = Path("policy_translation/output/carminati/xacml2_1.csv")
    translate(xacml2_1_input_path, xacml2_1_output_path)

    xacml2_2_input_path = Path("policy_generation/output/xacml/xacBench/xacml2_2.csv")
    xacml2_2_output_path = Path("policy_translation/output/carminati/xacml2_2.csv")
    translate(xacml2_2_input_path, xacml2_2_output_path)

    xacml2_3_input_path = Path("policy_generation/output/xacml/xacBench/xacml2_3.csv")
    xacml2_3_output_path = Path("policy_translation/output/carminati/xacml2_3.csv")
    translate(xacml2_3_input_path, xacml2_3_output_path)

    xacml3_1_input_path = Path("policy_generation/output/xacml/xacBench/xacml3_1.csv")
    xacml3_1_output_path = Path("policy_translation/output/carminati/xacml3_1.csv")
    translate(xacml3_1_input_path, xacml3_1_output_path)

    xacml3_2_input_path = Path("policy_generation/output/xacml/xacBench/xacml3_2.csv")
    xacml3_2_output_path = Path("policy_translation/output/carminati/xacml3_2.csv")
    translate(xacml3_2_input_path, xacml3_2_output_path)

    xacml3_3_input_path = Path("policy_generation/output/xacml/xacBench/xacml3_3.csv")
    xacml3_3_output_path = Path("policy_translation/output/carminati/xacml3_3.csv")
    translate(xacml3_3_input_path, xacml3_3_output_path)
