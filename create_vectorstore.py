import os
from langchain_community.document_loaders import PyPDFLoader
from langchain.embeddings import HuggingFaceEmbeddings  # Use HuggingFace embeddings or another embedding model
from langchain.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Path to your folder containing PDF documents
pdf_folder_path = "./docs"

# Function to load documents from PDF files
def load_documents_from_pdfs(pdf_path):
    documents = []
    for filename in os.listdir(pdf_path):
        if filename.endswith(".pdf"):
            file_path = os.path.join(pdf_path, filename)
            loader = PyPDFLoader(file_path)
            documents.extend(loader.load())
    return documents

# Load documents from the folder
documents = load_documents_from_pdfs(pdf_folder_path)

# Use RecursiveCharacterTextSplitter to split documents into chunks with overlap
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,  # Maximum size of each chunk
    chunk_overlap=150,  # Overlap between chunks
)
split_documents = text_splitter.split_documents(documents)

# Initialize the embedding function for Chroma
embedding_function = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# Define the collection name for Chroma
collection_name = "my_collection"
# Define the path where the vector store should be persisted
persist_directory = "./app/chroma_db"

# Create the vector store using Chroma and specify the persist directory
vectorstore = Chroma.from_documents(
    documents=split_documents,  # The split documents
    embedding=embedding_function,  # The embedding function
    collection_name=collection_name,  # Name of the collection
    persist_directory=persist_directory  # Path to store the vector store
)

# Persist the vector store to the specified directory
vectorstore.persist()

# Set up the retriever
retriever = vectorstore.as_retriever()

# Print confirmation message
print(f"Vector store created and persisted to '{persist_directory}'")
