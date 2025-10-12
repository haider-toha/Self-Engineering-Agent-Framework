"""
Seed Tools - Populate the registry with initial capabilities
"""

import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.capability_registry import CapabilityRegistry


def seed_tools():
    """Seed the registry with initial tools"""
    registry = CapabilityRegistry()
    
    tools_to_seed = [
        {
            "name": "calculate_percentage",
            "code_file": "tools/calculate_percentage.py",
            "test_file": "tools/test_calculate_percentage.py",
            "docstring": "Calculate percentage values. Find what percentage one number is of another, or calculate a percentage of a number. Examples: 'What is 25% of 80?', 'Calculate 15 percent of 300', 'Find percentage value'. Takes a base number and percentage, returns the calculated result."
        },
        {
            "name": "celsius_to_fahrenheit",
            "code_file": "tools/celsius_to_fahrenheit.py",
            "test_file": "tools/test_celsius_to_fahrenheit.py",
            "docstring": "Convert temperature from Celsius to Fahrenheit. Temperature conversion between metric and imperial units. Examples: 'Convert 20 degrees Celsius to Fahrenheit', 'What is 100C in Fahrenheit?', 'Temperature conversion from Celsius'. Takes Celsius temperature and returns Fahrenheit equivalent."
        }
    ]
    
    print("Seeding capability registry with initial tools...\n")
    
    for tool_info in tools_to_seed:
        # Check if tool already exists
        existing = registry.get_tool_by_name(tool_info["name"])
        if existing:
            print(f"- Tool '{tool_info['name']}' already exists, skipping...")
            continue
        
        # Read code and tests
        try:
            with open(tool_info["code_file"], 'r', encoding='utf-8') as f:
                code = f.read()
            
            with open(tool_info["test_file"], 'r', encoding='utf-8') as f:
                tests = f.read()
            
            # Add to registry
            metadata = registry.add_tool(
                name=tool_info["name"],
                code=code,
                tests=tests,
                docstring=tool_info["docstring"]
            )
            
            print(f"+ Added tool: {tool_info['name']}")
            
        except Exception as e:
            print(f"X Failed to add tool '{tool_info['name']}': {str(e)}")
    
    print(f"\nTotal tools in registry: {registry.count_tools()}")
    print("Seeding complete!")


if __name__ == "__main__":
    seed_tools()

