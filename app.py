"""
Question-Answering API Service for Member Messages
Exposes /ask endpoint to answer natural language questions about member data
"""

import os
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from qa_engine import QAEngine

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Initialize QA engine
try:
    qa_engine = QAEngine()
    logger.info("QA Engine initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize QA Engine: {e}")
    qa_engine = None


@app.route('/', methods=['GET'])
def home():
    """Health check and API information"""
    return jsonify({
        "status": "running",
        "service": "Question-Answering API",
        "version": "1.0.0",
        "endpoints": {
            "/ask": "POST - Submit a question",
            "/health": "GET - Health check",
            "/stats": "GET - System statistics"
        }
    })


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    if qa_engine is None:
        return jsonify({"status": "unhealthy", "reason": "QA engine not initialized"}), 503
    
    return jsonify({
        "status": "healthy",
        "messages_loaded": qa_engine.get_message_count(),
        "users_loaded": qa_engine.get_user_count()
    })


@app.route('/stats', methods=['GET'])
def stats():
    """Return system statistics"""
    if qa_engine is None:
        return jsonify({"error": "QA engine not initialized"}), 503
    
    return jsonify(qa_engine.get_stats())


@app.route('/ask', methods=['POST'])
def ask():
    """
    Main endpoint for question answering
    
    Request body:
    {
        "question": "When is Layla planning her trip to London?"
    }
    
    Response:
    {
        "answer": "Based on Layla's messages, she is planning..."
    }
    """
    if qa_engine is None:
        return jsonify({"error": "QA engine not initialized"}), 503
    
    # Validate request
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400
    
    data = request.get_json()
    question = data.get('question', '').strip()
    
    if not question:
        return jsonify({"error": "Question is required and cannot be empty"}), 400
    
    if len(question) > 500:
        return jsonify({"error": "Question is too long (max 500 characters)"}), 400
    
    # Process question
    try:
        logger.info(f"Processing question: {question}")
        answer = qa_engine.answer_question(question)
        logger.info(f"Generated answer: {answer[:100]}...")
        
        return jsonify({"answer": answer})
    
    except Exception as e:
        logger.error(f"Error processing question: {e}", exc_info=True)
        return jsonify({
            "error": "An error occurred while processing your question",
            "details": str(e) if app.debug else None
        }), 500


@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Internal server error"}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Starting Flask app on port {port} (debug={debug})")
    app.run(host='0.0.0.0', port=port, debug=debug)

