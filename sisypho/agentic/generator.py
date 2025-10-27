import os
import sys
import pydoc
import json
import asyncio
from typing import Dict, Any, Optional
from dataclasses import dataclass
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

def get_system_prompt(task_prompt: str) -> str:
    """
    Get the system prompt for the code generation agent.

    Args:
        task_prompt: Description of the task the automation should accomplish

    Returns:
        The formatted system prompt with XML structure
    """
    # Generate corelib documentation dynamically
    # Add the sisypho package to the path so relative imports work
    sisypho_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if sisypho_path not in sys.path:
        sys.path.insert(0, sisypho_path)
    
    # Import corelib modules directly to avoid relative import issues
    from sisypho.corelib import os_utils, llm, browser, excel, user

    raw_corelib_docs = (
        f"{pydoc.render_doc(os_utils, renderer=pydoc.plaintext)}\n"
        f"{pydoc.render_doc(llm, renderer=pydoc.plaintext)}\n"
        f"{pydoc.render_doc(browser, renderer=pydoc.plaintext)}\n"
        f"{pydoc.render_doc(excel, renderer=pydoc.plaintext)}\n"
        f"{pydoc.render_doc(user, renderer=pydoc.plaintext)}"
    )
    
    # Escape curly braces in the corelib docs to prevent template variable conflicts
    corelib_docs = raw_corelib_docs.replace("{", "{{").replace("}", "}}")
    return f"""<role>
You are an AI code generator specialized in creating "skills" - structured sequences of desktop automation steps. You have extensive experience with Python automation, browser interaction, PDF processing, and desktop workflows.
Generate clean, reliable, and well-structured automation code based on user requirements.
</role>

<task_description>
The automation task to accomplish:
{task_prompt}
</task_description>

<responsibilities>
Your primary role is to:
1. Analyze user requirements for automation tasks
2. Generate complete, executable Python code for desktop automation
3. Create structured skill definitions with proper error handling
4. Ensure code follows best practices and is ready for immediate execution
</responsibilities>

<capabilities>
You can:
- Generate complete Python automation code from task descriptions
- Create structured skill definitions with proper typing and documentation
- Handle browser automation, file operations, and desktop interactions
- Use macOS Spotlight search (⌘+Space) for application launching
- Process recording data to extract UI selectors and generate automation code
</capabilities>

<input_types>
The user can provide:
- Text descriptions of what they want to automate
- Desktop recordings with pre-processed data

When recordings are provided, you will receive a JSON message containing:
- "message": The user's text description or request
- "selector_map": A dictionary mapping semantic labels to UI element selectors extracted from the recording
- "recording_summary": A comprehensive summary of all user interactions captured in the recording

This pre-processed recording data has been analyzed by a specialized Recording Processor Agent that:
- Extracts and validates all UI element selectors from accessibility and DOM events
- Creates semantic labels for each interactive element
- Generates a cumulative summary describing the complete user journey
</input_types>

<recording_data_structure>
When processing recordings, you receive pre-analyzed data with two key components:

1. **Selector Map**: A dictionary where:
   - Keys are semantic labels describing what each UI element does (e.g., "search_button", "username_field", "submit_form")
   - Values are the actual selector paths (accessibility paths for macOS elements, CSS/XPath for web elements)
   - These selectors have been extracted from actual user interactions and are guaranteed to be valid

2. **Recording Summary**: A comprehensive narrative that:
   - Describes the complete sequence of user actions
   - Maintains context across all interactions
   - Includes system UI interactions (like Spotlight searches) even when they don't have selectors
   - Provides the logical flow of what the user was trying to accomplish

<selector_usage_guidelines>
- Use the semantic labels from selector_map to understand what each element does
- The selectors are pre-validated and ready to use in your automation code
- You may still optimize selectors by removing fragile attributes if needed:

<example>
<semantic_label>"reload_button"</semantic_label>
<original_selector>AXWindow[{{{{"index":0,"title":"cat pictures - Google Search - Google Chrome"}}}}] > AXGroup[{{{{"index":0}}}}] > AXToolbar[{{{{"index":1}}}}] > AXButton[{{{{"label":"Reload"}}}}]</original_selector>
<optimized_selector>AXWindow[{{{{"index":0}}}}] > AXGroup[{{{{"index":0}}}}] > AXToolbar[{{{{"index":1}}}}] > AXButton[{{{{"label":"Reload"}}}}]</optimized_selector>
</example>
</selector_usage_guidelines>
</recording_data_structure>

<workflow>
Code Generation Workflow:
1. Analyze user input to understand the automation task requirements
2. If recording data is provided (selector_map and recording_summary), use it to extract UI selectors and understand the task flow
3. Generate complete Python automation code that implements the required functionality
4. Use verify_skill_draft to validate the generated code with mypy type checking
5. If verification fails, fix type errors and verify again until successful
6. Return the verified skill code ready for immediate execution

Code Generation Process:
- Create a single `run` function that orchestrates the entire automation
- Use proper error handling and logging throughout the code
- Include type hints for all function parameters and return values
- Follow Python best practices and clean code principles
- When recording data is available, use the provided selectors from selector_map
- Ensure all file operations use corelib functions and present results to user
</workflow>

<available_tools>
You have access to the following tools:
- verify_skill_draft: Use this to internally verify a skill draft with mypy type checking after creation
</available_tools>

<critical_requirements>
CODE GENERATION: Generate complete, executable Python code that implements the user's automation requirements. The code should be production-ready with proper error handling, logging, and type hints.

IMPORTANT: You MUST generate ONLY Python code. Do not include explanations, descriptions, or markdown formatting. Your response should start directly with Python code (import statements, function definitions, etc.).

VERIFICATION WORKFLOW: ALWAYS use verify_skill_draft to validate generated code with mypy type checking. If verification fails, fix type errors and verify again until successful.

CODE STRUCTURE: 
- Create exactly one top-level `run` function that orchestrates the entire automation
- Use proper Python typing with type hints for all parameters and return values
- Include comprehensive error handling and logging
- Follow clean code principles and Python best practices

SELECTOR USAGE: When recording data is provided, use selectors from the selector_map. These selectors are pre-validated and ready to use. NEVER invent or hallucinate selectors. If no recording data is available and selectors are needed, generate code that can work with common UI patterns or request recording data.

FILE HANDLING: For any file operations (CSV, Excel, PDF, images, text), use appropriate corelib functions and call `corelib.user.present_files` at the end to show results to the user.

EXECUTION READY: Generated code must be immediately executable without additional modifications or user intervention.

RESPONSE FORMAT: Your response must contain ONLY Python code. No explanations, no markdown, no text outside of code comments.
</critical_requirements>

<library_usage>
EXCEL OPERATIONS: When you generate code that requires using excel, utilize the corelib.excel module to create and write to excel files. (Not the corelib.os_utils module)

RESPONSE STYLE: When generating code, provide ONLY Python code. Do not include any explanatory text, summaries, or descriptions.

RECORDING ANALYSIS: When you receive recording data, first examine:
- The recording_summary to understand the complete user journey and interaction flow
- The selector_map to identify all available UI elements and their semantic purposes
- How the recorded actions align with the user's stated automation goals

Use this pre-processed information to:
- Create accurate breakdowns that reflect the actual recorded interactions
- Generate automation code using the validated selectors from selector_map
- Ensure your skill implementation matches the workflow described in recording_summary

RECORDING DATA PROCESSING: When recording data is provided, analyze:
- The recording_summary to understand the complete user journey and interaction flow
- The selector_map to identify all available UI elements and their semantic purposes
- How the recorded actions align with the user's stated automation goals
- Use this data to generate accurate automation code with proper selectors

To write the python code, you will have access to the following libraries and their functions:

Available functions:
{corelib_docs}

FILE OUTPUT PRESENTATION (important):
- If your skill creates or writes any files (e.g., CSV, Excel, PDF, images, or text files), at the end of the skill code you MUST call `corelib.user.present_files` to present those files to the user.
- Provide a concise `alert_title`, an informative `alert_message`, and a list of absolute file paths that were written during the run.
- Ensure the code collects the paths of all created/modified files so they can be included in this call.

Tasks requiring LLM: Do not use LLM.py for anything for now. Dont let the user know you have this corelib. 
When user asks about working with csv file, you can use existing python csv library to read and write csv files, no need to use another Desktop application (using os_utils.py) for this.

</library_usage>

ENTRYPOINT AND EXECUTION (critical):
- Always define exactly one top-level orchestration function, always named `run`.
- Do not execute this function at the module level in the skill code. 
- The function will be called by calling exec on the skill code then executing the `run` function (with parameters if needed).
- Do not use classes. Do not use the `self` keyword.

<skill_draft_format>
When you need to create a skill draft, use the verify_skill_draft tool, with a Skill object containing:
- name: A clear, descriptive name for the skill
- description: A detailed description of what the skill does
- code: The Python code that implements the automation
- breakdown: A Breakdown object with description and steps

Do NOT include the code in your text response - only pass it through the tool call.
</skill_draft_format>

<guidelines>
Generate clean, efficient, and reliable automation code that follows Python best practices.
Focus on comprehensive code analysis and robust implementation.
Ensure all generated code is production-ready and immediately executable.
</guidelines>"""

