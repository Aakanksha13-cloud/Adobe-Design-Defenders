"""
Gemini 3 Flash Preview + MCP Integration
With System Prompt & Few-Shot Examples for Adobe Express Add-on Code Generation
Saves code responses to ../src/code.js automatically
"""

import asyncio
import json
import re
import os
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from google import genai
from google.genai import types


API_KEY = "AIzaSyAZSxDDRAnU6qs5imoyfyo1yWIyepqxpaM"


# ============================================
# SYSTEM PROMPT WITH FEW-SHOT EXAMPLES
# ============================================
SYSTEM_PROMPT = """You are an Adobe Express add-on code generator. You MUST follow these CRITICAL RULES when generating code.js.

## IMMUTABLE STRUCTURE (NEVER CHANGE THESE):
1. Line 1-2: Import statements - EXACTLY as shown, DO NOT MODIFY
2. Line 4: `const { runtime } = addOnSandboxSdk.instance;` - EXACTLY as shown
3. Line 6: `function start() {` - Function name MUST be "start"
4. Line 8: `const sandboxApi = {` - Variable name MUST be "sandboxApi"
5. Line 9: `createShape: () => {` - Function name MUST be "createShape" (this is called from index.js)
6. LAST TWO LINES inside createShape function MUST BE:
   ```
   const insertionParent = editor.context.insertionParent;
   insertionParent.children.append(SHAPE_VARIABLE);
   ```
7. Line before end of start(): `runtime.exposeApi(sandboxApi);` - EXACTLY as shown
8. FINAL LINE: `start();` - EXACTLY as shown

## MODIFIABLE SECTION (ONLY CHANGE THIS):
Between the start of createShape() and the last two lines, you can:
- Create ANY shape (ellipse, rectangle, path, text, etc.)
- Set ANY dimensions, colors, positions, strokes, fills
- Use ANY Adobe Express Document SDK functions

## CRITICAL RULES:
- NEVER change function names: start, createShape, sandboxApi
- NEVER remove runtime lines
- NEVER remove start() call at end
- ALWAYS end createShape with insertionParent lines
- ONLY modify shape creation code
- ALWAYS wrap code in ```javascript code block

## FEW-SHOT EXAMPLES:

### Example 1: User asks "draw a circle"
```javascript
import addOnSandboxSdk from "add-on-sdk-document-sandbox";
import { editor, colorUtils } from "express-document-sdk";

const { runtime } = addOnSandboxSdk.instance;

function start() {
    const sandboxApi = {
        createShape: () => {
            const ellipse = editor.createEllipse();
            ellipse.rx = 100;
            ellipse.ry = 100;
            ellipse.translation = { x: 200, y: 200 };
            const fillColor = colorUtils.fromHex("#A38AF0");
            ellipse.fill = editor.makeColorFill(fillColor);

            const insertionParent = editor.context.insertionParent;
            insertionParent.children.append(ellipse);
        }
    };
    runtime.exposeApi(sandboxApi);
}
start();
```

### Example 2: User asks "draw a red rectangle"
```javascript
import addOnSandboxSdk from "add-on-sdk-document-sandbox";
import { editor, colorUtils } from "express-document-sdk";

const { runtime } = addOnSandboxSdk.instance;

function start() {
    const sandboxApi = {
        createShape: () => {
            const rect = editor.createRectangle();
            rect.width = 200;
            rect.height = 150;
            rect.translation = { x: 100, y: 100 };
            const fillColor = colorUtils.fromHex("#FF0000");
            rect.fill = editor.makeColorFill(fillColor);

            const insertionParent = editor.context.insertionParent;
            insertionParent.children.append(rect);
        }
    };
    runtime.exposeApi(sandboxApi);
}
start();
```

### Example 3: User asks "draw a blue circle with green stroke"
```javascript
import addOnSandboxSdk from "add-on-sdk-document-sandbox";
import { editor, colorUtils } from "express-document-sdk";

const { runtime } = addOnSandboxSdk.instance;

function start() {
    const sandboxApi = {
        createShape: () => {
            const ellipse = editor.createEllipse();
            ellipse.rx = 80;
            ellipse.ry = 80;
            ellipse.translation = { x: 150, y: 150 };
            ellipse.fill = editor.makeColorFill(colorUtils.fromHex("#0000FF"));
            ellipse.stroke = editor.makeStroke({
                color: colorUtils.fromHex("#00FF00"),
                width: 5
            });

            const insertionParent = editor.context.insertionParent;
            insertionParent.children.append(ellipse);
        }
    };
    runtime.exposeApi(sandboxApi);
}
start();
```

### Example 4: User asks "create a triangle"
```javascript
import addOnSandboxSdk from "add-on-sdk-document-sandbox";
import { editor, colorUtils } from "express-document-sdk";

const { runtime } = addOnSandboxSdk.instance;

function start() {
    const sandboxApi = {
        createShape: () => {
            const triangle = editor.createPath();
            triangle.setPathData("M 100 0 L 200 200 L 0 200 Z");
            triangle.translation = { x: 100, y: 100 };
            triangle.fill = editor.makeColorFill(colorUtils.fromHex("#FFD700"));

            const insertionParent = editor.context.insertionParent;
            insertionParent.children.append(triangle);
        }
    };
    runtime.exposeApi(sandboxApi);
}
start();
```

REMEMBER: Always use this EXACT structure. Only modify the shape creation code inside createShape(). Always end with the insertionParent lines.
"""


