from mcp_server.prompts import pr_summary_prompt, chat_prompt
from openai import OpenAI
from mcp_server.config import settings
from typing import List, Dict, Any

client = OpenAI(api_key=settings.OPENAI_API_KEY)


def summarize_diff(title: str, description: str, diff: str) -> str:
    prompt = pr_summary_prompt(title, description, diff)

    try:
        response = client.chat.completions.create(
            model=settings.DEFAULT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print("[LLM ERROR]", e)
        return "Summary unavailable due to LLM error."


async def chat_with_llm(
    user_message: str,
    chat_history: List[Dict[str, str]],
    rules: List[Dict[str, Any]],
    context: Dict[str, Any] = None
) -> str:
    """Handle chat conversations with rule management capabilities"""
    
    print(f"[DEBUG] Starting chat_with_llm")
    print(f"[DEBUG] User message: {user_message[:100]}...")
    print(f"[DEBUG] Chat history length: {len(chat_history)}")
    print(f"[DEBUG] Rules count: {len(rules)}")
    
    try:
        # Build system prompt with rules context
        system_prompt = chat_prompt(rules)
        print(f"[DEBUG] System prompt length: {len(system_prompt)}")
        
        # Prepare messages for OpenAI
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add chat history (limit to last 10 messages to avoid token limits)
        for msg in chat_history[-10:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        
        # Add current user message
        messages.append({"role": "user", "content": user_message})
        
        print(f"[DEBUG] Calling OpenAI API...")
        
        response = client.chat.completions.create(
            model=settings.DEFAULT_MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        )
        
        result = response.choices[0].message.content.strip()
        print(f"[DEBUG] OpenAI response received: {result[:100]}...")
        
        # Check if the user's message contains rule management requests and execute them
        result = await process_rule_requests(user_message, result, rules)
        
        return result
        
    except Exception as e:
        print(f"[ERROR] LLM CHAT ERROR: {e}")
        print(f"[ERROR] Error type: {type(e)}")
        import traceback
        print(f"[ERROR] Full traceback: {traceback.format_exc()}")
        return "I apologize, but I'm experiencing technical difficulties. Please try again later."


async def process_rule_requests(user_message: str, ai_response: str, current_rules: List[Dict[str, Any]]) -> str:
    """Process rule management requests using LLM to interpret natural language"""
    from mcp_server.rule_engine import create_rule, update_rule, delete_rule, get_rule_by_id
    
    print(f"[DEBUG] Processing rule requests using LLM interpretation")
    
    # Use LLM to interpret the user's message and determine what actions to take
    interpretation = await interpret_rule_request(user_message, current_rules)
    
    if not interpretation:
        return ai_response
    
    print(f"[DEBUG] LLM interpretation: {interpretation}")
    
    # Execute the interpreted actions
    result_messages = []
    
    for action in interpretation:
        action_type = action.get("action")
        rule_id = action.get("rule_id")
        
        if action_type == "update":
            field = action.get("field")
            value = action.get("value")
            
            print(f"[DEBUG] Updating rule {rule_id}, field {field} to {value}")
            
            existing_rule = get_rule_by_id(rule_id)
            if existing_rule:
                updated_rule = existing_rule.copy()
                updated_rule[field] = value
                
                success = update_rule(rule_id, updated_rule)
                if success:
                    result_messages.append(f"✅ **Updated rule '{rule_id}': {field} = {value}**")
                else:
                    result_messages.append(f"❌ **Failed to update rule '{rule_id}'**")
            else:
                result_messages.append(f"❌ **Rule '{rule_id}' not found**")
        
        elif action_type == "create":
            rule_data = action.get("rule_data", {})
            
            print(f"[DEBUG] Creating rule: {rule_data}")
            
            success = create_rule(rule_data)
            if success:
                result_messages.append(f"✅ **Created rule '{rule_id}'**")
            else:
                result_messages.append(f"❌ **Failed to create rule '{rule_id}'**")
        
        elif action_type == "delete":
            print(f"[DEBUG] Deleting rule: {rule_id}")
            
            success = delete_rule(rule_id)
            if success:
                result_messages.append(f"✅ **Deleted rule '{rule_id}'**")
            else:
                result_messages.append(f"❌ **Failed to delete rule '{rule_id}'**")
    
    if result_messages:
        ai_response += "\n\n" + "\n".join(result_messages)
    
    return ai_response


async def interpret_rule_request(user_message: str, current_rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Use LLM to interpret natural language rule requests"""
    
    # Create a prompt for the LLM to interpret the request
    rules_text = "\n".join([f"- {rule['rule_id']}: {rule.get('type', 'unknown')} type, {rule.get('reason', 'no reason')}" for rule in current_rules])
    
    interpretation_prompt = f"""
You are a rule management interpreter. Based on the user's request and current rules, determine what actions need to be taken.

Current rules:
{rules_text}

User request: "{user_message}"

Analyze the request and return a JSON array of actions to perform. Each action should have:
- "action": "update", "create", or "delete"
- "rule_id": the rule identifier
- For updates: "field" and "value" 
- For creates: "rule_data" object with all rule fields
- For deletes: just "rule_id"

Examples:
- User: "change file limit to 30" → [{{"action": "update", "rule_id": "max_file_limit", "field": "threshold", "value": 30}}]
- User: "update no_env_file reason" → [{{"action": "update", "rule_id": "no_env_file", "field": "reason", "value": "new reason"}}]
- User: "create rule for .log files" → [{{"action": "create", "rule_id": "no_log_files", "rule_data": {{"rule_id": "no_log_files", "type": "endswith", "match": ".log", "reason": "Log files should not be committed"}}}}]

Return only valid JSON array, no other text.
"""
    
    try:
        response = client.chat.completions.create(
            model=settings.DEFAULT_MODEL,
            messages=[{"role": "user", "content": interpretation_prompt}],
            temperature=0.1,
            max_tokens=500
        )
        
        result = response.choices[0].message.content.strip()
        print(f"[DEBUG] LLM interpretation result: {result}")
        
        import json
        actions = json.loads(result)
        return actions
        
    except Exception as e:
        print(f"[ERROR] Failed to interpret rule request: {e}")
        return []