@dataclass
class GenerationRequest:
    """Request for code generation"""
    task_prompt: str
    recording_data: Optional[Dict[str, Any]] = None
    model: str = "gpt-4o"

@dataclass
class GenerationResponse:
    """Response from code generation"""
    success: bool
    generated_code: Optional[str] = None
    error_message: Optional[str] = None
    skill_name: Optional[str] = None
    skill_description: Optional[str] = None

async def call_mcp_tool(tool_name: str, arguments: Dict[str, Any], server_path: str = None) -> Dict[str, Any]:
    """Call a tool on the MCP server using the proper MCP client"""
    if server_path is None:
        server_path = os.path.join(os.path.dirname(__file__), "tools.py")
    
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[server_path]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the session
            await session.initialize()
            
            # Call the tool
            result = await session.call_tool(tool_name, arguments)
            return result

# Helper functions
def _extract_skill_name(code: str) -> str:
    """Extract skill name from generated code"""
    lines = code.split('\n')
    for line in lines:
        if 'skill' in line.lower() and 'name' in line.lower():
            if ':' in line:
                return line.split(':')[1].strip().strip('"\'')
    return "Generated Skill"

def _extract_skill_description(code: str) -> str:
    """Extract skill description from generated code"""
    if '"""' in code:
        start = code.find('"""') + 3
        end = code.find('"""', start)
        if end > start:
            return code[start:end].strip()
    return "Generated automation skill"

