# advanced_features.py
import google.generativeai as genai
import google.generativeai.types as genai_types

# FIX for Function Calling response construction: Import protos directly
try:
    # Try importing specific protos needed
    from google.ai.generativelanguage import FunctionResponse, Part
except ImportError:
    print("Warning: Could not import FunctionResponse/Part from google.ai.generativelanguage. Function calling might fail.")
    class FunctionResponse: pass
    class Part: pass

# Import GoogleSearchRetrieval for grounding attempt
try:
    # Note: Even if GoogleSearch type exists, Tool constructor might expect retrieval
    from google.generativeai.types import GoogleSearchRetrieval
    GROUNDING_RETRIEVAL_TYPE_AVAILABLE = True
except ImportError:
    print("Warning: Could not import GoogleSearchRetrieval type. Grounding will likely fail.")
    class GoogleSearchRetrieval: pass # Dummy placeholder
    GROUNDING_RETRIEVAL_TYPE_AVAILABLE = False

import json
import time

from google.protobuf.struct_pb2 import Struct
from utils import print_section_header

# Import safety types carefully
try:
    from google.generativeai.types import HarmBlockThreshold, HarmCategory
    SAFETY_TYPES_AVAILABLE = True
except ImportError:
    SAFETY_TYPES_AVAILABLE = False
    class HarmCategory: HARM_CATEGORY_HARASSMENT, HARM_CATEGORY_HATE_SPEECH, HARM_CATEGORY_SEXUALLY_EXPLICIT, HARM_CATEGORY_DANGEROUS_CONTENT = ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]
    class HarmBlockThreshold: BLOCK_MEDIUM_AND_ABOVE, BLOCK_ONLY_HIGH, BLOCK_NONE = ["BLOCK_MEDIUM_AND_ABOVE", "BLOCK_ONLY_HIGH", "BLOCK_NONE"]


def run_thinking_control(model):
    """Attempts to run thinking control examples."""
    print("\n--- V.A Thinking & Reasoning Control ---")
    # This section was already 'Partial' (correctly skipping explicit control). No changes needed.
    status = "Partial - Default Ran, Explicit Skipped (SDK Limitation?)"
    complex_prompt = """
    Consider a system with two components, A and B, operating independently.
    Component A has a reliability (probability of working) of R_A = 0.95 over a 10-hour period.
    Component B has a reliability R_B = 0.90 over the same 10-hour period.
    The system functions if at least one of the components is working.
    What is the probability that the system is functioning after 10 hours?
    Explain your reasoning step-by-step.
    """
    try:
        print("\nRunning with Default Thinking...")
        start_time = time.time()
        response_default = model.generate_content(complex_prompt)
        default_time = time.time() - start_time
        print(f"(Default Time: {default_time:.2f}s)")

        usage = getattr(response_default, 'usage_metadata', None)
        if usage and hasattr(usage, 'total_token_count'):
             total_t = usage.total_token_count
             think_t = usage.thinking_token_count if hasattr(usage, 'thinking_token_count') else 'N/A'
             print(f"  Usage (Default): Total Tokens: {total_t}, Thinking Tokens: {think_t}")
        else:
             print("  Usage (Default): No usage data captured.")
        print("\nSkipping Explicit Thinking Budget control due to SDK structure uncertainty.")

    except Exception as e:
        print(f"ERROR during Default Thinking run: {e}")
        status = f"Failed - {type(e).__name__}"

    return status


