-- Schema for raw-material substitution decision-support system

-- Table to store enriched raw material data
CREATE TABLE IF NOT EXISTS raw_material_master (
    product_id INTEGER NOT NULL,
    product_name TEXT NOT NULL,
    product_json TEXT,  -- JSON string from Ollama API
    product_class TEXT,  -- general_class from JSON
    supplier_id INTEGER NOT NULL,
    supplier_name TEXT NOT NULL,
    supplier_json TEXT,  -- supplier summary JSON
    PRIMARY KEY (product_id, supplier_id)
);

-- Table to store embeddings for raw materials
CREATE TABLE IF NOT EXISTS raw_material_embeddings (
    product_id INTEGER NOT NULL,
    supplier_id INTEGER NOT NULL,
    embedding_text TEXT NOT NULL,
    embedding_model TEXT NOT NULL,
    embedding_vector BLOB NOT NULL,
    PRIMARY KEY (product_id, supplier_id)
);

-- Table to store comparison results between raw materials
CREATE TABLE IF NOT EXISTS raw_material_comparisons (
    product_id_a INTEGER NOT NULL,
    supplier_id_a INTEGER NOT NULL,
    product_id_b INTEGER NOT NULL,
    supplier_id_b INTEGER NOT NULL,
    taste_score REAL NOT NULL,
    feasibility_score REAL NOT NULL,
    usage_score REAL NOT NULL,
    confidence_score REAL NOT NULL,
    general_comparison_score REAL NOT NULL,
    comparison_label TEXT NOT NULL,
    comparison_reason TEXT NOT NULL,
    PRIMARY KEY (product_id_a, supplier_id_a, product_id_b, supplier_id_b)
);