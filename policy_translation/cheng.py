import csv
import re
import os
from pathlib import Path
import collections


class ChengTranslator:
    def __init__(self):
        pass

    def parse_datalog_rule(self, rule_str):
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

        # Handle constraints
        if any(op in pred_str for op in [">=", "<=", "==", ">", "<", "!="]):
            return {"name": "constraint", "raw": pred_str, "negated": False}

        return None

    def build_graph(self, body_preds):
        # Build a graph where nodes are variables and edges are relationships
        # Returns adjacency list: u -> [(v, type, negated)]
        adj = collections.defaultdict(list)

        for pred in body_preds:
            if pred["name"] == "constraint":
                continue

            name = pred["name"]
            args = pred["args"]
            negated = pred["negated"]

            # Unary predicates (types) - ignore for path finding, or treat as self-loop?
            # For now ignore.
            if len(args) < 2:
                continue

            # Binary or more
            u = args[0]
            v = args[1]

            # Add forward edge
            adj[u].append((v, name, negated))
            # Add backward edge
            adj[v].append((u, name + "^{-1}", negated))

            # If > 2 args, link first to others?
            for i in range(2, len(args)):
                w = args[i]
                adj[u].append((w, name, negated))
                adj[w].append((u, name + "^{-1}", negated))

        return adj

    def find_all_paths(self, adj, start, end, path=[]):
        path = path + [start]
        if start == end:
            return [
                []
            ]  # Path of edges is empty if start==end, but we need to return something to indicate success

        if start not in adj:
            return []

        paths = []
        for neighbor, type_name, negated in adj[start]:
            if neighbor not in path:  # Avoid cycles
                newpaths = self.find_all_paths(adj, neighbor, end, path)
                for newpath in newpaths:
                    paths.append([(type_name, negated)] + newpath)
        return paths

    def format_path_spec(self, edge_path):
        # edge_path is list of (type_name, negated)
        # Cheng's model: PathSpec -> ("Path", HopCount)
        # Path -> [TypeSeq]
        # TypeSeq -> type.type...

        # If any edge is negated, the whole path might be negated?
        # Or is it a negated relationship?
        # Cheng's grammar: PathSpecExp -> PathSpec | "¬" PathSpec
        # If we have a path A -(!f)-> B, it means "NOT friend".
        # This fits "¬" PathSpec if the whole path is just that edge.
        # But if A -f-> B -(!g)-> C?
        # "friend.¬colleague"?
        # The grammar TypeSpecifier -> sigma | sigma^-1 ...
        # It doesn't seem to support negation on individual edges inside a sequence in TypeSpecifier.
        # However, PathSpecExp supports negation of the whole PathSpec.
        # If we have mixed negation, maybe we can't represent it easily.
        # But let's assume negation applies to the whole path rule if present?
        # Actually, Datalog `not p(A,B)` means "no p link".
        # If the path requires "no p link", it's a negative condition.

        # For now, I will format the types.
        types = []
        hop_count = len(edge_path)

        # Check if any edge is negated
        # If so, mark the whole path as negated?
        # But `not p(A,B)` usually appears as a constraint.
        # If it's part of the path connectivity, it breaks the path?
        # No, `:- p(A,B)` means path exists. `:- not p(A,B)` means path must NOT exist.
        # If we are finding a path for authorization, usually we look for positive paths.
        # If there is a negative predicate, it's a "negative path" constraint.

        is_negated_path = False

        for name, negated in edge_path:
            types.append(name)
            if negated:
                is_negated_path = True

        path_str = ".".join(types)
        path_spec = f'("[{path_str}]", {hop_count})'

        if is_negated_path:
            return f"¬ {path_spec}"
        return path_spec

    def translate_rule(self, rule_str):
        head, body = self.parse_datalog_rule(rule_str)
        if not head:
            return ""

        if len(head["args"]) < 2:
            return ""

        subject_var = head["args"][0]
        object_var = head["args"][-1]
        action = head["name"]

        adj = self.build_graph(body)

        # 1. Try to find paths from Subject to Object (Accessing User Policy)
        paths_ua = self.find_all_paths(adj, subject_var, object_var)

        path_rules = []

        if paths_ua:
            # Convert paths to PathSpecs
            path_specs = [self.format_path_spec(p) for p in paths_ua]
            # Join with AND (since Datalog body is conjunction)
            # Wait, if there are multiple paths in the graph between S and O,
            # does the Datalog rule require ALL of them?
            # The Datalog rule requires all predicates in the body to be true.
            # If the body forms a diamond (A->B->D, A->C->D), then YES, both paths must exist.
            # So we join with ∧.
            combined_path_rule = " ∧ ".join(path_specs)
            path_rules.append(f"(u_a, {combined_path_rule})")

        # 2. If no paths from Subject to Object, check if we have paths from Object to Subject?
        # This would be (t, ...).
        # But find_all_paths(adj, object_var, subject_var) would find inverse paths.
        # If we found paths in (1), we don't need to duplicate them as (t, ...).
        # Unless the rule specifically frames it from the target's perspective.
        # Usually (u_a, ...) is preferred.

        # 3. Check for disconnected components involving Object?
        # e.g. `can_prescribe(D, P, DR) :- ... not has_allergy(P, DR)`
        # D is Subject, DR is Object.
        # If D is not connected to DR, paths_ua is empty.
        # But we have `has_allergy(P, DR)`.
        # We can represent this as a policy on `t` (DR).
        # Path from DR to P?
        # But P is a free variable (existentially quantified?).
        # In Datalog, P is bound if it appears in positive predicates.
        # If P is only in `not has_allergy(P, DR)`, it's unsafe.
        # But usually P is bound by `Patient(P)`.
        # If P is not connected to D, then for every P, check allergy?
        # No, P is an argument of the head `can_prescribe(D, P, DR)`.
        # So P is fixed.
        # So we have a relationship between P and DR.
        # But P is neither u_a nor t.
        # Cheng's model doesn't seem to support "Other Node" as starting node.
        # However, if P is an argument, maybe we can treat it as a secondary target?
        # But the output format expects a single policy tuple.

        # If we found nothing for u_a, let's try to find paths from t (Object) to *any* other argument?
        # But we can't express "Path from t to P" in Cheng's model unless P is u_a.
        # Wait, if P is u_a, we handled it.
        # If P is not u_a, we can't express it.

        # So, if paths_ua is empty, we might return "No Path".

        if not path_rules:
            return "No Path Found"

        # Construct the final policy string
        # < act, graphrule >
        # If multiple graph rules?
        # The paper says "Policies applied to this example...".
        # It lists Bob's P_AS, Alice's P_TU, etc.
        # We can output multiple.

        full_policy = f"< {action}, {' ∧ '.join(path_rules)} >"
        return full_policy

    def process_csv(self, input_file, output_file):
        results = []
        with open(input_file, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                datalog_action = row.get("datalog_actions", "")

                # Split by newline if multiple
                # But usually one rule per line in this dataset?
                # The example showed multiple rules in one cell sometimes?
                # "has_filter... has_criteria... is_empty... can_modify..."
                # We only care about the rule that defines the action in the head?
                # Or all of them?
                # Usually the last one is the main authorization rule.
                # I'll try to parse all, but filter for the one that looks like an authorization (can_...).

                rules = datalog_action.split("\n")
                converted_policies = []
                for rule in rules:
                    if not rule.strip():
                        continue
                    # Heuristic: only translate rules starting with "can_" or "authorized"
                    # Or just translate everything.
                    # But helper rules like "has_specialty" are not policies.
                    if rule.strip().startswith("can_") or rule.strip().startswith(
                        "authorized"
                    ):
                        policy = self.translate_rule(rule)
                        if policy:
                            converted_policies.append(policy)

                if converted_policies:
                    results.append(
                        {
                            "datalog_actions": datalog_action,
                            "cheng_policy": "\n".join(converted_policies),
                        }
                    )
                else:
                    # If no can_ rule found, maybe just try to translate the last one?
                    pass

        # Write output
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "w") as f:
            writer = csv.DictWriter(f, fieldnames=["datalog_actions", "cheng_policy"])
            writer.writeheader()
            writer.writerows(results)

        print(f"Processed {len(results)} rules. Output saved to {output_file}")


