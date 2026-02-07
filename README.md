# Unifize AI Assignment

## Data Modelling

To enable traceability and keep track of customers and their specific documents, embeddings, etc. we would have the following data models:

- Customer
  - customer_id
  - ...other metadata related to a customer
- Document
  - document_id
  - customer_id (FK)
  - file_location (link to s3 for the stored PDF)
  - ...other file metadata
- Document_Chunk (linked to Embeddings)
  - chunk_id
  - document_id
  - customer_id
  - chunk_text
  - other metadata related to chunk
- AI Outputs
  - response_id
  - user query
  - prompt_used
  - response
  - chunk_ids (chunks used to answer query)
  - chunk_texts
  - other LLM-related metadata

In the VectorDB (Pinecone or Weaviate)

- Embeddings
  - chunk_id (related to the SQL table)
  - vector
  - metadata (same as the Document Chunk) - for added context in responses

### Traceability

We mainitain records at each step from:

1. Customer Onboarding (in the Customer table)
2. Document Upload (in the Document table) with the location of the original file.
3. During chunking, we store the embeddings in the vectorDB as well as the associated chunks (in the DocumentChunk table)
4. When a user inputs a query, the referenced chunks (the ids as well as the texts) are logged in the db.
5. And the AI response, the prompt used as well as other LLM details like model, temperatures, input-output costs are also stored and logged.

### Tenant Isolation

1. VectorDB Layer:
   - For isolation at the vector level, we use namespacesto store the embeddings. In weaviate, we store the embeddings in tenants, which serve the same purpose as namespaces in Pinecone.

2. Database Layer:
   - At the database level, we use RLS (row-level security) to only allow querying the currently selected customer by adding filters for customer_id.

3. Application Layer:
   - At the application level, we can use authentication strategies using JWT tokens, middlewares, etc.

## Embedding Pipeline

### Design Decisions

- Granularity - chunking (512 or 1024 tokens per chunk)
  - Document-level is too large to be used effectively in an LLM context window, while Field-level is too small, the context around the content is missed and doesn't provide with much information to the usafe of the field.

  - We need to process documents such that there is enough content in the embedding to gather any paragraph or page-level context and is fit to be used by LLMs in responses and prompts without losing any context of a quite large data.
  - Additionaly, we can add some 50-100 tokens of overlap between chunks as well to preserve page/paragraph overflows.

### Pipeline

**Ingestion Pipeline**

Upload PDF --> Extract text (PyMuPDF) --> Create chunks with a hash (Langchain; hash for chunk text matching) --> Save to DB (embedding pending) --> Publish to Queue (chunk-level) --> Worker picks up chunk and generates embeddings (Ada002) --> Save in the vector DB (along with all the metadata related to the chunk; update embedding status to completed)

**Update Pipeline**

Document Updated --> Update the older document file path --> Mark current chunks inactive --> Create new chunks with version += 1 --> Generate embeddings on new chunks --> Older chunks are either deleted or moved to an archived namespace (to preserve audit trail and prevent older embeddings to affect the RAG pipeline)

To ensure the embeddings are in sync with the source document, we can have either -

1. Always mark all the older chunks as inactive and store the new chunks for the document even if minor changes were made.
2. Keep a content hash for all the chunks and only embed for the chunks with a content hash not already present in the vector db.

We only re-embed if new chunks are added, content hash has changed or if the embedding model has been updated.

## RAG Workflow

User Query --> Context Intake & Validation (customer id, user role, usecase, query, etc.) --> Generate Retrieval Query (for better retrieval from vectordb rather than using the user question directly) --> Retrieval from VectorDB (hybrid search - keyword+ semantic search -> merge, rerank and dedup) --> Create Prompt with the Added Context from Retrieved Chunks (add user context, chunks as well other instructions to always cite the relevant sources) --> LLM Invokation (set temperature, token_limits, etc. ) --> Post Processing (validate cited chunks, format the output properly, add confidence scores based on results containing relevant sources, answer quality, user feedback, etc)

### Prompt Template Example

```markdown
SYSTEM:
You are an AI assistant for analyzing Standard Operating Procedures (SOPs).
You must ONLY use the provided excerpts.
If the answer is not present, say "Not found in SOP".

Always:
• Provide citations [DocID:Section]
• Highlight risks or gaps explicitly
• Be concise and factual

USER CONTEXT:
Record ID: {record_id}
User Role: {role}
Workflow Stage: {stage}
Use Case: {analysis_type}

USER QUESTION:
{question}

## RETRIEVED SOP EXCERPTS:

[Doc: {doc_id} | Section: {section}]
{chunk_text}

---

TASK:

1. Answer the question.
2. Suggest improvements (if applicable).
3. Provide citations.
4. Provide confidence level (High/Medium/Low).
5. Mention if information is missing.
```

### Retrieval Strategies

We can have different strategies for retrieval from vector db mostly mixing and matching based on the quality of the retrieved chunks.

