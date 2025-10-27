"""
Test Dataset Generator

Generates diverse test cases for comprehensive agent evaluation.
Creates queries spanning different:
- Complexity levels
- Domain areas
- Query types
- Edge cases
"""

import json
import random
from typing import List, Dict, Any
from dataclasses import dataclass, asdict


@dataclass
class TestCase:
    """Represents a single test case"""
    id: str
    query: str
    category: str
    complexity: str  # simple, medium, complex
    expected_behavior: str
    expected_answer: Any = None
    requires_synthesis: bool = False
    tags: List[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


class TestDatasetGenerator:
    """
    Generates comprehensive test datasets for agent evaluation.
    Covers various scenarios, complexities, and edge cases.
    """
    
    def __init__(self, seed: int = 42):
        """
        Initialize the test dataset generator
        
        Args:
            seed: Random seed for reproducibility
        """
        self.seed = seed
        random.seed(seed)
    
    def generate_full_dataset(
        self,
        num_simple: int = 20,
        num_medium: int = 15,
        num_complex: int = 10,
        include_edge_cases: bool = True
    ) -> List[TestCase]:
        """
        Generate a complete test dataset
        
        Args:
            num_simple: Number of simple test cases
            num_medium: Number of medium complexity cases
            num_complex: Number of complex test cases
            include_edge_cases: Whether to include edge cases
            
        Returns:
            List of test cases
        """
        dataset = []
        
        # Generate simple cases
        dataset.extend(self.generate_simple_cases(num_simple))
        
        # Generate medium complexity cases
        dataset.extend(self.generate_medium_cases(num_medium))
        
        # Generate complex cases
        dataset.extend(self.generate_complex_cases(num_complex))
        
        # Add edge cases
        if include_edge_cases:
            dataset.extend(self.generate_edge_cases())
        
        return dataset
    
    def generate_simple_cases(self, count: int = 20) -> List[TestCase]:
        """Generate simple single-tool test cases"""
        cases = []
        
        # Percentage calculations
        percentage_templates = [
            ("Calculate {}% of {}", "percentage_calculation"),
            ("What is {} percent of {}?", "percentage_calculation"),
            ("Find {}% from {}", "percentage_calculation")
        ]
        
        for i in range(min(count // 4, 5)):
            template, category = random.choice(percentage_templates)
            percentage = random.choice([10, 15, 20, 25, 30, 50, 75])
            base = random.choice([100, 200, 300, 500, 1000])
            query = template.format(percentage, base)
            expected = (percentage * base) / 100
            
            cases.append(TestCase(
                id=f"simple_perc_{i+1}",
                query=query,
                category=category,
                complexity="simple",
                expected_behavior="use_existing_tool",
                expected_answer=expected,
                requires_synthesis=False,
                tags=["percentage", "arithmetic"]
            ))
        
        # String operations
        string_templates = [
            ("Reverse the string '{}'", "string_reversal"),
            ("Reverse '{}'", "string_reversal"),
            ("What is '{}' reversed?", "string_reversal")
        ]
        
        test_strings = ["hello", "world", "test", "python", "code"]
        
        for i in range(min(count // 4, 5)):
            template, category = random.choice(string_templates)
            test_str = random.choice(test_strings)
            query = template.format(test_str)
            expected = test_str[::-1]
            
            cases.append(TestCase(
                id=f"simple_str_{i+1}",
                query=query,
                category=category,
                complexity="simple",
                expected_behavior="use_existing_tool",
                expected_answer=expected,
                requires_synthesis=False,
                tags=["string", "manipulation"]
            ))
        
        # Mathematical operations
        math_templates = [
            ("Calculate the factorial of {}", "factorial"),
            ("What is the factorial of {}?", "factorial"),
            ("Find factorial of {}", "factorial")
        ]
        
        for i in range(min(count // 4, 5)):
            template, category = random.choice(math_templates)
            number = random.choice([3, 4, 5, 6, 7])
            query = template.format(number)
            
            # Calculate expected factorial
            import math
            expected = math.factorial(number)
            
            cases.append(TestCase(
                id=f"simple_math_{i+1}",
                query=query,
                category=category,
                complexity="simple",
                expected_behavior="use_existing_tool",
                expected_answer=expected,
                requires_synthesis=False,
                tags=["math", "factorial"]
            ))
        
        # Temperature conversion
        temp_templates = [
            ("Convert {} Celsius to Fahrenheit", "temperature_conversion"),
            ("What is {} degrees Celsius in Fahrenheit?", "temperature_conversion"),
            ("{} Celsius to Fahrenheit", "temperature_conversion")
        ]
        
        for i in range(min(count // 4, 5)):
            template, category = random.choice(temp_templates)
            celsius = random.choice([0, 10, 20, 25, 30, 100])
            query = template.format(celsius)
            expected = (celsius * 9/5) + 32
            
            cases.append(TestCase(
                id=f"simple_temp_{i+1}",
                query=query,
                category=category,
                complexity="simple",
                expected_behavior="use_existing_tool",
                expected_answer=expected,
                requires_synthesis=False,
                tags=["temperature", "conversion"]
            ))
        
        return cases[:count]
    
    def generate_medium_cases(self, count: int = 15) -> List[TestCase]:
        """Generate medium complexity test cases"""
        cases = []
        
        # Sequential multi-tool queries
        sequential_templates = [
            ("Calculate {}% of {} and also find the square root of {}", "multi_tool_sequential"),
            ("What is {} percent of {} and the factorial of {}?", "multi_tool_sequential"),
            ("Find {}% of {} and reverse the string '{}'", "multi_tool_sequential")
        ]
        
        for i in range(min(count // 3, 5)):
            template, category = random.choice(sequential_templates)
            if "square root" in template:
                query = template.format(
                    random.choice([20, 25, 50]),
                    random.choice([100, 200, 400]),
                    random.choice([16, 64, 144])
                )
            elif "factorial" in template:
                query = template.format(
                    random.choice([10, 20, 30]),
                    random.choice([100, 200, 500]),
                    random.choice([3, 4, 5])
                )
            else:
                query = template.format(
                    random.choice([25, 50, 75]),
                    random.choice([100, 200]),
                    random.choice(["test", "hello", "world"])
                )
            
            cases.append(TestCase(
                id=f"medium_seq_{i+1}",
                query=query,
                category=category,
                complexity="medium",
                expected_behavior="execute_workflow",
                requires_synthesis=False,
                tags=["multi_tool", "sequential"]
            ))
        
        # Queries requiring new tools
        synthesis_queries = [
            ("Check if {} is a prime number", "primality_test"),
            ("Calculate the GCD of {} and {}", "gcd_calculation"),
            ("Find the LCM of {} and {}", "lcm_calculation"),
            ("Convert '{}' to title case", "string_formatting"),
            ("Check if '{}' is a palindrome", "palindrome_check")
        ]
        
        for i in range(min(count // 3, 5)):
            query_template, category = random.choice(synthesis_queries)
            
            if "prime" in query_template:
                query = query_template.format(random.choice([7, 11, 13, 17, 19]))
            elif "GCD" in query_template or "LCM" in query_template:
                query = query_template.format(
                    random.choice([12, 18, 24, 36]),
                    random.choice([8, 16, 20, 32])
                )
            elif "palindrome" in query_template:
                query = query_template.format(
                    random.choice(["racecar", "hello", "level", "world"])
                )
            else:
                query = query_template.format(
                    random.choice(["hello world", "test string", "python code"])
                )
            
            cases.append(TestCase(
                id=f"medium_synth_{i+1}",
                query=query,
                category=category,
                complexity="medium",
                expected_behavior="synthesize_tool",
                requires_synthesis=True,
                tags=["synthesis", "new_tool"]
            ))
        
        # Complex string operations
        string_ops = [
            ("Reverse '{}' and then convert to uppercase", "string_operations"),
            ("Count the vowels in '{}'", "string_analysis"),
            ("Remove spaces from '{}'", "string_formatting")
        ]
        
        for i in range(min(count // 3, 5)):
            query_template, category = random.choice(string_ops)
            test_string = random.choice([
                "hello world",
                "python programming",
                "test case",
                "evaluation framework"
            ])
            query = query_template.format(test_string)
            
            cases.append(TestCase(
                id=f"medium_str_{i+1}",
                query=query,
                category=category,
                complexity="medium",
                expected_behavior="synthesize_tool",
                requires_synthesis=True,
                tags=["string", "advanced"]
            ))
        
        return cases[:count]
    
    def generate_complex_cases(self, count: int = 10) -> List[TestCase]:
        """Generate complex multi-step test cases"""
        cases = []
        
        # Dependent workflow queries
        dependent_workflows = [
            ("Calculate {}% of {}, then find the factorial of the result", "dependent_workflow"),
            ("Find the square root of {}, then calculate {}% of that", "dependent_workflow"),
            ("Reverse '{}' and then count the characters", "dependent_workflow"),
            ("Calculate {}% of {}, convert to string, then reverse it", "dependent_workflow"),
            ("Find factorial of {}, then check if it's greater than {}", "dependent_workflow")
        ]
        
        for i in range(min(count // 2, 5)):
            query_template, category = random.choice(dependent_workflows)
            
            if "factorial" in query_template and "%" in query_template:
                query = query_template.format(
                    random.choice([20, 25, 50]),
                    random.choice([10, 15, 20])
                )
            elif "square root" in query_template:
                query = query_template.format(
                    random.choice([144, 256, 400]),
                    random.choice([20, 30, 50])
                )
            elif "Reverse" in query_template and "count" in query_template:
                query = query_template.format(random.choice(["hello", "testing", "python"]))
            elif "convert to string" in query_template:
                query = query_template.format(
                    random.choice([50, 25, 75]),
                    random.choice([100, 200])
                )
            else:
                query = query_template.format(
                    random.choice([4, 5]),
                    random.choice([100, 150, 200])
                )
            
            cases.append(TestCase(
                id=f"complex_dep_{i+1}",
                query=query,
                category=category,
                complexity="complex",
                expected_behavior="execute_composed_workflow",
                requires_synthesis=False,
                tags=["multi_tool", "dependent", "composition"]
            ))
        
        # Multi-step with synthesis
        complex_synthesis = [
            ("Calculate the median of [1, 2, 3, 4, 5], then find its factorial", "complex_synthesis"),
            ("Find the mode of [1, 2, 2, 3, 3, 3] and calculate {}% of it", "complex_synthesis"),
            ("Calculate the sum of [10, 20, 30, 40, 50] and then find its square root", "complex_synthesis")
        ]
        
        for i in range(min(count // 2, 5)):
            query_template, category = random.choice(complex_synthesis)
            
            if "%" in query_template:
                query = query_template.format(random.choice([20, 50, 100]))
            else:
                query = query_template
            
            cases.append(TestCase(
                id=f"complex_synth_{i+1}",
                query=query,
                category=category,
                complexity="complex",
                expected_behavior="synthesize_and_compose",
                requires_synthesis=True,
                tags=["synthesis", "multi_step", "advanced"]
            ))
        
        return cases[:count]
    
    def generate_edge_cases(self) -> List[TestCase]:
        """Generate edge case test cases"""
        cases = []
        
        edge_case_queries = [
            # Zero values
            ("What is 0% of 100?", "edge_zero", "simple", 0),
            ("Calculate factorial of 0", "edge_zero", "simple", 1),
            ("Reverse empty string ''", "edge_empty", "simple", ""),
            
            # Large values
            ("What is 100% of 1000000?", "edge_large", "simple", 1000000),
            ("Calculate {}% of {}", "edge_large", "simple", None),
            
            # Invalid inputs (should handle gracefully)
            ("Calculate factorial of -5", "edge_invalid", "simple", None),
            ("What is -10% of 100?", "edge_invalid", "simple", None),
            
            # Ambiguous queries
            ("Calculate it", "edge_ambiguous", "simple", None),
            ("Find the result", "edge_ambiguous", "simple", None),
            
            # Missing information
            ("Calculate percentage", "edge_incomplete", "simple", None),
            ("Reverse the string", "edge_incomplete", "simple", None)
        ]
        
        for i, (query, category, complexity, expected) in enumerate(edge_case_queries):
            if query == "Calculate {}% of {}":
                query = query.format(50, 999999)
                expected = 499999.5
            
            cases.append(TestCase(
                id=f"edge_{i+1}",
                query=query,
                category=category,
                complexity=complexity,
                expected_behavior="handle_gracefully",
                expected_answer=expected,
                requires_synthesis=False,
                tags=["edge_case", category.split("_")[1]]
            ))
        
        return cases
    
    def save_dataset(self, dataset: List[TestCase], filepath: str):
        """
        Save dataset to JSON file
        
        Args:
            dataset: List of test cases
            filepath: Output file path
        """
        data = {
            "metadata": {
                "total_cases": len(dataset),
                "simple_count": sum(1 for c in dataset if c.complexity == "simple"),
                "medium_count": sum(1 for c in dataset if c.complexity == "medium"),
                "complex_count": sum(1 for c in dataset if c.complexity == "complex"),
                "seed": self.seed
            },
            "test_cases": [case.to_dict() for case in dataset]
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"Dataset saved to {filepath}")
        print(f"Total cases: {len(dataset)}")
    
    def load_dataset(self, filepath: str) -> List[TestCase]:
        """
        Load dataset from JSON file
        
        Args:
            filepath: Input file path
            
        Returns:
            List of test cases
        """
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        cases = []
        for case_dict in data['test_cases']:
            # Convert back to TestCase object
            case = TestCase(**case_dict)
            cases.append(case)
        
        return cases


if __name__ == "__main__":
    # Generate and save a test dataset
    generator = TestDatasetGenerator(seed=42)
    
    dataset = generator.generate_full_dataset(
        num_simple=20,
        num_medium=15,
        num_complex=10,
        include_edge_cases=True
    )
    
    print(f"Generated {len(dataset)} test cases")
    
    # Save to file
    generator.save_dataset(dataset, "evaluation/data/test_dataset.json")
    
    # Print summary
    print("\nDataset Summary:")
    print(f"Simple cases: {sum(1 for c in dataset if c.complexity == 'simple')}")
    print(f"Medium cases: {sum(1 for c in dataset if c.complexity == 'medium')}")
    print(f"Complex cases: {sum(1 for c in dataset if c.complexity == 'complex')}")
    print(f"Cases requiring synthesis: {sum(1 for c in dataset if c.requires_synthesis)}")

