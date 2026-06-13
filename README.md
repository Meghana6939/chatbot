# AI Chat Application

A mini AI chat application with cross-thread memory capabilities, built with FastAPI, Streamlit, SQLite, and the Groq API.

## Features

- **Multi-thread conversations**: Create and manage multiple chat threads
- **Cross-thread memory**: The AI remembers context from your past conversations across different threads
- **Modern UI**: Clean Streamlit interface with chat message display
- **SQLite database**: Persistent storage for threads and messages
- **FastAPI backend**: RESTful API with proper error handling and CORS support

## Tech Stack

- **Backend**: FastAPI (Python)
- **Frontend**: Streamlit
- **Database**: SQLite using SQLAlchemy ORM
- **LLM Provider**: Groq API (llama-3.1-8b-instant model)

## Project Structure

```
askfirst/
├── database.py          # SQLAlchemy models and database setup
├── main.py              # FastAPI backend with API endpoints
├── app.py               # Streamlit frontend
├── requirements.txt     # Python dependencies
├── .env.example         # Environment variables template
├── .env                 # Your actual environment variables (create this)
├── chat.db              # SQLite database (auto-created)
└── README.md            # This file
```

## Setup Instructions

### 1. Create a Virtual Environment

```bash
python -m venv venv
```

### 2. Activate the Virtual Environment

**Windows:**
```bash
venv\Scripts\activate
```

**Mac/Linux:**
```bash
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy the example environment file and add your Groq API key:

```bash
copy .env.example .env
```

Edit the `.env` file and replace `your_groq_api_key_here` with your actual Groq API key:

```
GROQ_API_KEY=gsk_your_actual_api_key_here
MODEL_NAME=llama-3.1-8b-instant
```

To get a Groq API key, visit [https://console.groq.com/](https://console.groq.com/)

## Running the Application

You need to run both the backend server and the frontend simultaneously in separate terminals.

### Terminal 1: Start the FastAPI Backend

```bash
uvicorn main:app --reload --port 8000
```

The backend will start at `http://localhost:8000`

### Terminal 2: Start the Streamlit Frontend

```bash
streamlit run app.py
```

The frontend will open in your browser (typically at `http://localhost:8501`)

## API Endpoints

### POST /threads
Create a new thread.

**Request Body:**
```json
{
  "title": "Optional custom title"
}
```

**Response:**
```json
{
  "id": 1,
  "title": "New Chat 2024-01-01 12:00:00",
  "created_at": "2024-01-01T12:00:00"
}
```

### GET /threads
List all threads (newest first).

**Response:**
```json
[
  {
    "id": 1,
    "title": "New Chat 2024-01-01 12:00:00",
    "created_at": "2024-01-01T12:00:00"
  }
]
```

### GET /threads/{thread_id}/messages
Get message history for a specific thread.

**Response:**
```json
[
  {
    "id": 1,
    "thread_id": 1,
    "role": "user",
    "content": "Hello!",
    "created_at": "2024-01-01T12:00:00"
  },
  {
    "id": 2,
    "thread_id": 1,
    "role": "assistant",
    "content": "Hi there! How can I help you?",
    "created_at": "2024-01-01T12:00:01"
  }
]
```

### POST /threads/{thread_id}/messages
Send a message and get AI response with cross-thread memory.

**Request Body:**
```json
{
  "content": "Your message here"
}
```

**Response:**
```json
{
  "reply": "AI response here"
}
```

## Cross-Thread Memory Logic

The application implements a universal memory system that allows the AI to reference context from your past conversations:

1. When you send a message in a thread, the system fetches the full message history of the current thread
2. It also fetches the last 10 messages from all other threads (excluding the current one)
3. These cross-thread messages are formatted and included in a system message as context
4. The AI receives: [system message with cross-thread context] + [current thread history] + [your new message]
5. This allows the AI to maintain awareness of your past conversations without explicitly repeating them

## Database Schema

### threads table
- `id` (PK, autoincrement)
- `title` (string)
- `created_at` (datetime, default now)

### messages table
- `id` (PK, autoincrement)
- `thread_id` (FK → threads.id)
- `role` (string: "user" or "assistant")
- `content` (text)
- `created_at` (datetime, default now)

## Troubleshooting

- **Backend not starting**: Ensure port 8000 is not in use by another application
- **Frontend can't connect to backend**: Make sure the FastAPI server is running on port 8000
- **Groq API errors**: Verify your API key is correct in the `.env` file
- **Database errors**: The `chat.db` file will be auto-created on first run

## License

This project is provided as-is for educational purposes.