def extract_code_from_response(text):
    """Extract code blocks from Gemini's response."""
    if not text:
        return None
    
    patterns = [
        r'```(?:javascript|js|tsx|jsx|typescript|ts)\n(.*?)```',
        r'```\n(.*?)```',
    ]
    
    code_blocks = []
    for pattern in patterns:
        matches = re.findall(pattern, text, re.DOTALL)
        code_blocks.extend(matches)
    
    if code_blocks:
        return '\n\n'.join(code_blocks)
    return None


def save_code_to_file(code, filename="../src/code.js"):
    """Save extracted code to src/code.js file."""
    # Get the directory of this script
    script_dir = Path(__file__).parent
    # Construct path to src/code.js
    target_path = script_dir / filename
    
    # Create src directory if it doesn't exist
    target_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(target_path, 'w', encoding='utf-8') as f:
        f.write(code)
    
    print(f"\n💾 Code saved to {target_path.absolute()}")


async def run_gemini_with_mcp():
    """Main function to run the Gemini chatbot with MCP integration."""
    
    # MCP Server connection
    server_params = StdioServerParameters(
        command="npx",
        args=["@adobe/express-developer-mcp@latest", "--yes"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            
            # Initialize MCP session
            await session.initialize()
            print("✅ Connected to Adobe Express MCP server!")
            
            # Get available MCP tools
            tools_response = await session.list_tools()
            mcp_tools = tools_response.tools
            
            print(f"\n📦 Found {len(mcp_tools)} MCP tools:")
            for tool in mcp_tools:
                print(f"   • {tool.name}")
            
            # Convert MCP tools to Gemini function declarations
            gemini_functions = []
            
            for tool in mcp_tools:
                schema = tool.inputSchema or {}
                properties = schema.get("properties", {})
                required = schema.get("required", [])
                
                gemini_props = {}
                for name, prop in properties.items():
                    type_map = {
                        "string": types.Type.STRING,
                        "number": types.Type.NUMBER,
                        "integer": types.Type.INTEGER,
                        "boolean": types.Type.BOOLEAN,
                        "array": types.Type.ARRAY,
                        "object": types.Type.OBJECT,
                    }
                    gemini_props[name] = types.Schema(
                        type=type_map.get(prop.get("type", "string"), types.Type.STRING),
                        description=prop.get("description", ""),
                    )
                
                func_decl = types.FunctionDeclaration(
                    name=tool.name,
                    description=tool.description or "",
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        properties=gemini_props,
                        required=required,
                    ) if gemini_props else None,
                )
                gemini_functions.append(func_decl)
            
            gemini_tools = [types.Tool(function_declarations=gemini_functions)]
            
            # Initialize Gemini client
            gemini = genai.Client(api_key=API_KEY)
            model = "gemini-3-flash-preview"
            
            print(f"\n🤖 Gemini AI ready! (Model: {model})")
            print("="*60)
            print("💡 Type your shape request (e.g., 'draw a blue circle')")
            print("💡 Generated code will be saved to src/code.js")
            print("💡 Type 'quit' or 'exit' to stop")
            print("="*60)
            
            # Chat loop
            while True:
                user_input = input("\n👤 You: ").strip()
                
                # Exit commands
                if user_input.lower() in ['quit', 'exit', 'q']:
                    break
                
                if not user_input:
                    continue
                
                try:
                    # Build contents with system prompt
                    contents = [
                        types.Content(
                            role="user",
                            parts=[types.Part(text=SYSTEM_PROMPT + "\n\nUser Request: " + user_input)]
                        )
                    ]
                    
                    # Function calling loop
                    while True:
                        response = gemini.models.generate_content(
                            model=model,
                            contents=contents,
                            config=types.GenerateContentConfig(
                                tools=gemini_tools,
                                system_instruction=SYSTEM_PROMPT,
                            ),
                        )
                        
                        model_response_content = response.candidates[0].content
                        
                        # Check if there are function calls
                        if not response.function_calls:
                            # No more function calls - get final response
                            response_text = response.text
                            if response_text is None:
                                response_text = ""
                                for part in model_response_content.parts:
                                    if hasattr(part, 'text') and part.text:
                                        response_text += part.text
                            
                            if response_text:
                                print(f"\n🤖 Gemini: {response_text}")
                                
                                # Extract and save code
                                code = extract_code_from_response(response_text)
                                if code:
                                    save_code_to_file(code)
                                else:
                                    print("⚠️  No code block found in response")
                            else:
                                print("\n🤖 Gemini: (No response text)")
                            
                            break
                        
                        # Add model's response to contents
                        contents.append(model_response_content)
                        
                        # Execute function calls
                        function_response_parts = []
                        
                        for fc in response.function_calls:
                            func_name = fc.name
                            func_args = dict(fc.args) if fc.args else {}
                            
                            print(f"\n🔧 Calling MCP tool: {func_name}({json.dumps(func_args, indent=2)})")
                            
                            # Call the MCP tool
                            result = await session.call_tool(func_name, func_args)
                            
                            # Extract result text
                            result_text = ""
                            for item in result.content:
                                if hasattr(item, 'text'):
                                    result_text += item.text
                                else:
                                    result_text += str(item)
                            
                            print(f"   📄 Result: {result_text[:200]}...")
                            
                            # Add function response to parts
                            function_response_parts.append(
                                types.Part.from_function_response(
                                    name=func_name,
                                    response={"result": result_text}
                                )
                            )
                        
                        # Add function responses to contents
                        contents.append(
                            types.Content(
                                role="user",
                                parts=function_response_parts
                            )
                        )
                
                except Exception as e:
                    print(f"\n❌ Error: {e}")
                    import traceback
                    traceback.print_exc()
            
            print("\n👋 Goodbye!")


if __name__ == "__main__":
    asyncio.run(run_gemini_with_mcp())
