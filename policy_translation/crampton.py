import csv
import re

# import sys
import os
from pathlib import Path


class CramptonTranslator:
    def __init__(self):
        pass

    def parse_datalog_rule(self, rule_str):
        # Remove trailing dot
        rule_str = rule_str.strip().rstrip(".")
        if ":-" not in rule_str:
            return None, None

        head_str, body_str = rule_str.split(":-", 1)
        head = self.parse_predicate(head_str.strip())

        body_preds = []
        body_parts = self.split_body(body_str)
        for part in body_parts:
            pred = self.parse_predicate(part.strip())
            if pred:
                body_preds.append(pred)

        return head, body_preds

    def split_body(self, body_str):
        parts = []
        current = ""
        depth = 0
        for char in body_str:
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1

            if char == "," and depth == 0:
                parts.append(current)
                current = ""
            else:
                current += char
        if current:
            parts.append(current)
        return parts

    def parse_predicate(self, pred_str):
        # Handle negation
        is_negated = False
        pred_str = pred_str.strip()
        if pred_str.startswith("not "):
            is_negated = True
            pred_str = pred_str[4:].strip()

        match = re.match(r"(\w+)\((.*)\)", pred_str)
        if match:
            name = match.group(1)
            args = [a.strip() for a in match.group(2).split(",")]
            return {"name": name, "args": args, "negated": is_negated}
        # Handle comparison like Count >= 0
        if (
            ">=" in pred_str
            or "<=" in pred_str
            or "==" in pred_str
            or ">" in pred_str
            or "<" in pred_str
        ):
            return {"name": "constraint", "raw": pred_str, "negated": False}
        return None

    def build_dependency_graph(self, body_preds):
        adj = {}
        # We want to find a path from Subject to Object.
        # Nodes are variables.
        # Edges are predicates.

        for pred in body_preds:
            if pred["name"] == "constraint":
                continue
            if pred["negated"]:
                continue  # Crampton model typically positive paths. Negation is a constraint.

            args = pred["args"]
            # Unary predicates are node types, not edges usually.
            if len(args) == 1:
                u = args[0]
                if u not in adj:
                    adj[u] = []
                continue

            if len(args) == 2:
                u, v = args[0], args[1]
                if u not in adj:
                    adj[u] = []
                if v not in adj:
                    adj[v] = []

                adj[u].append((v, pred["name"]))
                # Add inverse edge?
                # In ReBAC, usually yes.
                adj[v].append((u, pred["name"] + "^{-1}"))

            # What if > 2 args? e.g. pending_procedures(L, P, Count)
            # Treat as hyperedge or multiple edges?
            # For now, link first to others?
            if len(args) > 2:
                u = args[0]
                if u not in adj:
                    adj[u] = []
                for i in range(1, len(args)):
                    v = args[i]
                    if v not in adj:
                        adj[v] = []
                    adj[u].append((v, pred["name"]))
                    adj[v].append((u, pred["name"] + "^{-1}"))

        return adj

    def find_path(self, adj, start, end):
        if start not in adj or end not in adj:
            return None

        # BFS to find shortest path
        queue = [(start, [])]
        visited = {start}

        while queue:
            curr, path = queue.pop(0)
            if curr == end:
                return path

            if curr in adj:
                for neighbor, label in adj[curr]:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        new_path = path + [label]
                        queue.append((neighbor, new_path))
        return None

    def translate_rule(self, rule_str):
        head, body = self.parse_datalog_rule(rule_str)
        if not head:
            return None

        # Identify Subject and Object
        # Assumption: Subject is 1st arg, Object is last arg.
        if len(head["args"]) < 2:
            return ""
            # return "Cannot determine Subject/Object (arity < 2)"

        subject_var = head["args"][0]
        object_var = head["args"][-1]

        adj = self.build_dependency_graph(body)

        path = self.find_path(adj, subject_var, object_var)

        if path is None:
            # Check if they are the same variable?
            if subject_var == object_var:
                # return "self"
                return ""
            return ""
            # return "No Path Found"

        if len(path) == 0:
            # return "Direct Link (or same node)"
            return ""

        return ".".join(path)

    def process_csv(
        self, input_file, output_file, source_type="natural_language_statements"
    ):
        results = []
        with open(input_file, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                type = ""
                if source_type == "natural_language_statements":
                    type = source_type
                elif source_type == "xacml":
                    type = "xacml"
                first_field = row.get(type, "")
                datalog_subject = row.get("datalog_subjects", "")
                datalog_object = row.get("datalog_objects", "")
                datalog_relationships = row.get("datalog_relationships", "")
                datalog_action = row.get("datalog_actions", "")

                # Split by newline if multiple
                rules = datalog_action.split("\n")
                for rule in rules:
                    if not rule.strip():
                        continue
                    path_condition = self.translate_rule(rule)
                    if path_condition:
                        if source_type == "natural_language_statements":
                            results.append(
                                {
                                    "natural_language_statements": first_field,
                                    "datalog_subjects": datalog_subject,
                                    "datalog_objects": datalog_object,
                                    "datalog_relationships": datalog_relationships,
                                    "datalog_actions": rule,
                                    "crampton": path_condition,
                                }
                            )
                        elif source_type == "xacml":
                            results.append(
                                {
                                    "xacml": first_field,
                                    "datalog_subjects": datalog_subject,
                                    "datalog_objects": datalog_object,
                                    "datalog_relationships": datalog_relationships,
                                    "datalog_actions": rule,
                                    "crampton": path_condition,
                                }
                            )

        # Write output
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "w") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    source_type,
                    "datalog_subjects",
                    "datalog_objects",
                    "datalog_relationships",
                    "datalog_actions",
                    "crampton",
                ],
            )
            writer.writeheader()
            writer.writerows(results)

        print(f"Processed {len(results)} rules. Output saved to {output_file}")
        return results


if __name__ == "__main__":
    translator = CramptonTranslator()

    # Process NaturalLanguageStatements files
    files = [
        "acre_acp.csv",
        "collected_acp.csv",
        "cyber_acp.csv",
        "ibm_acp.csv",
        "t2p_acp.csv",
    ]

    for fname in files:
        in_p = Path(f"policy_generation/output/litroacp/{fname}")
        out_p = Path(f"policy_translation/output/crampton/{fname}")
        if in_p.exists():
            translator.process_csv(
                in_p, out_p, source_type="natural_language_statements"
            )

    # XACML files
    xacml_files = [
        "xacml2_1.csv",
        "xacml2_2.csv",
        "xacml2_3.csv",
        "xacml3_1.csv",
        "xacml3_2.csv",
        "xacml3_3.csv",
    ]

    for fname in xacml_files:
        in_p = Path(f"policy_generation/output/xacml/xacBench/{fname}")
        out_p = Path(f"policy_translation/output/crampton/{fname}")
        out_p.parent.mkdir(parents=True, exist_ok=True)
        if in_p.exists():
            translator.process_csv(in_p, out_p, source_type="xacml")
