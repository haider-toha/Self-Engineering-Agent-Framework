# Self-Engineering Agent Demo Script
## "The Autonomous E-commerce Analyst"

**Demo Duration:** 8-10 minutes  
**Audience:** Technical interviewer  
**Goal:** Showcase autonomous tool synthesis, multi-step workflows, pattern learning, and self-repair

---

## Setup (Pre-Demo)
1. **Rebuild Docker image:** `docker build -f docker/sandbox.dockerfile -t self-eng-sandbox docker/`
2. **Start the web server:** Navigate to project root and run `python web/app.py` (or `py web/app.py` on Windows)
3. **Open browser:** Go to `http://localhost:5000`
4. **Verify datasets:** Check that `data/ecommerce_products.csv` and `data/sales_targets.json` exist
5. **Check baseline:** Ensure only basic tools exist (`calculate_percentage`, `reverse_string`)

### Quick Test (Optional)
Run `python test_csv_demo.py` to verify the CSV synthesis works before the demo.

---

## Phase 1: Tool Synthesis from Raw Data (3 minutes)

### Opening Statement
*"I'm going to show you an agent that doesn't just execute predefined workflows—it creates its own tools on demand. Let's say I'm an e-commerce manager who just received a CSV dump of product data, and I need to analyze profit margins to identify products for a flash sale."*

### Prompt 1: Data Loading & Tool Creation
```
I have product data in data/ecommerce_products.csv with columns: product_name, price, cost, category, units_sold, rating. I need to load this CSV file and calculate profit margins for each product. The profit margin formula is (price - cost) / price.
```

**What to highlight:**
- Point to the streaming events: "searching" → "no_tool_found" → "entering_synthesis_mode"
- Explain: *"The agent realizes it doesn't have a CSV loader or profit margin calculator, so it's creating them from scratch using TDD."*
- Show the synthesis steps: "specification" → "test_generation" → "implementation" → "verification"
- *"Notice it's writing tests FIRST, then implementing the code to pass those tests—this ensures reliability."*

### Prompt 2: Data Analysis Tool Creation
```
Now I need a tool that can identify underperforming products. Create a function that takes a list of products (each with name, price, cost, and margin fields) and a margin_threshold, then returns only products where the margin is below that threshold.
```

**What to highlight:**
- *"Again, no existing tool matches this need, so it's synthesizing a new one."*
- Show the tool appearing in the UI's tool list
- *"These aren't just scripts—they're fully tested, documented tools that can be reused."*

---

## Phase 2: Multi-Tool Workflow & Pattern Learning (3 minutes)

### Prompt 3: Complex Workflow Execution
```
Using the data from data/ecommerce_products.csv:
1. Load the product data
2. Calculate profit margins for all products  
3. Find products with margins below 15% (0.15)
4. Format the results as a markdown table showing product name, price, and margin
```

**What to highlight:**
- *"Now watch how it chains multiple tools together intelligently."*
- Point to the execution sequence in the event stream
- Show the final markdown output
- *"This is a 4-step workflow that required creating 2 new tools and orchestrating them perfectly."*

### Prompt 4: Repeat for Pattern Detection
```
Do the same analysis but for products with margins below 20% (0.20) instead.
```

### Prompt 5: Third Iteration
```
Analyze products with margins below 10% (0.10) and also include the category in the output table.
```

**What to highlight:**
- After the third run, navigate to the Analytics tab
- Show the detected workflow pattern
- *"The system has learned this is a common sequence. It can now synthesize a single composite tool that does all 4 steps in one optimized function."*

---

## Phase 3: Self-Repair Demonstration (2-3 minutes)

### Prompt 6: Trigger Failure with Edge Case Data
```
Now analyze the data from data/ecommerce_products.csv, but this time calculate margins for ALL products including the ones with zero or negative prices. Use a 15% margin threshold.
```

**What to highlight:**
- The calculation will fail on the "Broken Price Item" with price=0 (division by zero)
- Point to the error in the event stream
- *"A normal system would just crash here. But watch what happens..."*
- Show the reflection engine activating: "analyzing_failure" → "generating_fix" → "testing_fix"
- *"The agent analyzed the failure, proposed a fix (handle zero prices), wrote a test for the edge case, and verified the fix in the sandbox."*
- Show the successful re-execution with the repaired tool

---

## Phase 4: Advanced Capabilities Showcase (1-2 minutes)

### Show the Analytics Dashboard
- **Tool Relationships:** Show how tools are connected
- **Workflow Patterns:** Display the learned sequences
- **Session History:** Show the complete execution trace

### Prompt 7: Demonstrate Caching
```
Analyze products with margins below 15% again using the same data.
```

**What to highlight:**
- Point to "cache_hit" events
- *"Since this is deterministic data with the same inputs, it's returning cached results instantly—no re-computation needed."*

---

## Closing Statement (30 seconds)

*"What you've seen is an agent that doesn't just follow predefined workflows. It:*
- *Creates new tools on-demand using test-driven development*
- *Learns from usage patterns to optimize future workflows* 
- *Self-repairs when it encounters edge cases*
- *Caches results for efficiency*
- *Maintains full traceability and versioning*

*This isn't just automation—it's autonomous capability evolution. The agent gets smarter and more capable with every interaction."*

---

## Technical Deep-Dive Questions (If Asked)

**Q: How does it ensure the generated code is safe?**
A: All code generation and testing happens in a sandboxed Docker environment with no network access and strict resource limits.

**Q: What if the LLM generates bad code?**
A: The TDD approach means tests are written first. If the implementation doesn't pass the tests, it iterates until it does. Plus, the reflection engine can fix issues post-deployment.

**Q: How does pattern learning work?**
A: The workflow tracker logs all tool executions with timestamps and success rates. It uses sequence mining algorithms to detect frequent patterns, then the composite synthesizer can promote patterns to optimized single tools.

**Q: Can it integrate with existing systems?**
A: Yes, it has a full REST API and WebSocket interface. The tool synthesis engine can wrap existing APIs or databases as needed.

---

## Backup Prompts (If Demo Needs Extension)

### Advanced Analysis
```
Load the sales targets from data/sales_targets.json and compare actual performance vs targets by category. Identify which categories are underperforming and suggest promotion strategies.
```

### Multi-Data Source
```
Cross-reference the product data with the sales targets to create a comprehensive performance report that includes target vs actual revenue, margin analysis, and recommended actions for each category.
```