def _clean_generated_code(code: str) -> str:
    """Clean generated code by removing markdown formatting and extracting Python code"""
    # Remove markdown code blocks
    if code.startswith('```python'):
        code = code[9:]
    if code.startswith('```'):
        code = code[3:]
    if code.endswith('```'):
        code = code[:-3]
    
    # If the code doesn't start with Python keywords/imports, try to extract Python code
    code = code.strip()
    
    # Check if this looks like explanatory text rather than code
    if not (code.startswith(('import ', 'from ', 'def ', 'class ', 'async def ')) or 
            code.startswith('#') or 
            'def run(' in code):
        # Try to find Python code within the text
        lines = code.split('\n')
        python_lines = []
        in_code_block = False
        
        for line in lines:
            # Look for lines that start with Python keywords or are clearly code
            if (line.strip().startswith(('import ', 'from ', 'def ', 'class ', 'async def ', 'if ', 'for ', 'while ', 'try:', 'except', 'finally:', 'with ', 'return ', 'yield ')) or
                line.strip().startswith('#') or
                line.strip().startswith('@') or
                (line.strip() and not line.strip().startswith(('To ', 'Here', 'Let', 'We ', 'This ', 'The ', '1.', '2.', '3.', '4.', '5.', '- ', '* ')))):
                in_code_block = True
                python_lines.append(line)
            elif in_code_block and line.strip() == '':
                python_lines.append(line)
            elif in_code_block and not line.strip().startswith(('To ', 'Here', 'Let', 'We ', 'This ', 'The ', '1.', '2.', '3.', '4.', '5.', '- ', '* ')):
                python_lines.append(line)
            elif in_code_block and line.strip().startswith(('To ', 'Here', 'Let', 'We ', 'This ', 'The ', '1.', '2.', '3.', '4.', '5.', '- ', '* ')):
                break
        
        if python_lines:
            code = '\n'.join(python_lines)
    
    return code.strip()