def run_function_calling(model):
    """Runs the function calling example."""
    print("\n--- V.B Function Calling ---")
    status = f"Failed - Unknown"
    try:
        # 1. Define Tool (Function Declaration) using DICT for parameters
        get_weather_func = genai_types.FunctionDeclaration(
            name="get_current_weather",
            description="Get the current weather conditions for a specific location.",
            parameters={
                "type": "OBJECT", "properties": {
                    "location": {"type": "STRING", "description": "The city and state"},
                    "unit": {"type": "STRING", "enum": ["celsius", "fahrenheit"]}
                }, "required": ["location"]
            }
        )
        weather_tool = genai_types.Tool(function_declarations=[get_weather_func])

        def get_current_weather(location: str, unit: str = "celsius"):
            print(f"--- SIMULATING External Call: get_current_weather(location='{location}', unit='{unit}') ---")
            if "boston" in location.lower(): return {"location": location, "temperature": "15", "unit": unit, "description": "Partly cloudy"}
            if "tokyo" in location.lower(): return {"location": location, "temperature": "22", "unit": unit, "description": "Sunny"}
            return {"location": location, "temperature": "unknown", "unit": unit, "description": "Weather data not available"}

        # 2. Send Prompt and Tool
        prompt_func = "What's the weather like in Boston today in fahrenheit?"
        print(f"User Prompt: {prompt_func}")

        # 3. Initial Call
        response_part_1 = model.generate_content(prompt_func, tools=[weather_tool])

        # 4. Handle Response - Extract function call AND the Content object containing it
        func_call = None
        model_content_with_call = None # Store the model's content part containing the call
        try:
            # Prioritize getting the Content object from the candidate
            if response_part_1.candidates and response_part_1.candidates[0].content.parts:
                 part = response_part_1.candidates[0].content.parts[0]
                 if part.function_call:
                     func_call = part.function_call
                     # Store the actual Content object from the candidate
                     model_content_with_call = response_part_1.candidates[0].content
            # Fallback: check response.parts directly (less common for function calls)
            elif hasattr(response_part_1, 'parts') and response_part_1.parts:
                 part = response_part_1.parts[0]
                 if part.function_call:
                     func_call = part.function_call
                     # How to get the Content proto here is less clear, might need response_part_1 itself?
                     # Let's try assigning the whole response object content if available
                     if hasattr(response_part_1, 'candidates') and response_part_1.candidates:
                          model_content_with_call = response_part_1.candidates[0].content
                     else: # Cannot reliably get the model Content object
                          print("Warning: Could not extract model's Content object containing function call.")
                          model_content_with_call = None # Signal that history might be incomplete

        except (IndexError, AttributeError) as check_e:
             print(f"Could not reliably extract function call part: {check_e}")

        if func_call and model_content_with_call: # Ensure we have both
            func_name = func_call.name
            args = dict(func_call.args)
            print(f"--- Model requested Function Call: {func_name}({args}) ---")

            # 5. Execute Function
            if func_name == "get_current_weather":
                if 'unit' not in args and 'fahrenheit' in prompt_func.lower(): args['unit'] = 'fahrenheit'
                function_result_data = get_current_weather(**args)
                print(f"--- Function Execution Result: {function_result_data} ---")

                # 6. Send Result Back
                print("--- Sending Function Response back to model ---")
                s = Struct()
                if isinstance(function_result_data, dict): s.update(function_result_data)
                else: s.update({"result": str(function_result_data)})

                function_response_part = Part( # Use imported proto Part
                    function_response=FunctionResponse( # Use imported proto FunctionResponse
                        name=func_name,
                        response=s
                    )
                )

                # FIX: Construct history list correctly. Need user prompt -> model response -> function result
                # The user prompt needs to be a Part or Content object too.
                user_prompt_part = genai_types.Part.from_text(prompt_func) # Convert simple string
                user_content = genai_types.Content(parts=[user_prompt_part], role="user")

                # Send history list: [user_content, model_content_with_call, function_response_part]
                response_part_2 = model.generate_content(
                    [user_content, model_content_with_call, function_response_part],
                    tools=[weather_tool]
                )

                # 7. Final Response
                print("\n--- Final Model Response (after function call) ---")
                print(response_part_2.text)
                status = "Success"
            else:
                print(f"Error: Application does not have a function named '{func_name}'")
                status = "Failed - Unknown Function Name"
        else:
            if func_call is None and response_part_1.text:
                print("\n--- Direct Model Response (No Function Call Triggered/Extracted) ---")
                print(response_part_1.text)
                status = "Success (No Call Triggered/Extracted)"
            else:
                print("\n--- Function Call Extraction Failed or No Text Response ---")
                status = "Failed - Function Call Extraction/Response Error"


    except TypeError as te:
         print(f"TypeError during Function Calling: {te}")
         print("      (Check history format or proto imports)")
         status = f"Failed - TypeError ({type(te).__name__})"
    except AttributeError as ae:
         print(f"AttributeError during Function Calling: {ae}")
         print("      (Check SDK documentation for FunctionDeclaration/Tool/Proto structure)")
         status = "Failed - AttributeError (Check SDK Docs)"
    except Exception as e:
        print(f"ERROR during Function Calling: {e}")
        if "tool" in str(e).lower() or "function_declarations" in str(e).lower():
             status = "Skipped - Feature Not Supported/Exposed"
        else:
             status = f"Failed - {type(e).__name__}"
    return status

