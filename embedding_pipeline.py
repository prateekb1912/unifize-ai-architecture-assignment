def add_document(customer_id: str, pdf_file: str):
    # Check if file already in s3 for the customer

    # using sha256 file hash

    # create new s3 link for pdf and upload to s3
    # create a job to extract text from the pdf

    pass

def update_document(customer_id, pdf_file):
    # Find the document id, update with new file hash and new file_path with an updated version
    # Re-run extraction job as before
    pass

def extract_text(document_id: str):
    # Get the file path from DB
    # Download the file from S3

    # Use PyMuPDF or other library to extract text from the PDF

    # Create a job to create chunks from the full PDF text

    pass

def create_chunks(pdf_text: str):
    # chunks = TextSplitter from Langchain or similar framework

    # for each chunk, create a chunk_id and a content_hash 
    # and publish to the queue for each chunk the task to create embeddings

    # for chunk in chunks:
    # queue.publish("create_embedding", {chunk_data: chunk})

    pass

def create_embedding(chunk: str):
    # for the chunk, check if embedding already present (using metadata)
    # and verify if the content_hash is the same or not
    # If different, create new embedding
    #  openai.embeddings.create(chunk, dimension = 1536)
    # Store in vectorDB
    # weaviate.add_document(tenant: customer_id, vector: embedding, metadtaa: chunk_metadata)

    pass

