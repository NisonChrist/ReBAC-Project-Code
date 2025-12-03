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
    xacml3_mli_interface_input_path = Path(
        "policy_generation/output/xacml/xacml3-mli-interface.csv"
    )
    xacml3_mli_interface_output_path = Path(
        "policy_translation/output/carminati/xacml3-mli-interface.csv"
    )
    translate(xacml3_mli_interface_input_path, xacml3_mli_interface_output_path)
    pps_pip_role_input_path = Path(
        "policy_generation/output/xacml/upperlicl/PPS-PIP-Role.csv"
    )
    pps_pip_role_output_path = Path(
        "policy_translation/output/carminati/PPS-PIP-Role.csv"
    )
    translate(pps_pip_role_input_path, pps_pip_role_output_path)
    pps_vio_n_role_input_path = Path(
        "policy_generation/output/xacml/upperlicl/PPS-VIO-N-Role.csv"
    )
    pps_vio_n_role_output_path = Path(
        "policy_translation/output/carminati/PPS-VIO-N-Role.csv"
    )
    translate(pps_vio_n_role_input_path, pps_vio_n_role_output_path)
    pps_vio_role_input_path = Path(
        "policy_generation/output/xacml/upperlicl/PPS-VIO-Role.csv"
    )
    pps_vio_role_output_path = Path(
        "policy_translation/output/carminati/PPS-VIO-Role.csv"
    )
    translate(pps_vio_role_input_path, pps_vio_role_output_path)
    rps_pip_role_input_path = Path(
        "policy_generation/output/xacml/upperlicl/RPS-PIP-Role.csv"
    )
    rps_pip_role_output_path = Path(
        "policy_translation/output/carminati/RPS-PIP-Role.csv"
    )
    translate(rps_pip_role_input_path, rps_pip_role_output_path)
    rps_vio_n_role_input_path = Path(
        "policy_generation/output/xacml/upperlicl/RPS-VIO-N-Role.csv"
    )
    rps_vio_n_role_output_path = Path(
        "policy_translation/output/carminati/RPS-VIO-N-Role.csv"
    )
    translate(rps_vio_n_role_input_path, rps_vio_n_role_output_path)
    rps_vio_role_input_path = Path(
        "policy_generation/output/xacml/upperlicl/RPS-VIO-Role.csv"
    )
    rps_vio_role_output_path = Path(
        "policy_translation/output/carminati/RPS-VIO-Role.csv"
    )
    translate(rps_vio_role_input_path, rps_vio_role_output_path)
    permission_cci_operations_input_path = Path(
        "policy_generation/output/xacml/upperlicl/permission-cci-operations.csv"
    )
    permission_cci_operations_output_path = Path(
        "policy_translation/output/carminati/permission-cci-operations.csv"
    )
    translate(
        permission_cci_operations_input_path, permission_cci_operations_output_path
    )
    permission_mli_replanning_vlink_operations_input_path = Path(
        "policy_generation/output/xacml/upperlicl/permission-mli-replanning-vlink-operations.csv"
    )
    permission_mli_replanning_vlink_operations_output_path = Path(
        "policy_translation/output/carminati/permission-mli-replanning-vlink-operations.csv"
    )
    translate(
        permission_mli_replanning_vlink_operations_input_path,
        permission_mli_replanning_vlink_operations_output_path,
    )
    permission_mli_replanning_vr_it_operations_input_path = Path(
        "policy_generation/output/xacml/upperlicl/permission-mli-replanning-vr-it-operations.csv"
    )
    permission_mli_replanning_vr_it_operations_output_path = Path(
        "policy_translation/output/carminati/permission-mli-replanning-vr-it-operations.csv"
    )
    translate(
        permission_mli_replanning_vr_it_operations_input_path,
        permission_mli_replanning_vr_it_operations_output_path,
    )
    permission_mli_vi_operations_input_path = Path(
        "policy_generation/output/xacml/upperlicl/permission-mli-vi-operations.csv"
    )
    permission_mli_vi_operations_output_path = Path(
        "policy_translation/output/carminati/permission-mli-vi-operations.csv"
    )
    translate(
        permission_mli_vi_operations_input_path,
        permission_mli_vi_operations_output_path,
    )
    permission_mli_vi_request_operations_input_path = Path(
        "policy_generation/output/xacml/upperlicl/permission-mli-vi-request-operations.csv"
    )
    permission_mli_vi_request_operations_output_path = Path(
        "policy_translation/output/carminati/permission-mli-vi-request-operations.csv"
    )
    translate(
        permission_mli_vi_request_operations_input_path,
        permission_mli_vi_request_operations_output_path,
    )
    permission_ros_notifications_input_path = Path(
        "policy_generation/output/xacml/upperlicl/permission-ros-notifications.csv"
    )
    permission_ros_notifications_output_path = Path(
        "policy_translation/output/carminati/permission-ros-notifications.csv"
    )
    translate(
        permission_ros_notifications_input_path,
        permission_ros_notifications_output_path,
    )
    permission_sli_operations_input_path = Path(
        "policy_generation/output/xacml/upperlicl/permission-sli-operations.csv"
    )
    permission_sli_operations_output_path = Path(
        "policy_translation/output/carminati/permission-sli-operations.csv"
    )
    translate(
        permission_sli_operations_input_path, permission_sli_operations_output_path
    )
