# 🤖 Self-Engineering Agent Framework

An autonomous agent that doesn't just use a fixed set of tools, but actively and safely engineers new tools for itself in real-time using Test-Driven Development (TDD) methodology.

## 🌟 Overview

When faced with a user request it cannot fulfill with existing capabilities, this agent enters "synthesis mode" where it:

1. **Defines requirements** for the missing tool
2. **Writes unit tests** to ensure correctness (TDD)
3. **Implements the code** to pass those tests
4. **Verifies in a secure sandbox** (Docker container)
5. **Integrates permanently** into its skillset for future use

The agent becomes more capable over time with every new tool it builds, effectively learning from interactions.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    User Request (Web UI)                     │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  Central Orchestrator                        │
│  (Coordinates the entire flow with real-time updates)       │
└──────────────────────────┬──────────────────────────────────┘
                           │
          ┌────────────────┴────────────────┐
          ▼                                 ▼
┌──────────────────────┐         ┌──────────────────────┐
│ Capability Registry  │   YES   │   Tool Executor      │
│  (Vector DB Search)  ├────────▶│ (Dynamic Loading)    │
│                      │         └──────────┬───────────┘
│  Tool Found?         │                    │
│                      │                    │
└──────────┬───────────┘                    │
           │ NO                             │
           ▼                                │
┌──────────────────────┐                   │
│ Synthesis Engine     │                   │
│  (TDD Workflow)      │                   │
│                      │                   │
│ 1. Generate Spec     │                   │
│ 2. Generate Tests    │                   │
│ 3. Implement Code    │                   │
│ 4. Verify in Sandbox │◀──┐               │
│ 5. Register Tool     │   │               │
└──────────┬───────────┘   │               │
           │                │               │
           │         ┌──────┴───────────┐   │
           │         │ Secure Sandbox   │   │
           │         │ (Docker)         │   │
           │         └──────────────────┘   │
           │                                │
           └────────────────┬───────────────┘
                            ▼
                 ┌──────────────────────┐
                 │ Response Synthesizer │
                 │ (Natural Language)   │
                 └──────────┬───────────┘
                            │
                            ▼
                    ┌──────────────┐
                    │ Final Response│
                    └──────────────┘
```

## ✨ Key Features

- **🔧 Self-Engineering**: Creates new tools autonomously when needed
- **✅ Test-Driven Development**: Every tool is tested before integration
- **🔒 Security First**: All code runs in isolated Docker containers
- **📊 Real-Time Visualization**: Web UI shows the entire synthesis process
- **🧠 Semantic Search**: Uses vector embeddings to find relevant tools
- **♻️ Reusability**: Tools persist and are reused for future requests
- **🌐 Modern Web Interface**: Beautiful, responsive UI with WebSocket updates

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- Docker Desktop (running)
- OpenAI API key

### Installation

1. **Clone the repository**
   ```bash
   cd "Self-Engineering Agent Framework"
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**
   
   Create a `.env` file in the root directory:
   ```env
   OPENAI_API_KEY=your_openai_api_key_here
   OPENAI_MODEL=gpt-4
   SIMILARITY_THRESHOLD=0.75
   DOCKER_IMAGE_NAME=self-eng-sandbox
   CHROMA_PERSIST_DIR=./chroma_db
   ```

4. **Build the Docker sandbox image**
   ```bash
   python -c "from src.sandbox import SecureSandbox; SecureSandbox().build_image()"
   ```

5. **Seed initial tools** (optional but recommended)
   ```bash
   python seed_tools.py
   ```

6. **Start the web server**
   ```bash
   python web/app.py
   ```

7. **Open your browser**
   
   Navigate to `http://localhost:5000`

## 🎯 Usage Examples

### Example 1: Using an Existing Tool

**User Query**: "What is 15 percent of 300?"

**Agent Behavior**:
1. Searches capability registry
2. Finds `calculate_percentage` tool (high similarity)
3. Executes the tool with extracted arguments
4. Returns natural language response: "15 percent of 300 is 45."

### Example 2: Creating a New Tool

**User Query**: "Reverse the string 'hello world'"

**Agent Behavior**:
1. Searches capability registry
2. No matching tool found - enters synthesis mode
3. **Specification**: Defines `reverse_string(s: str) -> str`
4. **Tests**: Generates test cases (normal, empty, single char)
5. **Implementation**: Writes the function code
6. **Verification**: Runs tests in Docker sandbox - all pass ✅
7. **Registration**: Saves tool permanently
8. **Execution**: Runs the new tool immediately
9. Returns: "The reversed string is 'dlrow olleh'"

### Example 3: Reusing a Synthesized Tool

**User Query**: "Reverse 'Python'"

**Agent Behavior**:
1. Finds the previously created `reverse_string` tool
2. Executes it immediately
3. Returns: "The reversed string is 'nohtyP'"

