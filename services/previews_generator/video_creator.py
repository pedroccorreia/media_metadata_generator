#Required Imports
import moviepy as mp
import os
from moviepy import VideoFileClip, concatenate_videoclips
from typing import List, Optional


def create_final_highlight_reel(segment_paths: List[str], output_path: str = "highlight_reel.mp4") -> Optional[str]:
    """
    Create a highlight reel by concatenating video segments.

    Args:
        segment_paths (List[str]): List of file paths to the video segments.
        output_path (str): File path to save the final highlight reel. Defaults to "highlight_reel.mp4".

    Returns:
        str: Path to the created highlight reel video file.
    """
    try:
        clips = [VideoFileClip(path) for path in segment_paths]
        final_clip = concatenate_videoclips(clips, method="chain")
        final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac")

        # Close all clips to release resources
        for clip in clips:
            clip.close()
        final_clip.close()

        print(f"Highlight reel created at: {output_path}")
        return output_path

    except Exception as e:
        print(f"Error creating highlight reel: {e}")
        return None