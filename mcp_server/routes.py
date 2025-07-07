# mcp_server/routes.py

from fastapi import APIRouter, HTTPException
from mcp_server.models import (
    AnalyzeRequest, AnalyzeResponse, ChatRequest, ChatResponse, 
    ChatSession, Rule, RuleCreateRequest, RuleUpdateRequest, 
    RulesResponse
)
from mcp_server.llm_client import summarize_diff, chat_with_llm
from mcp_server.rule_engine import (
    run_static_checks, get_all_rules, create_rule, 
    update_rule, delete_rule
)
from db.crud import (
    create_chat_session, add_chat_message, get_chat_sessions, 
    get_chat_messages, delete_chat_session
)
from typing import List

mcp_router = APIRouter()


@mcp_router.post("/analyze_pr", response_model=AnalyzeResponse)
async def analyze_pr(payload: AnalyzeRequest):
    # Run static rule checks (e.g., .env, .sql, file limits)
    rule_violations = run_static_checks(payload.files)

    # Get summary from LLM based on title, description, diff
    summary = summarize_diff(payload.title, payload.description, payload.diff)

    return AnalyzeResponse(
        summary=summary,
        rule_violations=rule_violations
    )


# Chat routes
@mcp_router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Handle chat messages and return AI response"""
    print(f"[DEBUG] Chat request received: {request}")
    try:
        # Create or get existing session
        if not request.session_id:
            print(f"[DEBUG] Creating new session for user: {request.user_id}")
            session_id = await create_chat_session(request.user_id)
            print(f"[DEBUG] Created session with ID: {session_id}")
        else:
            session_id = request.session_id
            print(f"[DEBUG] Using existing session ID: {session_id}")

        # Get current rules for context (needed for both new session and normal chat)
        print(f"[DEBUG] Fetching rules")
        rules = get_all_rules()
        print(f"[DEBUG] Found {len(rules)} rules")

        # Check if this is a new session creation request
        if request.context and request.context.get("action") == "new_session":
            # For new session creation, don't add the initial message
            print(f"[DEBUG] New session creation - skipping initial message")
            ai_response = "Hello! I'm ready to help you with rule management and code review questions."
        else:
            # Add user message to database for normal conversations
            print(f"[DEBUG] Adding user message to database")
            await add_chat_message(
                session_id=session_id,
                role="user",
                content=request.message,
                metadata=request.context
            )
            print(f"[DEBUG] User message added successfully")

            # Get chat history for context
            print(f"[DEBUG] Fetching chat history")
            messages = await get_chat_messages(session_id)
            chat_history = [
                {"role": msg["role"], "content": msg["content"]} 
                for msg in messages
            ]
            print(f"[DEBUG] Chat history length: {len(chat_history)}")
            
            # Call LLM with context
            print(f"[DEBUG] Calling LLM with message: {request.message[:100]}...")
            ai_response = await chat_with_llm(
                user_message=request.message,
                chat_history=chat_history,
                rules=rules,
                context=request.context or {}
            )
            print(f"[DEBUG] LLM response received: {ai_response[:100]}...")

            # Add AI response to database
            print(f"[DEBUG] Adding AI response to database")
            await add_chat_message(
                session_id=session_id,
                role="assistant",
                content=ai_response,
                metadata={"rules_accessed": len(rules)}
            )
            print(f"[DEBUG] AI response added successfully")

        return ChatResponse(
            message=ai_response,
            session_id=session_id,
            metadata={"rules_accessed": len(rules)}
        )

    except Exception as e:
        print(f"[ERROR] Chat error occurred: {str(e)}")
        print(f"[ERROR] Error type: {type(e)}")
        import traceback
        print(f"[ERROR] Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")


@mcp_router.get("/chat/sessions/{user_id}", response_model=List[ChatSession])
async def get_user_sessions(user_id: str):
    """Get all chat sessions for a user"""
    print(f"[DEBUG] get_user_sessions called with user_id: {user_id}")
    try:
        print(f"[DEBUG] Calling get_chat_sessions from database")
        sessions = await get_chat_sessions(user_id)
        print(f"[DEBUG] Retrieved {len(sessions)} sessions from database")
        
        result = [
            ChatSession(
                id=session["id"],
                session_name=session["session_name"],
                created_at=session["created_at"].isoformat(),
                message_count=session["message_count"],
                last_message_at=session["last_message_at"].isoformat() if session["last_message_at"] else None
            )
            for session in sessions
        ]
        print(f"[DEBUG] Returning {len(result)} sessions")
        return result
    except Exception as e:
        print(f"[ERROR] Error in get_user_sessions: {str(e)}")
        print(f"[ERROR] Error type: {type(e)}")
        import traceback
        print(f"[ERROR] Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error fetching sessions: {str(e)}")


@mcp_router.get("/chat/sessions/{session_id}/messages")
async def get_session_messages(session_id: int):
    """Get all messages in a chat session"""
    try:
        messages = await get_chat_messages(session_id)
        return [
            {
                "id": msg["id"],
                "role": msg["role"],
                "content": msg["content"],
                "metadata": msg["metadata"],
                "created_at": msg["created_at"].isoformat()
            }
            for msg in messages
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching messages: {str(e)}")


@mcp_router.delete("/chat/sessions/{session_id}")
async def delete_session(session_id: int, user_id: str):
    """Delete a chat session"""
    print(f"[DEBUG] Delete session request: session_id={session_id}, user_id={user_id}")
    try:
        success = await delete_chat_session(session_id, user_id)
        print(f"[DEBUG] Delete session result: {success}")
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        return {"message": "Session deleted successfully"}
    except Exception as e:
        print(f"[ERROR] Error deleting session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting session: {str(e)}")


# Rule management routes
@mcp_router.get("/rules", response_model=RulesResponse)
async def get_rules():
    """Get all rules"""
    try:
        rules_data = get_all_rules()
        rules = [Rule(**rule) for rule in rules_data]
        return RulesResponse(rules=rules, total=len(rules))
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error fetching rules: {str(e)}"
        )


@mcp_router.post("/rules", response_model=Rule)
async def create_rule_route(request: RuleCreateRequest):
    """Create a new rule"""
    try:
        success = create_rule(request.rule.dict())
        if not success:
            raise HTTPException(
                status_code=500, 
                detail="Failed to create rule"
            )
        return request.rule
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error creating rule: {str(e)}"
        )


@mcp_router.put("/rules/{rule_id}", response_model=Rule)
async def update_rule_route(rule_id: str, request: RuleUpdateRequest):
    """Update an existing rule"""
    try:
        success = update_rule(rule_id, request.rule.dict())
        if not success:
            raise HTTPException(status_code=404, detail="Rule not found")
        return request.rule
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error updating rule: {str(e)}"
        )


@mcp_router.delete("/rules/{rule_id}")
async def delete_rule_route(rule_id: str):
    """Delete a rule"""
    try:
        success = delete_rule(rule_id)
        if not success:
            raise HTTPException(status_code=404, detail="Rule not found")
        return {"message": "Rule deleted successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error deleting rule: {str(e)}"
        )
