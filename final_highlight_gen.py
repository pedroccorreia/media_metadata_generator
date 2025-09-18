#Required Imports
from typing import Optional, Dict, Any, List
from google import genai
from google.genai.types import Part, GenerateContentConfig
import json
import os
import traceback
import tempfile
from moviepy import VideoFileClip
from prompts import VIDEO_OVERVIEW_PROMPT, VIDEO_CHUNKING_PROMPT, REEL_ANALYSIS_PROMPT
from video_creator import create_final_highlight_reel
from utils import (
    seconds_to_mmss, 
    smooth_segment_boundaries,    
    mmss_to_seconds, 
    extract_json_from_response, 
    initialize_vertex_client,
    validate_timestamp_markers, 
    detect_segment_overlap)
from get_video_gcs import download_from_gcs
from google.cloud import storage


from dotenv import load_dotenv
# This line loads the variables from .env into the environment
load_dotenv()


### Function to analyze video overview and extract master character list

def analyze_video_overview(video_url: str, duration: int, model_id: str = 'gemini-2.5-flash') -> Optional[Dict[str, Any]]:
    """
    Step 2.1: Analyze entire video to get overview and master character list.
    Uses Gemini Flash for faster, cost-effective analysis.
    
    Args:
        video_url: YouTube video URL
        duration: Video duration in seconds
        model_id: Gemini model to use (default: flash)
        
    Returns:
        Dict with video overview data or None if failed
    """
    try:
        # Extract video ID (Optional)
        #video_id = extract_youtube_video_id(video_url)
        #if not video_id:
        #    return None
        
        # Initialize Vertex AI client
        client = initialize_vertex_client()
        
        # Create overview prompt
        prompt = VIDEO_OVERVIEW_PROMPT.format(
            video_info=f"{duration} seconds"
        )
        
        # Generate analysis using Vertex AI client with video Part
        print(f"Analyzing video overview with {model_id}...")
        print(f"Video URL: {video_url}")
        
        try:
            # Try to create the video part
            video_part = Part.from_uri(
                file_uri=video_url,
                mime_type="video/webm",
            )
            print("Successfully created video Part from URI")
            
            # Generate content - VIDEO FIRST (best practice)
            response = client.models.generate_content(
                model=model_id,
                contents=[video_part, prompt],  # Video before prompt
            )
            print("Successfully generated video overview")
        except Exception as e:
            print(f"ERROR in analyze_video_overview: {str(e)}")
            print(f"Error type: {type(e).__name__}")
            raise Exception(f"Failed to analyze video overview: {str(e)}") from e
        
        # Parse the response
        response_text = response.text
        
        # Extract and parse JSON
        json_text = extract_json_from_response(response_text)
        overview_data = json.loads(json_text)
        
        # Add video_id to the data
        # overview_data['video_id'] = video_id
        
        # Log character count
        char_count = len(overview_data.get('master_character_list', []))
        print(f"✓ Video overview complete: Found {char_count} characters")
        print(f"✓ Video type: {overview_data.get('video_type', 'unknown')}")
        
        return overview_data
        
    except Exception as e:
        print(f"Error in analyze_video_overview: {e}")
        traceback.print_exc()
        return None

### Function to chunk video into segments with character validation
# Configuration for video chunking - low temperature for deterministic results
video_chunking_config = GenerateContentConfig(
    temperature=0.01
)

