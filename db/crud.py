import json
from db.connection import get_db_pool as _get_db_pool
from datetime import datetime
from typing import List, Dict, Any


async def upsert_pr_summary(
    repo_full_name: str,
    pr_number: int,
    pr_url: str,
    title: str,
    author_login: str,
    created_at,
    closed_at,
    merged_at,
    is_merged: bool,
    commits_count: int,
    additions: int,
    deletions: int,
    changed_files: int,
    comments_count: int,
    review_comments_count: int,
    approvals_count: int,
    violation_count: int,
    violations: list,
    summary_text: str,
    summary_generated_at,
) -> int:
    pool = _get_db_pool()
    sql = """
    INSERT INTO pr_summary (
      repo_full_name, pr_number, pr_url, title, author_login,
      created_at, closed_at, merged_at, is_merged,
      commits_count, additions, deletions, changed_files,
      comments_count, review_comments_count, approvals_count,
      violation_count, violations, summary_text, summary_generated_at,
      metrics_updated_at
    ) VALUES (
      $1, $2, $3, $4, $5,
      $6, $7, $8, $9,
      $10, $11, $12, $13,
      $14, $15, $16,
      $17, $18::jsonb, $19, $20,
      now()
    )
    ON CONFLICT (repo_full_name, pr_number) DO UPDATE SET
      pr_url                = EXCLUDED.pr_url,
      title                 = EXCLUDED.title,
      author_login          = EXCLUDED.author_login,
      created_at            = EXCLUDED.created_at,
      closed_at             = EXCLUDED.closed_at,
      merged_at             = EXCLUDED.merged_at,
      is_merged             = EXCLUDED.is_merged,
      commits_count         = EXCLUDED.commits_count,
      additions             = EXCLUDED.additions,
      deletions             = EXCLUDED.deletions,
      changed_files         = EXCLUDED.changed_files,
      comments_count        = EXCLUDED.comments_count,
      review_comments_count = EXCLUDED.review_comments_count,
      approvals_count       = EXCLUDED.approvals_count,
      violation_count       = EXCLUDED.violation_count,
      violations            = EXCLUDED.violations,
      summary_text          = EXCLUDED.summary_text,
      summary_generated_at  = EXCLUDED.summary_generated_at,
      metrics_updated_at    = now()
    RETURNING id;
    """
    row = await pool.fetchrow(
        sql,
        repo_full_name, pr_number, pr_url, title, author_login,
        created_at, closed_at, merged_at, is_merged,
        commits_count, additions, deletions, changed_files,
        comments_count, review_comments_count, approvals_count,
        violation_count, json.dumps(violations), summary_text, summary_generated_at
    )
    return row["id"]


async def insert_pr_event(
    pr_summary_id: int, event_type: str, payload: dict
):
    pool = get_db_pool()
    await pool.execute(
        "INSERT INTO pr_events(pr_summary_id, event_type, payload) VALUES($1,$2,$3::jsonb)",
        pr_summary_id, event_type, json.dumps(payload),
    )


async def insert_assistant_interaction(
    pr_summary_id: int, user_query: str, assistant_resp: dict
):
    pool = get_db_pool()
    await pool.execute(
        "INSERT INTO pr_assistant_interactions(pr_summary_id, user_query, assistant_resp) VALUES($1,$2,$3::jsonb)",
        pr_summary_id, user_query, json.dumps(assistant_resp),
    )


# Chat conversation functions
async def create_chat_session(user_id: str, session_name: str | None = None) -> int:
    """Create a new chat session and return its ID"""
    print(f"[DEBUG] Creating chat session for user: {user_id}")
    try:
        pool = get_db_pool()
        if not session_name:
            session_name = f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        print(f"[DEBUG] Session name: {session_name}")
        row = await pool.fetchrow(
            "INSERT INTO chat_sessions (user_id, session_name, created_at) "
            "VALUES ($1, $2, now()) RETURNING id",
            user_id, session_name
        )
        session_id = row["id"]
        print(f"[DEBUG] Successfully created session with ID: {session_id}")
        return session_id
    except Exception as e:
        print(f"[ERROR] Failed to create chat session: {str(e)}")
        import traceback
        print(f"[ERROR] Full traceback: {traceback.format_exc()}")
        raise


async def add_chat_message(
    session_id: int, role: str, content: str, metadata: dict | None = None
) -> int:
    """Add a message to a chat session"""
    pool = get_db_pool()
    row = await pool.fetchrow(
        "INSERT INTO chat_messages (session_id, role, content, metadata, created_at) "
        "VALUES ($1, $2, $3, $4::jsonb, now()) RETURNING id",
        session_id, role, content, json.dumps(metadata) if metadata else None
    )
    return row["id"]


