"""
Flask Web Application - Real-time web interface for the Self-Engineering Agent
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit
from flask_swagger_ui import get_swaggerui_blueprint
from src.orchestrator import AgentOrchestrator
from config import Config
import eventlet
import os

# Patch for async support
eventlet.monkey_patch()

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'self-engineering-agent-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Initialize orchestrator
try:
    orchestrator = AgentOrchestrator()
    # Clean up any orphaned tools on startup
    removed_count = orchestrator.registry.cleanup_orphaned_tools()
    if removed_count > 0:
        print(f"Cleaned up {removed_count} orphaned tool(s) from database")
except Exception as e:
    print(f"Failed to initialize orchestrator: {e}")
    # Create a minimal fallback
    orchestrator = None

SWAGGER_URL = '/api/docs'
API_URL = '/api/openapi.yaml'
swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={
        'app_name': "Self-Engineering Agent Framework API",
        'docExpansion': 'list',
        'defaultModelsExpandDepth': 3,
        'displayRequestDuration': True
    }
)
app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)


@app.route('/')
def index():
    """Serve the main web interface"""
    return render_template('index.html')


@app.route('/api/openapi.yaml')
def serve_openapi_spec():
    """Serve the OpenAPI specification file"""
    docs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'docs')
    return send_from_directory(docs_dir, 'openapi.yaml')


@app.route('/api/tools', methods=['GET'])
def get_tools():
    """Get list of all available tools"""
    try:
        if orchestrator is None:
            return jsonify({
                "success": False,
                "error": "Orchestrator not initialized"
            }), 500
            
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


@app.route('/api/session', methods=['POST'])
def create_session():
    """Create a new UI session for conversational memory."""
    if orchestrator is None:
        return jsonify({
            "success": False,
            "error": "Orchestrator not initialized"
        }), 500

    try:
        session_id = orchestrator.memory_manager.start_session()
        return jsonify({
            "success": True,
            "session_id": session_id
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/session/<session_id>/messages', methods=['GET'])
def get_session_messages(session_id):
    """Return recent messages for a session."""
    if orchestrator is None:
        return jsonify({
            "success": False,
            "error": "Orchestrator not initialized"
        }), 500

    try:
        limit = int(request.args.get('limit', 20))
        messages = orchestrator.memory_manager.get_recent_messages(session_id, limit=limit)
        return jsonify({
            "success": True,
            "messages": messages,
            "count": len(messages)
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


@app.route('/api/analytics/relationships', methods=['GET'])
def get_tool_relationships():
    """Get tool relationship analytics"""
    try:
        tool_name = request.args.get('tool_name')
        min_confidence = float(request.args.get('min_confidence', 0.5))
        
        relationships = orchestrator.workflow_tracker.get_tool_relationships(
            tool_name=tool_name,
            min_confidence=min_confidence
        )
        
        return jsonify({
            "success": True,
            "relationships": relationships,
            "count": len(relationships)
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/analytics/patterns', methods=['GET'])
def get_workflow_patterns():
    """Get detected workflow patterns"""
    try:
        min_frequency = int(request.args.get('min_frequency', 2))
        limit = int(request.args.get('limit', 10))
        
        patterns = orchestrator.workflow_tracker.get_workflow_patterns(
            min_frequency=min_frequency,
            limit=limit
        )
        
        return jsonify({
            "success": True,
            "patterns": patterns,
            "count": len(patterns)
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/analytics/sessions/<session_id>', methods=['GET'])
def get_session_history(session_id):
    """Get execution history for a session"""
    try:
        limit = int(request.args.get('limit', 100))
        
        history = orchestrator.workflow_tracker.get_session_history(
            session_id=session_id,
            limit=limit
        )
        
        return jsonify({
            "success": True,
            "session_id": session_id,
            "executions": history,
            "count": len(history)
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/analytics/stats', methods=['GET'])
def get_workflow_stats():
    """Get overall workflow statistics"""
    try:
        # Get basic stats
        patterns = orchestrator.workflow_tracker.get_workflow_patterns(min_frequency=1, limit=100)
        relationships = orchestrator.workflow_tracker.get_tool_relationships(min_confidence=0.1)
        
        # Calculate stats
        total_patterns = len(patterns)
        total_relationships = len(relationships)
        
        # Most frequent pattern
        most_frequent_pattern = patterns[0] if patterns else None
        
        # Most connected tools
        tool_connection_counts = {}
        for rel in relationships:
            tool_a = rel['tool_a']
            tool_b = rel['tool_b']
            tool_connection_counts[tool_a] = tool_connection_counts.get(tool_a, 0) + 1
            tool_connection_counts[tool_b] = tool_connection_counts.get(tool_b, 0) + 1
        
        most_connected_tools = sorted(
            tool_connection_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        return jsonify({
            "success": True,
            "stats": {
                "total_patterns": total_patterns,
                "total_relationships": total_relationships,
                "most_frequent_pattern": {
                    "name": most_frequent_pattern['pattern_name'],
                    "frequency": most_frequent_pattern['frequency'],
                    "tools": most_frequent_pattern['tool_sequence']
                } if most_frequent_pattern else None,
                "most_connected_tools": [
                    {"tool": tool, "connections": count}
                    for tool, count in most_connected_tools
                ]
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
    session_id = data.get('session_id')
    
    if not user_prompt:
        emit('error', {'message': 'No prompt provided'})
        return

    if not session_id:
        emit('error', {'message': 'Please start a new session before sending prompts.'})
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
        session_id=session_id,
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
        },
        'session_id': result.get('session_id') or session_id
    })
    
    # Send updated memory snapshot for UI
    messages = orchestrator.memory_manager.get_recent_messages(session_id, limit=10)
    socketio.emit('session_memory', {
        'session_id': session_id,
        'messages': messages
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