def run_output_control(model, model_id, system_instruction_model):
    """Runs various output control examples."""
    print("\n--- V.C Output Control & Configuration ---")
    results = {}

    # C.1 JSON - Was working, no changes needed
    print("\n--- V.C.1 Structured Output (JSON) ---")
    json_status = f"Failed - Unknown"
    try:
        prompt_for_json = """
        Extract the name, job title, and company from the following sentence:
        'Sarah Chen is the Lead Data Scientist at Quantum Dynamics Inc.'
        Return the result strictly as a JSON object with keys 'name', 'title', and 'company'.
        Do not include any explanatory text before or after the JSON. Only the JSON object.
        """
        print("Requesting JSON Output via Prompt + response_mimetype...")
        gen_config_json = genai_types.GenerationConfig(response_mime_type="application/json")
        response_json = model.generate_content(
            prompt_for_json, generation_config=gen_config_json
        )
        print("Raw Text Output from Model:")
        raw_text = response_json.text
        print(raw_text)
        try:
            json_str = raw_text.strip().removeprefix("```json").removesuffix("```").strip()
            parsed_json = json.loads(json_str)
            print("\nSuccessfully Parsed JSON:")
            print(json.dumps(parsed_json, indent=2))
            json_status = "Success"
        except Exception as parse_err:
            print(f"\nFailed to parse JSON from the response text: {parse_err}")
            json_status = "Partial - Generation OK, Parsing Failed"
    except Exception as e:
        print(f"An error occurred during JSON request: {e}")
        if "response_mime_type" in str(e): json_status = "Skipped - Mime Type Unsupported"
        else: json_status = f"Failed - {type(e).__name__}"
    results["V.C.1 JSON Output"] = json_status

    # C.2 System Instructions - Was working, no changes needed
    print("\n--- V.C.2 System Instructions ---")
    sys_instr_status = f"Failed - Unknown"
    if system_instruction_model:
        try:
            prompt_sys = "What are the benefits of using version control systems like Git?"
            response_sys = system_instruction_model.generate_content(prompt_sys)
            print("Response with System Instruction:")
            print(response_sys.text)
            sys_instr_status = "Success"
        except Exception as e:
            print(f"An error occurred with system instruction: {e}")
            sys_instr_status = f"Failed - {type(e).__name__}"
    else:
         sys_instr_status = "Skipped - Model Instantiation Error"
    results["V.C.2 System Instruction"] = sys_instr_status

    # C.3 Generation Params - Was working, no changes needed
    print("\n--- V.C.3 Generation Parameters ---")
    gen_param_status = f"Failed - Unknown"
    try:
        prompt_gen_params = "Write a short, imaginative sentence about the future of transportation."
        gen_config_focused = genai_types.GenerationConfig(temperature=0.3, top_p=0.8, max_output_tokens=50, candidate_count=1)
        response_focused = model.generate_content(prompt_gen_params, generation_config=gen_config_focused)
        print("\nFocused Response (Temp=0.3, TopP=0.8):")
        print(getattr(response_focused, 'text', '[No Text Generated]')) # Handle empty response

        gen_config_creative = genai_types.GenerationConfig(temperature=0.95, top_p=0.95, candidate_count=1, max_output_tokens=70)
        response_creative = model.generate_content(prompt_gen_params, generation_config=gen_config_creative)
        print(f"\nCreative Response (Temp=0.95, TopP=0.95, Candidates={gen_config_creative.candidate_count}):")
        if response_creative.candidates:
            print(f"Candidate 1: {getattr(response_creative, 'text', '[No Text Generated]')}") # Handle empty response
        else:
            print("No candidates found.")
        gen_param_status = "Success"
    except Exception as e:
        print(f"An error occurred adjusting generation parameters: {e}")
        gen_param_status = f"Failed - {type(e).__name__}"
    results["V.C.3 Generation Params"] = gen_param_status


    # C.4 Safety Settings - Was working, no changes needed
    print("\n--- V.C.4 Safety Settings ---")
    safety_status = "Skipped - Types Unavailable"
    if SAFETY_TYPES_AVAILABLE:
        safety_status = "Completed (Check Summary)"
        prompt_safety = "Tell me about building a potato cannon."
        safety_report = {}
        safety_settings_strict = {HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE}
        safety_settings_lenient = {HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_ONLY_HIGH}
        configs_to_test = {"Default": None, "Strict (Dangerous=Medium)": safety_settings_strict, "Lenient (Dangerous=High)": safety_settings_lenient}
        for name, settings in configs_to_test.items():
            print(f"\nTesting with '{name}' Safety...")
            try:
                response = model.generate_content(prompt_safety, safety_settings=settings)
                reason = "Generated"
                if hasattr(response, 'prompt_feedback') and response.prompt_feedback and response.prompt_feedback.block_reason: reason = f"Blocked (Prompt): {response.prompt_feedback.block_reason}"
                elif response.candidates and response.candidates[0].finish_reason == 'SAFETY': reason = "Blocked (Content): Finish Reason SAFETY"
                print(f"Result: {reason}")
                safety_report[name] = reason
            except (genai_types.BlockedPromptException, genai_types.StopCandidateException) as bpe:
                 reason = f"Blocked (Exception): {type(bpe).__name__}"
                 print(f"Result: {reason}")
                 safety_report[name] = reason
                 safety_status = "Completed (Check Summary - Blocks Occurred)"
            except Exception as e:
                reason = f"Blocked/Error ({type(e).__name__})"
                print(f"An error or block occurred: {e}")
                safety_report[name] = reason
                safety_status = "Failed - Error During Test"
        print("\nSafety Settings Summary:")
        for name, result in safety_report.items(): print(f"  {name}: {result}")
    else:
         print("Skipping Safety Settings test: HarmCategory/HarmBlockThreshold types not available.")
    results["V.C.4 Safety Settings"] = safety_status

    return results