async def get_chat_sessions(user_id: str) -> List[Dict[str, Any]]:
    """Get all chat sessions for a user"""
    print(f"[DEBUG] get_chat_sessions called with user_id: {user_id}")
    try:
        pool = get_db_pool()
        print(f"[DEBUG] Got database pool")
        
        query = """
        SELECT cs.id, cs.session_name, cs.created_at, 
               COUNT(cm.id) as message_count,
               MAX(cm.created_at) as last_message_at
        FROM chat_sessions cs
        LEFT JOIN chat_messages cm ON cs.id = cm.session_id
        WHERE cs.user_id = $1
        GROUP BY cs.id, cs.session_name, cs.created_at
        ORDER BY cs.created_at DESC
        """
        print(f"[DEBUG] Executing query: {query}")
        print(f"[DEBUG] With user_id parameter: {user_id}")
        
        rows = await pool.fetch(query, user_id)
        print(f"[DEBUG] Query executed, got {len(rows)} rows")
        
        result = [dict(row) for row in rows]
        print(f"[DEBUG] Converted to dict, returning {len(result)} sessions")
        return result
    except Exception as e:
        print(f"[ERROR] Error in get_chat_sessions: {str(e)}")
        print(f"[ERROR] Error type: {type(e)}")
        import traceback
        print(f"[ERROR] Full traceback: {traceback.format_exc()}")
        raise


async def get_chat_messages(session_id: int) -> List[Dict[str, Any]]:
    """Get all messages in a chat session"""
    pool = get_db_pool()
    rows = await pool.fetch(
        "SELECT id, role, content, metadata, created_at "
        "FROM chat_messages WHERE session_id = $1 ORDER BY created_at ASC",
        session_id
    )
    return [dict(row) for row in rows]


async def delete_chat_session(session_id: int, user_id: str) -> bool:
    """Delete a chat session and all its messages"""
    print(f"[DEBUG] delete_chat_session called: session_id={session_id}, user_id={user_id}")
    try:
        pool = get_db_pool()
        result = await pool.execute(
            "DELETE FROM chat_sessions WHERE id = $1 AND user_id = $2",
            session_id, user_id
        )
        print(f"[DEBUG] Delete result: {result}")
        success = result == "DELETE 1"
        print(f"[DEBUG] Delete success: {success}")
        return success
    except Exception as e:
        print(f"[ERROR] Error in delete_chat_session: {str(e)}")
        return False


# Rule management functions
async def get_all_rules() -> List[Dict[str, Any]]:
    """Get all rules from the rules.yaml file"""
    import yaml  # type: ignore
    from mcp_server.config import settings
    
    try:
        with open(settings.RULES_PATH, "r") as f:
            rules = yaml.safe_load(f)
        return rules or []
    except Exception as e:
        print(f"Error loading rules: {e}")
        return []


async def update_rules(rules: List[Dict[str, Any]]) -> bool:
    """Update the rules.yaml file"""
    import yaml
    from mcp_server.config import settings
    
    print(f"[DEBUG] update_rules called with {len(rules)} rules")
    print(f"[DEBUG] Rules to update: {rules}")
    print(f"[DEBUG] Rules path: {settings.RULES_PATH}")
    
    try:
        with open(settings.RULES_PATH, "w") as f:
            yaml.dump(rules, f, default_flow_style=False, indent=2)
        print(f"[DEBUG] Successfully updated rules.yaml")
        return True
    except Exception as e:
        print(f"[ERROR] Error updating rules: {e}")
        import traceback
        print(f"[ERROR] Full traceback: {traceback.format_exc()}")
        return False


async def add_rule(rule: Dict[str, Any]) -> bool:
    """Add a new rule to the rules.yaml file"""
    rules = await get_all_rules()
    rules.append(rule)
    return await update_rules(rules)


async def update_rule(rule_id: str, updated_rule: Dict[str, Any]) -> bool:
    """Update an existing rule"""
    print(f"[DEBUG] update_rule called with rule_id: {rule_id}")
    print(f"[DEBUG] updated_rule: {updated_rule}")
    try:
        rules = await get_all_rules()
        print(f"[DEBUG] Current rules: {rules}")
        for i, rule in enumerate(rules):
            if rule.get("rule_id") == rule_id:
                print(f"[DEBUG] Found rule to update at index {i}")
                rules[i] = updated_rule
                result = await update_rules(rules)
                print(f"[DEBUG] update_rules result: {result}")
                return result
        print(f"[DEBUG] Rule {rule_id} not found")
        return False
    except Exception as e:
        print(f"[ERROR] Error in update_rule: {str(e)}")
        import traceback
        print(f"[ERROR] Full traceback: {traceback.format_exc()}")
        return False


async def delete_rule(rule_id: str) -> bool:
    """Delete a rule from the rules.yaml file"""
    rules = await get_all_rules()
    rules = [rule for rule in rules if rule.get("rule_id") != rule_id]
    return await update_rules(rules)


def get_db_pool():
    """Get the database connection pool"""
    print("[DEBUG] Getting database pool")
    try:
        pool = _get_db_pool()
        print("[DEBUG] Database pool retrieved successfully")
        return pool
    except Exception as e:
        print(f"[ERROR] Failed to get database pool: {str(e)}")
        import traceback
        print(f"[ERROR] Full traceback: {traceback.format_exc()}")
        raise
