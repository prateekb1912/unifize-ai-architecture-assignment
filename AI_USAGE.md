## Tools Used

- Claude: To discuss about the data modelling and sync strategies, as well as generating ER diagrams from a rough schema for the tables and an openapi spec file from an overview of the required APIs structure.

## Accepted Examples:

```
Given the following data models schemas, create a simplified ER diagram using Mermaid.

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

```

Purpose: To generate an initial ER diagram suited to the schemas for the models in use.

```
Provide an OpenAPI specification for ingestion, querying, and audit  retrieval APIs.
```

Purpose: To speed up documentation and ensure consistent API structure.

## Rejected Examples

```
AI initially suggested always creating new chunks and re-embedding even when new chunks are same as older ones.
```

This decision was rejected because we will be re-embedding a lot of chunks if minimal changes are made to the document, then I went ahead with having a content hash for each chunk and keeping those in-place when new chunks are being added.
