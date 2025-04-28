# core_interactions.py
import google.generativeai as genai
from utils import print_response_summary, print_section_header


def run_basic_text(model):
    """Runs basic text generation and response inspection."""
    print_section_header("III. Core Interaction: Generating Content")
    print("\n--- III.A Basic Text Generation ---")
    status = f"Failed - Unknown"
    response = None
    try:
        prompt = "Explain the concept of 'thinking budget' in Gemini 2.5 Flash in simple terms."
        response = model.generate_content(prompt)
        print("Basic Text Response:")
        print(response.text)
        status = "Success"
    except Exception as e:
        print(f"ERROR during Basic Text Generation: {e}")
        status = f"Failed - {type(e).__name__}"
        return status, "Skipped - Error in Basic Text" # Skip inspection if basic fails

    print("\n--- III.C Inspecting Response Object ---")
    inspection_status = f"Failed - Unknown"
    try:
        if response:
            print_response_summary(response)
            inspection_status = "Success"
        else:
            inspection_status = "Skipped - No Response Object"
    except Exception as e:
        print(f"ERROR during Response Inspection: {e}")
        inspection_status = f"Failed - {type(e).__name__}"

    return status, inspection_status


def run_streaming(model):
    """Runs streaming text generation."""
    print("\n--- III.D Streaming Responses ---")
    status = f"Failed - Unknown"
    try:
        prompt_stream = "Write a short story about a curious robot exploring Mars."
        response_stream = model.generate_content(
            prompt_stream,
            stream=True
        )
        print("Streaming Response Start:")
        full_response_text = ""
        final_metadata = None

        for chunk in response_stream:
            if hasattr(chunk, 'usage_metadata') and chunk.usage_metadata:
                final_metadata = chunk.usage_metadata # Capture last known metadata

            if chunk.parts:
                 print(chunk.text, end="", flush=True)
                 full_response_text += chunk.text
            elif hasattr(chunk, 'prompt_feedback') and chunk.prompt_feedback and chunk.prompt_feedback.block_reason:
                 print(f"\n\nSTREAM BLOCKED (Prompt): {chunk.prompt_feedback.block_reason}")
                 break
            elif chunk.candidates and chunk.candidates[0].finish_reason == 'SAFETY':
                print(f"\n\nSTREAM BLOCKED (Content): Finish Reason SAFETY")
                break

        print("\n--- End of Stream ---")

        # Attempt to get final metadata
        usage_info_printed = False
        if final_metadata:
            print(f"\nUsage Metadata (captured from stream):")
            print(f"  Prompt Tokens: {getattr(final_metadata, 'prompt_token_count', 'N/A')}")
            print(f"  Candidates Tokens: {getattr(final_metadata, 'candidates_token_count', 'N/A')} (May be 0 in stream)")
            print(f"  Total Tokens: {getattr(final_metadata, 'total_token_count', 'N/A')}")
            usage_info_printed = True
        else:
            # Try resolving the stream object (SDK dependent)
            try:
                # This resolve() might or might not exist or work depending on SDK state
                final_usage = response_stream.usage_metadata
                if final_usage:
                    print(f"\nUsage Metadata (from resolved stream):")
                    print(f"  Prompt Tokens: {getattr(final_usage, 'prompt_token_count', 'N/A')}")
                    print(f"  Candidates Tokens: {getattr(final_usage, 'candidates_token_count', 'N/A')}")
                    print(f"  Total Tokens: {getattr(final_usage, 'total_token_count', 'N/A')}")
                    usage_info_printed = True
            except Exception:
                 pass # Ignore if resolve fails

        if not usage_info_printed:
            print("\nUsage Metadata: Not available or reliably captured after stream completion.")

        status = "Success"
    except Exception as e:
        print(f"\nERROR during Streaming: {e}")
        status = f"Failed - {type(e).__name__}"
    return status