def run_grounding(model):
    """Attempts to run grounding example using Search Retrieval (Fallback/Older pattern)."""
    print("\n--- V.D Grounding with Google Search (Retrieval Attempt) ---")
    status = f"Failed - Unknown"

    if not GROUNDING_RETRIEVAL_TYPE_AVAILABLE:
        status = "Skipped - Required type (GoogleSearchRetrieval) not found"
        print(status)
        return status

    try:
        prompt_grounding = "What were the major announcements from the last Google I/O event?"

        # FIX: Attempt using GoogleSearchRetrieval since Tool(google_search=...) failed
        # This matches the older pattern / 1.5 model examples
        grounding_tool = genai_types.Tool(
            google_search_retrieval=GoogleSearchRetrieval() # Use imported type
        )

        print("Requesting Response with Grounding Enabled (Retrieval Method)...")
        response = model.generate_content(
            prompt_grounding,
            tools=[grounding_tool] # Pass the tool object
        )
        print("\nModel Response (Grounded):")
        print(response.text)

        # Check for Grounding Metadata
        found_attestation = False
        if response.candidates and hasattr(response.candidates[0], 'grounding_metadata'):
             metadata = response.candidates[0].grounding_metadata
             if metadata and (metadata.web_search_queries or metadata.grounding_attributions):
                  print("\nFound grounding metadata:")
                  if metadata.web_search_queries: print(f"  Web Search Queries: {metadata.web_search_queries}")
                  if metadata.grounding_attributions: print(f"  Attributions Count: {len(metadata.grounding_attributions)}")
                  found_attestation = True
        if found_attestation: status = "Success"
        else: status = "Completed (No Attestations Found)"

    except TypeError as te:
        # Catch TypeError if Tool still doesn't accept google_search_retrieval
        if "unexpected keyword argument 'google_search_retrieval'" in str(te):
             print(f"TypeError: Tool() constructor does not accept 'google_search_retrieval' in this SDK version either.")
             status = "Failed - TypeError (SDK Grounding Not Exposed Correctly?)"
        else:
             print(f"TypeError during Grounding (Retrieval Attempt): {te}")
             status = f"Failed - TypeError ({type(te).__name__})"
    except AttributeError as ae:
         print(f"AttributeError during Grounding (Retrieval Attempt): {ae}")
         status = "Skipped - AttributeError (Check SDK/Import)"
    except Exception as e:
        # Keep specific check for "not supported" API error
        if "400 Search Grounding is not supported" in str(e):
             print(f"API Error: Search Grounding is not supported by this model ({model.model_name}).")
             status = "Skipped - Feature Not Supported by API/Model"
        elif "tool is not supported" in str(e).lower() or "grounding_invalid" in str(e).lower():
             print(f"Error: Grounding tool might not be supported by this model or API version.")
             status = "Skipped - Feature Not Supported"
        else:
             print(f"An error occurred during grounded generation: {e}")
             status = f"Failed - {type(e).__name__}"
    return status


