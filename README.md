# Raw Material Substitution Decision-Support System

A modular Python system for raw-material substitution in supply-chain AI assistants. This system analyzes raw materials, generates structured data using Ollama with qwen2.5:72b, computes similarity scores, and provides substitution recommendations.

## Features

- **Automatic Schema Detection**: Works with multiple database schemas (standard or Product_FinishedGood)
- **Data Enrichment**: Clean product names and enrich with structured data from Ollama qwen2.5:72b
- **Embedding Generation**: Create text embeddings for semantic similarity analysis
- **Comparison Engine**: Calculate compatibility scores between raw materials
- **Substitution Suggestions**: Find and rank alternative materials
- **Modular Architecture**: Clean separation of concerns with configurable backends

## Supported Database Schemas

The system automatically detects and adapts to different database schemas:

### Schema 1: Standard (Product + Supplier + Supplier_Product)
- `Product` table with `Id`, `SKU`, `Type` columns
- `Supplier` table with `Id`, `Name` columns
- `Supplier_Product` junction table

### Schema 2: Product_FinishedGood (Remote Server)
- `Product_FinishedGood` table with `ProductId`, `Market`, `MarketSearch`, `MarketAdditional` columns
- No separate Supplier table (Market field used as supplier identifier)

## Project Structure

```
├── schema.sql                 # Database schema
├── db.py                      # Database utilities with schema introspection
├── config.py                  # Configuration management
├── name_cleaning.py           # Product name cleaning functions
├── ollama_client.py           # Ollama API client
├── enrich_raw_materials.py    # Enrichment pipeline script
├── embedding_text_builder.py  # Embedding text generation
├── embeddings.py              # Embedding service with multiple backends
├── comparison_scores.py       # Score calculation functions
├── comparison_engine.py       # Product comparison logic
├── service.py                 # High-level service functions
├── main.py                    # CLI entry point
├── test_schema.py             # Schema detection test utility
└── requirements.txt           # Python dependencies
```

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Ensure Ollama is running locally with qwen2.5:72b model:
```bash
ollama serve
ollama pull qwen2.5:72b
```

3. Initialize database (creates tables if needed):
```bash
python main.py setup
```

4. Verify schema detection (optional but recommended):
```bash
python test_schema.py
```

## Usage

### Test Schema Detection

Before running enrichment, verify the database schema is detected correctly:

```bash
# Comprehensive schema test
python test_schema.py

# Or inspect with detailed output
python main.py inspect-source
```

### Enrich Raw Materials

Run the enrichment pipeline to process raw materials with Ollama:

```bash
python main.py enrich
```

### Compare Products

Compare two specific products:

```bash
python main.py compare <product_a_id> <supplier_a_id> <product_b_id> <supplier_b_id>
```

### Suggest Alternatives

Find substitution alternatives for a product:

```bash
python main.py suggest <product_id> [--supplier <supplier_id>]
```

## Database Schema

### raw_material_master
Stores enriched product data with supplier information.

### raw_material_embeddings
Stores text embeddings for similarity analysis.

### raw_material_comparisons
Stores comparison results between product pairs.

## API Functions

### compare_products(product_id_a, supplier_id_a, product_id_b, supplier_id_b)
Returns structured comparison data including scores and recommendations.

### suggest_alternatives(product_id, supplier_id=None)
Returns ranked list of alternative materials with compatibility scores.

## Configuration

The system uses Ollama locally:
- **Base URL**: http://localhost:11434
- **Model**: qwen2.5:72b
- **Timeout**: 120 seconds

Embedding backends:
- **sentence-transformers**: Local, free, good performance (default)
- **OpenAI**: Cloud-based, requires API key, high quality

Configure via environment variables or modify `config.py`.

## Dependencies

- requests: HTTP client for API calls
- sentence-transformers: Local embedding generation (optional)
- openai: OpenAI API client (optional)
- sqlite3: Database (built-in)

## Architecture Principles

- **Modular**: Each component has a single responsibility
- **Configurable**: Easy to switch embedding backends
- **Type-safe**: Full type hints throughout
- **Error-handling**: Comprehensive logging and error management
- **Production-ready**: Clean code with documentation