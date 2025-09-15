import re
import os
from typing import Dict, Any, List, Optional
from google import genai

def initialize_vertex_client():
    """
    Initialize Vertex AI client with project settings.
    
    Returns:
        genai.Client configured for Vertex AI
    """
    PROJECT_ID = os.environ.get('GCP_PROJECT_ID')
    LOCATION = os.environ.get('GCP_LOCATION', 'us-central1')
    
    print(f"Initializing Vertex AI client...")
    print(f"  PROJECT_ID: {PROJECT_ID}")
    print(f"  LOCATION: {LOCATION}")
    
    if not PROJECT_ID:
        raise ValueError("GCP_PROJECT_ID environment variable is not set")
    
    try:
        client = genai.Client(
            vertexai=True, 
            project=PROJECT_ID, 
            location=LOCATION
        )
        print("Successfully initialized Vertex AI client")
        return client
    except Exception as e:
        print(f"ERROR initializing Vertex AI client: {str(e)}")
        raise

def extract_json_from_response(response_text: str) -> str:
    """
    Extract JSON content from Gemini response, handling markdown code blocks.
    
    Args:
        response_text: Raw response text from Gemini
        
    Returns:
        Cleaned JSON string
    """
    text = response_text.strip()
    
    # Check for markdown code blocks
    if '```json' in text:
        json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if json_match:
            return json_match.group(1).strip()
    elif '```' in text:
        json_match = re.search(r'```\s*(.*?)\s*```', text, re.DOTALL)
        if json_match:
            return json_match.group(1).strip()
    
    # Return as-is if no code blocks found
    return text

def seconds_to_mmss(seconds: int) -> str:
    """
    Convert seconds to MM:SS format for Gemini video analysis.
    
    Args:
        seconds: Time in seconds (e.g., 90)
        
    Returns:
        Time in MM:SS format (e.g., "01:30")
    """
    minutes = int(seconds) // 60
    secs = int(seconds) % 60
    return f"{minutes:02d}:{secs:02d}"

def mmss_to_seconds(mmss: str) -> int:
    """
    Convert MM:SS format to seconds.
    
    Args:
        mmss: Time in MM:SS format (e.g., "01:30")
        
    Returns:
        Time in seconds (e.g., 90)
    """
    try:
        # Handle both MM:SS and plain seconds
        if ':' in str(mmss):
            parts = mmss.split(':')
            return int(parts[0]) * 60 + int(parts[1])
        else:
            # Already in seconds
            return int(mmss)
    except (ValueError, IndexError) as e:
        print(f"Warning: Invalid timestamp format '{mmss}', defaulting to 0")
        return 0

def validate_timestamp_markers(segment: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check if summary contains timestamp boundary markers and potential issues,
    and suggest corrections.
    
    Args:
        segment: Segment dictionary with main_plot and timestamps
        
    Returns:
        Dict with validation results and suggestions
    """
    summary = segment.get('main_plot', '').lower()
    issues = []
    suggestions = {
        'adjust_start': 0,
        'adjust_end': 0,
        'confidence': 10
    }
    
    TEMPORAL_WORDS = {
        'before': ['previously', 'earlier', 'before this', 'prior to', 'preceding', 'had been'],
        'after': ['later', 'will', 'about to', 'following', 'next', 'subsequently', 'then']
    }
    
    for direction, words in TEMPORAL_WORDS.items():
        for word in words:
            if word in summary:
                issues.append(f"Temporal reference '{word}' suggests content from {direction} segment boundaries")
                suggestions['confidence'] -= 2
                if direction == 'before':
                    suggestions['adjust_start'] = -2
                else:
                    suggestions['adjust_end'] = 2
    
    start_indicators = ['continues', 'still', 'already', 'ongoing', 'in progress', 'resumes']
    if any(indicator in summary[:30] for indicator in start_indicators):
        issues.append("Start indicator suggests action started before segment")
        suggestions['adjust_start'] = -2
        suggestions['confidence'] -= 3

    end_indicators = ['continues', 'ongoing', 'begins to', 'starts to', 'about to']
    if any(indicator in summary[-50:] for indicator in end_indicators):
        issues.append("End indicator suggests action continues after segment")
        suggestions['adjust_end'] = 2
        suggestions['confidence'] -= 3

    if summary.endswith('...') or summary.endswith('—'):
        issues.append("Summary ends with ellipsis/dash suggesting cut-off dialogue")
        suggestions['adjust_end'] = 1
        suggestions['confidence'] -= 2

    return {
        'issues': issues,
        'suggestions': suggestions,
        'needs_adjustment': len(issues) > 0 or suggestions['confidence'] < 8
    }

def detect_segment_overlap(seg1: Dict[str, Any], seg2: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    start1, end1 = seg1['start_timestamp'], seg1['end_timestamp']
    start2, end2 = seg2['start_timestamp'], seg2['end_timestamp']
    
    if start1 < end2 and start2 < end1:
        overlap_start = max(start1, start2)
        overlap_end = min(end1, end2)
        return {
            'segments': [seg1['segment_id'], seg2['segment_id']],
            'overlap_start': overlap_start,
            'overlap_end': overlap_end,
            'duration': overlap_end - overlap_start
        }
    return None

def smooth_segment_boundaries(segments: List[Dict[str, Any]], max_gap: int = 2) -> List[Dict[str, Any]]:
    if len(segments) <= 1:
        return segments
    
    smoothed = []
    for i, seg in enumerate(segments):
        smoothed_seg = seg.copy()
        if i > 0:
            prev_seg = smoothed[-1]
            gap = seg['start_timestamp'] - prev_seg['end_timestamp']
            if 0 < gap <= max_gap:
                mid_point = prev_seg['end_timestamp'] + gap / 2
                smoothed[-1]['end_timestamp'] = mid_point
                smoothed_seg['start_timestamp'] = mid_point
                print(f"   → Smoothed gap between segments {prev_seg['segment_id']} and {seg['segment_id']}")
        smoothed.append(smoothed_seg)
    
    return smoothed
