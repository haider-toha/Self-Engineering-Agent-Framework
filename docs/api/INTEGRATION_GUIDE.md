# Integration Guide

This guide provides three complete working examples demonstrating how to integrate with the Self-Engineering Agent Framework API.

## Table of Contents

1. [Example 1: Basic Query Submission](#example-1-basic-query-submission)
2. [Example 2: Tool Synthesis Workflow](#example-2-tool-synthesis-workflow)
3. [Example 3: Multi-Tool Composition](#example-3-multi-tool-composition)

---

## Prerequisites

### Installation

```bash
# Install required packages
pip install requests python-socketio[client]
```

### Configuration

```python
# config.py
API_BASE_URL = "http://localhost:5001"
API_PREFIX = "/api"
```

---

## Example 1: Basic Query Submission

This example demonstrates the complete workflow for submitting a query, receiving real-time progress updates, and handling the response.

### Python Implementation

```python
import requests
import socketio
import time
from typing import Dict, Any

class AgentClient:
    """Client for interacting with the Self-Engineering Agent Framework"""
    
    def __init__(self, base_url: str = "http://localhost:5001"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.session_id = None
        self.sio = socketio.Client()
        self._setup_socket_handlers()
    
    def _setup_socket_handlers(self):
        """Configure Socket.IO event handlers"""
        
        @self.sio.on('connect')
        def on_connect():
            print("✓ Connected to agent")
        
        @self.sio.on('connected')
        def on_connected(data):
            print(f"✓ Server confirmed: {data['data']}")
        
        @self.sio.on('tool_count')
        def on_tool_count(data):
            print(f"✓ Available tools: {data['count']}")
        
        @self.sio.on('agent_event')
        def on_agent_event(event):
            event_type = event['event_type']
            data = event['data']
            
            # Display progress based on event type
            if event_type == 'searching':
                print(f"  🔍 Searching for existing tool...")
            elif event_type == 'tool_found':
                print(f"  ✓ Found tool: {data['tool_name']} (similarity: {data['similarity']:.2f})")
            elif event_type == 'executing':
                print(f"  ⚙️  Executing: {data['tool_name']}")
            elif event_type == 'execution_complete':
                print(f"  ✓ Execution complete")
            elif event_type == 'entering_synthesis_mode':
                print(f"  🔨 Creating new tool...")
            elif event_type == 'synthesis_step':
                step = data['step']
                status = data['status']
                if status == 'in_progress':
                    print(f"  ⏳ Synthesis: {step}...")
                elif status == 'complete':
                    print(f"  ✓ Synthesis: {step} complete")
        
        @self.sio.on('query_complete')
        def on_query_complete(result):
            print("\n" + "="*60)
            if result['success']:
                print("✓ Query completed successfully!")
                print(f"\nResponse: {result['response']}")
                print(f"\nMetadata:")
                print(f"  - Tool: {result['metadata']['tool_name']}")
                print(f"  - Synthesized: {result['metadata']['synthesized']}")
            else:
                print("✗ Query failed")
                print(f"Error: {result['response']}")
            print("="*60)
        
        @self.sio.on('error')
        def on_error(error):
            print(f"✗ Error: {error['message']}")
    
    def connect(self):
        """Connect to the agent server"""
        self.sio.connect(self.base_url)
        time.sleep(0.5)  # Wait for connection to establish
    
    def disconnect(self):
        """Disconnect from the agent server"""
        self.sio.disconnect()
    
    def create_session(self) -> str:
        """Create a new session for conversational memory"""
        response = requests.post(f"{self.api_url}/session")
        response.raise_for_status()
        data = response.json()
        
        if data['success']:
            self.session_id = data['session_id']
            print(f"✓ Session created: {self.session_id}")
            return self.session_id
        else:
            raise Exception(f"Failed to create session: {data['error']}")
    
    def submit_query(self, prompt: str):
        """Submit a query to the agent"""
        if not self.session_id:
            raise Exception("No active session. Call create_session() first.")
        
        print(f"\n📝 Submitting query: {prompt}\n")
        self.sio.emit('query', {
            'prompt': prompt,
            'session_id': self.session_id
        })
    
    def get_tools(self) -> list:
        """Get list of all available tools"""
        response = requests.get(f"{self.api_url}/tools")
        response.raise_for_status()
        data = response.json()
        
        if data['success']:
            return data['tools']
        else:
            raise Exception(f"Failed to get tools: {data['error']}")
    
    def get_tool_details(self, tool_name: str) -> Dict[str, Any]:
        """Get detailed information about a specific tool"""
        response = requests.get(f"{self.api_url}/tools/{tool_name}")
        response.raise_for_status()
        data = response.json()
        
        if data['success']:
            return data['tool']
        else:
            raise Exception(f"Failed to get tool details: {data['error']}")


def main():
    """Example 1: Basic Query Submission"""
    
    # Initialize client
    client = AgentClient()
    
    try:
        # Connect to server
        client.connect()
        
        # Create a session
        client.create_session()
        
        # Submit a query
        client.submit_query("Calculate profit margins from data/ecommerce_products.csv")
        
        # Wait for processing to complete
        time.sleep(10)
        
        # Get list of available tools
        print("\n📚 Available tools:")
        tools = client.get_tools()
        for tool in tools[:5]:  # Show first 5 tools
            print(f"  - {tool['name']}: {tool['docstring'][:60]}...")
        
    finally:
        # Disconnect
        client.disconnect()


if __name__ == "__main__":
    main()
```

### JavaScript Implementation

```javascript
const io = require('socket.io-client');
const axios = require('axios');

class AgentClient {
  constructor(baseUrl = 'http://localhost:5001') {
    this.baseUrl = baseUrl;
    this.apiUrl = `${baseUrl}/api`;
    this.sessionId = null;
    this.socket = null;
  }

  connect() {
    return new Promise((resolve) => {
      this.socket = io(this.baseUrl);
      
      this.socket.on('connect', () => {
        console.log('✓ Connected to agent');
      });
      
      this.socket.on('connected', (data) => {
        console.log(`✓ Server confirmed: ${data.data}`);
        resolve();
      });
      
      this.socket.on('tool_count', (data) => {
        console.log(`✓ Available tools: ${data.count}`);
      });
      
      this.socket.on('agent_event', (event) => {
        const { event_type, data } = event;
        
        switch(event_type) {
          case 'searching':
            console.log('  🔍 Searching for existing tool...');
            break;
          case 'tool_found':
            console.log(`  ✓ Found tool: ${data.tool_name} (similarity: ${data.similarity.toFixed(2)})`);
            break;
          case 'executing':
            console.log(`  ⚙️  Executing: ${data.tool_name}`);
            break;
          case 'execution_complete':
            console.log('  ✓ Execution complete');
            break;
          case 'entering_synthesis_mode':
            console.log('  🔨 Creating new tool...');
            break;
          case 'synthesis_step':
            if (data.status === 'in_progress') {
              console.log(`  ⏳ Synthesis: ${data.step}...`);
            } else if (data.status === 'complete') {
              console.log(`  ✓ Synthesis: ${data.step} complete`);
            }
            break;
        }
      });
      
      this.socket.on('query_complete', (result) => {
        console.log('\n' + '='.repeat(60));
        if (result.success) {
          console.log('✓ Query completed successfully!');
          console.log(`\nResponse: ${result.response}`);
          console.log('\nMetadata:');
          console.log(`  - Tool: ${result.metadata.tool_name}`);
          console.log(`  - Synthesized: ${result.metadata.synthesized}`);
        } else {
          console.log('✗ Query failed');
          console.log(`Error: ${result.response}`);
        }
        console.log('='.repeat(60));
      });
      
      this.socket.on('error', (error) => {
        console.error(`✗ Error: ${error.message}`);
      });
    });
  }

  async createSession() {
    const response = await axios.post(`${this.apiUrl}/session`);
    
    if (response.data.success) {
      this.sessionId = response.data.session_id;
      console.log(`✓ Session created: ${this.sessionId}`);
      return this.sessionId;
    } else {
      throw new Error(`Failed to create session: ${response.data.error}`);
    }
  }

  submitQuery(prompt) {
    if (!this.sessionId) {
      throw new Error('No active session. Call createSession() first.');
    }
    
    console.log(`\n📝 Submitting query: ${prompt}\n`);
    this.socket.emit('query', {
      prompt: prompt,
      session_id: this.sessionId
    });
  }

  async getTools() {
    const response = await axios.get(`${this.apiUrl}/tools`);
    
    if (response.data.success) {
      return response.data.tools;
    } else {
      throw new Error(`Failed to get tools: ${response.data.error}`);
    }
  }

  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
    }
  }
}

async function main() {
  const client = new AgentClient();
  
  try {
    // Connect to server
    await client.connect();
    
    // Create a session
    await client.createSession();
    
    // Submit a query
    client.submitQuery('Calculate profit margins from data/ecommerce_products.csv');
    
    // Wait for processing to complete
    await new Promise(resolve => setTimeout(resolve, 10000));
    
    // Get list of available tools
    console.log('\n📚 Available tools:');
    const tools = await client.getTools();
    tools.slice(0, 5).forEach(tool => {
      console.log(`  - ${tool.name}: ${tool.docstring.substring(0, 60)}...`);
    });
    
  } finally {
    client.disconnect();
  }
}

main().catch(console.error);
```

### Expected Output

```
✓ Connected to agent
✓ Server confirmed: Connected to agent
✓ Available tools: 15
✓ Session created: 550e8400-e29b-41d4-a716-446655440000

📝 Submitting query: Calculate profit margins from data/ecommerce_products.csv

  🔍 Searching for existing tool...
  ✓ Found tool: calculate_profit_margins (similarity: 0.95)
  ⚙️  Executing: calculate_profit_margins
  ✓ Execution complete

============================================================
✓ Query completed successfully!

Response: Profit margins calculated successfully. Average margin: 42.5%

Metadata:
  - Tool: calculate_profit_margins
  - Synthesized: False
============================================================

📚 Available tools:
  - calculate_profit_margins: Calculate profit margins from product...
  - analyze_sales_data: Analyze sales data and generate insights...
  - generate_report: Generate formatted reports from data...
```

---

## Example 2: Tool Synthesis Workflow

This example demonstrates how to explicitly request tool synthesis and monitor the 5-stage TDD pipeline.

### Python Implementation

```python
import requests
import socketio
import time
from typing import Dict, List

class SynthesisMonitor:
    """Monitor tool synthesis progress"""
    
    def __init__(self, base_url: str = "http://localhost:5001"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.session_id = None
        self.sio = socketio.Client()
        self.synthesis_stages = []
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Configure Socket.IO event handlers for synthesis monitoring"""
        
        @self.sio.on('connect')
        def on_connect():
            print("✓ Connected to agent\n")
        
        @self.sio.on('agent_event')
        def on_agent_event(event):
            event_type = event['event_type']
            data = event['data']
            
            if event_type == 'entering_synthesis_mode':
                print("🔨 TOOL SYNTHESIS INITIATED")
                print("="*60)
            
            elif event_type == 'synthesis_step':
                step = data['step']
                status = data['status']
                
                stage_info = {
                    'step': step,
                    'status': status,
                    'timestamp': time.time()
                }
                
                if 'data' in data:
                    stage_info['data'] = data['data']
                if 'error' in data:
                    stage_info['error'] = data['error']
                
                self.synthesis_stages.append(stage_info)
                
                # Display stage progress
                stage_emoji = {
                    'specification': '📋',
                    'tests': '🧪',
                    'implementation': '💻',
                    'verification': '✅',
                    'registration': '📦'
                }
                
                emoji = stage_emoji.get(step, '⚙️')
                
                if status == 'in_progress':
                    print(f"{emoji} Stage {len(self.synthesis_stages)}: {step.upper()}")
                    print(f"   Status: In Progress...")
                
                elif status == 'complete':
                    print(f"   Status: ✓ Complete")
                    if 'data' in data:
                        if 'test_count' in data['data']:
                            print(f"   Tests generated: {data['data']['test_count']}")
                        elif 'function_name' in data['data']:
                            print(f"   Function: {data['data']['function_name']}")
                        elif 'tests_passed' in data['data']:
                            print(f"   Tests passed: {data['data']['tests_passed']}")
                        elif 'tool_name' in data['data']:
                            print(f"   Tool registered: {data['data']['tool_name']}")
                    print()
                
                elif status == 'failed':
                    print(f"   Status: ✗ Failed")
                    if 'error' in data:
                        print(f"   Error: {data['error']}")
                    print()
                
                elif status == 'warning':
                    print(f"   Status: ⚠️  Warning")
                    if 'error' in data:
                        print(f"   Message: {data['error']}")
                    print()
            
            elif event_type == 'synthesis_successful':
                print("="*60)
                print(f"✓ SYNTHESIS SUCCESSFUL: {data['tool_name']}")
                if data.get('experimental'):
                    print("⚠️  Note: Tool registered as experimental (tests failed)")
                print("="*60)
            
            elif event_type == 'synthesis_failed':
                print("="*60)
                print(f"✗ SYNTHESIS FAILED at stage: {data['step']}")
                print(f"Error: {data['error']}")
                print("="*60)
        
        @self.sio.on('query_complete')
        def on_query_complete(result):
            print("\n" + "="*60)
            print("FINAL RESULT")
            print("="*60)
            if result['success']:
                print(f"✓ Success: {result['response']}")
                print(f"\nTool: {result['metadata']['tool_name']}")
                print(f"Synthesized: {result['metadata']['synthesized']}")
                if result['metadata']['tool_result']:
                    print(f"Result: {result['metadata']['tool_result']}")
            else:
                print(f"✗ Failed: {result['response']}")
            print("="*60)
    
    def connect(self):
        """Connect to the agent server"""
        self.sio.connect(self.base_url)
        time.sleep(0.5)
    
    def disconnect(self):
        """Disconnect from the agent server"""
        self.sio.disconnect()
    
    def create_session(self) -> str:
        """Create a new session"""
        response = requests.post(f"{self.api_url}/session")
        response.raise_for_status()
        data = response.json()
        
        if data['success']:
            self.session_id = data['session_id']
            return self.session_id
        else:
            raise Exception(f"Failed to create session: {data['error']}")
    
    def request_synthesis(self, prompt: str):
        """Request synthesis of a new tool"""
        if not self.session_id:
            raise Exception("No active session. Call create_session() first.")
        
        # Use explicit synthesis trigger phrase
        synthesis_prompt = f"Create a new function to {prompt}"
        
        print(f"📝 Requesting synthesis: {synthesis_prompt}\n")
        self.sio.emit('query', {
            'prompt': synthesis_prompt,
            'session_id': self.session_id
        })
    
    def get_synthesis_summary(self) -> Dict:
        """Get summary of synthesis stages"""
        return {
            'total_stages': len(self.synthesis_stages),
            'stages': self.synthesis_stages,
            'successful': all(s['status'] in ['complete', 'warning'] for s in self.synthesis_stages)
        }


def main():
    """Example 2: Tool Synthesis Workflow"""
    
    monitor = SynthesisMonitor()
    
    try:
        # Connect to server
        monitor.connect()
        
        # Create a session
        monitor.create_session()
        
        # Request synthesis of a new tool
        monitor.request_synthesis(
            "calculate the Fibonacci sequence up to n terms"
        )
        
        # Wait for synthesis to complete
        time.sleep(15)
        
        # Get synthesis summary
        summary = monitor.get_synthesis_summary()
        print(f"\n📊 Synthesis Summary:")
        print(f"   Total stages: {summary['total_stages']}")
        print(f"   Successful: {summary['successful']}")
        
    finally:
        monitor.disconnect()


if __name__ == "__main__":
    main()
```

### Expected Output

```
✓ Connected to agent

📝 Requesting synthesis: Create a new function to calculate the Fibonacci sequence up to n terms

🔨 TOOL SYNTHESIS INITIATED
============================================================
📋 Stage 1: SPECIFICATION
   Status: In Progress...
   Status: ✓ Complete

🧪 Stage 2: TESTS
   Status: In Progress...
   Status: ✓ Complete
   Tests generated: 5

💻 Stage 3: IMPLEMENTATION
   Status: In Progress...
   Status: ✓ Complete
   Function: calculate_fibonacci

✅ Stage 4: VERIFICATION
   Status: In Progress...
   Status: ✓ Complete
   Tests passed: True

📦 Stage 5: REGISTRATION
   Status: In Progress...
   Status: ✓ Complete
   Tool registered: calculate_fibonacci

============================================================
✓ SYNTHESIS SUCCESSFUL: calculate_fibonacci
============================================================

============================================================
FINAL RESULT
============================================================
✓ Success: Tool 'calculate_fibonacci' created successfully!
Tool: calculate_fibonacci
Synthesized: True
Result: [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]
============================================================

📊 Synthesis Summary:
   Total stages: 5
   Successful: True
```

---

## Example 3: Multi-Tool Composition

This example demonstrates how to submit complex queries that require multiple tools working together.

### Python Implementation

```python
import requests
import socketio
import time
from typing import List, Dict

class WorkflowClient:
    """Client for monitoring multi-tool workflows"""
    
    def __init__(self, base_url: str = "http://localhost:5001"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.session_id = None
        self.sio = socketio.Client()
        self.workflow_steps = []
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Configure Socket.IO event handlers for workflow monitoring"""
        
        @self.sio.on('connect')
        def on_connect():
            print("✓ Connected to agent\n")
        
        @self.sio.on('agent_event')
        def on_agent_event(event):
            event_type = event['event_type']
            data = event['data']
            
            if event_type == 'plan_complete':
                print("📋 EXECUTION PLAN")
                print("="*60)
                print(f"Strategy: {data['strategy']}")
                print(f"Reasoning: {data['reasoning']}")
                print("="*60 + "\n")
            
            elif event_type == 'workflow_start':
                print("🔄 MULTI-TOOL WORKFLOW INITIATED")
                print("="*60)
                print(f"Total steps: {data['total_steps']}")
                print(f"Sub-tasks: {', '.join(data['sub_tasks'])}")
                print("="*60 + "\n")
            
            elif event_type == 'workflow_step':
                step_num = data['step']
                total = data['total']
                task = data['task']
                status = data['status']
                
                step_info = {
                    'step': step_num,
                    'task': task,
                    'status': status,
                    'timestamp': time.time()
                }
                self.workflow_steps.append(step_info)
                
                print(f"Step {step_num}/{total}: {task}")
                print(f"  Status: {status}")
            
            elif event_type == 'tool_found':
                print(f"  ✓ Found tool: {data['tool_name']}")
            
            elif event_type == 'executing':
                print(f"  ⚙️  Executing: {data['tool_name']}")
            
            elif event_type == 'execution_complete':
                print(f"  ✓ Complete")
                if 'result' in data:
                    result_preview = str(data['result'])[:100]
                    print(f"  Result: {result_preview}...")
                print()
            
            elif event_type == 'workflow_complete':
                print("="*60)
                print(f"✓ WORKFLOW COMPLETE")
                print(f"Total steps: {data['total_steps']}")
                print(f"Successful steps: {data['successful_steps']}")
                print("="*60 + "\n")
            
            elif event_type == 'composite_created':
                print("🎯 COMPOSITE TOOL CREATED")
                print(f"Name: {data['composite_name']}")
                print(f"Components: {', '.join(data['component_tools'])}")
                print()
        
        @self.sio.on('query_complete')
        def on_query_complete(result):
            print("="*60)
            print("FINAL RESULT")
            print("="*60)
            if result['success']:
                print(f"✓ Success!")
                print(f"\nResponse:\n{result['response']}")
            else:
                print(f"✗ Failed: {result['response']}")
            print("="*60)
    
    def connect(self):
        """Connect to the agent server"""
        self.sio.connect(self.base_url)
        time.sleep(0.5)
    
    def disconnect(self):
        """Disconnect from the agent server"""
        self.sio.disconnect()
    
    def create_session(self) -> str:
        """Create a new session"""
        response = requests.post(f"{self.api_url}/session")
        response.raise_for_status()
        data = response.json()
        
        if data['success']:
            self.session_id = data['session_id']
            return self.session_id
        else:
            raise Exception(f"Failed to create session: {data['error']}")
    
    def submit_complex_query(self, prompt: str):
        """Submit a complex query requiring multiple tools"""
        if not self.session_id:
            raise Exception("No active session. Call create_session() first.")
        
        print(f"📝 Submitting complex query:\n   {prompt}\n")
        self.sio.emit('query', {
            'prompt': prompt,
            'session_id': self.session_id
        })
    
    def get_workflow_patterns(self, min_frequency: int = 2) -> List[Dict]:
        """Get detected workflow patterns"""
        response = requests.get(
            f"{self.api_url}/analytics/patterns",
            params={'min_frequency': min_frequency, 'limit': 10}
        )
        response.raise_for_status()
        data = response.json()
        
        if data['success']:
            return data['patterns']
        else:
            raise Exception(f"Failed to get patterns: {data['error']}")
    
    def get_tool_relationships(self, tool_name: str = None) -> List[Dict]:
        """Get tool relationship analytics"""
        params = {}
        if tool_name:
            params['tool_name'] = tool_name
        
        response = requests.get(
            f"{self.api_url}/analytics/relationships",
            params=params
        )
        response.raise_for_status()
        data = response.json()
        
        if data['success']:
            return data['relationships']
        else:
            raise Exception(f"Failed to get relationships: {data['error']}")


def main():
    """Example 3: Multi-Tool Composition"""
    
    client = WorkflowClient()
    
    try:
        # Connect to server
        client.connect()
        
        # Create a session
        client.create_session()
        
        # Submit a complex query requiring multiple tools
        client.submit_complex_query(
            "Load the sales data from data/sales.csv, calculate the profit margins, "
            "identify the top 10 products by margin, and generate a summary report"
        )
        
        # Wait for workflow to complete
        time.sleep(20)
        
        # Get workflow patterns
        print("\n📊 Detected Workflow Patterns:")
        patterns = client.get_workflow_patterns()
        for pattern in patterns[:3]:
            print(f"\n  Pattern: {pattern['pattern_name']}")
            print(f"  Tools: {' → '.join(pattern['tool_sequence'])}")
            print(f"  Frequency: {pattern['frequency']}")
            print(f"  Success rate: {pattern['avg_success_rate']:.1%}")
        
        # Get tool relationships
        print("\n🔗 Tool Relationships:")
        relationships = client.get_tool_relationships()
        for rel in relationships[:5]:
            print(f"  {rel['tool_a']} ↔ {rel['tool_b']} "
                  f"(confidence: {rel['confidence_score']:.2f})")
        
    finally:
        client.disconnect()


if __name__ == "__main__":
    main()
```

### Expected Output

```
✓ Connected to agent

📝 Submitting complex query:
   Load the sales data from data/sales.csv, calculate the profit margins, identify the top 10 products by margin, and generate a summary report

📋 EXECUTION PLAN
============================================================
Strategy: multi_tool_sequential
Reasoning: Query requires multiple sequential operations on data
============================================================

🔄 MULTI-TOOL WORKFLOW INITIATED
============================================================
Total steps: 4
Sub-tasks: load_csv_data, calculate_profit_margins, filter_top_products, generate_summary_report
============================================================

Step 1/4: load_csv_data
  Status: executing
  ✓ Found tool: load_csv_data
  ⚙️  Executing: load_csv_data
  ✓ Complete
  Result: DataFrame with 500 rows loaded...

Step 2/4: calculate_profit_margins
  Status: executing
  ✓ Found tool: calculate_profit_margins
  ⚙️  Executing: calculate_profit_margins
  ✓ Complete
  Result: Profit margins calculated for 500 products...

Step 3/4: filter_top_products
  Status: executing
  ✓ Found tool: filter_top_products
  ⚙️  Executing: filter_top_products
  ✓ Complete
  Result: Top 10 products identified...

Step 4/4: generate_summary_report
  Status: executing
  ✓ Found tool: generate_summary_report
  ⚙️  Executing: generate_summary_report
  ✓ Complete
  Result: Summary report generated...

============================================================
✓ WORKFLOW COMPLETE
Total steps: 4
Successful steps: 4
============================================================

🎯 COMPOSITE TOOL CREATED
Name: analyze_sales_and_report
Components: load_csv_data, calculate_profit_margins, filter_top_products, generate_summary_report

============================================================
FINAL RESULT
============================================================
✓ Success!

Response:
Sales Analysis Complete

Top 10 Products by Profit Margin:
1. Product A: 67.5%
2. Product B: 62.3%
3. Product C: 58.9%
...

Average margin across all products: 42.5%
Total revenue: $1,250,000
Total profit: $531,250

Full report saved to: reports/sales_analysis_2025-11-04.pdf
============================================================

📊 Detected Workflow Patterns:

  Pattern: sales_analysis_workflow
  Tools: load_csv_data → calculate_profit_margins → filter_top_products → generate_summary_report
  Frequency: 12
  Success rate: 91.7%

  Pattern: data_processing_pipeline
  Tools: load_csv_data → calculate_profit_margins
  Frequency: 28
  Success rate: 95.0%

  Pattern: reporting_workflow
  Tools: filter_top_products → generate_summary_report
  Frequency: 15
  Success rate: 93.3%

🔗 Tool Relationships:
  load_csv_data ↔ calculate_profit_margins (confidence: 0.89)
  calculate_profit_margins ↔ filter_top_products (confidence: 0.76)
  filter_top_products ↔ generate_summary_report (confidence: 0.82)
  load_csv_data ↔ generate_summary_report (confidence: 0.65)
  calculate_profit_margins ↔ generate_summary_report (confidence: 0.71)
```

---

## Best Practices

### 1. Session Management

Always create a session before submitting queries to maintain conversational context:

```python
# Create session once
session_id = client.create_session()

# Reuse session for multiple queries
client.submit_query("First query", session_id)
client.submit_query("Follow-up query", session_id)
```

### 2. Error Handling

Implement robust error handling for network issues and API errors:

```python
try:
    result = client.submit_query(prompt)
except requests.exceptions.ConnectionError:
    print("Failed to connect to server")
except requests.exceptions.Timeout:
    print("Request timed out")
except Exception as e:
    print(f"Unexpected error: {e}")
```

### 3. Event Monitoring

Use callbacks to monitor progress and provide user feedback:

```python
def progress_callback(event_type, data):
    if event_type == 'synthesis_step':
        # Update progress bar
        update_progress(data['step'], data['status'])
    elif event_type == 'error':
        # Show error notification
        show_error(data['error'])
```

### 4. Resource Cleanup

Always disconnect Socket.IO connections when done:

```python
try:
    client.connect()
    # ... perform operations ...
finally:
    client.disconnect()
```

### 5. Rate Limiting

Implement client-side rate limiting to avoid overwhelming the server:

```python
import time

class RateLimitedClient:
    def __init__(self, max_requests_per_minute=10):
        self.max_requests = max_requests_per_minute
        self.requests = []
    
    def submit_query(self, prompt):
        # Remove requests older than 1 minute
        current_time = time.time()
        self.requests = [t for t in self.requests if current_time - t < 60]
        
        # Check rate limit
        if len(self.requests) >= self.max_requests:
            wait_time = 60 - (current_time - self.requests[0])
            time.sleep(wait_time)
        
        # Submit query
        self.requests.append(current_time)
        return super().submit_query(prompt)
```

---

## Troubleshooting

### Connection Issues

```python
# Test connection
try:
    response = requests.get(f"{base_url}/api/tools", timeout=5)
    print(f"Server status: {response.status_code}")
except requests.exceptions.ConnectionError:
    print("Cannot connect to server. Is it running?")
```

### Session Expiration

```python
# Check if session is still valid
def is_session_valid(session_id):
    try:
        response = requests.get(
            f"{api_url}/session/{session_id}/messages",
            params={'limit': 1}
        )
        return response.status_code == 200
    except:
        return False
```

### Tool Not Found

```python
# Search for similar tools
def find_similar_tools(query, threshold=0.5):
    tools = client.get_tools()
    # Implement similarity search
    similar = [t for t in tools if similarity(query, t['docstring']) > threshold]
    return similar
```