def chunk_video_segments(video_url: str, duration: int, video_overview: Optional[Dict[str, Any]] = None, model_id: str = 'gemini-2.5-pro') -> Optional[Dict[str, Any]]:
    """
    Step 2: Use Gemini AI to chunk video into segments with metadata.
    Uses Gemini's multimodal capabilities to analyze video content.
    
    Args:
        video_url: GCS video URL fetched from Firestore
        duration: Video duration in seconds fetched from Firestore
        video_overview: Optional video overview data with master character list from previous step
        model_id: Gemini model to use
        
    Returns:
        Dict with segmented video data or None if failed
    """
    try:
        # Extract video ID
        # video_id = extract_youtube_video_id(video_url)
        # if not video_id:
        #    return None

        # We no longer need metadata since we're only using duration
        
        # Initialize Vertex AI client
        client = initialize_vertex_client()
        
        # Create video context if overview is provided
        video_context = ""
        if video_overview:
            char_list = video_overview.get('master_character_list', [])
            char_names = [f"- {c['name']} ({c['role']}): {c['description']}" for c in char_list]
            video_context = f"""**VIDEO OVERVIEW - YOU MUST USE THIS INFORMATION:**
- Overall Summary: {video_overview.get('overall_summary', 'N/A')}
- Video Type: {video_overview.get('video_type', 'N/A')}

**MASTER CHARACTER LIST (YOU MAY ONLY USE THESE CHARACTERS):**
{chr(10).join(char_names)}

Total Characters: {len(char_list)}
"""
        
        # Create a context-aware prompt with video duration in MM:SS format
        duration_mmss = seconds_to_mmss(duration)
        prompt = VIDEO_CHUNKING_PROMPT.format(
            video_context=video_context,
            video_info=f"{duration} seconds ({duration_mmss})"
        )
        
        # Generate analysis using Vertex AI client with video Part
        print(f"Analyzing video with {model_id}...")
        print(f"Video URL: {video_url}")
        print(f"Duration: {duration_mmss}")
        
        try:
            # Try to create the video part
            video_part = Part.from_uri(
                file_uri=video_url,
                mime_type="video/webm",
            )
            print("Successfully created video Part from URI")
            
            # Generate content - VIDEO FIRST (best practice)
            response = client.models.generate_content(
                model=model_id,
                contents=[video_part, prompt],  # Video before prompt
                config=video_chunking_config,
            )
            print("Successfully generated content from Vertex AI")
        except Exception as e:
            print(f"ERROR in generate_content: {str(e)}")
            print(f"Error type: {type(e).__name__}")
            # Try alternative approach or raise with more context
            raise Exception(f"Failed to analyze video: {str(e)}") from e
        
        # Parse the response
        response_text = response.text
        
        # Extract and parse JSON
        json_text = extract_json_from_response(response_text)
        segments_data = json.loads(json_text)
        
        # Create master character name list for validation
        master_char_names = []
        if video_overview:
            master_char_names = [char['name'].lower() for char in video_overview.get('master_character_list', [])]
        
        # Process and validate segments with new format
        print("Processing segments with enhanced validation...")
        validated_segments = []
        
        for seg in segments_data.get('segments', []):
            segment_id = seg.get('segment_id', 'unknown')
            # Convert MM:SS format to seconds
            start = mmss_to_seconds(seg.get('start_timestamp', '00:00'))
            end = mmss_to_seconds(seg.get('end_timestamp', '00:00'))
            
            # Check segment duration
            segment_duration = end - start
            if segment_duration > 30:
                print(f"⚠️  Warning: Segment {segment_id} exceeds 30s limit ({segment_duration}s)")
                print(f"   Original: {seconds_to_mmss(start)} - {seconds_to_mmss(end)}")
                end = start + 30
                print(f"   Adjusted: {seconds_to_mmss(start)} - {seconds_to_mmss(end)}")
            
            # Extract boundary verification data
            boundary_data = seg.get('boundary_verification', {})
            alignment_check = seg.get('alignment_check', {})
            
            # Validate alignment checks
            if not all(alignment_check.values()):
                print(f"⚠️  Alignment issues in segment {segment_id}:")
                if not alignment_check.get('summary_matches_video'):
                    print(f"   - Summary doesn't match video content")
                if not alignment_check.get('characters_match_summary'):
                    print(f"   - Characters don't match summary")
                if not alignment_check.get('no_temporal_bleeding'):
                    print(f"   - Temporal bleeding detected (content from outside timestamps)")
            
            # Validate characters against master list
            characters = seg.get('characters', [])
            if video_overview and master_char_names:
                for char in characters:
                    if char.lower() not in master_char_names:
                        print(f"⚠️  ERROR: Character '{char}' in segment {segment_id} NOT in master character list!")
                        print(f"   Available characters: {', '.join([c['name'] for c in video_overview.get('master_character_list', [])])}")
            
            # Check main_plot quality
            main_plot = seg.get('main_plot', '')
            if not main_plot:
                print(f"⚠️  Warning: Segment {segment_id} has empty main_plot")
                continue
                
            # Run enhanced validation with auto-correction suggestions
            validation_result = validate_timestamp_markers(seg)
            
            if validation_result['needs_adjustment']:
                print(f"⚠️  Validation issues in segment {segment_id}:")
                for issue in validation_result['issues']:
                    print(f"   - {issue}")
                
                # Apply suggested adjustments
                suggestions = validation_result['suggestions']
                if suggestions['adjust_start'] != 0:
                    new_start = max(0, start + suggestions['adjust_start'])
                    print(f"   → Adjusting start from {start}s to {new_start}s")
                    start = new_start
                
                if suggestions['adjust_end'] != 0:
                    new_end = min(duration, end + suggestions['adjust_end'])
                    print(f"   → Adjusting end from {end}s to {new_end}s")
                    end = new_end
                
                print(f"   → Confidence score: {suggestions['confidence']}/10")
            
            # Build validated segment with enhanced metadata
            validated_segment = {
                'segment_id': segment_id,
                'start_timestamp': float(start),
                'end_timestamp': float(end),
                'characters': characters,
                'main_plot': main_plot,
                'tension_level': seg.get('tension_level', 'medium'),
                'importance_score': int(seg.get('importance_score', 5)),
                'boundary_verification': boundary_data,
                'alignment_validated': all(alignment_check.values()),
                'validation_confidence': validation_result['suggestions']['confidence']
            }
            
            # Only include segments with reasonable confidence
            if validation_result['suggestions']['confidence'] >= 5:
                validated_segments.append(validated_segment)
            else:
                print(f"⚠️  Skipping segment {segment_id} due to low confidence score")
        
        # Return the validated segments with video overview if provided
        result = {
            'segments': validated_segments,
            'total_segments': len(validated_segments),
            'video_duration': duration
        }
        
        # Include video overview data if available
        if video_overview:
            result['video_overview'] = video_overview
        
        return result
        
    except Exception as e:
        print(f"Error in chunk_video_segments: {e}")
        traceback.print_exc()
        return None


