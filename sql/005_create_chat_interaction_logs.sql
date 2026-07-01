-- Chat interaction logging.
--
-- Records every question sent to the experimental Chat endpoints so we can see
-- how people use it and review whether any prompt-injection attempts changed
-- the model's behaviour. `raw_model_response` is the verbatim model output and
-- is the primary field for injection review.
--
-- Privacy note: `question`, `client_ip`, and `user_agent` can be personal data.
-- Client IP capture can be disabled with CHAT_LOG_INCLUDE_CLIENT_IP=0. Apply a
-- retention policy appropriate to your deployment.

CREATE TABLE IF NOT EXISTS chat_interaction_logs (
    log_id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    endpoint TEXT NOT NULL,                       -- 'ask' | 'retrieve'
    status TEXT NOT NULL,                         -- 'ok' | 'error'
    question TEXT NOT NULL,                        -- raw user input, verbatim
    dataset_id TEXT,                              -- optional dataset filter chosen by the user
    error TEXT,                                   -- error detail when status = 'error'
    latency_ms INTEGER,
    model TEXT,                                   -- chat model used (ask only)
    answer TEXT,                                  -- final answer text (ask only)
    raw_model_response TEXT,                      -- verbatim model output (ask only)
    retrieval_queries JSONB,                      -- expanded retrieval queries
    candidate_series_ids JSONB,                   -- series ids retrieved as candidates
    selected_series_ids JSONB,                    -- series ids the model selected
    selected_reference_chunk_ids JSONB,           -- reference chunk ids the model selected
    client_ip TEXT,                               -- best-effort client IP (proxy-aware)
    user_agent TEXT
);

CREATE INDEX IF NOT EXISTS chat_interaction_logs_created_idx
    ON chat_interaction_logs (created_at);

CREATE INDEX IF NOT EXISTS chat_interaction_logs_endpoint_idx
    ON chat_interaction_logs (endpoint, created_at);

CREATE INDEX IF NOT EXISTS chat_interaction_logs_status_idx
    ON chat_interaction_logs (status, created_at);
