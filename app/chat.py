from flask import Blueprint, request, jsonify
from langchain.prompts import PromptTemplate
from langchain.schema import SystemMessage, HumanMessage
from langchain_mistralai import ChatMistralAI
from langchain.vectorstores import Chroma
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel
from typing import List
import os
import json

# Initialize Flask Blueprint
chatbot_bp = Blueprint("chatbot", __name__)
# Initialize embedding function
embedding_function = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# Absolute path to ChromaDB
persist_directory = os.path.join(os.path.dirname(__file__), "chromadb")

# Initialize ChromaDB retriever
vectorstore = Chroma(persist_directory=persist_directory, embedding_function=embedding_function)
retriever = vectorstore.as_retriever()

# Initialize LLM
llm = ChatMistralAI(
    model="mistral-large-latest",
    temperature=0.3,
)

# Chat history storage (Temporary in-memory, can be extended with Redis or DB)
chat_history = {}

# Define system message for PramanAI
system_message = SystemMessage(
    content=(
        "You are PramanAI, an expert in legal document analysis. You extract metadata, legal provisions, "
        "and format-specific information from uploaded legal documents. Your responses should be well-structured, "
        "detailed, and formatted in Markdown with headings, bullet points, and numbered lists."
    )
)

# Define prompt template for chatbot queries
prompt_template = PromptTemplate(
    input_variables=["chat_history", "retrieved_documents", "user_query"],
    template=(
        "Chat History:\n{chat_history}\n\n"
        "You have access to the following retrieved legal information:\n\n"
        "{retrieved_documents}\n\n"
        "The user asked:\n\n"
        "{user_query}\n\n"
        "Provide a structured legal response with citations where needed, using Markdown for clarity."
    )
)

# Define prompt template for document generation
document_prompt_template = PromptTemplate(
    input_variables=["ocr_text", "ner_data", "format_instructions"],
    template=(
        "Extract structured legal information from the given OCR-extracted text and Named Entity Recognition (NER) data. "
        "Return the response as a **strictly formatted JSON** object with the following keys:\n\n"
        "- case_number\n"
        "- petitioners\n"
        "- respondents\n"
        "- judgment_date\n"
        "- judges\n"
        "- address\n"
        "- court\n"
        "- subject_categories\n"
        "- act_sections (List of legal acts and sections cited)\n"
        "- case_summary (Brief summary of the case)\n\n"
        "{format_instructions}\n\n"
        "### OCR Extracted Text:\n{ocr_text}\n\n"
        "### NER Extracted Data:\n{ner_data}\n\n"
        "Ensure that your response is **pure JSON** without any additional text."
    )
)

# Define Pydantic model for validation
class LegalDocument(BaseModel):
    case_number: str
    petitioners: List[str]
    respondents: List[str]
    judgment_date: str
    judges: List[str]
    address: str
    court: str
    subject_categories: List[str]
    act_sections: List[str]
    case_summary: str

# Initialize PydanticOutputParser
parser = PydanticOutputParser(pydantic_object=LegalDocument)

@chatbot_bp.route("/chatbot", methods=["POST"])
def chatbot_query():
    data = request.json
    query = data.get("query")
    user_id = data.get("user_id", "default_user")  # Use a session ID or user-specific identifier

    if not query:
        return jsonify({"error": "Query is required"}), 400

    try:
        # Retrieve relevant documents
        retrieved_docs = retriever.invoke(query)
        retrieved_text = "\n".join([doc.page_content for doc in retrieved_docs])

        # Fetch previous chat history
        history = chat_history.get(user_id, [])
        formatted_history = "\n".join([f"User: {msg['user']}\nPramanAI: {msg['bot']}" for msg in history])

        # Construct prompt
        prompt = prompt_template.format(
            chat_history=formatted_history,
            retrieved_documents=retrieved_text,
            user_query=query
        )

        # Generate response using LLM
        messages = [system_message, HumanMessage(content=prompt)]
        response = llm.invoke(messages)

        # Update chat history
        history.append({"user": query, "bot": response.content})
        chat_history[user_id] = history[-5:]  # Keep only the last 5 messages

        return jsonify({"response": response.content})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@chatbot_bp.route("/generate-document", methods=["POST"])
def generate_document():
    data = request.json
    ocr_text = data.get("ocr_text", "")
    ner_data = data.get("ner_data", {})

    if not ocr_text:
        return jsonify({"error": "OCR text is required"}), 400
    if not ner_data:
        return jsonify({"error": "NER data is required"}), 400

    try:
        # Construct prompt for document generation
        prompt = document_prompt_template.format(
            ocr_text=ocr_text,
            ner_data=ner_data,
            format_instructions=parser.get_format_instructions()
        )

        # Generate JSON response using LLM
        messages = [SystemMessage(content="Extract structured legal information as JSON."), HumanMessage(content=prompt)]
        response = llm.invoke(messages)

        # Parse and validate the output JSON
        json_response = parser.parse(response.content)

        return jsonify(json_response.dict())

    except Exception as e:
        return jsonify({"error": str(e)}), 500