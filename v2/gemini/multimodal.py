# multimodal.py
import google.generativeai as genai  # Import genai to access types
from utils import check_and_download, get_mime_type, print_section_header

# Import PIL for direct image handling, which is often supported
try:
    import PIL.Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("Warning: Pillow library not found. `pip install Pillow`. Image tests require it.")


def run_image_text(model):
    """Handles Image+Text input."""
    print("\n--- IV.A Image + Text ---")
    status = "Skipped - Pillow/PIL not available"
    image_part_for_combined = None # Return this for section E

    if not PIL_AVAILABLE:
        print("Skipping Image+Text: Pillow library (PIL.Image) is required.")
        return status, image_part_for_combined

    # This section was working ('Success') in the last log. No changes needed.
    try:
        image_path = check_and_download(
            "scones.jpg",
            "https://storage.googleapis.com/generativeai-downloads/images/scones.jpg",
            "image"
        )
        if image_path:
            print(f"Using local image: {image_path}")
            img = PIL.Image.open(image_path)
            image_part_for_combined = img # Store the PIL Image object
            prompt_text = "Describe this image in detail. What food items are present and what is the setting?"
            contents = [prompt_text, img]
            response = model.generate_content(contents)
            print("\nImage + Text Response:")
            print(response.text)
            status = "Success"
        else:
            print("Skipping Image+Text: Sample image download/validation failed.")
            status = "Skipped - File Error"
    except Exception as e:
        print(f"ERROR during Image+Text generation: {e}")
        status = f"Failed - {type(e).__name__}"
        image_part_for_combined = None

    return status, image_part_for_combined

def run_video_text(model):
    """Handles Video+Text input using GCS URI."""
    print("\n--- IV.B Video + Text ---")
    status = f"Failed - Unknown"
    try:
        gcs_video_uri = "gs://cloud-samples-data/video/animals.mp4"
        video_mime_type = "video/mp4"
        print(f"Using video from GCS: {gcs_video_uri}")

        # FIX: Revert to using the dictionary structure for URI as Part.from_uri caused AttributeError
        video_part = {
            "file_data": {
                "mime_type": video_mime_type,
                "file_uri": gcs_video_uri
            }
        }

        prompt_text = "What animals appear briefly in this video? Describe one scene."
        contents = [prompt_text, video_part] # Pass prompt and the dictionary part
        response = model.generate_content(contents)
        print("\nVideo + Text Response:")
        print(response.text)
        status = "Success"
    except Exception as e:
         # Keep specific error checks
         if "Unable to retrieve URI" in str(e) or "permission" in str(e).lower():
              print(f"ERROR during Video+Text generation: Could not access GCS URI {gcs_video_uri}. Check URI and permissions.")
              status = f"Failed - GCS Access Error"
         elif "400 Request contains an invalid argument" in str(e):
             print(f"ERROR during Video+Text generation: API returned Invalid Argument (400). Check if model supports video or URI format/permissions.")
             status = f"Failed - InvalidArgument (API)"
         else:
              print(f"ERROR during Video+Text generation: {e}")
              status = f"Failed - {type(e).__name__}"
    return status


def run_audio_text(model):
    """Handles Audio+Text input from local file."""
    print("\n--- IV.C Audio + Text ---")
    status = f"Failed - Unknown"
    audio_part_for_combined = None # Return this for section E

    # This section was working ('Success') in the last log. No changes needed.
    try:
        audio_path = check_and_download(
            "pixel.mp3",
            "https://storage.googleapis.com/cloud-samples-data/generative-ai/audio/pixel.mp3",
            "audio"
        )
        if audio_path:
             mime_type = get_mime_type(audio_path, 'audio')
             if mime_type:
                 print(f"Using local audio: {audio_path} (MIME Type: {mime_type})")
                 audio_data = audio_path.read_bytes()
                 # Using dict for inline data was working
                 audio_part = {
                     "inline_data": {
                         "mime_type": mime_type,
                         "data": audio_data
                     }
                 }
                 audio_part_for_combined = audio_part # Store the dict part
                 prompt_text = "Please transcribe the speech in this short audio file."
                 contents = [prompt_text, audio_part]
                 response = model.generate_content(contents)
                 print("\nAudio + Text Response:")
                 # Truncate long transcriptions for the report
                 print(response.text[:1000] + "..." if len(response.text) > 1000 else response.text)
                 status = "Success"
             else:
                 print("Skipping Audio+Text: Could not determine MIME type.")
                 status = "Skipped - MIME Type Error"
        else:
            print("Skipping Audio+Text: Sample audio download/validation failed.")
            status = "Skipped - File Error"
    except Exception as e:
        print(f"ERROR during Audio+Text generation: {e}")
        status = f"Failed - {type(e).__name__}"
        audio_part_for_combined = None

    return status, audio_part_for_combined

def run_pdf_text(model):
    """Handles PDF+Text input from local file."""
    print("\n--- IV.D PDF + Text ---")
    status = f"Failed - Unknown"

    # This section was working ('Success') in the last log. No changes needed.
    try:
        pdf_path = check_and_download(
            "sample_paper.pdf",
            "https://arxiv.org/pdf/1706.03762", # Attention is All You Need
            "PDF"
        )
        if pdf_path:
            pdf_mime_type = "application/pdf"
            print(f"Using local PDF: {pdf_path}")
            # Using dict for inline data was working
            pdf_part = {
                 "inline_data": {
                     "mime_type": pdf_mime_type,
                     "data": pdf_path.read_bytes()
                 }
            }
            prompt_text = "What is the main topic of this document? Summarize its abstract or introduction briefly."
            contents = [prompt_text, pdf_part]
            response = model.generate_content(contents)
            print("\nPDF + Text Response:")
            print(response.text)
            status = "Success"
        else:
            print("Skipping PDF+Text: Sample PDF download/validation failed.")
            status = "Skipped - File Error"
    except Exception as e:
        print(f"ERROR during PDF+Text generation: {e}")
        status = f"Failed - {type(e).__name__}"
    return status


def run_combined_modalities(model, image_input, audio_input):
    """Handles combined Image+Audio+Text input."""
    print("\n--- IV.E Combining Modalities (Image + Audio + Text) ---")
    status = "Skipped - Missing valid input"

    # This section was working ('Success') in the last log. No changes needed.
    if image_input and audio_input:
        try:
            prompt_text = "Consider the provided image and audio clip. Describe the scene shown in the image. Does the audio seem related to the visual content? Explain briefly."
            contents = [prompt_text, image_input, audio_input]
            print("Sending combined request (Text + Image Object + Audio Dict)...")
            response = model.generate_content(contents)
            print("\nCombined Modalities Response:")
            print(response.text)
            status = "Success"
        except Exception as e:
            print(f"ERROR during combined modalities generation: {e}")
            status = f"Failed - {type(e).__name__}"
    else:
        print("Skipping combined modalities: Missing valid image or audio part from previous steps.")

    return status

def run_all_multimodal(model):
    """Runs all multimodal tests and returns their statuses."""
    print_section_header("IV. Leveraging Multimodal Inputs")
    results = {}
    img_status, img_part = run_image_text(model)
    results["IV.A Image+Text"] = img_status
    aud_status, aud_part = run_audio_text(model)
    results["IV.C Audio+Text"] = aud_status
    results["IV.B Video+Text"] = run_video_text(model) # Run video test
    results["IV.D PDF+Text"] = run_pdf_text(model)
    results["IV.E Combined"] = run_combined_modalities(model, img_part, aud_part)
    return results