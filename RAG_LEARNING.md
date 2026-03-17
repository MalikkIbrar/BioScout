# 🧠 RAG System Deep-Dive — BioScout

> A practical explanation of Retrieval-Augmented Generation (RAG) for AI engineers,
> using BioScout's hybrid retrieval system as a concrete example.

---

## What Problem Does RAG Solve?

Large Language Models (LLMs) like GPT-4 or DeepSeek have a fundamental limitation:
their knowledge is frozen at training time. Ask them about a specific species in a
specific region, and they may hallucinate facts or give generic answers.

**RAG fixes this by giving the LLM a "cheat sheet" at query time.**

Instead of relying on memorised weights, the model retrieves relevant documents from
a knowledge base and uses them as grounded context. The answer is only as wrong as
the documents — which you control.

```
WITHOUT RAG:
  User: "What do snow leopards eat in Pakistan?"
  LLM:  [generates from memorised training data — may hallucinate]

WITH RAG:
  User: "What do snow leopards eat in Pakistan?"
  Retriever: [finds Snow Leopard document from knowledge base]
  LLM:  [reads document, generates grounded answer]
  → Answer cites actual facts from your curated data
```

---

## The Three Components of RAG

### 1. Knowledge Base (Documents)
A collection of structured text documents. In BioScout, each document is a Python
dict with fields like `species_name`, `habitat`, `diet`, `description`, `threats`.

```python
# Pseudocode: one knowledge base document
{
    "species_name": "Snow Leopard",
    "scientific_name": "Panthera uncia",
    "category": "mammal",
    "habitat": "Alpine rocky terrain, 3000-5500m",
    "diet": "Blue sheep, ibex, marmots",
    "conservation_status": "VU",
    "description": "Pakistan holds 200-420 individuals...",
    "threats": "Poaching, retaliatory killing, climate change",
}
```

### 2. Retriever
Given a user query, finds the most relevant documents. BioScout uses a **hybrid
retriever** combining two methods (explained below).

### 3. Generator (LLM)
Takes the retrieved documents as context and generates a natural-language answer.
BioScout uses DeepSeek Chat.

---

## BM25 — Keyword Search

BM25 (Best Match 25) is a probabilistic ranking function. It scores documents based
on how often query terms appear, adjusted for document length and term frequency
across the corpus.

### How it works

```
BM25 Score(document, query) =
  Σ IDF(term) × (TF(term, doc) × (k1 + 1)) / (TF(term, doc) + k1 × (1 - b + b × |doc|/avgdl))

Where:
  IDF = Inverse Document Frequency (rare terms score higher)
  TF  = Term Frequency in this document
  k1  = term frequency saturation parameter (default 1.5)
  b   = length normalisation parameter (default 0.75)
  |doc| = document length
  avgdl = average document length in corpus
```

### Pseudocode

```python
def build_bm25_index(documents):
    # Tokenise each document
    tokenised_corpus = [tokenise(doc_to_text(doc)) for doc in documents]
    # Build BM25 model
    bm25 = BM25Okapi(tokenised_corpus)
    return bm25

def bm25_search(query, bm25, documents, top_k=3):
    tokens = tokenise(query)
    scores = bm25.get_scores(tokens)          # score for every document
    normalised = [s / max(scores) for s in scores]  # 0-1 range
    ranked = sorted(enumerate(normalised), key=lambda x: x[1], reverse=True)
    return [documents[idx] for idx, score in ranked[:top_k]]
```

### Strengths
- Exact keyword matching — "Snow Leopard" → finds Snow Leopard documents
- No GPU, no model download, runs in milliseconds
- Interpretable — you can see exactly why a document was ranked

### Weaknesses
- Vocabulary mismatch — "big cat" won't find "Snow Leopard" unless those words appear
- No semantic understanding — "apex predator" won't match "top of the food chain"

---

## Vector Search — Semantic Similarity

Vector search converts text into dense numerical vectors (embeddings) where
semantically similar texts are close together in vector space.

### How embeddings work

```
"Snow Leopard eats blue sheep"  →  [0.23, -0.41, 0.87, ...]  (384 dimensions)
"Panthera uncia preys on bharal" →  [0.21, -0.39, 0.85, ...]  (very similar!)
"House Sparrow eats seeds"       →  [-0.12, 0.67, -0.23, ...] (very different)
```

The model (all-MiniLM-L6-v2) was trained to place semantically similar sentences
near each other in this 384-dimensional space.

### Cosine Similarity

```
similarity(A, B) = (A · B) / (|A| × |B|)

Range: -1 (opposite) to 1 (identical)
```

### Pseudocode

```python
def build_vector_index(documents, embedding_model):
    for doc in documents:
        text = doc_to_text(doc)           # combine all fields into one string
        vector = embedding_model.embed(text)  # 384-dim float array
        chromadb.upsert(id=doc["species_name"], vector=vector, metadata=doc)

def vector_search(query, embedding_model, chromadb, top_k=3):
    query_vector = embedding_model.embed(query)
    results = chromadb.query(query_vector, n_results=top_k)
    # ChromaDB returns cosine distance (0=identical, 2=opposite)
    # Convert to similarity: score = 1 - distance
    return results
```

### Strengths
- Semantic understanding — "big cat" finds "Snow Leopard"
- Handles paraphrases and synonyms
- Language-agnostic (works across languages)

### Weaknesses
- Misses exact keyword matches sometimes
- Requires model download and inference time
- Less interpretable — hard to explain why a document was retrieved

---

## Hybrid Retrieval — Best of Both Worlds

BioScout combines BM25 and vector search. Neither method alone is best:

| Query | BM25 wins | Vector wins |
|---|---|---|
| "Snow Leopard diet" | ✅ exact name match | ✅ semantic match |
| "big cats of Pakistan" | ❌ no "big cats" in docs | ✅ semantic match |
| "Panthera uncia" | ✅ scientific name match | ✅ semantic match |
| "animals that hunt at night" | ❌ "nocturnal" not in query | ✅ semantic match |

### Reciprocal Rank Fusion (RRF)

RRF merges two ranked lists into one. The key insight: **a document appearing in
both lists is more likely to be relevant than one appearing in only one**.

```
RRF_score(document) = Σ  1 / (k + rank_in_list)
                    for each ranked list

Where k = 60 (standard constant from the original RRF paper, 2009)
```

### Pseudocode

```python
def reciprocal_rank_fusion(bm25_results, vector_results, k=60):
    scores = {}

    # Score from BM25 ranking
    for rank, doc in enumerate(bm25_results, start=1):
        name = doc["species_name"]
        scores[name] = scores.get(name, 0) + 1 / (k + rank)

    # Score from vector ranking
    for rank, doc in enumerate(vector_results, start=1):
        name = doc["species_name"]
        scores[name] = scores.get(name, 0) + 1 / (k + rank)

    # Sort by combined score
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)

# Example:
# BM25 results:   [Snow Leopard(1), Markhor(2), Ibex(3)]
# Vector results: [Snow Leopard(1), Common Leopard(2), Markhor(3)]
#
# RRF scores:
#   Snow Leopard  = 1/(60+1) + 1/(60+1) = 0.0328  ← appears in BOTH → highest
#   Markhor       = 1/(60+2) + 1/(60+3) = 0.0321
#   Common Leopard = 1/(60+2)            = 0.0161
#   Ibex          = 1/(60+3)             = 0.0159
```

Why k=60? It prevents a rank-1 result from dominating too much. With k=60, the
difference between rank 1 and rank 2 is small, so documents appearing in both
lists reliably beat documents appearing in only one.

---

## Full RAG Pipeline — Pseudocode

```python
def rag_answer(user_question):
    # Step 1: Retrieve relevant documents
    bm25_results = bm25.search(user_question, top_k=6)
    vector_results = chromadb.search(user_question, top_k=6)

    # Step 2: Fuse rankings
    fused_scores = reciprocal_rank_fusion(bm25_results, vector_results)
    top_3_names = [name for name, score in fused_scores[:3]]

    # Step 3: Fetch full documents
    context_docs = [knowledge_base[name] for name in top_3_names]

    # Step 4: Format context for LLM
    context = format_context(context_docs)
    # → "[Source 1: Snow Leopard (Panthera uncia)]\nHabitat: Alpine...\n..."

    # Step 5: Generate grounded answer
    prompt = f"""
    Context from knowledge base:
    {context}

    Question: {user_question}

    Answer using ONLY the provided context. Cite source species names.
    """
    answer = deepseek_llm.chat(prompt)

    return {
        "answer": answer,
        "sources": top_3_names,
        "method": "hybrid_bm25_vector",
    }
```

---

## Evaluation — How Do We Know It Works?

BioScout includes a benchmark with 10 questions and expected species names.

```python
BENCHMARK = [
    {
        "question": "What do snow leopards eat?",
        "expected_species": ["Snow Leopard"],
    },
    {
        "question": "Which birds are common in Lahore?",
        "expected_species": ["House Sparrow", "Common Myna"],
    },
    # ... 8 more
]

def evaluate(retriever, top_k=3):
    hits = 0
    for item in BENCHMARK:
        results = retriever.hybrid_search(item["question"], top_k=top_k)
        retrieved_names = [r["species_name"] for r in results]
        # Hit = at least one expected species in top_k results
        if any(exp in retrieved_names for exp in item["expected_species"]):
            hits += 1
    return hits / len(BENCHMARK)  # BioScout achieves 70%
```

**BioScout result: 7/10 (70%) retrieval accuracy**

---

## Why Not Just Use the LLM Directly?

| | Pure LLM | RAG |
|---|---|---|
| Accuracy | May hallucinate | Grounded in your data |
| Freshness | Frozen at training | Update knowledge base anytime |
| Cost | Full context window | Only relevant docs sent |
| Explainability | Black box | Shows which sources were used |
| Control | None | You own the knowledge base |

---

## Key Design Decisions in BioScout

**No torch/transformers** — The embedding model (all-MiniLM-L6-v2) runs via
`onnxruntime` inside ChromaDB's `DefaultEmbeddingFunction`. This saves ~2GB of
disk space and avoids CUDA dependencies entirely.

**Persistent indexes** — Both ChromaDB (vector) and BM25 (pickle) are saved to
disk. The `HybridRetriever` loads them on startup, so there's no re-indexing on
every request.

**Title boosting in BM25** — Species names are repeated 3× in the BM25 document
text to give them higher weight. This ensures "Snow Leopard" queries reliably
surface the Snow Leopard document.

**RRF k=60** — The standard value from the original 2009 paper by Cormack et al.
It works well empirically across many retrieval tasks.

---

## Further Reading

- [BM25 original paper — Robertson & Zaragoza (2009)](https://www.staff.city.ac.uk/~sbrp622/papers/foundations_bm25_review.pdf)
- [RRF paper — Cormack et al. (2009)](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf)
- [ChromaDB docs](https://docs.trychroma.com)
- [all-MiniLM-L6-v2 on HuggingFace](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)
- [RAG survey paper — Lewis et al. (2020)](https://arxiv.org/abs/2005.11401)