if __name__ == "__main__":
    translator = ChengTranslator()

    # LitroACP files
    files = [
        "acre_acp.csv",
        "collected_acp.csv",
        "cyber_acp.csv",
        "ibm_acp.csv",
        "t2p_acp.csv",
    ]

    for fname in files:
        in_p = Path(f"policy_generation/output/litroacp/{fname}")
        out_p = Path(f"policy_translation/output/cheng/{fname}")
        if in_p.exists():
            translator.process_csv(in_p, out_p)

    # XACML files
    xacml_files = [
        "xacml3-mli-interface.csv",
        "upperlicl/PPS-PIP-Role.csv",
        "upperlicl/PPS-VIO-N-Role.csv",
        "upperlicl/PPS-VIO-Role.csv",
        "upperlicl/RPS-PIP-Role.csv",
        "upperlicl/RPS-VIO-N-Role.csv",
        "upperlicl/RPS-VIO-Role.csv",
        "upperlicl/permission-cci-operations.csv",
        "upperlicl/permission-mli-replanning-vlink-operations.csv",
        "upperlicl/permission-mli-replanning-vr-it-operations.csv",
        "upperlicl/permission-mli-vi-operations.csv",
        "upperlicl/permission-mli-vi-request-operations.csv",
        "upperlicl/permission-ros-notifications.csv",
        "upperlicl/permission-sli-operations.csv",
    ]

    for fname in xacml_files:
        in_p = Path(f"policy_generation/output/xacml/{fname}")
        out_p = Path(f"policy_translation/output/cheng/{fname}")
        if in_p.exists():
            translator.process_csv(in_p, out_p)
