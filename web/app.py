"""
Flask Web Application - Real-time web interface for the Self-Engineering Agent
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
from flask_restx import Api, Resource, fields, Namespace
from src.orchestrator import AgentOrchestrator
from config import Config
import eventlet

# Patch for async support
eventlet.monkey_patch()

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'self-engineering-agent-secret-key'
app.config['RESTX_MASK_SWAGGER'] = False

# Initialize Flask-RESTX API with OpenAPI documentation
api = Api(
    app,
    version='1.0',
    title='Self-Engineering Agent Framework API',
    description='API for interacting with the Self-Engineering Agent Framework - an autonomous AI system that dynamically creates tools on demand using Test-Driven Development',
    doc='/api/docs',
    prefix='/api'
)

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


ns_session = api.namespace('session', description='Session management operations')
ns_tools = api.namespace('tools', description='Tool management and retrieval operations')
ns_analytics = api.namespace('analytics', description='Analytics and workflow pattern operations')

session_model = api.model('Session', {
    'session_id': fields.String(required=True, description='Unique session identifier', example='550e8400-e29b-41d4-a716-446655440000')
})

session_response = api.model('SessionResponse', {
    'success': fields.Boolean(required=True, description='Whether the operation was successful'),
    'session_id': fields.String(description='Created session identifier'),
    'error': fields.String(description='Error message if operation failed')
})

message_model = api.model('Message', {
    'role': fields.String(required=True, description='Message role (user or assistant)', enum=['user', 'assistant']),
    'content': fields.String(required=True, description='Message content'),
    'created_at': fields.String(description='ISO timestamp of message creation')
})

messages_response = api.model('MessagesResponse', {
    'success': fields.Boolean(required=True, description='Whether the operation was successful'),
    'messages': fields.List(fields.Nested(message_model), description='List of session messages'),
    'count': fields.Integer(description='Number of messages returned'),
    'error': fields.String(description='Error message if operation failed')
})

tool_summary = api.model('ToolSummary', {
    'name': fields.String(required=True, description='Tool function name', example='calculate_profit_margins'),
    'docstring': fields.String(description='Tool description and documentation'),
    'created_at': fields.String(description='ISO timestamp of tool creation'),
    'file_path': fields.String(description='Path to tool implementation file')
})

tools_response = api.model('ToolsResponse', {
    'success': fields.Boolean(required=True, description='Whether the operation was successful'),
    'tools': fields.List(fields.Nested(tool_summary), description='List of available tools'),
    'count': fields.Integer(description='Number of tools returned'),
    'error': fields.String(description='Error message if operation failed')
})

tool_detail = api.model('ToolDetail', {
    'name': fields.String(required=True, description='Tool function name'),
    'code': fields.String(description='Python implementation code'),
    'test_code': fields.String(description='Pytest test suite code'),
    'docstring': fields.String(description='Tool description and documentation'),
    'timestamp': fields.String(description='ISO timestamp of tool creation'),
    'file_path': fields.String(description='Path to tool implementation file'),
    'test_path': fields.String(description='Path to tool test file')
})

tool_detail_response = api.model('ToolDetailResponse', {
    'success': fields.Boolean(required=True, description='Whether the operation was successful'),
    'tool': fields.Nested(tool_detail, description='Detailed tool information'),
    'error': fields.String(description='Error message if operation failed')
})

relationship_model = api.model('ToolRelationship', {
    'tool_a': fields.String(required=True, description='First tool in relationship'),
    'tool_b': fields.String(required=True, description='Second tool in relationship'),
    'confidence_score': fields.Float(description='Confidence score of relationship (0-1)'),
    'frequency': fields.Integer(description='Number of times tools were used together')
})

relationships_response = api.model('RelationshipsResponse', {
    'success': fields.Boolean(required=True, description='Whether the operation was successful'),
    'relationships': fields.List(fields.Nested(relationship_model), description='List of tool relationships'),
    'count': fields.Integer(description='Number of relationships returned'),
    'error': fields.String(description='Error message if operation failed')
})

pattern_model = api.model('WorkflowPattern', {
    'pattern_name': fields.String(required=True, description='Name of the workflow pattern'),
    'tool_sequence': fields.List(fields.String, description='Ordered list of tools in pattern'),
    'frequency': fields.Integer(description='Number of times pattern was observed'),
    'avg_success_rate': fields.Float(description='Average success rate (0-1)'),
    'confidence_score': fields.Float(description='Confidence score (0-1)')
})

patterns_response = api.model('PatternsResponse', {
    'success': fields.Boolean(required=True, description='Whether the operation was successful'),
    'patterns': fields.List(fields.Nested(pattern_model), description='List of workflow patterns'),
    'count': fields.Integer(description='Number of patterns returned'),
    'error': fields.String(description='Error message if operation failed')
})

execution_model = api.model('Execution', {
    'tool_name': fields.String(required=True, description='Name of executed tool'),
    'execution_order': fields.Integer(description='Order in workflow sequence'),
    'inputs': fields.Raw(description='Tool input parameters'),
    'outputs': fields.Raw(description='Tool execution results'),
    'success': fields.Boolean(description='Whether execution succeeded'),
    'execution_time_ms': fields.Integer(description='Execution time in milliseconds'),
    'timestamp': fields.String(description='ISO timestamp of execution')
})

session_history_response = api.model('SessionHistoryResponse', {
    'success': fields.Boolean(required=True, description='Whether the operation was successful'),
    'session_id': fields.String(description='Session identifier'),
    'executions': fields.List(fields.Nested(execution_model), description='List of executions'),
    'count': fields.Integer(description='Number of executions returned'),
    'error': fields.String(description='Error message if operation failed')
})

stats_response = api.model('StatsResponse', {
    'success': fields.Boolean(required=True, description='Whether the operation was successful'),
    'stats': fields.Raw(description='Workflow statistics'),
    'error': fields.String(description='Error message if operation failed')
})


@app.route('/')
def index():
    """Serve the main web interface"""
    return render_template('index.html')


@ns_session.route('')
class SessionResource(Resource):
    @ns_session.doc('create_session')
    @ns_session.response(200, 'Success', session_response)
    @ns_session.response(500, 'Internal Server Error')
    def post(self):
        """Create a new session for conversational memory"""
        if orchestrator is None:
            return {
                "success": False,
                "error": "Orchestrator not initialized"
            }, 500

        try:
            session_id = orchestrator.memory_manager.start_session()
            return {
                "success": True,
                "session_id": session_id
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }, 500


@ns_session.route('/<string:session_id>/messages')
@ns_session.param('session_id', 'The session identifier')
class SessionMessagesResource(Resource):
    @ns_session.doc('get_session_messages')
    @ns_session.param('limit', 'Maximum number of messages to return', type=int, default=20)
    @ns_session.response(200, 'Success', messages_response)
    @ns_session.response(500, 'Internal Server Error')
    def get(self, session_id):
        """Get recent messages for a session"""
        if orchestrator is None:
            return {
                "success": False,
                "error": "Orchestrator not initialized"
            }, 500

        try:
            limit = int(request.args.get('limit', 20))
            messages = orchestrator.memory_manager.get_recent_messages(session_id, limit=limit)
            return {
                "success": True,
                "messages": messages,
                "count": len(messages)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }, 500


@ns_tools.route('')
class ToolsResource(Resource):
    @ns_tools.doc('get_tools')
    @ns_tools.response(200, 'Success', tools_response)
    @ns_tools.response(500, 'Internal Server Error')
    def get(self):
        """Get list of all available tools"""
        try:
            if orchestrator is None:
                return {
                    "success": False,
                    "error": "Orchestrator not initialized"
                }, 500
                
            tools = orchestrator.get_all_tools()
            return {
                "success": True,
                "tools": tools,
                "count": len(tools)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }, 500


@ns_tools.route('/<string:tool_name>')
@ns_tools.param('tool_name', 'The tool name')
class ToolDetailResource(Resource):
    @ns_tools.doc('get_tool_details')
    @ns_tools.response(200, 'Success', tool_detail_response)
    @ns_tools.response(404, 'Tool not found')
    @ns_tools.response(500, 'Internal Server Error')
    def get(self, tool_name):
        """Get detailed information about a specific tool"""
        try:
            tool_info = orchestrator.registry.get_tool_by_name(tool_name)
            if not tool_info:
                return {
                    "success": False,
                    "error": "Tool not found"
                }, 404
            
            test_code = ""
            try:
                with open(tool_info['test_path'], 'r', encoding='utf-8') as f:
                    test_code = f.read()
            except FileNotFoundError:
                test_code = "Test file not found"
            except Exception as e:
                test_code = f"Error reading test file: {str(e)}"
            
            return {
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
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }, 500


@ns_analytics.route('/relationships')
class RelationshipsResource(Resource):
    @ns_analytics.doc('get_tool_relationships')
    @ns_analytics.param('tool_name', 'Filter by specific tool name', type=str)
    @ns_analytics.param('min_confidence', 'Minimum confidence score', type=float, default=0.5)
    @ns_analytics.response(200, 'Success', relationships_response)
    @ns_analytics.response(500, 'Internal Server Error')
    def get(self):
        """Get tool relationship analytics"""
        try:
            tool_name = request.args.get('tool_name')
            min_confidence = float(request.args.get('min_confidence', 0.5))
            
            relationships = orchestrator.workflow_tracker.get_tool_relationships(
                tool_name=tool_name,
                min_confidence=min_confidence
            )
            
            return {
                "success": True,
                "relationships": relationships,
                "count": len(relationships)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }, 500


@ns_analytics.route('/patterns')
class PatternsResource(Resource):
    @ns_analytics.doc('get_workflow_patterns')
    @ns_analytics.param('min_frequency', 'Minimum pattern frequency', type=int, default=2)
    @ns_analytics.param('limit', 'Maximum number of patterns to return', type=int, default=10)
    @ns_analytics.response(200, 'Success', patterns_response)
    @ns_analytics.response(500, 'Internal Server Error')
    def get(self):
        """Get detected workflow patterns"""
        try:
            min_frequency = int(request.args.get('min_frequency', 2))
            limit = int(request.args.get('limit', 10))
            
            patterns = orchestrator.workflow_tracker.get_workflow_patterns(
                min_frequency=min_frequency,
                limit=limit
            )
            
            return {
                "success": True,
                "patterns": patterns,
                "count": len(patterns)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }, 500


@ns_analytics.route('/sessions/<string:session_id>')
@ns_analytics.param('session_id', 'The session identifier')
class SessionHistoryResource(Resource):
    @ns_analytics.doc('get_session_history')
    @ns_analytics.param('limit', 'Maximum number of executions to return', type=int, default=100)
    @ns_analytics.response(200, 'Success', session_history_response)
    @ns_analytics.response(500, 'Internal Server Error')
    def get(self, session_id):
        """Get execution history for a session"""
        try:
            limit = int(request.args.get('limit', 100))
            
            history = orchestrator.workflow_tracker.get_session_history(
                session_id=session_id,
                limit=limit
            )
            
            return {
                "success": True,
                "session_id": session_id,
                "executions": history,
                "count": len(history)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }, 500


@ns_analytics.route('/stats')
class StatsResource(Resource):
    @ns_analytics.doc('get_workflow_stats')
    @ns_analytics.response(200, 'Success', stats_response)
    @ns_analytics.response(500, 'Internal Server Error')
    def get(self):
        """Get overall workflow statistics"""
        try:
            patterns = orchestrator.workflow_tracker.get_workflow_patterns(min_frequency=1, limit=100)
            relationships = orchestrator.workflow_tracker.get_tool_relationships(min_confidence=0.1)
            
            total_patterns = len(patterns)
            total_relationships = len(relationships)
            
            most_frequent_pattern = patterns[0] if patterns else None
            
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
            
            return {
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
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }, 500


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

