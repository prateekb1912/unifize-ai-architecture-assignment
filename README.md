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
