# app/main.py

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any # Import List, Dict, Any for typing

# Import the analytics functions we created
from . import analytics

# --- ADD THIS IMPORT ---
# Import the rag_qa module to access its functions
from . import rag_qa
# --- END OF ADDITION ---

# Create the FastAPI app instance
app = FastAPI(
    title="Hotel Booking Analytics API",
    description="API to provide analytics and Q&A for hotel booking data.",
    version="0.1.0"
)

# --- Define Request/Response Models ---
class Question(BaseModel):
    query: str

# --- ADD THIS RESPONSE MODEL for /ask ---
class Answer(BaseModel):
     query: str
     answer: str
     # Include retrieved_context, make it optional if it might be empty
     retrieved_context: List[str] | None = None
# --- END OF ADDITION ---

class AnalyticsReport(BaseModel):
    # Use precise types if possible, otherwise Any or Dict
    revenue_trends: List[Dict[str, Any]] | None = None
    cancellation_rate: Dict[str, Any] | None = None
    geo_distribution: List[Dict[str, Any]] | None = None
    lead_time_stats: Dict[str, Any] | None = None

# --- API Endpoints ---

# Analytics Endpoint (as per assignment spec: POST)
@app.post("/analytics", response_model=AnalyticsReport)
async def get_analytics_report():
    """
    Provides key analytics reports based on the hotel booking data stored in MySQL.
    """
    print("Received request for /analytics")
    try:
        # Convert DataFrames to list of dicts for JSON serialization
        revenue_df = analytics.get_revenue_trends()
        revenue = revenue_df.to_dict(orient='records') if revenue_df is not None and not revenue_df.empty else []

        rate = analytics.get_cancellation_rate() # This returns a dict

        geo_df = analytics.get_geo_distribution()
        geo = geo_df.to_dict(orient='records') if geo_df is not None and not geo_df.empty else []

        lead_time = analytics.get_lead_time_distribution() # This returns a dict

        # Simplified check: just assign what we got
        report = AnalyticsReport(
            revenue_trends=revenue,
            cancellation_rate=rate if rate else {},
            geo_distribution=geo,
            lead_time_stats=lead_time if lead_time else {}
        )
        print("Successfully generated analytics report.")
        return report

    except Exception as e:
        print(f"❌ Error generating analytics report: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


# --- MODIFY THIS ENDPOINT ---
@app.post("/ask", response_model=Answer) # Use the new response model
async def ask_question_endpoint(question: Question): # Renamed function for clarity
    """
    Answers booking-related questions using the RAG system.
    """
    print(f"Received question for /ask: {question.query}")

    # Check if RAG resources loaded properly (accessing variables from rag_qa)
    if rag_qa.index is None or rag_qa.embedding_model is None or not rag_qa.all_formatted_texts:
         # Log the specific issue if possible
         print("❌ RAG system resources are not available. Check rag_qa.py loading.")
         raise HTTPException(status_code=503, detail="RAG system resources are not available.")

    try:
        # Call the answer_question function from rag_qa module
        result = rag_qa.answer_question(question.query) # This should return a dict

        # Check if the answer indicates an error occurred within rag_qa
        # (e.g., Ollama connection error handled inside answer_question)
        if "Sorry," in result.get("answer", ""):
             # Log the specific error if available in result
             print(f"⚠️ RAG system returned an error message: {result.get('answer')}")
             # Return a 500 error to the client indicating internal failure
             raise HTTPException(status_code=500, detail=result.get("answer", "Failed to get answer from RAG system."))

        # Ensure the result dictionary matches the Answer model structure
        # The rag_qa.answer_question should return keys: "query", "answer", "retrieved_context"
        return Answer(**result)

    except Exception as e:
         # Catch any unexpected errors during the RAG process
         print(f"❌ Unexpected error processing /ask request: {e}")
         raise HTTPException(status_code=500, detail=f"Internal server error during RAG processing: {e}")

# --- END OF MODIFICATION ---


# Health Check Endpoint (Bonus)
@app.get("/health")
async def health_check():
    """
    Checks the status of the system, primarily the database connection.
    """
    print("Received request for /health")
    db_status = analytics.check_db_connection()
    if db_status.get("status") == "ok":
        return {"status": "ok", "database_connection": db_status}
    else:
        raise HTTPException(status_code=503, detail={"status": "error", "database_connection": db_status})

# Root endpoint (optional, good for testing if the server is running)
@app.get("/")
async def read_root():
    return {"message": "Welcome to the Hotel Booking Analytics API!"}

# --- How to Run (Instructions for terminal) ---
# Make sure you are in the root directory (solvei8_booking_analytics_project)
# Ensure your virtual environment is activated.
# Run: uvicorn app.main:app --reload
#
# The API will be available at http://127.0.0.1:8000
# You can access the interactive documentation at http://127.0.0.1:8000/docs