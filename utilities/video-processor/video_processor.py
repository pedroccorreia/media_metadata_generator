import logging
import os
import tempfile
from moviepy.editor import VideoFileClip, ImageClip, concatenate_videoclips, CompositeVideoClip, ColorClip
from storage_utils import download_from_gcs, upload_blob, parse_gcs_uri

# --- NEW IMPORTS for robust image handling ---
from PIL import Image
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def timecode_to_seconds(timecode: str) -> float:
    """Converts a HH:MM:SS.ms or MM:SS.ms timecode string to total seconds as a float."""
    try:
        if '.' in timecode:
            main_part, ms_part = timecode.split('.')
            milliseconds = int(ms_part) / 1000.0
        else:
            main_part = timecode
            milliseconds = 0.0

        parts = list(map(int, main_part.split(':')))
        
        if len(parts) > 0 and parts[-1] > 99:
            last_part = str(parts[-1])
            seconds_part = int(last_part[:-3])
            ms_part = int(last_part[-3:])
            parts[-1] = seconds_part
            milliseconds += ms_part / 1000.0
        
        seconds = 0
        if len(parts) == 3:  # HH:MM:SS
            seconds = parts[0] * 3600 + parts[1] * 60 + parts[2]
        elif len(parts) == 2:  # MM:SS
            seconds = parts[0] * 60 + parts[1]
        else:
            raise ValueError("Timecode must be in HH:MM:SS or MM:SS format.")
            
        return seconds + milliseconds
    except (ValueError, IndexError) as e:
        logging.error(f"Could not parse invalid timecode format: '{timecode}'. Error: {e}")
        raise

def trim_and_add_logo(main_video_path: str, start_time: float, end_time: float, output_path: str, logo_path: str = None, logo_duration: int = 3):
    """Trims a video clip, adds a logo at the end, and saves the result."""
    logging.info(f"Processing clip from {start_time:.2f}s to {end_time:.2f}s...")
    try:
        with VideoFileClip(main_video_path) as main_video:
            if start_time >= main_video.duration:
                logging.error(f"Start time ({start_time:.2f}s) is beyond video's duration ({main_video.duration:.2f}s). Skipping.")
                return None
            if end_time > main_video.duration:
                logging.warning(f"End time ({end_time:.2f}s) is beyond video duration. Trimming to end ({main_video.duration:.2f}s).")
                end_time = main_video.duration
            if start_time >= end_time:
                 logging.error(f"Start time ({start_time:.2f}s) is after end time ({end_time:.2f}s). Skipping.")
                 return None
            
            trimmed_clip = main_video.subclip(start_time, end_time)
            final_clips_to_join = [trimmed_clip]

            if logo_path:
                logging.info("Logo path provided. Creating logo video clip.")
                
                # --- START OF FIX ---
                # Robustly load the logo image to handle different PNG formats and prevent channel errors.
                with Image.open(logo_path) as pil_logo:
                    # Convert to RGBA to ensure it has an alpha channel for transparency
                    rgba_logo = pil_logo.convert("RGBA")
                    
                    # Separate the RGB (color) and Alpha (transparency) channels into numpy arrays
                    rgb_array = np.array(rgba_logo)[:, :, :3]
                    alpha_array = np.array(rgba_logo)[:, :, 3]

                    # Create the main logo clip from the 3-channel RGB color data
                    logo_clip = ImageClip(rgb_array)
                    
                    # Create the mask clip from the single-channel Alpha data
                    mask_clip = ImageClip(alpha_array, ismask=True)
                    
                    # Apply the transparency mask to the logo clip
                    logo = logo_clip.set_mask(mask_clip)
                # --- END OF FIX ---

                logo = (logo
                        .set_duration(logo_duration)
                        .resize(height=int(trimmed_clip.h * 0.15))
                        .set_position(("center", "center")))
                        
                background = ColorClip(size=trimmed_clip.size, color=(255, 255, 255), duration=logo_duration).set_fps(trimmed_clip.fps)
                logo_video_clip = CompositeVideoClip([background, logo])
                final_clips_to_join.append(logo_video_clip)

            final_clip = concatenate_videoclips(final_clips_to_join, method="compose")
            final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac")
        logging.info(f"Successfully created clip: {output_path}")
        return output_path
    except Exception as e:
        logging.error(f"Error during video processing for clip {start_time:.2f}s-{end_time:.2f}s: {e}", exc_info=True)
        return None

def process_video_from_document_data(doc_data: dict, document_id: str):
    """Main orchestrator function that downloads, processes, and uploads clips."""
    main_video_gs_path = doc_data.get("file_path")
    logo_gs_path = doc_data.get("logo_path")
    sections = doc_data.get("summary", {}).get("sections", [])
    output_bucket_uri = doc_data.get("output_bucket_uri")

    if not all([main_video_gs_path, sections, output_bucket_uri]):
        logging.error("Missing 'file_path', 'sections', or 'output_bucket_uri' in document. Aborting.")
        return

    if not output_bucket_uri.startswith("gs://"):
        logging.error(f"Invalid 'output_bucket_uri' provided: {output_bucket_uri}")
        return
    output_bucket_name = output_bucket_uri.replace("gs://", "").strip("/")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        logging.info(f"Created temporary directory: {temp_dir}")
        local_video_path = download_from_gcs(main_video_gs_path, temp_dir)
        local_logo_path = download_from_gcs(logo_gs_path, temp_dir) if logo_gs_path else None

        for i, section in enumerate(sections):
            clip_num = i + 1
            logging.info(f"--- Processing Section {clip_num} ---")
            start_tc = section.get("start_time")
            end_tc = section.get("end_time")

            if not start_tc or not end_tc:
                logging.warning(f"Skipping section {clip_num} due to missing timecodes.")
                continue
            
            try:
                start_seconds = timecode_to_seconds(start_tc)
                end_seconds = timecode_to_seconds(end_tc)

                output_filename = f"clip_{clip_num}_{os.path.basename(local_video_path)}"
                local_output_path = os.path.join(temp_dir, output_filename)
                
                processed_clip_path = trim_and_add_logo(
                    main_video_path=local_video_path,
                    start_time=start_seconds,
                    end_time=end_seconds,
                    output_path=local_output_path,
                    logo_path=local_logo_path
                )
                
                if processed_clip_path:
                    destination_blob_name = f"processed_clips/{document_id}/{output_filename}"
                    logging.info(f"Uploading {local_output_path} to gs://{output_bucket_name}/{destination_blob_name}")
                    upload_blob(output_bucket_name, processed_clip_path, destination_blob_name)
                    logging.info(f"Successfully uploaded clip {clip_num}.")
                else:
                    logging.error(f"Failed to process clip {clip_num}, skipping upload.")

            except Exception as e:
                logging.error(f"An unexpected error occurred processing section {clip_num}: {e}", exc_info=True)

        logging.info("--- All sections processed. ---")

