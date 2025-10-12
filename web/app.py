"""
Flask Web Application - Real-time web interface for the Self-Engineering Agent
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
from src.orchestrator import AgentOrchestrator
from config import Config
import eventlet

# Patch for async support
eventlet.monkey_patch()

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'self-engineering-agent-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Initialize orchestrator
orchestrator = AgentOrchestrator()


@app.route('/')
def index():
    """Serve the main web interface"""
    return render_template('index.html')


@app.route('/api/tools', methods=['GET'])
def get_tools():
    """Get list of all available tools"""
    try:
        tools = orchestrator.get_all_tools()
        return jsonify({
            "success": True,
            "tools": tools,
            "count": len(tools)
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/tools/<tool_name>', methods=['GET'])
def get_tool_details(tool_name):
    """Get detailed information about a specific tool"""
    try:
        tool_info = orchestrator.registry.get_tool_by_name(tool_name)
        if not tool_info:
            return jsonify({
                "success": False,
                "error": "Tool not found"
            }), 404
        
        # Read the test file
        test_code = ""
        try:
            with open(tool_info['test_path'], 'r', encoding='utf-8') as f:
                test_code = f.read()
        except FileNotFoundError:
            test_code = "Test file not found"
        except Exception as e:
            test_code = f"Error reading test file: {str(e)}"
        
        return jsonify({
            "success": True,
            "tool": {
                "name": tool_info['name'],
                "code": tool_info['code'],
                "test_code": test_code,
                "docstring": tool_info['docstring'],
                "timestamp": tool_info['timestamp'],
                "file_path": tool_info['file_path'],
                "test_path": tool_info['test_path']
            }
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print('Client connected')
    emit('connected', {'data': 'Connected to agent'})
    
    # Send initial tool count
    tool_count = orchestrator.get_tool_count()
    emit('tool_count', {'count': tool_count})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print('Client disconnected')


@socketio.on('query')
def handle_query(data):
    """Handle user query"""
    user_prompt = data.get('prompt', '')
    
    if not user_prompt:
        emit('error', {'message': 'No prompt provided'})
        return
    
    print(f"Processing query: {user_prompt}")
    
    # Callback function to emit events to client
    def event_callback(event_type, event_data):
        socketio.emit('agent_event', {
            'event_type': event_type,
            'data': event_data
        })
    
    # Process the request
    result = orchestrator.process_request(
        user_prompt=user_prompt,
        callback=event_callback
    )
    
    # Send final result
    socketio.emit('query_complete', {
        'success': result['success'],
        'response': result['response'],
        'metadata': {
            'tool_name': result.get('tool_name'),
            'synthesized': result.get('synthesized', False),
            'tool_result': str(result.get('tool_result', ''))
        }
    })
    
    # Update tool count
    tool_count = orchestrator.get_tool_count()
    socketio.emit('tool_count', {'count': tool_count})


if __name__ == '__main__':
    print("=" * 60)
    print("Self-Engineering Agent Framework")
    print("=" * 60)
    print(f"Starting web server on {Config.FLASK_HOST}:{Config.FLASK_PORT}")
    print(f"Available tools: {orchestrator.get_tool_count()}")
    print("=" * 60)
    
    socketio.run(
        app,
        host=Config.FLASK_HOST,
        port=Config.FLASK_PORT,
        debug=Config.FLASK_DEBUG
    )

