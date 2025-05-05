import streamlit as st
import os
import json
from dotenv import load_dotenv
from agent import DispatcherAgent
from autogen import LLMConfig

# Load environment variables
load_dotenv()

# Initialize the dispatcher agent
def initialize_agent():
    """Initialize the dispatcher agent with LLM config"""
    llm_config = LLMConfig(
        api_type="groq",
        api_key=os.environ.get("GROQ_API_KEY"),
        model="meta-llama/llama-4-scout-17b-16e-instruct",  
    )
    
    return DispatcherAgent(llm_config=llm_config)

# Streamlit UI
st.set_page_config(page_title="A2A Dispatcher Agent", layout="wide")

# Initialize session state for chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

if "agent" not in st.session_state:
    st.session_state.agent = initialize_agent()

# App header
st.title("A2A Dispatcher Agent")
st.markdown(
    """This agent uses the A2A protocol to connect with specialized agents:
    - **SQL Writer Agent** (localhost:10002): For database queries and data analysis (sales and customer data)
    - **RAG Agent** (localhost:10001): For information retrieval and question answering about Pinecone DB or general question
    """
)

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# Chat input
if prompt := st.chat_input("What would you like to ask?"):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.write(prompt)
    
    # Get agent response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            # Determine which agent to use
            agent_type = st.session_state.agent.decide_agent(prompt)
            st.write(f"Routing to {agent_type.upper()} agent...")
            
            # Process query with streaming
            client = st.session_state.agent.process_query_stream(prompt, agent_type)
            full_response = ""
            message_placeholder = st.empty()  # Initialize the placeholder here

            final_response = {"status": "incomplete", "content": ""}
            if isinstance(client, str):
                message_placeholder.write(client)
                # stop here
                final_response["status"] = "complete"
                final_response["content"] = client
            else:
                for event in client.events():
                    if not event.data:
                        continue
                        
                    data = json.loads(event.data)
                    if "result" in data:
                        result = data["result"]
                        
                        # Handle task status update
                        if "status" in result:
                            status = result["status"]
                            if "message" in status and status["message"]:
                                message_parts = status["message"]["parts"]
                                for part in message_parts:
                                    if part["type"] == "text":
                                        final_response["content"] = part["text"]
                                        message_placeholder.write(final_response["content"])
                        
                        # Check if this is the final message
                        if "final" in result and result["final"]:
                            final_response["status"] = "complete"
                            break
                    
                    # Handle errors
                    if "error" in data:
                        final_response["status"] = "error"
                        final_response["error"] = data["error"]
                        break
    
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": final_response["content"]})

# Main function
def main():
    # The Streamlit app is defined above
    pass

if __name__ == "__main__":
    main()
