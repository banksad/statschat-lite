CREATE TABLE IF NOT EXISTS series_search_documents (
    series_id BIGINT PRIMARY KEY REFERENCES series(series_id) ON DELETE CASCADE,
    dataset_id TEXT NOT NULL,
    series_key TEXT NOT NULL,
    indicator_code TEXT,
    indicator_name TEXT,
    document_version TEXT NOT NULL,
    primary_text TEXT NOT NULL,
    embedding_text TEXT NOT NULL,
    keyword_text TEXT NOT NULL,
    parsed_metadata JSONB NOT NULL,
    content_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_series_search_documents_dataset_id
    ON series_search_documents(dataset_id);

CREATE INDEX IF NOT EXISTS idx_series_search_documents_indicator_code
    ON series_search_documents(indicator_code);

CREATE INDEX IF NOT EXISTS idx_series_search_documents_document_version
    ON series_search_documents(document_version);

CREATE INDEX IF NOT EXISTS idx_series_search_documents_content_hash
    ON series_search_documents(content_hash);