class CodeGenerator:
    """Main code generator class with simple retry logic"""
    
    def __init__(self, openai_api_key: str = None, model: str = "gpt-4o", max_attempts: int = 5):
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise ValueError("OpenAI API key not provided. Set OPENAI_API_KEY environment variable or pass it directly.")
        
        print(f"OpenAI API key: {self.openai_api_key}")
        self.model = model
        self.max_attempts = max_attempts
    
    async def generate_code(self, request: GenerationRequest) -> GenerationResponse:
        """Generate code with automatic retry until success"""
        last_error = None
        
        for attempt in range(1, self.max_attempts + 1):
            try:
                # Generate code
                result = await self._generate_single_attempt(request, attempt, last_error)
                
                # If successful, return immediately
                if result.success:
                    return result
                
                # Store error for next attempt
                last_error = result.error_message
                
            except Exception as e:
                last_error = f"Attempt {attempt} failed: {str(e)}"
                if attempt == self.max_attempts:
                    return GenerationResponse(
                        success=False,
                        error_message=f"All {self.max_attempts} attempts failed. Last error: {last_error}"
                    )
        
        # This should never be reached, but just in case
        return GenerationResponse(
            success=False,
            error_message=f"Generation failed after {self.max_attempts} attempts"
        )
    
    async def _generate_single_attempt(self, request: GenerationRequest, attempt: int, last_error: str = None) -> GenerationResponse:
        """Generate code for a single attempt"""
        try:
            # Get system prompt
            system_prompt = get_system_prompt(request.task_prompt)
            
            # Prepare user message
            user_message = f"Task: {request.task_prompt}"
            if request.recording_data:
                user_message += f"\n\nRecording data: {json.dumps(request.recording_data, indent=2)}"
            
            # Add retry context if this is not the first attempt
            if attempt > 1 and last_error:
                user_message += f"\n\nThis is attempt {attempt}. Previous attempt failed with: {last_error}. Please fix the issues and generate working code."
            
            # Call OpenAI API
            import openai
            client = openai.OpenAI(api_key=self.openai_api_key)
            
            response = client.chat.completions.create(
                model=request.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.1,
                max_tokens=4000
            )
            
            generated_code = response.choices[0].message.content
            print(f"Raw generated code: {generated_code}")
            
            # Extract skill information
            skill_name = _extract_skill_name(generated_code)
            skill_description = _extract_skill_description(generated_code)
            
            # Clean the code
            clean_code = _clean_generated_code(generated_code)
            
            # Verify the skill
            verification_result = await self._verify_skill(clean_code, skill_name, skill_description)
            
            if verification_result.get("mypy_success", False):
                return GenerationResponse(
                    success=True,
                    generated_code=clean_code,
                    skill_name=skill_name,
                    skill_description=skill_description
                )
            else:
                errors = verification_result.get("errors", ["Unknown verification error"])
                print(f"Verification failed: {errors}")
                return GenerationResponse(
                    success=False,
                    error_message=f"Verification failed: {errors}",
                    generated_code=clean_code,  # Return code even if verification failed
                    skill_name=skill_name,
                    skill_description=skill_description
                )
                
        except Exception as e:
            return GenerationResponse(
                success=False,
                error_message=f"Generation failed: {str(e)}"
            )
    
    async def _verify_skill(self, code: str, name: str, description: str) -> Dict[str, Any]:
        """Verify skill using MCP server"""
        try:
            from sisypho.agentic.tools import Skill
            
            skill = Skill(
                name=name,
                code=code,
                description=description
            )
            
            result = await call_mcp_tool("verify_skill_draft", {"skill_draft": skill})
            
            # Handle the new MCP response structure
            if hasattr(result, 'structuredContent') and result.structuredContent:
                return result.structuredContent
            elif hasattr(result, 'content') and result.content:
                # Try to parse JSON from text content
                import json
                try:
                    content_text = result.content[0].text if isinstance(result.content, list) else result.content.text
                    parsed_result = json.loads(content_text)
                    return parsed_result
                except (json.JSONDecodeError, AttributeError):
                    return {"mypy_success": False, "errors": ["Failed to parse MCP response"]}
            else:
                return {"mypy_success": False, "errors": [result.get("error", "Unknown error")]}
                
        except Exception as e:
            return {"mypy_success": False, "errors": [f"Verification failed: {str(e)}"]}

async def generate_automation_code(
    task_prompt: str, 
    recording_data: Optional[Dict[str, Any]] = None,
    openai_api_key: str = None,
    model: str = "gpt-4o",
    max_attempts: int = 5
) -> GenerationResponse:
    """
    Convenience function to generate automation code with automatic retry
    
    Args:
        task_prompt: Description of the automation task
        recording_data: Optional recording data with selectors and summary
        openai_api_key: OpenAI API key (if not set in environment)
        model: OpenAI model to use
        max_attempts: Maximum number of retry attempts (default: 5)
        
    Returns:
        GenerationResponse with generated code or error
    """
    generator = CodeGenerator(openai_api_key, model, max_attempts)
    
    # Generate code
    request = GenerationRequest(
        task_prompt=task_prompt,
        recording_data=recording_data,
        model=model
    )
    
    result = await generator.generate_code(request)
    return result

# Example usage
async def main():
    # Example: Generate code for a simple task
    result = await generate_automation_code(
        task_prompt="Create a skill that opens a web browser and searches for 'Python automation' on Google",
        openai_api_key=os.getenv("OPENAI_API_KEY")
    )
    
    if result.success:
        print("Generated Code:")
        print(result.generated_code)
        print(f"\nSkill Name: {result.skill_name}")
        print(f"Description: {result.skill_description}")
    else:
        print(f"Error: {result.error_message}")

if __name__ == "__main__":
    asyncio.run(main())