- Metadata Filtering: We filter chunks based on our metadata and user context: tenant_id (for isolation), user_role, document_type, etc.
- Hybrid Search: Semantic Search using Vectors + Keyword BM25 Search - for both semantically similar results as well as matching certain important keywords/phrases required
- Merge, Dedup and Rerank: Combine the hybrid search results and dedup and rerank the chunks based on a score (maybe 50-50 for both vector and keyword search, maybe keyword has priority, etc.)

## Explainability, Audit & Compliance

- From the above workflows and data models, we can see that our system stores and logs data at each step from data ingestion to chunk, creating embeddings as well as enforcing citations in AI responses, storing prompts, queries, retrieved chunks, LLM and it's configurations used.
- These data allow us to replay the RAG workflow with the same configuration and inspect the AI decisions.
- The enforcement of retrieving chunks and citing the same helps is mitigating hallucinations to a minimum as the actual source which contains the ground truth is enforced in the prompt as well as the response from the LLM.
- We also have user-trust features including source citations, adding confidence level to each LLM response based on it's content and even enforcing the LLM to add a confidence level as well as disclaimers on it's own response and the source it used.

### Example of Auditable AI Response

```json
{
  "response_id": "resp_8f3a21",
  "tenant_id": "tenant_42",
  "user_id": "user_77",

  "query": {
    "record_id": "SOP-119",
    "workflow_stage": "Draft Review",
    "role": "Quality Manager",
    "question": "What risks are missing in this SOP?",
    "analysis_type": "risk_analysis"
  },

  "retrieval": {
    "retrieval_query": "Risks and missing controls in SOPs during Draft Review stage",
    "retrieved_chunks": [
      {
        "chunk_id": "chunk_881",
        "doc_id": "doc_vendor_onboarding_v3",
        "section": "Risk Assessment",
        "similarity_score": 0.82
      },
      {
        "chunk_id": "chunk_912",
        "doc_id": "doc_vendor_onboarding_v2",
        "section": "Compliance Checklist",
        "similarity_score": 0.78
      }
    ]
  },

  "model": {
    "name": "gpt-4.1",
    "temperature": 0.2,
    "max_tokens": 800
  },

  "prompt": "You are an AI assistant for analyzing SOPs...<full prompt stored>",

  "response": {
    "answer": "The SOP does not define a vendor risk classification step before approval.",
    "suggestions": [
      "Add vendor risk scoring based on financial and compliance history.",
      "Include escalation procedure for high-risk vendors."
    ],
    "citations": [
      {
        "doc_id": "doc_vendor_onboarding_v3",
        "section": "Risk Assessment",
        "chunk_id": "chunk_881"
      }
    ],
    "confidence": "Medium",
    "confidence_score": 0.67
  },

  "created_at": "2026-02-07T10:30:00Z"
}
```

## Performance and Scalability

According to the requirements, our system handles:

- ~1k AI queries/day
- Read-heavy workload

### Caching Strategies

- Query Result Cache: For each query, we hash query + user_id + tenant_id (or some other combination of metadata) and cache the final AI response

- Retrieval Cache: On the retrieval side, we can cache the query_embedding hash and cache the final retrieved chunks to be used in the AI response.

### Async vs Sync

Because we have some CPU-heavy processing - PDF ingestion, chunking, embedding creations, etc. we would lean towards async workers as they aren't also user facing (can be queued in the background till processing is done).

For the retrieval-side processing, we will use sync pipelines as they aren't a load on the CPU and are generally low in latency, plus user-facing so need to be resolved in the same request, ideally.

Although, the retrieval phase also can be moved to an async worker if the latency is high and then response is streamed (using Websockets or HttpStreaming) to the user.

### Cost Control

Use smaller embedding models during embedding phase and during query embedding generation.

For the RAQ query generation, use a mid-level model (general-purpose, e.g. gpt-4, etc.)

For the final response, we need a higher-end reasoning model (for source citation, context usage and to generate a confidence score, etc.)

Apart from this, caching, chunk compression, deduplication, etc. are small wins that can be easily implemented.

### Horizontal Scaling

| Component         | Scaling approach                                 |
| ----------------- | ------------------------------------------------ |
| API servers       | Horizontal autoscaling                           |
| Embedding workers | Scale worker count with queue                    |
| Vector DB         | Tenant-based sharding (already implemented)      |
| Database          | Read replicas, id-based or time-based partitions |
| Cahe              | Cluster mode                                     |

## Testing

1. Retrieval Relevance: Have a curated set of queries and expected chunks for them. And after each retrieval method change, check how many relevant chunks and how much noise is retrieved and compare the ranking quality.

2. Validating Prompt Changes: Again, for a set of queries, store expected answers and compare - citations, confidence scores, structure, hallucination, etc.

3. Regressions in AI Output: Keep track of amount of responses with citations, average confidence score, "Not found" issues, user feedback. Keep a running average and an alert at sudden changes in numbers.

4. Monitoring: Keep a track of the retrieval metrics (avg. similarity score, etc.), generation metrics (avg. tokens used, latency, cost per query, etc.) and confidence rates, user feedbacks, etc.

5. Additionally, we can also add human in the loop and regulary check the sample responses regularly by domain experts.
