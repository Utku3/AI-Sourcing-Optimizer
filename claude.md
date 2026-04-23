# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run Flask web app
python app.py

# CLI commands
python main.py setup                                          # Initialize enriched DB tables
python main.py enrich                                         # Run AI enrichment pipeline (slow — calls Ollama)
python main.py compare <prod_a> <supp_a> <prod_b> <supp_b>  # Compare two products
python main.py suggest <product_id> [--supplier <id>]        # Get ranked substitutes
python main.py inspect-source                                 # Inspect discovered DB schema

# Test schema detection and Ollama connectivity
python test_schema.py

# Create a test SQLite database with sample data
python setup_test_database.py
```

## Architecture

The system is a raw material substitution engine for food ingredient procurement. It enriches a pre-existing ERP database with AI-structured data, then computes multi-dimensional compatibility scores between products.

**Data flow:**
1. `db.py` auto-detects the source schema (standard `Product`/`Supplier`/`Supplier_Product` join, or the remote `Product_FinishedGood` variant) via `infer_raw_material_source_columns()`
2. `enrich_raw_materials.py` feeds product names through `ollama_client.py` (qwen2.5:72b) to produce a structured `product_json` with 10 fields (class, ingredient type, functional role, physical form, application domain, taste, etc.)
3. `embeddings.py` generates vectors from the enriched text — configurable between `sentence-transformers` (local, 384-dim) or OpenAI (cloud, 1536-dim)
4. `comparison_engine.py` scores two products on four axes: taste, usage, feasibility, and confidence; `comparison_scores.py` houses the individual scoring functions
5. `service.py` wraps comparison logic into `suggest_alternatives()` — filters by product class and organic status before returning ranked results
6. `app.py` (Flask) exposes a dark-themed UI with Companies, Suppliers, and comparison tabs, backed by `/api/company/<id>`, `/api/suggest/<id>`, and `/api/compare/<a>/<b>` endpoints

**Three-table enriched schema** (created by `main.py setup`):
- `raw_material_master` — AI-enriched product records (product_json, product_class, supplier info)
- `raw_material_embeddings` — vector embeddings per product-supplier pair
- `raw_material_comparisons` — cached comparison results (grows with use)

**Scoring weights** (`comparison_scores.py`): usage 30%, feasibility 30%, taste 20%, AI confidence 20%. Labels: ≥0.80 "strong substitute", ≥0.60 "possible substitute", <0.60 "weak substitute".

## Key Configuration

`config.py` reads from environment variables. Defaults:
- `OLLAMA_BASE_URL=http://localhost:11434`, model `qwen2.5:72b`, timeout 120 s
- `EMBEDDING_BACKEND=sentence-transformers`, model `all-MiniLM-L6-v2`
- `DATABASE_PATH` — path to the SQLite file

The enrichment pipeline (`enrich_raw_materials.py`) retries Ollama up to 3 times per product and validates required fields before storing. Enrichment is expensive; comparisons are cached in `raw_material_comparisons`.

## Database

The SQLite file (`db.sqlite`) is not committed. `schema.sql` defines the enriched tables. `DATABASE_TABLES_REFERENCE.md` documents the full pre-existing ERP schema (Company, Product, Supplier, Supplier_Product, BOM, BOM_Component tables with row counts and column details).
