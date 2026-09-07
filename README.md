# Standora

Standora is a local, source-grounded assistant for Indian Standards and BIS-related guidance. It retrieves relevant material from the included knowledge base and uses Groq to generate an answer from that retrieved context.

The assistant is designed to avoid unsupported claims. When the local sources do not contain enough information, it should say so.

## Included knowledge

- Food
- Toys
- Electricals
- Shared BIS and consumer guidance
- Structured standards, lab, FAQ, and CRS data

The Toys folder can also use local text-based PDF resources. The supplied BIS publication is ignored by Git by default because it may be copyrighted; keep it locally or add only material you are permitted to redistribute.

## Requirements

- Python 3.9 or newer
- A Groq API key for generated answers
- Internet access on the first run to download the embedding model

## Setup

```bash
git clone <your-repository-url>
cd standora_clean
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Open `.env` and replace `your_groq_api_key_here` with your Groq API key. Never commit `.env`.

## Run the web app

```bash
python3 -m standora.api
```

Open http://127.0.0.1:5002 in your browser.

On the first run, Standora builds `index/faiss.index` and `index/chunks.pkl` from `standora_data`. Those files are generated and ignored by Git. Later runs load the existing index.

To use another port:

```bash
PORT=5003 python3 -m standora.api
```

## Rebuild the index

Rebuild after adding or changing knowledge files:

```bash
python3 -c "from standora.ingestion.pipeline import run_ingestion; run_ingestion(data_root='standora_data', index_dir='index', force_rebuild=True)"
```

## Run the retrieval demo

```bash
