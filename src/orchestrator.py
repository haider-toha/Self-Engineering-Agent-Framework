"""
Agent Orchestrator - Central decision-making component that coordinates all subsystems
"""

import time
import hashlib
import json
from typing import Dict, Any, Optional, Callable
from src.capability_registry import CapabilityRegistry
from src.synthesis_engine import CapabilitySynthesisEngine
from src.executor import ToolExecutor
from src.response_synthesizer import ResponseSynthesizer
from src.llm_client import LLMClient
from src.sandbox import SecureSandbox
from src.workflow_tracker import WorkflowTracker
from src.query_planner import QueryPlanner
from src.composition_planner import CompositionPlanner

# NEW: Memory manager for conversational context
from src.session_memory import SessionMemoryManager

# NEW: Self-learning components
from src.policy_store import PolicyStore
from src.skill_graph import SkillGraph
from src.reflection_engine import ReflectionEngine


class AgentOrchestrator:
    """
    The brain of the agent. Coordinates the entire flow from user request to response.
    
    Enhanced Flow:
    1. Analyze query complexity and check for existing compositions/patterns
    2. For simple queries: search for single tool and execute
    3. For complex queries: plan and execute multi-tool workflows
    4. Track executions and learn patterns
    5. Synthesize natural language response
    """
    
    def __init__(
        self,
        registry: CapabilityRegistry = None,
        synthesis_engine: CapabilitySynthesisEngine = None,
        executor: ToolExecutor = None,
        synthesizer: ResponseSynthesizer = None,
        workflow_tracker: WorkflowTracker = None,
        query_planner: QueryPlanner = None,
        composition_planner: CompositionPlanner = None,
        memory_manager: SessionMemoryManager = None
    ):
        """
        Initialize the orchestrator
        
        Args:
            registry: Capability registry
            synthesis_engine: Synthesis engine for creating new tools
            executor: Tool executor
            synthesizer: Response synthesizer
            workflow_tracker: Workflow tracking component
            query_planner: Query analysis and planning component
            composition_planner: Multi-tool composition component
        """
        # Initialize shared components
        llm_client = LLMClient()
        sandbox = SecureSandbox()
        
        # Initialize core subsystems
        self.registry = registry or CapabilityRegistry()
        self.synthesis_engine = synthesis_engine or CapabilitySynthesisEngine(
            llm_client=llm_client,
            sandbox=sandbox,
            registry=self.registry
        )
        self.executor = executor or ToolExecutor(llm_client=llm_client)
        self.synthesizer = synthesizer or ResponseSynthesizer(llm_client=llm_client)
        
        # Initialize workflow and composition components
        self.workflow_tracker = workflow_tracker or WorkflowTracker()
        self.query_planner = query_planner or QueryPlanner(
            llm_client=llm_client,
            registry=self.registry
        )
        self.composition_planner = composition_planner or CompositionPlanner(
            registry=self.registry,
            executor=self.executor,
            llm_client=llm_client
        )
        
        # NEW: Initialize self-learning components
        self.policy_store = PolicyStore()
        self.skill_graph = SkillGraph()
        self.reflection_engine = ReflectionEngine(
            llm_client=llm_client,
            sandbox=sandbox,
            registry=self.registry
        )
        
        # Store shared components for reflection engine
        self.llm_client = llm_client
        self.sandbox = sandbox

        # Conversational memory
        self.memory_manager = memory_manager or SessionMemoryManager()
    
    def process_request(
        self,
        user_prompt: str,
        session_id: Optional[str] = None,
        callback: Optional[Callable[[str, Any], None]] = None
    ) -> Dict[str, Any]:
        """
        Process a user request from start to finish with enhanced workflow capabilities
        
        Args:
            user_prompt: User's natural language request
            callback: Optional callback function(event_type, data) for progress updates
            
        Returns:
            Dictionary with 'success', 'response', and optional metadata
        """
        
        def emit(event_type: str, data: Any = None):
            """Helper to emit events via callback"""
            if callback:
                callback(event_type, data)
        
        start_time = time.time()
        active_session_id = None
        agent_prompt = user_prompt

        # Optional conversational context
        if session_id:
            active_session_id = self.memory_manager.start_session(session_id)
            agent_prompt = self.memory_manager.build_prompt_with_context(
                active_session_id,
                user_prompt
            )
            # Persist the incoming user message immediately so the next turn has context
            self.memory_manager.append_message(active_session_id, "user", user_prompt)
        else:
            active_session_id = None

        # Start workflow tracker session (ties tool executions to the UI session when provided)
        self.workflow_tracker.start_session(active_session_id)
        
        try:
            # Step 0: Cleanup orphaned tools
            removed_count = self.registry.cleanup_orphaned_tools()
            if removed_count > 0:
                emit("orphans_cleaned", {"count": removed_count})
            
            # Step 1: Plan the execution strategy
            emit("planning_query", {"query": user_prompt})
            execution_plan = self.query_planner.plan_execution(agent_prompt)
            
            emit("plan_complete", {
                "strategy": execution_plan['strategy'],
                "reasoning": execution_plan.get('reasoning')
            })
            
            # Route based on execution strategy
            strategy = execution_plan['strategy']

            if strategy == 'force_synthesis':
                # User explicitly requested to create a new tool
                # BUT check if a similar tool already exists first
                existing_tool = self.registry.search_tool(agent_prompt, threshold=0.65)

                if existing_tool:
                    # Tool already exists - use it instead of re-creating
                    emit("tool_found", {
                        "tool_name": existing_tool['name'],
                        "similarity": existing_tool['similarity_score'],
                        "message": "Similar tool already exists, using it instead of creating new one"
                    })

                    # Execute the existing tool
                    emit("executing", {"tool_name": existing_tool['name']})
                    execution_result = self.executor.execute_with_retry(
                        tool_info=existing_tool,
                        user_prompt=agent_prompt
                    )

                    if execution_result['success']:
                        final_response = str(execution_result['result'])
                        result = {
                            "success": True,
                            "response": final_response,
                            "tool_name": existing_tool['name'],
                            "tool_result": execution_result['result'],
                            "reused_existing": True
                        }
                    else:
                        # Existing tool failed - fall through to synthesis
                        emit("tool_found", {"message": "Existing tool failed, creating new one"})
                        existing_tool = None

                if not existing_tool:
                    # No existing tool found or it failed - create new one
                    emit("no_tool_found", {"query": user_prompt})
                    emit("entering_synthesis_mode", {})

                    # Synthesize new capability
                    synthesis_result = self.synthesis_engine.synthesize_capability(
                        user_prompt=agent_prompt,
                        callback=callback
                    )

                    if not synthesis_result['success']:
                        error = synthesis_result.get('error', 'Unknown error')
                        emit("synthesis_failed", {
                            "error": error,
                            "step": synthesis_result.get('step', 'unknown')
                        })
                        error_response = self.synthesizer.synthesize_error(
                            user_prompt,
                            f"Failed to create new capability: {error}"
                        )
                        result = {
                            "success": False,
                            "response": error_response,
                            "error": error,
                            "synthesis_failed": True
                        }
                    else:
                        # Synthesis successful - now execute the new tool
                        tool_name = synthesis_result['tool_name']
                        tests_verified = synthesis_result.get('tests_verified', False)

                        emit("synthesis_successful", {
                            "tool_name": tool_name,
                            "experimental": not tests_verified
                        })

                        if not tests_verified:
                            emit("tool_experimental_warning", {
                                "message": f"Note: '{tool_name}' was registered as experimental (tests failed during verification)"
                            })

                        new_tool_info = self.registry.get_tool_by_name(tool_name)

                        emit("executing", {"tool_name": tool_name})

                        execution_result = self.executor.execute_with_retry(
                            tool_info=new_tool_info,
                            user_prompt=agent_prompt
                        )

                        if not execution_result['success']:
                            error = execution_result['error']

                            # If execution failed due to missing arguments in a synthesis request,
                            # treat it as successful creation (just don't execute)
                            if execution_result.get("error_type") == "ArgumentError":
                                emit("execution_skipped", {
                                    "reason": "Tool created successfully but requires explicit arguments for execution"
                                })

                                result = {
                                    "success": True,
                                    "response": f"Tool '{tool_name}' created successfully! It's ready to use when you provide the required arguments.",
                                    "tool_name": tool_name,
                                    "synthesized": True,
                                    "execution_skipped": True
                                }
                            else:
                                # Other execution errors are real failures
                                emit("execution_failed", {"error": error})
                                error_response = self.synthesizer.synthesize_error(user_prompt, error)
                                result = {
                                    "success": False,
                                    "response": error_response,
                                    "error": error,
                                    "tool_name": tool_name,
                                    "synthesized": True
                                }
                        else:
                            tool_result = execution_result['result']

                            emit("execution_complete", {
                                "tool_name": tool_name,
                                "result": str(tool_result)
                            })

                            emit("synthesizing_response", {})
                            final_response = str(tool_result)

                            emit("complete", {"response": final_response})

                            result = {
                                "success": True,
                                "response": final_response,
                                "tool_name": tool_name,
                                "tool_result": tool_result,
                                "synthesized": True
                            }

            elif strategy == 'composite_tool':
                # Use existing composite tool
                result = self._execute_composite_tool(
                    execution_plan['composite_tool'],
                    agent_prompt,
                    emit,
                    start_time,
                    callback
                )
            
            elif strategy == 'workflow_pattern':
                # Execute known workflow pattern
                result = self._execute_workflow_pattern(
                    execution_plan['pattern'],
                    agent_prompt,
                    emit,
                    start_time,
                    callback
                )
            
            elif strategy in ['multi_tool_composition', 'multi_tool_sequential']:
                # Execute multi-tool workflow
                result = self._execute_multi_tool_workflow(
                    execution_plan,
                    agent_prompt,
                    emit,
                    start_time,
                    callback
                )
            
            else:
                # Single tool execution (default/fallback)
                result = self._execute_single_tool(
                    agent_prompt,
                    emit,
                    start_time,
                    callback
                )

            if isinstance(result, dict) and active_session_id:
                if result.get('response'):
                    self.memory_manager.append_message(
                        active_session_id,
                        "assistant",
                        result['response']
                    )
                result['session_id'] = active_session_id

            return result
        
        except Exception as e:
            self.workflow_tracker.end_session()
            emit("error", {"error": str(e)})
            error_response = self.synthesizer.synthesize_error(
                user_prompt,
                f"An unexpected error occurred: {str(e)}"
            )
            if active_session_id:
                self.memory_manager.append_message(active_session_id, "assistant", error_response)
            return {
                "success": False,
                "response": error_response,
                "error": str(e),
                "session_id": active_session_id
            }
    
    def _execute_single_tool(
        self,
        user_prompt: str,
        emit: Callable,
        start_time: float,
        callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """Execute a single tool (original behavior with caching and reflection)"""
        try:
            # NEW: Get policy-driven threshold
            threshold_policy = self.policy_store.get_policy(
                "retrieval_similarity_threshold",
                default={"threshold": 0.7, "rerank": True}
            )
            
            # Search for existing capability with policy-driven settings
            emit("searching", {"query": user_prompt})
            
            tool_info = self.registry.search_tool(
                user_prompt,
                threshold=threshold_policy.get("threshold", 0.7),
                rerank=threshold_policy.get("rerank", True)
            )
            
            # Step 2a: If a tool is found, try to execute it
            if tool_info:
                emit("tool_found", {
                    "tool_name": tool_info['name'],
                    "similarity": tool_info['similarity_score']
                })
                
                # NEW: Extract arguments for cache key
                signature = self.executor.extract_function_signature(tool_info['code'])
                arguments = self.llm_client.extract_arguments(user_prompt, signature)
                
                # NEW: Check cache before execution
                cached_result = self.skill_graph.check_cache(tool_info['name'], arguments)
                if cached_result:
                    emit("cache_hit", {"tool": tool_info['name']})
                    
                    # Use cached result - return raw data
                    final_response = str(cached_result)
                    self.workflow_tracker.end_session()
                    
                    return {
                        "success": True,
                        "result": cached_result,
                        "response": final_response,
                        "tool_name": tool_info['name'],
                        "cached": True,
                        "execution_time": 0
                    }
                
                emit("executing", {"tool_name": tool_info['name']})
                exec_start = time.time()
                
                # Execute with pre-extracted arguments
                execution_result = self.executor.execute_with_retry(
                    tool_info=tool_info,
                    user_prompt=user_prompt
                )
                
                # If execution is successful, we are done
                if execution_result['success']:
                    tool_result = execution_result['result']
                    execution_time_ms = int((time.time() - exec_start) * 1000)
                    
                    # NEW: Cache the result
                    self.skill_graph.cache_result(
                        tool_info['name'],
                        arguments,
                        tool_result,
                        execution_time_ms
                    )
                    
                    # Log execution
                    self.workflow_tracker.log_execution(
                        tool_name=tool_info['name'],
                        inputs=arguments,
                        outputs=tool_result,
                        success=True,
                        execution_time_ms=execution_time_ms,
                        user_prompt=user_prompt
                    )
                    
                    emit("execution_complete", {
                        "tool_name": tool_info['name'],
                        "result": str(tool_result)
                    })
                    
                    emit("synthesizing_response", {})
                    # Return raw data instead of natural language synthesis
                    final_response = str(tool_result)
                    emit("complete", {"response": final_response})
                    
                    self.workflow_tracker.end_session()
                    
                    return {
                        "success": True,
                        "response": final_response,
                        "tool_name": tool_info['name'],
                        "tool_result": tool_result,
                        "synthesized": False
                    }

                # If execution failed because of an argument mismatch, invalidate the tool and proceed to synthesis
                elif execution_result.get("error_type") == "ArgumentError":
                    emit("tool_mismatch", {
                        "tool_name": tool_info['name'],
                        "error": "Tool found, but arguments in your prompt do not match its requirements. Attempting to synthesize a new tool."
                    })
                    tool_info = None  # Invalidate the found tool to trigger synthesis
                
                # For any other execution error, trigger reflection
                else:
                    error = execution_result['error']
                    emit("execution_failed", {"tool": tool_info['name'], "error": error})
                    
                    # NEW: Trigger reflection on failure
                    try:
                        analysis = self.reflection_engine.analyze_failure(
                            tool_name=tool_info['name'],
                            error_message=error,
                            inputs=arguments,
                            user_prompt=user_prompt
                        )
                        
                        emit("reflection_created", {
                            "reflection_id": analysis.get("reflection_id"),
                            "root_cause": analysis.get("root_cause", "Unknown")
                        })
                    except Exception as reflection_error:
                        print(f"Reflection failed: {reflection_error}")
                    
                    # Log failed execution
                    self.workflow_tracker.log_execution(
                        tool_name=tool_info['name'],
                        inputs=arguments,
                        outputs=None,
                        success=False,
                        execution_time_ms=int((time.time() - exec_start) * 1000),
                        user_prompt=user_prompt
                    )
                    
                    error_response = self.synthesizer.synthesize_error(user_prompt, error)
                    self.workflow_tracker.end_session()
                    
                    return {
                        "success": False,
                        "response": error_response,
                        "error": error,
                        "tool_name": tool_info['name']
                    }

            # Step 2b: If no tool was found OR it was a mismatch, enter synthesis mode
            if not tool_info:
                emit("no_tool_found", {"query": user_prompt})
                emit("entering_synthesis_mode", {})
                
                # Synthesize new capability
                synthesis_result = self.synthesis_engine.synthesize_capability(
                    user_prompt=user_prompt,
                    callback=callback
                )
                
                if not synthesis_result['success']:
                    error = synthesis_result.get('error', 'Unknown error')
                    emit("synthesis_failed", {
                        "error": error,
                        "step": synthesis_result.get('step', 'unknown')
                    })
                    error_response = self.synthesizer.synthesize_error(
                        user_prompt,
                        f"Failed to create new capability: {error}"
                    )
                    return {
                        "success": False,
                        "response": error_response,
                        "error": error,
                        "synthesis_failed": True
                    }
                
                # Synthesis successful - now execute the new tool
                tool_name = synthesis_result['tool_name']
                tests_verified = synthesis_result.get('tests_verified', False)

                emit("synthesis_successful", {
                    "tool_name": tool_name,
                    "experimental": not tests_verified
                })

                if not tests_verified:
                    emit("tool_experimental_warning", {
                        "message": f"Note: '{tool_name}' was registered as experimental (tests failed during verification)"
                    })

                new_tool_info = self.registry.get_tool_by_name(tool_name)
                
                emit("executing", {"tool_name": tool_name})
                
                execution_result = self.executor.execute_with_retry(
                    tool_info=new_tool_info,
                    user_prompt=user_prompt
                )
                
                if not execution_result['success']:
                    error = execution_result['error']
                    emit("execution_failed", {"error": error})
                    error_response = self.synthesizer.synthesize_error(user_prompt, error)
                    return {
                        "success": False,
                        "response": error_response,
                        "error": error,
                        "tool_name": tool_name,
                        "synthesized": True
                    }
                
                tool_result = execution_result['result']
                
                # Create concise summary for activity log
                result_summary = self._summarize_result(tool_result)
                
                emit("execution_complete", {
                    "tool_name": tool_name,
                    "result": result_summary
                })
                
                emit("synthesizing_response", {})
                # Return raw data instead of natural language synthesis  
                final_response = str(tool_result)
                
                emit("complete", {"response": final_response})
                
                return {
                    "success": True,
                    "response": final_response,
                    "tool_name": tool_name,
                    "tool_result": tool_result,
                    "synthesized": True
                }
        
        except Exception as e:
            self.workflow_tracker.end_session()
            emit("error", {"error": str(e)})
            error_response = self.synthesizer.synthesize_error(
                user_prompt,
                f"An unexpected error occurred: {str(e)}"
            )
            return {
                "success": False,
                "response": error_response,
                "error": str(e)
            }
    
    def _execute_composite_tool(
        self,
        composite_tool: Dict[str, Any],
        user_prompt: str,
        emit: Callable,
        start_time: float,
        callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """Execute an existing composite tool"""
        emit("using_composite_tool", {
            "tool_name": composite_tool['tool_name'],
            "component_tools": composite_tool['component_tools'],
            "similarity": composite_tool['similarity']
        })
        
        # Get the composite tool from registry
        tool_info = self.registry.get_tool_by_name(composite_tool['tool_name'])
        
        if not tool_info:
            return self._execute_single_tool(user_prompt, emit, start_time, callback)
        
        # Execute the composite tool
        execution_result = self.executor.execute_with_retry(
            tool_info=tool_info,
            user_prompt=user_prompt
        )
        
        if execution_result['success']:
            tool_result = execution_result['result']
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            self.workflow_tracker.log_execution(
                tool_name=composite_tool['tool_name'],
                inputs={},
                outputs=tool_result,
                success=True,
                execution_time_ms=execution_time_ms,
                user_prompt=user_prompt
            )
            
            # Return raw data instead of synthesized response
            final_response = str(tool_result)
            self.workflow_tracker.end_session()
            
            return {
                "success": True,
                "response": final_response,
                "tool_name": composite_tool['tool_name'],
                "tool_result": tool_result,
                "used_composite": True
            }
        else:
            # Fallback to single tool execution
            return self._execute_single_tool(user_prompt, emit, start_time, callback)
    
    def _summarize_result(self, result: Any) -> str:
        """
        Create a concise summary of tool execution result for activity logs
        
        Args:
            result: The result to summarize
            
        Returns:
            A concise string summary
        """
        if result is None:
            return "None"
        
        result_str = str(result)
        
        # If it's a list, show count and type info
        if isinstance(result, list):
            if len(result) == 0:
                return "Empty list"
            elif len(result) <= 3:
                return result_str
            else:
                # Show count and preview of first item
                first_item = str(result[0])[:100]
                if len(first_item) == 100:
                    first_item += "..."
                return f"List of {len(result)} items. First: {first_item}"
        
        # If it's a dict, show key count
        elif isinstance(result, dict):
            if len(result) <= 5:
                return result_str
            else:
                keys = list(result.keys())[:3]
                return f"Dict with {len(result)} keys: {keys}..."
        
        # For strings/numbers, truncate if too long
        elif len(result_str) > 200:
            return result_str[:200] + "..."
        
        return result_str
    
    def _execute_workflow_pattern(
        self,
        pattern: Dict[str, Any],
        user_prompt: str,
        emit: Callable,
        start_time: float,
        callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """Execute a known workflow pattern"""
        emit("using_workflow_pattern", {
            "pattern_name": pattern['pattern_name'],
            "tool_sequence": pattern['tool_sequence'],
            "similarity": pattern['similarity']
        })
        
        # Execute the pattern
        result = self.composition_planner.execute_pattern(
            pattern=pattern,
            user_prompt=user_prompt,
            callback=emit
        )
        
        if result['success']:
            # Log each tool execution
            for idx, tool_name in enumerate(result['tool_sequence']):
                self.workflow_tracker.log_execution(
                    tool_name=tool_name,
                    inputs={},
                    outputs=result['results'][idx] if idx < len(result['results']) else None,
                    success=True,
                    execution_time_ms=0,
                    user_prompt=user_prompt
                )
            
            # Create detailed context for response synthesis
            workflow_context = f"Used pattern '{pattern.get('pattern_name')}' - executed {len(result['tool_sequence'])} steps:\n"
            for idx, (tool_name, tool_result) in enumerate(zip(result['tool_sequence'], result['results']), 1):
                workflow_context += f"{idx}. {tool_name}: {tool_result}\n"
            workflow_context += f"Final result: {result['final_result']}"
            
            # Return raw data instead of synthesized response
            final_response = str(result['final_result'])
            self.workflow_tracker.end_session()
            
            return {
                "success": True,
                "response": final_response,
                "tool_sequence": result['tool_sequence'],
                "tool_result": result['final_result'],
                "used_pattern": True
            }
        else:
            # Fallback
            return self._execute_single_tool(user_prompt, emit, start_time, callback)
    
    def _execute_multi_tool_workflow(
        self,
        execution_plan: Dict[str, Any],
        user_prompt: str,
        emit: Callable,
        start_time: float,
        callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """Execute a multi-tool workflow"""
        sub_tasks = execution_plan['analysis']['sub_tasks']
        
        emit("multi_tool_workflow", {
            "num_tasks": len(sub_tasks),
            "requires_composition": execution_plan['analysis']['requires_composition']
        })
        
        # Execute the workflow
        result = self.composition_planner.execute_workflow(
            sub_tasks=sub_tasks,
            user_prompt=user_prompt,
            callback=emit
        )
        
        if result['success']:
            # Log each tool execution
            for idx, tool_name in enumerate(result['tool_sequence']):
                self.workflow_tracker.log_execution(
                    tool_name=tool_name,
                    inputs={},
                    outputs=result['results'][idx] if idx < len(result['results']) else None,
                    success=True,
                    execution_time_ms=0,
                    user_prompt=user_prompt
                )
            
            # Create detailed context for response synthesis
            workflow_context = f"Executed {len(result['tool_sequence'])} step workflow:\n"
            for idx, (tool_name, tool_result) in enumerate(zip(result['tool_sequence'], result['results']), 1):
                workflow_context += f"{idx}. {tool_name}: {tool_result}\n"
            workflow_context += f"Final result: {result['final_result']}"
            
            # Return raw data instead of synthesized response
            final_response = str(result['final_result'])
            self.workflow_tracker.end_session()
            
            return {
                "success": True,
                "response": final_response,
                "tool_sequence": result['tool_sequence'],
                "tool_result": result['final_result'],
                "multi_tool": True
            }
        elif result.get('needs_synthesis'):
            # One of the sub-tasks needs a new tool - synthesize it!
            step_failed = result['step_failed']
            failed_task = sub_tasks[step_failed - 1]['task']
            
            emit("workflow_step_synthesizing", {
                "step": step_failed,
                "task": failed_task
            })
            
            # Synthesize the missing tool
            emit("entering_synthesis_mode", {})
            synthesis_result = self.synthesis_engine.synthesize_capability(
                user_prompt=failed_task,
                callback=emit
            )
            
            if not synthesis_result['success']:
                error = synthesis_result.get('error', 'Unknown error')
                emit("synthesis_failed", {
                    "error": error,
                    "step": synthesis_result.get('step', 'unknown')
                })
                return {
                    "success": False,
                    "response": self.synthesizer.synthesize_error(
                        user_prompt,
                        f"Failed to create tool for workflow step {step_failed}: {error}"
                    ),
                    "error": error
                }
            
            # Tool synthesized! Retry the workflow
            emit("workflow_retry", {
                "reason": f"New tool '{synthesis_result['tool_name']}' created for step {step_failed}"
            })
            
            # Retry workflow execution
            retry_result = self.composition_planner.execute_workflow(
                sub_tasks=sub_tasks,
                user_prompt=user_prompt,
                callback=emit
            )
            
            if retry_result['success']:
                # Log executions
                for idx, tool_name in enumerate(retry_result['tool_sequence']):
                    self.workflow_tracker.log_execution(
                        tool_name=tool_name,
                        inputs={},
                        outputs=retry_result['results'][idx] if idx < len(retry_result['results']) else None,
                        success=True,
                        execution_time_ms=0,
                        user_prompt=user_prompt
                    )
                
                workflow_context = f"Executed {len(retry_result['tool_sequence'])} step workflow:\n"
                for idx, (tool_name, tool_result) in enumerate(zip(retry_result['tool_sequence'], retry_result['results']), 1):
                    workflow_context += f"{idx}. {tool_name}: {tool_result}\n"
                workflow_context += f"Final result: {retry_result['final_result']}"
                
                # Return raw data instead of synthesized response
                final_response = str(retry_result['final_result'])
                self.workflow_tracker.end_session()
                
                return {
                    "success": True,
                    "response": final_response,
                    "tool_sequence": retry_result['tool_sequence'],
                    "tool_result": retry_result['final_result'],
                    "multi_tool": True,
                    "synthesized_during_workflow": True
                }
            else:
                return {
                    "success": False,
                    "response": self.synthesizer.synthesize_error(user_prompt, retry_result.get('error', 'Workflow failed after synthesis')),
                    "error": retry_result.get('error')
                }
        else:
            return {
                "success": False,
                "response": self.synthesizer.synthesize_error(user_prompt, result.get('error', 'Workflow failed')),
                "error": result.get('error')
            }
    
    def get_all_tools(self):
        """Get list of all available tools"""
        return self.registry.get_all_tools()
    
    def get_tool_count(self):
        """Get the total number of available tools"""
        return self.registry.count_tools()


if __name__ == "__main__":
    # Simple test
    orchestrator = AgentOrchestrator()
    print(f"Agent Orchestrator initialized with {orchestrator.get_tool_count()} tools")
    
    # Test with a simple request
    def print_callback(event_type, data):
        print(f"[{event_type}] {data}")
    
    result = orchestrator.process_request(
        "What is 2 plus 2?",
        callback=print_callback
    )
    
    print(f"\nFinal response: {result['response']}")

