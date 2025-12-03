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
    return term

def parse_predicate(pred_str):
    is_negated = False
    pred_str = pred_str.strip()
    if pred_str.startswith("not "):
        is_negated = True
        pred_str = pred_str[4:].strip()

    match = re.match(r"(\w+)\((.*)\)", pred_str)
    if match:
        name = match.group(1)
        args_str = match.group(2)
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
        
        parsed_args = [parse_term(arg) for arg in args]
        return {"name": name, "args": parsed_args, "negated": is_negated, "raw": pred_str}
    
    # Infix
    infix_match = re.match(r"(.+?)\s*(=|>=|<=|>|<|!=|in)\s*(.+)", pred_str)
    if infix_match:
        return {"infix": True, "left": infix_match.group(1), "op": infix_match.group(2), "right": infix_match.group(3), "negated": is_negated, "raw": pred_str}

    return {"raw": pred_str, "negated": is_negated}

def datalog_to_fong_formula(head, body_preds):
    # Identify Subject (S) and Object (O)
    # Heuristic: S is 1st arg, O is 2nd arg (if exists)
    if not head.get("args"):
        return "Error: Head has no args"
    
    subject_var = head["args"][0]
    object_var = head["args"][1] if len(head["args"]) > 1 else None
    
    # Build Graph
    # Adjacency list: node -> [(rel, neighbor)]
    adj = {}
    # Node properties: node -> [props]
    props = {}
    
    # Constraints (negated relations or infix)
    constraints = {} # node -> [constraint_formulas]

    # Initialize nodes
    all_vars = set()
    all_vars.add(subject_var)
    if object_var:
        all_vars.add(object_var)

    for pred in body_preds:
        if pred.get("infix"):
            # Treat as constraint on the variables involved
            # For simplicity, attach to the first variable found in 'left'
            # This is a simplification.
            left_var = pred["left"].strip()
            if left_var not in constraints: 
                constraints[left_var] = []
            constraints[left_var].append(pred["raw"])
            continue

        name = pred.get("name")
        args = pred.get("args")
        negated = pred.get("negated")
        
        if not args: 
            continue
        
        for arg in args:
            all_vars.add(arg)
            
        if len(args) == 1:
            # Unary property
            v = args[0]
            if v not in props: 
                props[v] = []
            p = name
            if negated: 
                p = f"¬{p}"
            props[v].append(p)
        elif len(args) == 2:
            u, v = args[0], args[1]
            if negated:
                # Treat as constraint on u? "not name(u, v)"
                # In Fong's logic: [name] false ? Only if v is wildcard.
                # If v is specific, it's complex.
                # For now, add as a constraint string
                if u not in constraints: 
                    constraints[u] = []
                constraints[u].append(f"¬<{name}>T") # Simplified
            else:
                if u not in adj: 
                    adj[u] = []
                adj[u].append((name, v))
                
                # Inverse? Fong's model supports inverse.
                # But we construct formula from S.
                # If the rule says parent(O, S), we go S -> -parent -> O.
                if v not in adj: 
                    adj[v] = []
                adj[v].append((f"-{name}", u))

    # DFS/Recursive generation from Subject
    visited = set()
    
    def generate(u):
        if u in visited:
            return "cycle" # Cycle detected, break
        visited.add(u)
        
        parts = []
        
        # 1. Atomic properties at u
        if u in props:
            parts.extend(props[u])
            
        # 2. Is it Object?
        if u == object_var:
            parts.append("owner") # or 'resource'
            
        # 3. Constraints
        if u in constraints:
            parts.extend(constraints[u])
            
        # 4. Traversal to neighbors
        # We need to cover all conditions in the body.
        # The graph approach above puts ALL body relations as edges.
        # But we only want to traverse edges that lead to the Object or are required by the rule.
        # Actually, in Datalog "A, B, C", all must be true.
        # So we must satisfy all relations connected to S (and recursively).
        # However, we should avoid traversing back to parent (inverse of inverse).
        
        if u in adj:
            for rel, v in adj[u]:
                # Avoid immediate loopback if we just came from v (handled by visited, but be careful)
                if v in visited: 
                    continue
                
                # We only traverse if v is "useful" (leads to object or has constraints)
                # For now, traverse all.
                sub_formula = generate(v)
                if sub_formula and sub_formula != "cycle":
                    parts.append(f"<{rel}>({sub_formula})")
        
        visited.remove(u)
        
        if not parts:
            return "T" # True
            
        if len(parts) == 1:
            return parts[0]
        
        return f"({' ∧ '.join(parts)})"

    # Start generation
    formula = generate(subject_var)
    return formula

def convert_datalog_to_fong(csv_path):
    results = []
    if not os.path.exists(csv_path):
        return []

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            action = row.get("datalog_actions", "")
            if not action:
                continue
            action = action.replace("\n", " ")
            
            if ":-" in action:
                parts = action.split(":-")
                head_str = parts[0].strip()
                body_str = parts[1].strip()
                if body_str.endswith("."): 
                    body_str = body_str[:-1]
                
                head_pred = parse_predicate(head_str)
                
                # Parse body
                body_preds = []
                current = ""
                depth = 0
                for char in body_str:
                    if char == "(": 
                        depth += 1
                    elif char == ")": 
                        depth -= 1
                    elif char == "," and depth == 0:
                        body_preds.append(parse_predicate(current.strip()))
                        current = ""
                        continue
                    current += char
                if current:
                    body_preds.append(parse_predicate(current.strip()))
                
                fong_formula = datalog_to_fong_formula(head_pred, body_preds)
                results.append(fong_formula)
            else:
                results.append("")
    return results

def translate(input_path: Path, output_path: Path):
    fong_rules = convert_datalog_to_fong(input_path)
    
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["fong"])
        for rule in fong_rules:
            writer.writerow([rule])
            
    # Merge
    input_df = pd.read_csv(input_path)
    output_df = pd.read_csv(output_path)
    merged_df = pd.concat([input_df, output_df], axis=1)
    merged_df.to_csv(output_path, index=False)
    print(f"Saved {output_path}")

if __name__ == "__main__":
    # Process NaturalLanguageStatements files
    files = [
        "acre_acp.csv", "collected_acp.csv", "cyber_acp.csv", "ibm_acp.csv", "t2p_acp.csv"
    ]
    
    for fname in files:
        in_p = Path(f"policy_generation/output/litroacp/{fname}")
        out_p = Path(f"policy_translation/output/fong/{fname}")
        if in_p.exists():
            translate(in_p, out_p)
            
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
        "upperlicl/permission-sli-operations.csv"
    ]
    
    for fname in xacml_files:
        in_p = Path(f"policy_generation/output/xacml/{fname}")
        out_p = Path(f"policy_translation/output/fong/{fname}")
        out_p.parent.mkdir(parents=True, exist_ok=True)
        if in_p.exists():
            translate(in_p, out_p)