## Function to detect overlaps between segments and suggest boundary smoothing

def analyze_reel_flow(segments_data: Dict[str, Any], target_duration: int, model_id: str = 'gemini-2.5-pro') -> Optional[Dict[str, Any]]:
    """
    Step 3: Use Gemini AI to analyze and select best segments for reel with boundary smoothing.
    
    Args:
        segments_data: Output from chunk_video_segments
        target_duration: Target duration for the reel
        model_id: Gemini model to use
        
    Returns:
        Dict with selected segments or None if failed
    """
    try:
        # Initialize Vertex AI client
        client = initialize_vertex_client()
        
        # Filter segments by confidence if available
        high_confidence_segments = [
            seg for seg in segments_data['segments']
            if seg.get('validation_confidence', 10) >= 7
        ]
        
        if len(high_confidence_segments) < len(segments_data['segments']):
            print(f"Filtered to {len(high_confidence_segments)} high-confidence segments")
        
        # Use high confidence segments if available, otherwise use all
        segments_to_analyze = high_confidence_segments if high_confidence_segments else segments_data['segments']
        
        # Prepare the prompt
        prompt = REEL_ANALYSIS_PROMPT.format(
            target_duration=target_duration,
            min_duration=min(90, target_duration),
            max_duration=120,
            segments=json.dumps(segments_to_analyze, indent=2)
        )
        
        # Generate analysis using Vertex AI client
        print(f"Selecting best segments for highlight reel...")
        response = client.models.generate_content(
            model=model_id,
            contents=[prompt],
        )
        
        # Parse the response
        response_text = response.text
        
        # Extract and parse JSON
        json_text = extract_json_from_response(response_text)
        selection_data = json.loads(json_text)
        
        # Sort selected segments by order
        selected_segments = sorted(
            selection_data.get('selected_segments', []), 
            key=lambda x: x.get('order', 0)
        )
        
        # Check for overlaps
        print("Checking for segment overlaps...")
        overlaps = []
        for i in range(len(selected_segments) - 1):
            overlap = detect_segment_overlap(selected_segments[i], selected_segments[i + 1])
            if overlap:
                overlaps.append(overlap)
                print(f"⚠️  Overlap detected: {overlap['duration']}s between segments {overlap['segments']}")
        
        # Smooth boundaries if needed
        if any(seg.get('alignment_validated') for seg in selected_segments):
            print("Applying boundary smoothing...")
            selected_segments = smooth_segment_boundaries(selected_segments)
        
        # Recalculate total duration after smoothing
        total = sum(seg['end_timestamp'] - seg['start_timestamp'] 
                   for seg in selected_segments)
        
        selection_data['selected_segments'] = selected_segments
        selection_data['actual_total_duration'] = total
        selection_data['overlaps_detected'] = len(overlaps)
        selection_data['boundary_smoothing_applied'] = True
        
        print(f"✓ Final selection: {len(selected_segments)} segments, {total}s total duration")
        
        return selection_data
        
    except Exception as e:
        print(f"Error in analyze_reel_flow: {e}")
        traceback.print_exc()
        return None


