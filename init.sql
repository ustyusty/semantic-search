CREATE TABLE IF NOT EXISTS documents(
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    block TEXT,
    embedding DOUBLE PRECISION[],
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_documents_title ON documents(title);
