import os
import json
from typing import Annotated, TypedDict, List, Dict, Any, Literal
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
# LangChain & LangGraph Imports
from langchain_groq import ChatGroq
from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END, START
from langgraph.prebuilt import ToolNode
from langgraph.graph.message import add_messages
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GROQ_API_KEY")
# 1. Define the Agent State
class InteractionData(TypedDict):
    hcp_name: str
    interaction_type: str
    sentiment: str
    topics: List[str]
    follow_ups: List[str]

class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    interaction_data: InteractionData

# 2. Define the Tools
@tool
def hcp_search(query: str):
    """Searches for Healthcare Professionals (HCPs) in the database."""
    return json.dumps({"hcp_name": query, "status": "verified"})

@tool
def sentiment_analyzer(text: str):
    """Analyzes the sentiment of the HCP interaction text."""
    # Logic to determine mood
    return json.dumps({"sentiment": "Positive"})

@tool
def log_interaction(hcp_name: str, topics: list, sentiment: str, interaction_type: str = "Meeting"):
    """Saves interaction details and returns them for the UI state."""
    structured_data = {
        "hcp_name": hcp_name,
        "topics": topics,
        "sentiment": sentiment,
        "interaction_type": interaction_type
    }
    return json.dumps(structured_data)

@tool
def edit_interaction(interaction_id: str, updates: Dict[str, Any]):
    """Modifies an existing logged interaction."""
    return json.dumps(updates)

@tool
def follow_up_generator(summary: str):
    """Generates suggested follow-up tasks based on the interaction summary."""
    tasks = ["Schedule follow-up meeting in 2 weeks", "Send Product X clinical data"]
    return json.dumps({"follow_ups": tasks})

tools = [hcp_search, sentiment_analyzer, log_interaction, edit_interaction, follow_up_generator]
tool_node = ToolNode(tools)

# 3. Initialize the Model (Llama 3.3 for tool-calling stability)
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.1,
    api_key="YOUR_API_KEY"
).bind_tools(tools)

# 4. Graph Logic Nodes
def call_model(state: AgentState):
    response = llm.invoke(state["messages"])
    return {"messages": [response]}

def sync_state(state: AgentState):
    """Parses tool outputs and syncs them to the interaction_data dictionary."""
    messages = state["messages"]
    current_data = state.get("interaction_data", {})
    
    # Check if the last message is a ToolMessage (result from a tool)
    if isinstance(messages[-1], ToolMessage):
        try:
            # Parse the tool's JSON output
            tool_output = json.loads(messages[-1].content)
            if isinstance(tool_output, dict):
                # Update our structured data dictionary
                current_data.update(tool_output)
        except Exception:
            pass # Not JSON or error, skip update
            
    return {"interaction_data": current_data}

def should_continue(state: AgentState) -> Literal["tools", END]:
    messages = state["messages"]
    last_message = messages[-1]
    if last_message.tool_calls:
        return "tools"
    return END

# 5. Build the StateGraph
workflow = StateGraph(AgentState)

workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)
workflow.add_node("sync", sync_state) # <--- The Sync Node

workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})

# After tools run, we go to sync, then back to agent for a response
workflow.add_edge("tools", "sync")
workflow.add_edge("sync", "agent")

app_graph = workflow.compile()

# 6. FastAPI Setup
app = FastAPI(title="AI-First CRM Backend")

class ChatRequest(BaseModel):
    message: str
    current_data: Dict[str, Any] = {}

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        inputs = {
            "messages": [HumanMessage(content=request.message)],
            "interaction_data": request.current_data
        }
        # In a real app, thread_id would be unique per user session
        config = {"configurable": {"thread_id": "session_123"}}
        
        result = await app_graph.ainvoke(inputs, config)
        
        return {
            "response": result["messages"][-1].content,
            "updated_data": result.get("interaction_data", {})
        }
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
    
    from fastapi.middleware.cors import CORSMiddleware


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"], # Your Vite port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

system_prompt = """
You are a CRM assistant. Every time a user describes a meeting:
1. Extract the HCP Name (e.g., 'Dr. Das').
2. Extract the Sentiment.
3. Summarize the Topics.
4. Generate Follow-ups.

CRITICAL: You MUST call the 'log_interaction' tool with ALL these fields. 
Do not leave hcp_name or topics blank if they are mentioned in the chat.
"""