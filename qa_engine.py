"""
Core Question-Answering Engine
Implements RAG (Retrieval-Augmented Generation) with multiple LLM backends
"""

import os
import logging
from typing import List, Dict, Optional, Tuple
from collections import defaultdict
import requests
from rapidfuzz import fuzz

logger = logging.getLogger(__name__)


class QAEngine:
    """
    Question-Answering Engine using Retrieval-Augmented Generation
    """
    
    def __init__(self):
        """Initialize the QA engine and load data"""
        self.api_url = os.environ.get(
            'API_BASE_URL', 
            'https://november7-730026606190.europe-west1.run.app/messages/'
        )
        
        # Storage
        self.messages = []
        self.user_messages = defaultdict(list)  # user_name -> [messages]
        
        # LLM configuration
        self.llm_provider = self._detect_llm_provider()
        self._initialize_llm()
        
        # Load data
        self._fetch_messages()
        logger.info(f"Loaded {len(self.messages)} messages from {len(self.user_messages)} users")
    
    def _detect_llm_provider(self) -> str:
        """Detect which LLM provider to use based on environment variables"""
        if os.environ.get('OPENAI_API_KEY'):
            return 'openai'
        elif os.environ.get('ANTHROPIC_API_KEY'):
            return 'anthropic'
        else:
            logger.warning("No LLM API key found, using fallback mode")
            return 'fallback'
    
    def _initialize_llm(self):
        """Initialize the LLM client"""
        if self.llm_provider == 'openai':
            try:
                from openai import OpenAI
                self.llm_client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
                self.llm_model = os.environ.get('OPENAI_MODEL', 'gpt-4-turbo-preview')
                logger.info(f"Using OpenAI with model {self.llm_model}")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI: {e}")
                self.llm_provider = 'fallback'
        
        elif self.llm_provider == 'anthropic':
            try:
                from anthropic import Anthropic
                self.llm_client = Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))
                self.llm_model = os.environ.get('ANTHROPIC_MODEL', 'claude-3-sonnet-20240229')
                logger.info(f"Using Anthropic with model {self.llm_model}")
            except Exception as e:
                logger.error(f"Failed to initialize Anthropic: {e}")
                self.llm_provider = 'fallback'
        
        else:
            logger.info("Using fallback mode (keyword-based matching)")
    
    def _fetch_messages(self):
        """Fetch all messages from the API"""
        skip = 0
        limit = 100
        max_retries = 3
        
        while True:
            retry_count = 0
            while retry_count < max_retries:
                try:
                    response = requests.get(
                        self.api_url,
                        params={'skip': skip, 'limit': limit},
                        timeout=10
                    )
                    
                    if response.status_code != 200:
                        logger.warning(f"API returned status {response.status_code}")
                        break
                    
                    data = response.json()
                    
                    # Check for error or no items
                    if 'items' not in data or len(data['items']) == 0:
                        logger.info(f"No more data at skip={skip}")
                        return
                    
                    # Process messages
                    for msg in data['items']:
                        self.messages.append(msg)
                        self.user_messages[msg['user_name']].append(msg)
                    
                    logger.info(f"Fetched {len(data['items'])} messages (total: {len(self.messages)})")
                    
                    # Check if we got all messages
                    if len(self.messages) >= data.get('total', float('inf')):
                        return
                    
                    skip += limit
                    break  # Success, exit retry loop
                
                except requests.exceptions.RequestException as e:
                    retry_count += 1
                    logger.warning(f"API request failed (attempt {retry_count}/{max_retries}): {e}")
                    if retry_count >= max_retries:
                        logger.error("Max retries reached, stopping data fetch")
                        return
            
            # If we exited retry loop due to error, stop fetching
            if retry_count >= max_retries:
                return
    
    def _fuzzy_match_user(self, query: str) -> Optional[str]:
        """
        Find user name using fuzzy matching
        Returns exact match or best fuzzy match above threshold
        """
        query_lower = query.lower()
        
        # First try exact match
        for user in self.user_messages.keys():
            if user.lower() in query_lower or query_lower in user.lower():
                return user
        
        # Try fuzzy matching on first names
        best_match = None
        best_score = 0
        threshold = 75  # Minimum similarity score (0-100)
        
        for user in self.user_messages.keys():
            # Extract first name
            first_name = user.split()[0].lower()
            
            # Check similarity with query tokens
            for query_token in query_lower.split():
                score = fuzz.ratio(first_name, query_token)
                if score > best_score:
                    best_score = score
                    best_match = user
        
        if best_score >= threshold:
            logger.info(f"Fuzzy matched '{query}' to user '{best_match}' (score: {best_score})")
            return best_match
        
        return None
    
    def _retrieve_context(self, question: str) -> Tuple[str, List[Dict]]:
        """
        Retrieve relevant messages as context for the question
        Returns (context_text, source_messages)
        """
        # Try to extract user name from question
        user_name = self._fuzzy_match_user(question)
        
        if user_name and user_name in self.user_messages:
            # Get all messages from this user
            relevant_messages = self.user_messages[user_name]
            logger.info(f"Retrieved {len(relevant_messages)} messages for user '{user_name}'")
        else:
            # No specific user found, use all messages (or implement keyword filtering)
            logger.info("No specific user identified, using keyword-based retrieval")
            relevant_messages = self._keyword_retrieval(question)
        
        # Build context string
        context_parts = []
        for msg in relevant_messages:
            context_parts.append(
                f"[{msg['timestamp'][:10]}] {msg['user_name']}: {msg['message']}"
            )
        
        context_text = "\n".join(context_parts)
        return context_text, relevant_messages
    
    def _keyword_retrieval(self, question: str, top_k: int = 20) -> List[Dict]:
        """
        Retrieve messages using keyword overlap
        Returns top_k most relevant messages
        """
        question_words = set(question.lower().split())
        
        # Score each message
        scored_messages = []
        for msg in self.messages:
            msg_words = set(msg['message'].lower().split())
            overlap = len(question_words & msg_words)
            if overlap > 0:
                scored_messages.append((overlap, msg))
        
        # Sort by score and return top_k
        scored_messages.sort(reverse=True, key=lambda x: x[0])
        return [msg for score, msg in scored_messages[:top_k]]
    
    def _generate_answer_with_llm(self, question: str, context: str) -> str:
        """Generate answer using LLM"""
        prompt = self._build_prompt(question, context)
        
        try:
            if self.llm_provider == 'openai':
                return self._generate_openai(prompt)
            elif self.llm_provider == 'anthropic':
                return self._generate_anthropic(prompt)
            else:
                return self._generate_fallback(question, context)
        
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return "I apologize, but I encountered an error while processing your question. Please try again."
    
    def _build_prompt(self, question: str, context: str) -> str:
        """Build prompt for LLM"""
        return f"""You are a helpful assistant answering questions about member messages from a concierge service.

Context (member messages):
{context}

Question: {question}

Instructions:
- Answer based ONLY on the provided context above
- If the answer is not clearly stated in the context, say "I don't have enough information to answer that question."
- Be concise and specific
- For temporal questions (when/what date), look for dates, days of the week, or relative time expressions
- For quantitative questions (how many), count carefully or state if the information is not available
- For preference questions (favorite/preferred), infer from positive mentions or explicit statements
- Include relevant details from the messages to support your answer
- Do not make up information that is not in the context

Answer:"""
    
    def _generate_openai(self, prompt: str) -> str:
        """Generate answer using OpenAI"""
        response = self.llm_client.chat.completions.create(
            model=self.llm_model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that answers questions based on provided context."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=500
        )
        return response.choices[0].message.content.strip()
    
    def _generate_anthropic(self, prompt: str) -> str:
        """Generate answer using Anthropic Claude"""
        response = self.llm_client.messages.create(
            model=self.llm_model,
            max_tokens=500,
            temperature=0.3,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return response.content[0].text.strip()
    
    def _generate_fallback(self, question: str, context: str) -> str:
        """
        Fallback answer generation using keyword matching
        This is a simple heuristic-based approach when no LLM is available
        """
        # Extract user name if possible
        user_name = self._fuzzy_match_user(question)
        
        if not user_name:
            return "I apologize, but I need an LLM API key to answer complex questions. Please configure OPENAI_API_KEY or ANTHROPIC_API_KEY."
        
        # Simple keyword-based response
        question_lower = question.lower()
        
        # Get messages for this user
        messages = self.user_messages.get(user_name, [])
        
        if not messages:
            return f"I don't have any messages from {user_name}."
        
        # Try to find relevant messages based on keywords
        if 'trip' in question_lower or 'travel' in question_lower or 'when' in question_lower:
            relevant = [m for m in messages if 'trip' in m['message'].lower() or 'travel' in m['message'].lower()]
            if relevant:
                return f"Based on {user_name}'s messages: " + "; ".join([m['message'] for m in relevant[:3]])
        
        elif 'car' in question_lower or 'how many' in question_lower:
            relevant = [m for m in messages if 'car' in m['message'].lower()]
            if relevant:
                return f"Found {len(relevant)} message(s) from {user_name} mentioning cars. However, I need an LLM to provide a detailed answer."
            else:
                return f"I don't have enough information to answer that question about {user_name}."
        
        elif 'restaurant' in question_lower or 'favorite' in question_lower:
            relevant = [m for m in messages if 'restaurant' in m['message'].lower()]
            if relevant:
                return f"Based on {user_name}'s messages: " + "; ".join([m['message'] for m in relevant[:3]])
        
        return f"I found {len(messages)} message(s) from {user_name}, but I need an LLM API key to provide a detailed answer. Please configure OPENAI_API_KEY or ANTHROPIC_API_KEY."
    
    def answer_question(self, question: str) -> str:
        """
        Main method to answer a question
        """
        # Retrieve relevant context
        context, source_messages = self._retrieve_context(question)
        
        if not context:
            return "I couldn't find any relevant information to answer your question."
        
        # Generate answer using LLM
        answer = self._generate_answer_with_llm(question, context)
        
        return answer
    
    def get_message_count(self) -> int:
        """Return total number of messages loaded"""
        return len(self.messages)
    
    def get_user_count(self) -> int:
        """Return number of unique users"""
        return len(self.user_messages)
    
    def get_stats(self) -> Dict:
        """Return system statistics"""
        return {
            "total_messages": len(self.messages),
            "total_users": len(self.user_messages),
            "users": list(self.user_messages.keys()),
            "messages_per_user": {
                user: len(msgs) for user, msgs in self.user_messages.items()
            },
            "llm_provider": self.llm_provider,
            "llm_model": getattr(self, 'llm_model', None)
        }

