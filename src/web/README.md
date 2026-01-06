# RLM Agent Web UI

A modern web interface for the Recursive Language Model Agent built with FastAPI, HTMX, Alpine.js, and Tailwind CSS.

## 🚀 Quick Start

### Start the Server

```bash
uv run uvicorn src.web.app:app --reload --port 8000
```

Then open your browser to [http://localhost:8000](http://localhost:8000)

### Using the UI

1. **Session Management**: Sessions are automatically created and stored in your browser's localStorage
2. **Configuration**: Select a configuration profile from the dropdown
3. **API Keys**: If the profile requires API keys (Gemini, OpenAI), a modal will appear:
   - API keys are stored in memory only
   - Never persisted to disk or database
   - Cleared when you close the browser
4. **Run Tasks**: Enter your task description and click "Run Task"
5. **Real-time Streaming**: Watch execution steps, code, and output stream in real-time via WebSocket
6. **Results**: See the final answer with cost breakdown

## 🏗️ Architecture

### Frontend Stack

- **Tailwind CSS**: Utility-first styling
- **HTMX**: Dynamic content updates
- **Alpine.js**: Reactive UI components
- **WebSocket**: Real-time streaming

### Backend

- **FastAPI**: REST API + WebSocket
- **SQLite**: Task history persistence (via aiosqlite)
- **Jinja2**: Server-side template rendering

### Directory Structure

```
src/web/
├── app.py                 # FastAPI application factory
├── dependencies.py        # Dependency injection
├── database.py           # SQLite persistence
├── task_runner.py        # Async task execution
├── routes/
│   ├── sessions.py       # Session & API key management
│   ├── configs.py        # Configuration profiles
│   └── tasks.py          # Task CRUD & execution
├── websocket/
│   └── stream.py         # WebSocket streaming
├── templates/
│   ├── base.html         # Base template with CDN includes
│   ├── index.html        # Main task runner page
│   └── components/
│       └── api_key_modal.html  # API key configuration
└── static/
    └── css/
        └── app.css       # Custom styles
```

## 🔐 Security

### API Key Handling

- API keys are **never** persisted to disk or database
- Stored only in `SessionService` memory (Python dictionary)
- Automatically cleared when the server restarts
- Each browser session has a unique session ID

### Session Isolation

- Each user gets a unique session ID (UUIDv4)
- Sessions are isolated - one session cannot access another's tasks or keys
- Session IDs are stored in browser localStorage

## 📡 API Endpoints

### Sessions

- `POST /api/sessions` - Create a new session
- `PUT /api/sessions/{id}/keys` - Set API keys
- `GET /api/sessions/{id}/keys/status` - Check configured keys
- `DELETE /api/sessions/{id}` - Delete session and clear keys

### Configs

- `GET /api/configs` - List all configuration profiles
- `GET /api/configs/{name}` - Get profile details
- `GET /api/configs/{name}/estimate` - Estimate task cost

### Tasks

- `POST /api/tasks` - Create and start a task
- `GET /api/tasks` - List tasks for session
- `GET /api/tasks/{id}` - Get task details

### WebSocket

- `WS /ws/tasks/{id}` - Stream real-time updates

## 🎨 UI Components

### Task Runner (index.html)

- Configuration selector with auto-detection of required API keys
- Task input textarea
- Real-time execution display with:
  - Step-by-step progress
  - Code generation display
  - Execution output
  - Final results with cost breakdown

### API Key Modal

- Triggered automatically when profile requires keys
- Shows status of configured keys
- Links to get API keys from providers
- Validation and error handling

## 🧪 Testing

Run the web tests:

```bash
uv run pytest tests/test_web.py -v
```

All tests use temporary SQLite databases and mock sessions.

## 🔧 Development

### Hot Reload

The server runs in development mode with `--reload` flag, automatically restarting when code changes.

### Browser DevTools

- Check Network tab for WebSocket messages
- Check Console for JavaScript errors
- Check Application → localStorage for session ID

### Database

SQLite database is created at `data/rlm.db` (configurable in `database.py`).

View database:
```bash
sqlite3 data/rlm.db
.schema
SELECT * FROM tasks;
```

## 📦 Dependencies

Core dependencies (already in pyproject.toml):
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `aiosqlite` - Async SQLite
- `websockets` - WebSocket support
- `python-multipart` - Form parsing
- `jinja2` - Template engine

Frontend dependencies (CDN):
- Tailwind CSS 3.x
- HTMX 2.x
- Alpine.js 3.x

## 🚧 Future Enhancements (Phase 15+)

- [ ] Configuration comparison UI
- [ ] Cost estimator widget
- [ ] Chat interface for follow-up queries
- [ ] Task history viewer
- [ ] Export results to file

## 📄 License

MIT License - See LICENSE file
