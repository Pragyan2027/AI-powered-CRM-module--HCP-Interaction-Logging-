import os
import json
from typing import Annotated, TypedDict, List, Dict, Any, Literal
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

# LangChain & LangGraph Imports
from langchain_groq import ChatGroq
from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END, START
from langgraph.prebuilt import ToolNode
from langgraph.graph.message import add_messages
from dotenv import load_dotenv

# 0. Load Environment Variables
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
    # add_messages allows the history to append rather than overwrite
    messages: Annotated[list[BaseMessage], add_messages]
    interaction_data: InteractionData

# 2. Define the Tools (The 'Hands' of the AI)
@tool
def hcp_search(query: str):
    """Searches for Healthcare Professionals (HCPs) in the database."""
    # Mock database logic
    return json.dumps({"hcp_name": query, "status": "verified"})

@tool
def sentiment_analyzer(text: str):
    """Analyzes the sentiment of the HCP interaction text."""
    lower_text = text.lower()
    # Simple logic to detect negative sentiment for demo purposes
    neg_words = ["disaster", "frustrated", "shouting", "bad", "pricing", "delays", "upset"]
    if any(word in lower_text for word in neg_words):
        return json.dumps({"sentiment": "Negative"})
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

# 3. Initialize the Model
# Temperature 0.1 ensures the AI is predictable and follows tool schemas strictly
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.1,
    api_key=""
).bind_tools(tools)

# 4. Graph Logic Nodes
def call_model(state: AgentState):
    """Orchestrates the AI's thought process with a strict System Prompt."""
    sys_msg = SystemMessage(content=(
        "You are a professional CRM assistant for Life Sciences. "
        "When a user describes an interaction:\n"
        "1. Extract the HCP Name.\n"
        "2. Determine the Sentiment.\n"
        "3. Identify key Discussion Topics.\n"
        "4. Trigger follow-up tasks.\n\n"
        "CRITICAL: You MUST call 'log_interaction' and 'sentiment_analyzer' tools "
        "simultaneously to update the UI. Do not leave fields blank if they are mentioned."
    ))
    
    # We always put the SystemMessage at the start of the current context window
    messages = [sys_msg] + state["messages"]
    response = llm.invoke(messages)
    return {"messages": [response]}

def sync_state(state: AgentState):
    """
    The 'Glue' Node: Iterates through recent tool messages to ensure 
    multiple tool outputs (like Name + Sentiment) are all captured.
    """
    messages = state["messages"]
    current_data = state.get("interaction_data", {}).copy()
    
    # Iterate through the last 5 messages to catch parallel tool results
    for msg in reversed(messages[-5:]):
        if isinstance(msg, ToolMessage):
            try:
                tool_output = json.loads(msg.content)
                if isinstance(tool_output, dict):
                    # Patching existing data without overwriting unrelated fields
                    current_data.update(tool_output)
            except Exception:
                continue 
            
    return {"interaction_data": current_data}

def should_continue(state: AgentState) -> Literal["tools", END]:
    """Conditional logic to decide if tools need to be executed."""
    messages = state["messages"]
    last_message = messages[-1]
    if last_message.tool_calls:
        return "tools"
    return END

# 5. Build the StateGraph (The 'Brain' Structure)
workflow = StateGraph(AgentState)

workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)
workflow.add_node("sync", sync_state)

workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})

# After tools run, we sync the data to the structured dict, then back to agent for a response
workflow.add_edge("tools", "sync")
workflow.add_edge("sync", "agent")

app_graph = workflow.compile()

# 6. FastAPI Setup
app = FastAPI(title="HCP Interaction Module Backend")

# Middleware must be defined before the routes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    current_data: Dict[str, Any] = {}

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        # We start a fresh sequence for this specific interaction log
        inputs = {
            "messages": [HumanMessage(content=request.message)],
            "interaction_data": request.current_data
        }
        
        # Thread ID keeps the conversation separate from other users
        config = {"configurable": {"thread_id": "session_123"}}
        result = await app_graph.ainvoke(inputs, config)
        
        return {
            "response": result["messages"][-1].content,
            "updated_data": result.get("interaction_data", {})
        }
    except Exception as e:
        print(f"Server Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)