## 📁 Project Structure

```
Self-Engineering Agent Framework/
├── src/
│   ├── orchestrator.py          # Central decision-making component
│   ├── capability_registry.py   # Vector DB storage & retrieval
│   ├── synthesis_engine.py      # TDD-based tool creation
│   ├── sandbox.py               # Docker-based secure execution
│   ├── executor.py              # Dynamic tool loading & execution
│   ├── response_synthesizer.py # Natural language response generation
│   └── llm_client.py            # OpenAI API wrapper
├── tools/                        # Auto-generated tools persist here
├── web/
│   ├── app.py                   # Flask server with WebSocket support
│   ├── static/
│   │   ├── style.css            # Modern UI styling
│   │   └── script.js            # Real-time frontend logic
│   └── templates/
│       └── index.html           # Web interface
├── docker/
│   └── sandbox.dockerfile       # Minimal Python + pytest environment
├── chroma_db/                   # Vector database storage (auto-created)
├── config.py                    # Configuration management
├── requirements.txt             # Python dependencies
├── seed_tools.py                # Initial tool seeding script
├── .env.example                 # Environment variable template
└── README.md                    # This file
```

## 🔧 Configuration

All configuration is managed through environment variables in the `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | *required* | Your OpenAI API key |
| `OPENAI_MODEL` | `gpt-4` | LLM model to use |
| `SIMILARITY_THRESHOLD` | `0.75` | Minimum similarity for tool matching (0-1) |
| `DOCKER_IMAGE_NAME` | `self-eng-sandbox` | Name for the sandbox Docker image |
| `DOCKER_TIMEOUT` | `30` | Sandbox execution timeout (seconds) |
| `CHROMA_PERSIST_DIR` | `./chroma_db` | Vector database storage location |
| `TOOLS_DIR` | `./tools` | Directory for tool storage |
| `FLASK_HOST` | `0.0.0.0` | Web server host |
| `FLASK_PORT` | `5000` | Web server port |

## 🧪 Testing

### Test Individual Components

```bash
# Test LLM Client
python src/llm_client.py

# Test Capability Registry
python src/capability_registry.py

# Test Sandbox
python src/sandbox.py

# Test Synthesis Engine
python src/synthesis_engine.py

# Test Orchestrator
python src/orchestrator.py
```

### Run Tool Tests

```bash
# Test a specific tool
cd tools
pytest test_calculate_percentage.py -v
```

## 🔒 Security Considerations

1. **Docker Isolation**: All untrusted code runs in isolated containers with:
   - No network access
   - Limited CPU and memory
   - Read-only volume mounts
   - Immediate destruction after execution

2. **Code Verification**: Every synthesized tool must pass its test suite before integration

3. **API Key Protection**: Store your OpenAI API key securely in `.env` (never commit it)

4. **Input Validation**: All user inputs are processed through the LLM before execution

## 🎨 Web Interface Features

- **Real-Time Activity Log**: See exactly what the agent is doing
- **Color-Coded Status**: Visual feedback for each step
- **Tool Library**: Browse all available capabilities
- **Example Queries**: Quick-start templates
- **Responsive Design**: Works on desktop and mobile
- **WebSocket Updates**: Live progress without page refresh

## 🚧 Limitations & Future Enhancements

### Current Limitations

- Tools are Python-only (no multi-language support yet)
- Network access disabled in sandbox (can't make API calls)
- No tool versioning or rollback
- Single-threaded request processing

### Potential Enhancements

- **Multi-language support**: Generate tools in JavaScript, Go, etc.
- **Tool composition**: Combine existing tools to create complex workflows
- **Learning from failures**: Analyze failed syntheses to improve
- **Tool optimization**: Refactor tools for better performance
- **Collaborative filtering**: Suggest tools based on usage patterns
- **Export/Import**: Share tool libraries between instances
- **Version control**: Track tool evolution over time

## 🤝 Contributing

This is a demonstration framework. Key areas for contribution:

1. Improving LLM prompts for better code generation
2. Enhanced error handling and recovery
3. Additional seed tools for common operations
4. Performance optimizations
5. Security enhancements

## 📝 License

This project is provided as-is for educational and research purposes.

## 🙏 Acknowledgments

Built with:
- **OpenAI GPT-4** for code generation
- **ChromaDB** for vector similarity search
- **Docker** for secure sandboxing
- **Flask + Socket.IO** for real-time web interface
- **pytest** for testing framework

## 📞 Support

For issues or questions:
1. Check that Docker is running
2. Verify your OpenAI API key is valid
3. Ensure all dependencies are installed
4. Check the activity log in the web UI for detailed error messages

---

**Built with ❤️ as a demonstration of autonomous agent capabilities**

