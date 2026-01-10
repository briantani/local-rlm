# Web Interface

> 🚧 **WORK IN PROGRESS** 🚧
>
> The web interface is currently under development and **not fully functional**.
> Please use the [CLI](#cli-alternative) for production tasks.

## Overview

The RLM agent includes an experimental web interface built with:

- **FastAPI** - Backend API
- **HTMX** - Dynamic HTML updates
- **Alpine.js** - Client-side interactivity
- **Tailwind CSS** - Styling

## Current Status

### ✅ Working Features

- Basic page rendering
- Configuration profile listing
- API endpoint structure

### ❌ Not Working / Incomplete

- Real-time task streaming
- Session management
- Task execution via web UI
- Artifact display and download
- Cost estimation display
- Error handling in UI

## Architecture

```text
┌─────────────────────────────────────────────────┐
│                  Web Browser                    │
│  ┌───────────┐  ┌───────────┐  ┌─────────────┐ │
│  │   HTMX    │  │ Alpine.js │  │ Tailwind    │ │
│  └─────┬─────┘  └─────┬─────┘  └─────────────┘ │
│        │              │                         │
└────────┼──────────────┼─────────────────────────┘
         │              │
         ▼              ▼
┌─────────────────────────────────────────────────┐
│              FastAPI Backend                    │
│  ┌──────────────────────────────────────────┐  │
│  │  /api/configs    - List profiles         │  │
│  │  /api/tasks      - Submit/track tasks    │  │
│  │  /api/sessions   - Manage sessions       │  │
│  └──────────────────────────────────────────┘  │
│                      │                          │
│                      ▼                          │
│  ┌──────────────────────────────────────────┐  │
│  │         Service Layer                     │  │
│  │  TaskService, ConfigService, Session...   │  │
│  └──────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

## Known Issues

### Issue 1: SSE Streaming Not Working

**Symptom:** Task execution doesn't show real-time updates.

**Cause:** Server-Sent Events connection drops or doesn't establish.

**Workaround:** Use CLI instead.

### Issue 2: Session API Key Handling

**Symptom:** API keys not being passed to task execution.

**Cause:** Session management incomplete.

**Workaround:** Use environment variables in `.env` file.

### Issue 3: JavaScript Errors

**Symptom:** UI elements not responding.

**Cause:** Alpine.js/HTMX integration issues.

**Workaround:** Refresh page or use CLI.

## Running the Web Server (Development Only)

> ⚠️ **Warning:** The web interface is not production-ready.

```bash
# Start the development server
uv run uvicorn src.web.main:app --reload --port 8000

# Access at http://localhost:8000
```

## CLI Alternative

For reliable task execution, use the CLI:

```bash
# Basic task
uv run python src/main.py "Your task" --config configs/local-only.yaml

# With context files
uv run python src/main.py "Analyze data" --config configs/hybrid.yaml --context ./data

# With verbose output
uv run python src/main.py "Complex task" --config configs/high-quality.yaml --verbose
```

## Contributing to Web UI

If you'd like to help complete the web interface:

### Priority Areas

1. **Fix SSE streaming** - `src/web/routes/tasks.py`
2. **Complete session management** - `src/rlm/services/session_service.py`
3. **Add error handling** - JavaScript error boundaries
4. **Test coverage** - `tests/test_web.py`, `tests/test_web_ui.py`

### Development Setup

```bash
# Install development dependencies
uv sync --all-extras

# Run tests
uv run pytest tests/test_web.py tests/test_web_ui.py -v

# Start with auto-reload
uv run uvicorn src.web.main:app --reload
```

### File Structure

```text
src/web/
├── main.py              # FastAPI app entry point
├── routes/
│   ├── api.py           # API endpoints
│   ├── pages.py         # HTML page routes
│   └── tasks.py         # Task execution routes
├── templates/
│   ├── base.html        # Layout template
│   ├── index.html       # Home page
│   └── components/      # Reusable components
└── static/
    ├── css/             # Stylesheets
    └── js/              # JavaScript
```

## Roadmap

- [ ] Fix SSE streaming for real-time updates
- [ ] Implement proper session management
- [ ] Add task history and artifact browser
- [ ] Add configuration editor
- [ ] Add cost estimation preview
- [ ] Add dark mode toggle
- [ ] Mobile responsive design
- [ ] Deployment documentation

## Related Documentation

- [CLI Quick Start](../README.md#quick-start)
- [Configuration Guide](CONFIGURATION.md)
- [Installation Guide](INSTALLATION.md)
