import os
from dotenv import load_dotenv
from typing import List
from pydantic import BaseModel, Field

# LangChain and Hugging Face Hub Imports
from langchain_community.llms import HuggingFaceHub
from langchain_community.embeddings import HuggingFaceHubEmbeddings
from langchain_mongodb import MongoDBAtlasVectorSearch
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser, StrOutputParser
from langchain.chains import RetrievalQA

load_dotenv()

# --- Model Initialization ---
llm = HuggingFaceHub(
    repo_id="mistralai/Mixtral-8x7B-Instruct-v0.1",
    model_kwargs={"temperature": 0.5, "max_new_tokens": 1500}
)
embeddings = HuggingFaceHubEmbeddings(repo_id="sentence-transformers/all-MiniLM-L6-v2")

# --- Vector Store Connection ---
# This connects to your MongoDB collection where chunks and embeddings are stored.
# Ensure you have created a vector search index in your Atlas cluster.
vector_search = MongoDBAtlasVectorSearch.from_connection_string(
    os.environ["MONGODB_URI"],
    "college_management_db.study_material_chunks",
    embeddings,
    index_name="vector_index" # This must match the name of the index you create in Atlas.
)

# --- Pydantic Models for Structured Quiz Output ---

class MCQQuestion(BaseModel):
    question_text: str = Field(description="The text of the multiple-choice question.")
    options: List[str] = Field(description="A list of exactly 4 possible answers.")
    correct_answer_index: int = Field(description="The 0-based index of the correct answer in the options list.")

class ShortAnswerQuestion(BaseModel):
    question_text: str = Field(description="The text of the short-answer question.")
    ideal_answer: str = Field(description="A concise, ideal answer to the question.")

class LongAnswerQuestion(BaseModel):
    question_text: str = Field(description="The text of the long-answer question.")
    ideal_answer: str = Field(description="A detailed, ideal answer to the question.")

class Quiz(BaseModel):
    mcqs: List[MCQQuestion] = Field(description="A list of multiple-choice questions.")
    short_answers: List[ShortAnswerQuestion] = Field(description="A list of short-answer questions.")
    long_answers: List[LongAnswerQuestion] = Field(description="A list of long-answer questions.")

# --- AI Service Functions ---

def generate_structured_quiz_from_text(content: str, topic: str, num_mcq: int, num_short: int, num_long: int) -> Quiz:
    """Generates a structured quiz object with answers based on provided text content."""
    parser = PydanticOutputParser(pydantic_object=Quiz)
    prompt_template = """
    Based on the following content about "{topic}", please generate a quiz.
    The quiz must have exactly:
    - {num_mcq} Multiple Choice Questions.
    - {num_short} Short Answer Questions.
    - {num_long} Long Answer Questions.

    {format_instructions}

    Content:
    {context}
    """
    prompt = ChatPromptTemplate.from_template(
        template=prompt_template,
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )
    chain = prompt | llm | parser
    response = chain.invoke({
        "topic": topic,
        "num_mcq": num_mcq,
        "num_short": num_short,
        "num_long": num_long,
        "context": content
    })
    return response

def grade_submission(questions_with_correct_answers: list, student_answers: list) -> str:
    """Uses an LLM to grade a student's submission against the correct answers."""
    prompt_template = """
    You are an AI teaching assistant. Grade the student's submission based on the provided questions and their correct answers.
    For each question, evaluate the student's answer and assign a score out of 10.
    Finally, provide a total score and a brief overall feedback.
    
    Format the output STRICTLY as follows:
    Total Score: [Total Score] / [Maximum Possible Score]
    
    Overall Feedback: [Your brief feedback on the student's performance.]
    
    ---
    
    Here is the data:
    
    {submission_data}
    """
    submission_text = ""
    for i, qa in enumerate(questions_with_correct_answers):
        student_ans = next((sa['answer'] for sa in student_answers if sa['q_id'] == qa['q_id']), "Not Answered")
        submission_text += f"Question {i+1} ({qa['type']}): {qa['text']}\n"
        submission_text += f"Correct Answer: {qa['answer']}\n"
        submission_text += f"Student's Answer: {student_ans}\n\n"
    prompt = ChatPromptTemplate.from_template(prompt_template)
    chain = prompt | llm | StrOutputParser()
    response = chain.invoke({"submission_data": submission_text})
    return response

def answer_query_with_rag(query: str, material_id: str) -> str:
    """Performs RAG by querying an existing MongoDB Atlas Vector Store."""
    # Use the retriever to find relevant documents specifically for the given material
    retriever = vector_search.as_retriever(
        search_kwargs={'pre_filter': {'metadata.material_id': {'$eq': material_id}}}
    )
    # Create a standard question-answering chain
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever
    )
    result = qa_chain.invoke({"query": query})
    return result["result"]