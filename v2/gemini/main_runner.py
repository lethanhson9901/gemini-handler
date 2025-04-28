# main_runner.py
import advanced_features
import config
import core_interactions
import discovery
import google.generativeai as genai  # Import genai here too
import multimodal
import utils

if __name__ == "__main__":
    # --- Report Tracking ---
    report_status = {}

    utils.print_section_header(f"Gemini API Feature Runner ({config.MODEL_ID})")

    # --- II. Setup and Initialization ---
    utils.print_section_header("II. Setup and Initialization")
    report_status["II.A Installation"] = "Skipped - User Prerequisite"
    print("II.A Installation: Assumed user has run 'pip install -U google-generativeai requests Pillow'")

    print("\n--- II.B Authentication & Initialization ---")
    genai_configured, client_initialized = utils.initialize_gemini(
        config.API_KEY, config.FULL_MODEL_NAME_FOR_LISTING
    )
    report_status["II.B Initialization"] = "Success" if client_initialized else "Failed - Check Error Above"

    # --- Instantiate Model ---
    model = None
    if client_initialized:
        try:
            # Use the short Model ID from config
            model = genai_configured.GenerativeModel(config.MODEL_ID)
            print(f"GenerativeModel instance created for '{config.MODEL_ID}'.")
        except Exception as e:
            print(f"ERROR: Failed to instantiate GenerativeModel for {config.MODEL_ID}: {e}")
            client_initialized = False # Mark as failed if model instantiation fails
            report_status["II.B Initialization"] = f"Failed - Model Instantiation Error ({type(e).__name__})"

    # --- Run Sections ---
    if client_initialized and model:
        # --- III. Core Interactions ---
        # basic_status, inspect_status = core_interactions.run_basic_text(model)
        # report_status["III.A Basic Text"] = basic_status
        # report_status["III.C Inspect Response"] = inspect_status
        # report_status["III.D Streaming"] = core_interactions.run_streaming(model)

        # --- IV. Multimodal ---
        # multimodal_results = multimodal.run_all_multimodal(model)
        # report_status.update(multimodal_results) # Add multimodal results to main report

        # --- V. Advanced Features ---
        advanced_results = advanced_features.run_all_advanced(model, config.MODEL_ID)
        report_status.update(advanced_results)

        # --- VII. Discovery ---
        # Pass the configured genai module from utils.initialize_gemini
        report_status["VII Model Discovery"] = discovery.run_model_discovery(
            genai_configured, config.FULL_MODEL_NAME_FOR_LISTING
        )

    else:
        # --- Skip Sections if Initialization Failed ---
        init_status = report_status.get("II.B Initialization", "Unknown Failure")
        skip_reason = "Skipped - " + init_status
        print(f"\nSkipping Sections III, IV, V, VII due to initialization failure: {init_status}")
        report_status["III.A Basic Text"] = skip_reason
        report_status["III.C Inspect Response"] = skip_reason
        report_status["III.D Streaming"] = skip_reason
        report_status["IV.A Image+Text"] = skip_reason
        report_status["IV.B Video+Text"] = skip_reason
        report_status["IV.C Audio+Text"] = skip_reason
        report_status["IV.D PDF+Text"] = skip_reason
        report_status["IV.E Combined"] = skip_reason
        report_status["V.A Thinking Control"] = skip_reason
        report_status["V.B Function Calling"] = skip_reason
        report_status["V.C.1 JSON Output"] = skip_reason
        report_status["V.C.2 System Instruction"] = skip_reason
        report_status["V.C.3 Generation Params"] = skip_reason
        report_status["V.C.4 Safety Settings"] = skip_reason
        report_status["V.D Grounding"] = skip_reason
        report_status["V.E Code Execution"] = skip_reason
        report_status["V.F Context Caching"] = skip_reason
        report_status["VII Model Discovery"] = skip_reason


    # --- VI. Tooling (Informational) ---
    utils.print_section_header("VI. Essential Tooling")
    print("VI.A Google AI Studio: Web UI for prototyping (used for API Key).")
    print("VI.B Vertex AI Platform: GCP managed environment for production.")
    print("VI.C REST API: Direct HTTPS interface.")
    print("VI.D Community & Learning: Cookbook, Docs, Forums.")
    report_status["VI Tooling"] = "Informational"


    # --- Final Report ---
    utils.print_section_header("Final Execution Report")
    print(f"Gemini Model Used: {config.MODEL_ID}")
    print("-" * 60)
    if not client_initialized:
         init_status = report_status.get("II.B Initialization", "Unknown Failure")
         print(f"Core Initialization Failed ({init_status}). Most sections skipped.")

    # Define order for report keys if desired
    report_order = [
        "II.A Installation", "II.B Initialization",
        "III.A Basic Text", "III.C Inspect Response", "III.D Streaming",
        "IV.A Image+Text", "IV.B Video+Text", "IV.C Audio+Text", "IV.D PDF+Text", "IV.E Combined",
        "V.A Thinking Control", "V.B Function Calling", "V.C.1 JSON Output", "V.C.2 System Instruction",
        "V.C.3 Generation Params", "V.C.4 Safety Settings", "V.D Grounding", "V.E Code Execution", "V.F Context Caching",
        "VI Tooling", "VII Model Discovery"
    ]

    # Print sorted results, handling potential missing keys if a section failed catastrophically before reporting
    for section in report_order:
        status = report_status.get(section, "Status Not Recorded") # Get status safely
        status_indicator = "[INFO]"
        if "Success" in status or "Completed" in status or "Informational" in status or "OK" in status: status_indicator = "[OK]"
        elif "Skipped" in status: status_indicator = "[SKIPPED]"
        elif "Failed" in status or "Error" in status: status_indicator = "[FAILED]"
        elif "Partial" in status: status_indicator = "[PARTIAL]"
        elif "Not Recorded" in status: status_indicator = "[???]"

        print(f"{status_indicator: <10} {section: <30} | Status: {status}")

    print("=" * 60)
    print("Report Complete.")