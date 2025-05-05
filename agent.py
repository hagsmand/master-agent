import json
import requests
import sseclient
import os
import uuid
from dotenv import load_dotenv
from typing import Dict, List, Optional, Any, Union
from autogen import ConversableAgent, LLMConfig


load_dotenv()

class A2AClient:
    """Client for interacting with A2A protocol agents"""
    
    def __init__(self, agent_url: str):
        """Initialize A2A client with agent URL
        
        Args:
            agent_url: Base URL of the A2A agent
        """
        self.agent_url = agent_url.rstrip('/')
        self.session_id = str(uuid.uuid4())
        
    def discover_agent(self) -> Dict:
        """Discover agent capabilities by fetching agent card"""
        try:
            response = requests.get(f"{self.agent_url}/.well-known/agent.json")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error discovering agent: {e}")
            return {}
    
    def send_task(self, message: str) -> Dict:
        """Send a task to the agent
        
        Args:
            message: User message to send
            
        Returns:
            Task response from the agent
        """
        self.task_id = f"task-{os.urandom(8).hex()}"
        
        payload = {
            "jsonrpc": "2.0",
            "id": self.task_id,
            "method": "tasks/send",
            "params": {
                "id": self.task_id,
                "sessionId": self.session_id,
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": message}]
                },
                "acceptedOutputModes": ["text"]
            }
        }
        
        try:
            response = requests.post(
                f"{self.agent_url}/",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            print(response.json())
            response.raise_for_status()
            return response.json()['result']['status']['message']['parts'][0]['text']
        except Exception as e:
            print(f"Error sending task: {e}")
            return {}
    
    def send_task_subscribe(self, message: str) -> Dict:
        """Send a task and subscribe to updates
        
        Args:
            message: User message to send
            
        Returns:
            Generator that yields response chunks
        """
        self.task_id = f"task-{os.urandom(8).hex()}"
        
        # First send the task
        payload = {
            "jsonrpc": "2.0",
            "id": f"{self.task_id}-send",
            "method": "tasks/sendSubscribe",
            "params": {
                "id": self.task_id,
                "sessionId": self.session_id,
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": message}]
                },
                "acceptedOutputModes": ["text"]
            }
        }
        
        try:
            response = requests.post(
                f"{self.agent_url}/",
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "text/event-stream"
                },
                stream=True
            )
            response.raise_for_status()
            
            return sseclient.SSEClient(response)
        except Exception as e:
            print(f"Error sending task with subscription: {e}")
            return None

class DispatcherAgent:
    """Dispatcher agent that routes queries to appropriate specialized agents"""
    
    def __init__(self, llm_config: Optional[LLMConfig] = None):
        """Initialize the dispatcher agent
        
        Args:
            llm_config: LLM configuration for the agent
        """
        self.sql_agent = A2AClient(os.environ.get("SQL_AGENT_URL"))
        self.rag_agent = A2AClient(os.environ.get("RAG_AGENT_URL"))
        
        # Create AG2 agent for decision making
        self.agent = ConversableAgent(
            name="dispatcher",
            system_message="""
            You are a dispatcher agent that decides which specialized agent should handle a user query.
            For database queries (sales and customer data), SQL generation, or data analysis tasks, route to the SQL writer agent.
            For information retrieval (Pinecone DB documentation), document-based queries about Pinecone, route to the RAG agent.
            If nothing related to Pinecone DB or sales and customer data is mentioned, do not route and mention to anyone and finish the task by yourself. 
            If you answer by yourself, do not mention to anyone in your answer.
            """,
            llm_config=llm_config
        )
    
    def decide_agent(self, query: str) -> str:
        """Decide which agent should handle the query
        
        Args:
            query: User query
            
        Returns:
            Agent type: 'sql', 'nothing', or 'rag'
        """
        # Use the AG2 agent to make a decision
        response = self.agent.generate_reply(
            messages=[{"role": "user", "content": f"Decide if this query should be handled by the SQL writer agent or the RAG agent: {query}. You must answer only one word either 'sql', 'nothing', or 'rag' only."}]
        )
        
        if response['content'] and isinstance(response['content'], str):
            return response['content']
        
        return "nothing"
        
    def process_query_stream(self, query: str, agent_type: str) -> Union[sseclient.SSEClient, Dict, str]:
        """Process a user query and stream the response
        
        Args:
            query: User query
            
        Returns:
            SSE client for streaming updates, response dict, or string response
        """
        try:
            if agent_type == "sql":
                print("Routing to SQL writer agent (streaming)")
                stream_client = self.sql_agent.send_task_subscribe(query)
                if stream_client is None:
                    print("Streaming not available, falling back to regular request")
                    return self.sql_agent.send_task(query)
                return stream_client
            elif agent_type == "rag":
                print("Routing to RAG agent (streaming)")
                stream_client = self.rag_agent.send_task_subscribe(query)
                if stream_client is None:
                    print("Streaming not available, falling back to regular request")
                    return self.rag_agent.send_task(query)
                return stream_client
            else:
                print("Handling query directly")
                # Generate response using the dispatcher's own LLM
                response = self.agent.generate_reply(
                    messages=[{"role": "user", "content": query}]
                )
                return response['content'] if response['content'] else "I couldn't process your query."
        except Exception as e:
            print(f"Error in streaming, falling back to regular request: {e}")
            if agent_type == "sql":
                return self.sql_agent.send_task(query)
            elif agent_type == "rag":
                return self.rag_agent.send_task(query)
            else:
                # Handle directly in case of error
                response = self.agent.generate_reply(
                    messages=[{"role": "user", "content": query}]
                )
                return response['content'] if response['content'] else "I couldn't process your query."

                