def create_highlight_reel(video_url: str,duration: int, model_id: str = 'gemini-2.5-pro') -> Dict[str, Any]:
    """
    Main orchestrator function for the 4-step highlight reel generation process.
    
    Args:
        video_url: GCS video URL fetched from Firestore
        duration: Video duration in seconds fetched from Firestore
        model_id: AI model to use
        
    Returns:
        Dict with success status and generated HTML or error message
    """
    try:
        target_duration = min(90, duration // 4)
        target_duration = min(target_duration, 120) # Ensure it doesn't exceed 120s
        print(f"Video duration: {duration}s, Target reel duration: {target_duration}s")


        print(f"Starting highlight reel generation for: {video_url}")
        # Step 1: Get video overview with master character list
        print("\n=== Step 1: Analyzing video overview ===")
        video_overview = analyze_video_overview(video_url, duration,model_id)
        if video_overview:
            print(f"✓ Video title: {video_overview.get('video_title', 'N/A')}")
            print(f"✓ Found {len(video_overview.get('master_character_list', []))} characters")
            print(f"✓ Video type: {video_overview.get('video_type', 'N/A')}")
            print(f"✓ Overall summary: {video_overview.get('overall_summary', 'N/A')}")
        else:
            print("⚠️  Warning: Could not generate video overview, proceeding without character constraints")

        
        # Step 2: Chunk video into segments with character validation
        print("\n=== Step 2: Chunking video into segments ===")
        segments_data = chunk_video_segments(video_url, duration, video_overview, model_id)
        if not segments_data:
            return {
                'success': False,
                'error': 'Failed to analyze video segments. Video may not have captions/transcript available.'
            }
        
        print(f"Successfully chunked video into {segments_data['total_segments']} segments")

        # Step 3: Analyze and select best segments
        selection_data = analyze_reel_flow(segments_data, target_duration, model_id)
        if not selection_data:
            return {
                'success': False,
                'error': 'Failed to select highlight segments'
            }
        
        selected_segments = selection_data.get('selected_segments', [])
        print(f"Successfully selected as: {selected_segments}")
        print(f"Selected {len(selected_segments)} segments for highlight reel")

        # Step 4: Concatenate selected segments into final highlight reel
        print("\n=== Step 4: Creating final highlight reel ===")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            print(f"Downloading source video from {video_url}...")
            try:
                local_video_path = download_from_gcs(video_url, temp_dir)
            except Exception as e:
                print(f"Error downloading video from GCS: {e}")
                return {'success': False, 'error': f'Failed to download video from GCS: {e}'}

            segment_paths = []
            with VideoFileClip(local_video_path) as video:
                for i, segment in enumerate(selected_segments):
                    start_time = segment['start_timestamp']
                    end_time = segment['end_timestamp']
                    segment_id = segment['segment_id']
                    
                    print(f"Clipping segment {segment_id} ({start_time:.2f}s - {end_time:.2f}s)...")
                    clip_path = os.path.join(temp_dir, f"segment_{i+1}_{segment_id}.mp4")
                    
                    subclip = video.subclipped(start_time, end_time)
                    subclip.write_videofile(clip_path, codec="libx264", audio_codec="aac", logger=None)
                    segment_paths.append(clip_path)

            output_file_name = f"highlight_{os.path.basename(video_url).split('.')[0]}.mp4"
            output_highlight_path = create_final_highlight_reel(segment_paths, output_path=output_file_name)

            #Upload to GCS
            if output_highlight_path:
                print(f"✓ Successfully created highlight reel: {output_highlight_path}")
               
                BUCKET_NAME = "fox-metadata-output"
                DESTINATION_BLOB_NAME = f"video-highlights/{output_file_name}"
                storage_client = storage.Client()
                bucket = storage_client.bucket(BUCKET_NAME)
                blob = bucket.blob(DESTINATION_BLOB_NAME)
                print(f"Uploading {output_highlight_path} to gs://{BUCKET_NAME}/{DESTINATION_BLOB_NAME}...")
                blob.upload_from_filename(output_highlight_path)
        
                gcs_uri = f"gs://{BUCKET_NAME}/{DESTINATION_BLOB_NAME}"
                print(f"✓ Successfully uploaded highlight to GCS: {gcs_uri}")
                return {'success': True, 'output_path': output_highlight_path}
            else:
                return {'success': False, 'error': 'Failed to create final highlight reel'}


    except Exception as e:
        print(f"Error in create_highlight_reel: {e}")
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e)
        }