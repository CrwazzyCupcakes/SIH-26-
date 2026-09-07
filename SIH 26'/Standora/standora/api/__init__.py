"""Standora web app and API.

This app exposes:
- a simple browser UI for testing retrieval and category-aware queries
- a JSON API for local retrieval and structured lookups
- a Groq-backed response layer using a grounded RAG pattern
"""

import os
from pathlib import Path
from typing import Dict, List, Optional

from flask import Flask, jsonify, render_template, request
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from standora.ingestion import (
    get_crs_table,
    get_faqs,
    get_labs,
    init_retriever,
    lookup_standard,
    retrieve,
    search_crs,
    search_faqs,
    search_standards,
)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _groq_answer(query: str, category: Optional[str], results: List[Dict]) -> Optional[str]:
    api_key = os.environ.get("GROQ_API_KEY")
    model = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b")

    if not api_key:
        return None

    try:
        from groq import Groq
        from groq import APIError, NotFoundError
    except Exception:
        return None

    context_parts = []
    for index, item in enumerate(results[:5], 1):
        snippet = (item.get("text") or "").replace("\n", " ").strip()
        citation = item.get("citation") or item.get("source_file") or "Source not provided"
        context_parts.append(f"[{index}] {citation}\n{snippet[:600]}")

    context_text = "\n\n".join(context_parts) if context_parts else "No direct source context found."
    system_prompt = (
        "You are Standora, an expert BIS and Indian Standards assistant. "
        "Answer using ONLY the user-provided knowledge context below. "
        "Do not invent facts or claim certainty beyond the sources. "
        "When the context is insufficient, say that the information is not available in the provided sources. "
        "Always include the most relevant source references or citations in your answer. "
        "Keep the answer clear, practical, and suitable for MSMEs, startups, students, and consumers."
    )
    user_prompt = (
        f"User question: {query}\n"
        f"Category: {category or 'all'}\n\n"
        "Knowledge context:\n"
        f"{context_text}"
    )

    client = Groq(api_key=api_key)
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=700,
        )
        return response.choices[0].message.content.strip()
    except (APIError, NotFoundError):
        return None


def create_app():
    app = Flask(
        __name__,
        template_folder=str(Path(__file__).resolve().parent / "templates"),
        static_folder=str(Path(__file__).resolve().parent / "static"),
    )

    project_root = _project_root()
    data_root = os.environ.get("STANDORA_DATA_ROOT", str(project_root / "standora_data"))
    index_dir = os.environ.get("STANDORA_INDEX_DIR", str(project_root / "index"))
    os.environ.setdefault("GROQ_MODEL", "openai/gpt-oss-20b")

    try:
        init_retriever(index_dir=index_dir, data_root=data_root)
        app.config["DATA_ROOT"] = data_root
        app.config["INDEX_DIR"] = index_dir
    except Exception as exc:  # pragma: no cover - surfaced in runtime, not test logic
        app.config["INIT_ERROR"] = str(exc)

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/health")
    def health():
        return jsonify({"status": "ok", "data_root": data_root, "index_dir": index_dir})

    @app.route("/api/query", methods=["POST"])
    def api_query():
        payload = request.get_json(silent=True) or {}
        query = (payload.get("query") or "").strip()
        category = (payload.get("category") or "all").strip()
        k = int(payload.get("k") or 5)

        if not query:
            return jsonify({"error": "query is required"}), 400

        category_name = None if category.lower() == "all" else category
        results = retrieve(query, category=category_name, k=k)

        standard_hits = []
        if "is " in query.lower() or "standard" in query.lower():
            standard_hits = search_standards(query, category_name)[:3]

        faq_hits = []
        if "faq" in query.lower() or "question" in query.lower() or "certification" in query.lower():
            faq_hits = search_faqs(query, category_name)[:3]

        answer = _groq_answer(query, category_name, results)

        response = {
            "query": query,
            "category": category_name,
            "results": results,
            "standards": standard_hits,
            "faqs": faq_hits,
            "answer": answer,
            "model": os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b"),
        }
        return jsonify(response)

    @app.route("/api/retrieve", methods=["POST"])
    def api_retrieve():
        data = request.get_json(silent=True) or {}
        query = (data.get("query") or "").strip()
        category = data.get("category")
        k = data.get("k", 5)

        if not query:
            return jsonify({"error": "query required"}), 400

        results = retrieve(query, category, int(k))
        return jsonify({"results": results})

    @app.route("/api/standard", methods=["GET"])
    def api_standard():
        is_number = request.args.get("is_number")
        category = request.args.get("category")

        if not is_number:
            return jsonify({"error": "is_number required"}), 400

        result = lookup_standard(is_number, category)
        if result is None:
            return jsonify({"error": "not found"}), 404
        return jsonify(result)

    @app.route("/api/standards/search", methods=["GET"])
    def api_search_standards():
        keyword = request.args.get("keyword")
        category = request.args.get("category")

        if not keyword:
            return jsonify({"error": "keyword required"}), 400

        results = search_standards(keyword, category)
        return jsonify({"results": results})

    @app.route("/api/labs", methods=["GET"])
    def api_labs():
        category = request.args.get("category")
        location = request.args.get("location")
        results = get_labs(category, location)
        return jsonify({"results": results})

    @app.route("/api/faqs", methods=["GET"])
    def api_faqs():
        category = request.args.get("category")
        query = request.args.get("q")

        if query:
            results = search_faqs(query, category)
        else:
            results = get_faqs(category)

        return jsonify({"results": results})

    @app.route("/api/crs", methods=["GET"])
    def api_crs():
        category = request.args.get("category")
        keyword = request.args.get("keyword")

        if keyword:
            results = search_crs(keyword, category)
        else:
            results = get_crs_table(category)

        return jsonify({"results": results})

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5001")), debug=True)