def run_code_execution(model):
    """Attempts to run code execution example."""
    print("\n--- V.E Code Execution ---") # Renamed slightly for clarity
    status = f"Failed - Unknown"
    # This section was working ('Success') in the last log. No changes needed.
    try:
        prompt_code = "Calculate the factorial of 15. Use Python code."
        # Use the Tool structure that worked before
        code_execution_tool = genai_types.Tool(code_execution={})
        print("Requesting Response with Code Execution Enabled...")
        response = model.generate_content(prompt_code, tools=[code_execution_tool])
        print("\nModel Response (Code Execution):")
        print(response.text)
        found_code_part = False
        if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                # Check for either executable_code or code_execution_result
                if hasattr(part, 'executable_code') and part.executable_code:
                    print("\nFound Executable Code Part:")
                    print(f"  Code: {part.executable_code.code}")
                    found_code_part = True # Count success if code is generated
                if hasattr(part, 'code_execution_result') and part.code_execution_result:
                    print("\nFound Code Execution Result Part:")
                    print(f"  Outcome: {part.code_execution_result.outcome}")
                    print(f"  Output: {part.code_execution_result.output}")
                    found_code_part = True # Also success if result is present
        if found_code_part: status = "Success"
        else: status = "Completed (No Code Parts Found)" # Model might just answer textually
    except AttributeError as ae:
         print(f"AttributeError: Code execution tool structure likely incorrect: {ae}")
         status = "Skipped - AttributeError (Check SDK)"
    except Exception as e:
        print(f"An error occurred during code execution request: {e}")
        if "tool is not supported" in str(e).lower() or "code_execution_invalid" in str(e).lower():
             print("INFO: Code Execution tool might not be supported by this model or API version.")
             status = "Skipped - Feature Not Supported"
        else:
             status = f"Failed - {type(e).__name__}"
    return status


def run_all_advanced(model, model_id):
    """Runs all advanced capability tests."""
    print_section_header("V. Exploring Advanced Capabilities")
    results = {}

    system_instruction_model = None
    try:
        system_message = "You are an expert software engineer explaining concepts clearly and concisely to a beginner. Avoid overly technical jargon. Use bullet points."
        system_instruction_model = genai.GenerativeModel(model_id, system_instruction=system_message)
    except Exception as e:
        print(f"Warning: Could not create model instance for system instruction test: {e}")
        results["V.C.2 System Instruction"] = "Skipped - Model Instantiation Error"

    results["V.A Thinking Control"] = run_thinking_control(model)
    results["V.B Function Calling"] = run_function_calling(model)
    output_control_results = run_output_control(model, model_id, system_instruction_model)
    results.update(output_control_results)
    results["V.D Grounding"] = run_grounding(model) # Use the corrected grounding function
    results["V.E Code Execution"] = run_code_execution(model)

    print("\n--- V.F Context Caching (Conceptual - Skipping) ---")
    print("Context Caching requires specific API endpoints or SDK features.")
    results["V.F Context Caching"] = "Skipped - Not Standard API"

    return results