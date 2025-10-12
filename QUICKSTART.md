# 🚀 Quick Start Guide

Get the Self-Engineering Agent Framework up and running in 5 minutes!

## Prerequisites Check

Before starting, ensure you have:

- ✅ **Python 3.10+** installed
- ✅ **Docker Desktop** installed and **running**
- ✅ **OpenAI API key** ready

## Step-by-Step Setup

### 1. Install Dependencies

Open a terminal in the project directory and run:

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file in the project root:

```bash
# Windows PowerShell
Copy-Item .env.example .env

# Then edit .env and add your OpenAI API key
```

Edit the `.env` file and add your actual OpenAI API key:

```env
OPENAI_API_KEY=sk-your-actual-key-here
OPENAI_MODEL=gpt-4
```

### 3. Run Automated Setup

The setup script will:
- Verify your environment
- Build the Docker sandbox image
- Seed initial tools

```bash
python setup.py
```

### 4. Start the Agent

```bash
python web/app.py
```

You should see:

```
============================================================
Self-Engineering Agent Framework
============================================================
Starting web server on 0.0.0.0:5000
Available tools: 2
============================================================
```

### 5. Open the Web Interface

Open your browser and navigate to:

```
http://localhost:5000
```

## 🎯 Try These First Queries

Once the web interface is open, try these example queries:

### Using Existing Tools

1. **"What is 25 percent of 80?"**
   - Uses the pre-seeded `calculate_percentage` tool
   - Should return: "25 percent of 80 is 20."

2. **"Convert 100 degrees Fahrenheit to Celsius"**
   - This will trigger synthesis! No F→C tool exists yet
   - Watch the agent create, test, and use a new tool in real-time

### Triggering Synthesis Mode

3. **"Reverse the string 'hello world'"**
   - No reverse_string tool exists
   - Agent will synthesize it on-the-fly
   - Future reverse requests will use this new tool

4. **"Calculate the factorial of 5"**
   - Another synthesis trigger
   - Agent creates a factorial function with proper edge case handling

## 🔍 What to Watch For

In the web interface activity log, you'll see:

**For existing tools:**
```
🔍 Searching for existing capability...
✓ Found tool: calculate_percentage (similarity: 89.2%)
⚙️ Executing tool: calculate_percentage
✓ Execution complete: 20.0
💬 Generating natural language response...
✓ All done!
```

**For new tools (synthesis mode):**
```
🔍 Searching for existing capability...
⚠ No matching tool found
🔧 Entering synthesis mode - creating new capability...
⏳ Generating function specification...
✓ Generating function specification complete
⏳ Generating test suite...
✓ Generating test suite complete
⏳ Implementing function...
✓ Implementing function complete
⏳ Verifying in sandbox...
✓ Verifying in sandbox complete
⏳ Registering new tool...
✓ Registering new tool complete
✓ Successfully synthesized: reverse_string
⚙️ Executing tool: reverse_string
✓ Execution complete: dlrow olleh
💬 Generating natural language response...
✓ All done!
```

## 🛠️ Troubleshooting

### "Failed to connect to Docker"

**Solution**: Make sure Docker Desktop is running. You should see the Docker icon in your system tray.

```bash
# Test Docker is running
docker ps
```

### "OPENAI_API_KEY must be set"

**Solution**: Check your `.env` file exists and contains your API key:

```bash
# Windows
type .env

# Check the OPENAI_API_KEY line
```

### "Module not found" errors

**Solution**: Reinstall dependencies:

```bash
pip install --upgrade -r requirements.txt
```

### Docker build fails

**Solution**: Build the image manually:

```bash
docker build -t self-eng-sandbox -f docker/sandbox.dockerfile docker/
```

## 📊 Monitoring

### Check Available Tools

The web interface shows:
- **Tool count** in the header
- **Tool library** at the bottom with all available capabilities
- Each tool shows its name, description, and creation timestamp

### View Logs

The activity log shows real-time progress. Each step is color-coded:
- 🔵 **Blue**: Information (searching, executing)
- 🟢 **Green**: Success (tool found, execution complete)
- 🟡 **Orange**: Warning (no tool found, entering synthesis)
- 🔴 **Red**: Error (execution failed)

## 🎓 Learning Path

1. **Start with existing tools** - Get familiar with the interface
2. **Trigger synthesis** - Watch a tool being created
3. **Reuse synthesized tools** - See how they persist
4. **Experiment** - Try various requests to build your tool library

## 📝 Next Steps

- Read the full [README.md](README.md) for architecture details
- Check the `tools/` directory to see generated code
- Explore `chroma_db/` to see the vector database
- Modify seed tools to add your own initial capabilities

## 🆘 Getting Help

If you encounter issues:

1. Check the web interface activity log for detailed errors
2. Look at the terminal running `web/app.py` for backend logs
3. Verify Docker is running: `docker ps`
4. Verify Python version: `python --version` (should be 3.10+)
5. Check OpenAI API key is valid

## 🎉 Success!

If you see the web interface and can successfully query the agent, you're all set! 

The agent is now running and will autonomously create new tools as you need them. Enjoy exploring autonomous capability synthesis! 🚀

