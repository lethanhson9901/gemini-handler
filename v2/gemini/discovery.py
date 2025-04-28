# discovery.py
import google.generativeai as genai
from utils import print_section_header


def run_model_discovery(genai_module, target_model_name_full):
    """Lists models and gets details for the target model."""
    print_section_header("VII. Discovering Models Programmatically")
    status = f"Failed - Unknown"
    try:
        print("Listing available models supporting 'generateContent'...")
        count_gen = 0
        models_found = []
        for m in genai_module.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"- {m.name: <45} ({m.display_name})")
                models_found.append(m.name)
                count_gen += 1
        print(f"\nFound {count_gen} models supporting 'generateContent'.")

        if target_model_name_full in models_found:
            print(f"\nGetting Details for {target_model_name_full}...")
            try:
                model_info = genai_module.get_model(target_model_name_full)
                print(f"  Name: {getattr(model_info, 'name', 'N/A')}")
                print(f"  Display Name: {getattr(model_info, 'display_name', 'N/A')}")
                print(f"  Version: {getattr(model_info, 'version', 'N/A')}")
                print(f"  Input Limit: {getattr(model_info, 'input_token_limit', 'N/A')}")
                print(f"  Output Limit: {getattr(model_info, 'output_token_limit', 'N/A')}")
                print(f"  Supported Methods: {getattr(model_info, 'supported_generation_methods', 'N/A')}")
                status = "Success"
            except Exception as get_e:
                print(f"Could not retrieve details for {target_model_name_full}: {get_e}")
                status = f"Partial - List OK, Get Failed ({type(get_e).__name__})"
        else:
             print(f"\nTarget model {target_model_name_full} not found in list.")
             status = "Partial - List OK, Target Model Not Found"

    except Exception as e:
        print(f"An error occurred while listing/getting models: {e}")
        status = f"Failed - {type(e).__name__}"
    return status