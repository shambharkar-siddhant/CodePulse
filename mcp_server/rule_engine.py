# mcp_server/rule_engine.py

import yaml  # type: ignore
from typing import List, Dict, Any, Optional
from mcp_server.models import FileEntry, RuleViolation
from mcp_server.config import settings

RULES_FILE = settings.RULES_PATH


def load_rules():
    with open(RULES_FILE, "r") as f:
        return yaml.safe_load(f)


def run_static_checks(files: List[FileEntry]) -> List[RuleViolation]:
    rules = load_rules()
    violations = []

    for rule in rules:
        rule_id = rule["rule_id"]
        match_type = rule.get("type")

        if match_type == "global":
            # e.g. max file count
            threshold = rule.get("threshold", 0)
            if rule_id == "max_file_limit" and len(files) > threshold:
                violations.append(RuleViolation(
                    rule_id=rule_id,
                    status="fail",
                    reason=rule["reason"]
                ))

        else:
            # file-based checks
            for f in files:
                filename = f.filename
                match = rule.get("match", "")

                if match_type == "equals" and filename == match:
                    violations.append(RuleViolation(
                        rule_id=rule_id,
                        status="fail",
                        reason=rule["reason"]
                    ))
                elif match_type == "endswith" and filename.endswith(match):
                    violations.append(RuleViolation(
                        rule_id=rule_id,
                        status="fail",
                        reason=rule["reason"]
                    ))

    return violations


# Rule management functions
def get_all_rules() -> List[Dict[str, Any]]:
    """Get all rules from the rules.yaml file"""
    try:
        with open(RULES_FILE, "r") as f:
            rules = yaml.safe_load(f)
        return rules or []
    except Exception as e:
        print(f"[ERROR] Error loading rules: {e}")
        return []


def save_rules(rules: List[Dict[str, Any]]) -> bool:
    """Save rules to the rules.yaml file"""
    try:
        with open(RULES_FILE, "w") as f:
            yaml.dump(rules, f, default_flow_style=False, indent=2)
        print(f"[DEBUG] Successfully saved {len(rules)} rules to {RULES_FILE}")
        return True
    except Exception as e:
        print(f"[ERROR] Error saving rules: {e}")
        import traceback
        print(f"[ERROR] Full traceback: {traceback.format_exc()}")
        return False


def create_rule(rule_data: Dict[str, Any]) -> bool:
    """Create a new rule"""
    print(f"[DEBUG] Creating rule: {rule_data}")
    try:
        rules = get_all_rules()
        rules.append(rule_data)
        return save_rules(rules)
    except Exception as e:
        print(f"[ERROR] Error creating rule: {e}")
        return False


def update_rule(rule_id: str, updated_rule: Dict[str, Any]) -> bool:
    """Update an existing rule"""
    print(f"[DEBUG] Updating rule {rule_id}: {updated_rule}")
    try:
        rules = get_all_rules()
        for i, rule in enumerate(rules):
            if rule.get("rule_id") == rule_id:
                rules[i] = updated_rule
                return save_rules(rules)
        print(f"[DEBUG] Rule {rule_id} not found")
        return False
    except Exception as e:
        print(f"[ERROR] Error updating rule: {e}")
        return False


def delete_rule(rule_id: str) -> bool:
    """Delete a rule"""
    print(f"[DEBUG] Deleting rule: {rule_id}")
    try:
        rules = get_all_rules()
        rules = [rule for rule in rules if rule.get("rule_id") != rule_id]
        return save_rules(rules)
    except Exception as e:
        print(f"[ERROR] Error deleting rule: {e}")
        return False


def get_rule_by_id(rule_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific rule by ID"""
    try:
        rules = get_all_rules()
        for rule in rules:
            if rule.get("rule_id") == rule_id:
                return rule
        return None
    except Exception as e:
        print(f"[ERROR] Error getting rule: {e}")
        return None
