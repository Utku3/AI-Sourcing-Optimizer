# Raw Material Substitution Decision-Support System

A modular Python system for raw-material substitution in supply-chain AI assistants. This system analyzes raw materials, generates structured data using AI, computes similarity scores, and provides substitution recommendations.

## Features

- **Data Enrichment**: Clean product names and enrich with structured data from Qwen API
- **Embedding Generation**: Create text embeddings for semantic similarity analysis
- **Comparison Engine**: Calculate compatibility scores between raw materials
- **Substitution Suggestions**: Find and rank alternative materials
- **Modular Architecture**: Clean separation of concerns with configurable backends

## Project Structure

```
├── schema.sql                 # Database schema
├── db.py                      # Database utilities
├── config.py                  # Configuration management
├── name_cleaning.py           # Product name cleaning functions
├── qwen_client.py             # Qwen API client
├── enrich_raw_materials.py    # Enrichment pipeline script
├── embedding_text_builder.py  # Embedding text generation
├── embeddings.py              # Embedding service with multiple backends
├── comparison_scores.py       # Score calculation functions
├── comparison_engine.py       # Product comparison logic
├── service.py                 # High-level service functions
├── main.py                    # CLI entry point
└── requirements.txt           # Python dependencies
```

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set environment variables:
```bash
export QWEN_API_KEY="your-qwen-api-key"
export QWEN_BASE_URL="https://api.qwen.ai/v1"  # Optional
export QWEN_MODEL="qwen-turbo"                # Optional

# For OpenAI embeddings (optional)
export OPENAI_API_KEY="your-openai-api-key"
export EMBEDDING_BACKEND="openai"             # Default: sentence-transformers
```

3. Initialize database:
```bash
python main.py setup
```

## Usage

### Enrich Raw Materials

Run the enrichment pipeline to process raw materials with Qwen API:

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

### compare_products(product_id_a, product_id_b)
Returns structured comparison data including scores and recommendations.

### suggest_alternatives(product_id)
Returns ranked list of alternative materials with compatibility scores.

## Configuration

The system supports multiple embedding backends:
- **sentence-transformers**: Local, free, good performance (default)
- **OpenAI**: Cloud-based, requires API key, high quality

Configure via environment variables or modify `config.py`.

## Dependencies

- requests: HTTP client for API calls
- sentence-transformers: Local embedding generation
- openai: OpenAI API client (optional)
- sqlite3: Database (built-in)

## Architecture Principles

- **Modular**: Each component has a single responsibility
- **Configurable**: Easy to switch embedding backends
- **Type-safe**: Full type hints throughout
- **Error-handling**: Comprehensive logging and error management
- **Production-ready**: Clean code with documentation