from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from dotenv import load_dotenv
import os
from groq import Groq

from database import get_db, init_db, Thread, Message

# Load environment variables
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "llama-3.1-8b-instant")

# Initialize FastAPI app
app = FastAPI(title="AI Chat API")

# Add CORS middleware (allow all origins for local development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database on startup
@app.on_event("startup")
def startup_event():
    init_db()


# Pydantic models for request/response schemas
class ThreadCreate(BaseModel):
    title: Optional[str] = None


class ThreadResponse(BaseModel):
    id: int
    title: str
    created_at: datetime

    class Config:
        from_attributes = True


class MessageCreate(BaseModel):
    content: str


class MessageResponse(BaseModel):
    id: int
    thread_id: int
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class MessageReplyResponse(BaseModel):
    reply: str


# Endpoint 1: POST /threads - Create a new thread
@app.post("/threads", response_model=ThreadResponse, status_code=status.HTTP_201_CREATED)
def create_thread(thread_data: ThreadCreate, db: Session = Depends(get_db)):
    """
    Creates a new thread.
    Accepts optional "title" in request body; if not provided, defaults to "New Chat" + timestamp.
    Returns the created thread (id, title, created_at).
    """
    if thread_data.title is None:
        title = f"New Chat {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}"
    else:
        title = thread_data.title

    new_thread = Thread(title=title)
    db.add(new_thread)
    db.commit()
    db.refresh(new_thread)
    return new_thread


# Endpoint 2: GET /threads - List all threads
@app.get("/threads", response_model=List[ThreadResponse])
def list_threads(db: Session = Depends(get_db)):
    """
    Returns a list of all threads, ordered by created_at descending (newest first).
    """
    threads = db.query(Thread).order_by(Thread.created_at.desc()).all()
    return threads


# Endpoint 3: GET /threads/{thread_id}/messages - Get message history for a thread
@app.get("/threads/{thread_id}/messages", response_model=List[MessageResponse])
def get_thread_messages(thread_id: int, db: Session = Depends(get_db)):
    """
    Returns full message history for the specified thread, ordered by created_at ascending.
    Returns 404 if thread doesn't exist.
    """
    thread = db.query(Thread).filter(Thread.id == thread_id).first()
    if not thread:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")

    messages = db.query(Message).filter(Message.thread_id == thread_id).order_by(Message.created_at.asc()).all()
    return messages


# Endpoint 4: POST /threads/{thread_id}/messages - Send a message and get AI response
@app.post("/threads/{thread_id}/messages", response_model=MessageReplyResponse)
def create_message(thread_id: int, message_data: MessageCreate, db: Session = Depends(get_db)):
    """
    Accepts user message, saves it, and returns AI response using cross-thread memory logic.
    
    UNIVERSAL MEMORY LOGIC:
    1. Fetch the full message history of the CURRENT thread.
    2. Fetch the last 10 messages across ALL OTHER threads (ordered by created_at descending, 
       then reverse to chronological), excluding the current thread.
    3. Construct a system message with cross-thread context from other conversations.
    4. Send to Groq: [system message with cross-thread context] + [full current thread history] + [new user message]
    5. Save the assistant's response to the messages table.
    
    Returns 404 if thread doesn't exist.
    Returns 400 if content is empty.
    """
    # Validate thread exists
    thread = db.query(Thread).filter(Thread.id == thread_id).first()
    if not thread:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")

    # Validate content is not empty
    if not message_data.content or not message_data.content.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message content cannot be empty")

    # Save user message to database
    user_message = Message(thread_id=thread_id, role="user", content=message_data.content.strip())
    db.add(user_message)
    db.commit()
    db.refresh(user_message)

    # === CROSS-THREAD MEMORY LOGIC ===
    # Step 1: Fetch full message history of CURRENT thread
    current_thread_messages = db.query(Message).filter(Message.thread_id == thread_id).order_by(Message.created_at.asc()).all()

    # Step 2: Fetch last 10 messages across ALL OTHER threads (excluding current thread)
    # First get messages from other threads, ordered by created_at descending
    other_thread_messages = (
        db.query(Message)
        .filter(Message.thread_id != thread_id)
        .order_by(Message.created_at.desc())
        .limit(10)
        .all()
    )
    # Reverse to get chronological order
    other_thread_messages = list(reversed(other_thread_messages))

    # Step 3: Construct system message with cross-thread context
    # Format other-thread messages as "role: content" pairs
    context_str = "\n".join([f"{msg.role}: {msg.content}" for msg in other_thread_messages])
    
    if context_str:
        system_message_content = (
            "You are a helpful assistant. "
            "Here is relevant context from the user's other past conversations "
            "(for your memory/reference only — don't repeat it unless relevant):\n"
            f"{context_str}"
        )
    else:
        system_message_content = "You are a helpful assistant."

    # Step 4: Build message list for Groq API
    # Format: [system message with cross-thread context] + [full current thread history] + [new user message]
    messages_for_api = [{"role": "system", "content": system_message_content}]
    
    # Add current thread history (excluding the new user message we just saved, since it's already in current_thread_messages)
    for msg in current_thread_messages:
        messages_for_api.append({"role": msg.role, "content": msg.content})

    # Call Groq API
    try:
        client = Groq(api_key=GROQ_API_KEY)
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages_for_api,
            temperature=0.7,
        )
        assistant_reply = response.choices[0].message.content
    except Exception as e:
        # Return a friendly error message if Groq API call fails
        assistant_reply = f"I apologize, but I encountered an error while processing your request: {str(e)}"

    # Step 5: Save assistant's response to database
    assistant_message = Message(thread_id=thread_id, role="assistant", content=assistant_reply)
    db.add(assistant_message)
    db.commit()
    db.refresh(assistant_message)

    return MessageReplyResponse(reply=assistant_reply)
