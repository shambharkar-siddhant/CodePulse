# mcp_server/models.py

from typing import List, Optional, Union
from pydantic import BaseModel


class FileEntry(BaseModel):
    filename: str
    status: str
    additions: Optional[int] = 0
    deletions: Optional[int] = 0


class UserInfo(BaseModel):
    login: str
    id: Union[str, int]
    url: str


class AnalyzeRequest(BaseModel):
    title: str
    description: Optional[str] = ""
    diff: str
    files: List[FileEntry]
    repo_full_name: str
    pr_number: int
    user: UserInfo


class RuleViolation(BaseModel):
    rule_id: str
    status: str
    reason: str


class AnalyzeResponse(BaseModel):
    summary: str
    rule_violations: List[RuleViolation]


# Chat models
class ChatMessage(BaseModel):
    role: str  # "user", "assistant", "system"
    content: str
    metadata: Optional[dict] = None


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[int] = None
    user_id: str
    context: Optional[dict] = None


class ChatResponse(BaseModel):
    message: str
    session_id: int
    metadata: Optional[dict] = None


class ChatSession(BaseModel):
    id: int
    session_name: str
    created_at: str
    message_count: int
    last_message_at: Optional[str] = None


# Rule management models
class Rule(BaseModel):
    rule_id: str
    type: str  # "equals", "endswith", "global"
    match: Optional[str] = None
    threshold: Optional[int] = None
    reason: str


class RuleCreateRequest(BaseModel):
    rule: Rule


class RuleUpdateRequest(BaseModel):
    rule_id: str
    rule: Rule


class RuleDeleteRequest(BaseModel):
    rule_id: str


class RulesResponse(BaseModel):
    rules: List[Rule]
    total: int
