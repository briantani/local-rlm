# Installation Guide

Complete installation instructions for the RLM agent on macOS and Windows.

## Prerequisites

### Required

| Component | Version | Purpose |
|-----------|---------|---------|
| **Python** | 3.14+ | Free-Threaded build recommended |
| **uv** | Latest | Fast Python package manager |
| **Git** | Latest | Clone repository |

### Optional (for local execution)

| Component | Version | Purpose |
|-----------|---------|---------|
| **Ollama** | Latest | Run local LLMs |

### Optional (for cloud execution)

| Provider | API Key Source |
|----------|----------------|
| **Gemini** | [Google AI Studio](https://aistudio.google.com/apikey) |
| **OpenAI** | [OpenAI Platform](https://platform.openai.com/api-keys) |

## macOS Installation

### Step 1: Install Homebrew (if not installed)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### Step 2: Install Python 3.14

```bash
# Using Homebrew
brew install python@3.14

# Verify installation
python3.14 --version
```

Alternatively, download from [python.org](https://www.python.org/downloads/).

### Step 3: Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Step 4: Clone and Set Up

```bash
# Clone the repository
git clone https://github.com/briantani/local-rlm.git
cd local-rlm

# Install dependencies
uv sync

# Verify installation
uv run python src/main.py --help
```

### Step 5: Install Ollama (Optional, for local execution)

```bash
# Install Ollama
brew install ollama

# Start Ollama service
ollama serve

# In another terminal, pull a model
ollama pull qwen2.5-coder:7b
```

### Step 6: Configure API Keys (Optional, for cloud execution)

```bash
# Create .env file
echo "GEMINI_API_KEY=your-gemini-key-here" > .env
echo "OPENAI_API_KEY=your-openai-key-here" >> .env
```

## Windows Installation

### Step 1: Install Python 3.14

**Option A: Microsoft Store (Recommended)**

1. Open Microsoft Store
2. Search for "Python 3.14"
3. Click Install

**Option B: Direct Download**

1. Go to [python.org/downloads](https://www.python.org/downloads/)
2. Download Python 3.14 installer
3. Run installer, **check "Add Python to PATH"**
4. Click "Install Now"

Verify installation:

```powershell
python --version
```

### Step 2: Install uv

Open PowerShell (not CMD) and run:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Close and reopen PowerShell, then verify:

```powershell
uv --version
```

### Step 3: Clone and Set Up

```powershell
# Clone the repository
git clone https://github.com/briantani/local-rlm.git
cd local-rlm

# Install dependencies
uv sync

# Verify installation
uv run python src/main.py --help
```

### Step 4: Install Ollama (Optional, for local execution)

1. Download from [ollama.ai](https://ollama.ai/)
2. Run the installer
3. Open a new terminal and run:

```powershell
# Start Ollama (runs in background)
ollama serve

# In another terminal, pull a model
ollama pull qwen2.5-coder:7b
```

### Step 5: Configure API Keys (Optional, for cloud execution)

```powershell
# Create .env file
"GEMINI_API_KEY=your-gemini-key-here" | Out-File -FilePath .env -Encoding utf8
"OPENAI_API_KEY=your-openai-key-here" | Out-File -FilePath .env -Append -Encoding utf8
```

## Verifying Installation

### Test 1: Basic Execution

```bash
uv run python src/main.py "What is 2 + 2?" --config configs/local-only.yaml
```

Expected output: The agent executes and returns "4".

### Test 2: Run Unit Tests

```bash
uv run pytest tests/test_repl.py tests/test_budget.py -v
```

All tests should pass.

### Test 3: Check Ollama Connection (if using local models)

```bash
ollama list
```

Should show your installed models.

### Test 4: Check API Keys (if using cloud providers)

```bash
# Test Gemini
uv run python -c "
import os
from dotenv import load_dotenv
load_dotenv()
key = os.getenv('GEMINI_API_KEY')
print('Gemini key configured:', 'Yes' if key else 'No')
"
```

## Troubleshooting

### Python not found

**macOS:**

```bash
# Check if Python 3.14 is installed
which python3.14

# Add to PATH if needed
export PATH="/opt/homebrew/bin:$PATH"
```

**Windows:**

1. Reinstall Python, ensure "Add to PATH" is checked
2. Or manually add to PATH via System Properties > Environment Variables

### uv command not found

**macOS:**

```bash
# Add uv to PATH
export PATH="$HOME/.cargo/bin:$PATH"

# Add to shell profile
echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

**Windows:**

Restart PowerShell after installation. If still not found:

```powershell
# Check installation location
$env:PATH -split ';' | Where-Object { $_ -like '*cargo*' }
```

### Ollama connection refused

```bash
# Ensure Ollama is running
ollama serve

# Check status
curl http://localhost:11434/api/version
```

### API key errors

1. Verify `.env` file exists in project root
2. Check key format (no quotes needed in file)
3. Ensure key is valid and has available quota

### Import errors

```bash
# Reinstall dependencies
uv sync --reinstall
```

### Permission errors (macOS/Linux)

```bash
# Make scripts executable
chmod +x scripts/*.sh
```

## Next Steps

- [Quick Start Guide](../README.md#quick-start)
- [Configuration Guide](CONFIGURATION.md)
- [RLM Theory](THEORY.md)
