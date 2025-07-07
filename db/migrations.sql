-- Chat sessions table
CREATE TABLE IF NOT EXISTS chat_sessions (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    session_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Chat messages table
CREATE TABLE IF NOT EXISTS chat_messages (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- PR Summary table
CREATE TABLE IF NOT EXISTS pr_summary (
    id SERIAL PRIMARY KEY,
    repo_full_name VARCHAR(255) NOT NULL,
    pr_number INTEGER NOT NULL,
    pr_url TEXT NOT NULL,
    title TEXT NOT NULL,
    author_login VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE,
    closed_at TIMESTAMP WITH TIME ZONE,
    merged_at TIMESTAMP WITH TIME ZONE,
    is_merged BOOLEAN DEFAULT FALSE,
    commits_count INTEGER DEFAULT 0,
    additions INTEGER DEFAULT 0,
    deletions INTEGER DEFAULT 0,
    changed_files INTEGER DEFAULT 0,
    comments_count INTEGER DEFAULT 0,
    review_comments_count INTEGER DEFAULT 0,
    approvals_count INTEGER DEFAULT 0,
    violation_count INTEGER DEFAULT 0,
    violations JSONB DEFAULT '[]'::jsonb,
    summary_text TEXT,
    summary_generated_at TIMESTAMP WITH TIME ZONE,
    metrics_updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(repo_full_name, pr_number)
);

-- PR Events table
CREATE TABLE IF NOT EXISTS pr_events (
    id SERIAL PRIMARY KEY,
    pr_summary_id INTEGER NOT NULL REFERENCES pr_summary(id) ON DELETE CASCADE,
    event_type VARCHAR(100) NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- PR Assistant Interactions table
CREATE TABLE IF NOT EXISTS pr_assistant_interactions (
    id SERIAL PRIMARY KEY,
    pr_summary_id INTEGER NOT NULL REFERENCES pr_summary(id) ON DELETE CASCADE,
    user_query TEXT NOT NULL,
    assistant_resp JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for better performance
CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_id ON chat_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id ON chat_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_created_at ON chat_messages(created_at);
CREATE INDEX IF NOT EXISTS idx_pr_summary_repo_pr ON pr_summary(repo_full_name, pr_number);
CREATE INDEX IF NOT EXISTS idx_pr_events_summary_id ON pr_events(pr_summary_id);
CREATE INDEX IF NOT EXISTS idx_pr_assistant_interactions_summary_id ON pr_assistant_interactions(pr_summary_id);

-- Update trigger for chat_sessions
CREATE OR REPLACE FUNCTION update_chat_sessions_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_chat_sessions_updated_at
    BEFORE UPDATE ON chat_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_chat_sessions_updated_at(); 