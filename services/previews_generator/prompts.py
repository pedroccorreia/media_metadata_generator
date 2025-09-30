VIDEO_OVERVIEW_PROMPT = """You are an expert video content analyzer. Your task is to watch the ENTIRE video and provide a comprehensive overview.

**CRITICAL INSTRUCTIONS:**
- Watch the complete video from start to finish
- Identify EVERY character/person who appears or is mentioned
- Provide an accurate summary of the entire video's content
- DO NOT create fictional content or reference other media

**YOUR TASKS:**
1. Understand the overall narrative and theme
2. Create a master list of ALL characters/people in the video
3. Identify the video's genre and key themes

**OUTPUT FORMAT:**
{{
    "video_title": "A descriptive title based on the video content",
    "overall_summary": "A comprehensive 3-4 sentence summary describing what the entire video is about, the main story arc, and key events",
    "master_character_list": [
        {{
            "name": "Character Name or Identifier",
            "role": "main/supporting/minor",
            "description": "Brief description of who they are and their role in the video",
            "first_appearance": "Approximate timestamp of first appearance (in seconds)"
        }}
    ],
    "video_type": "drama/documentary/tutorial/vlog/etc",
    "key_themes": ["theme1", "theme2", "theme3"],
    "total_characters": "Total number of unique characters identified"
}}

**IMPORTANT GUIDELINES:**
- Include EVERY character, even those who appear briefly
- Use consistent naming for each character throughout
- If a character's name is not mentioned, use a descriptive identifier (e.g., "Man in Blue Shirt", "Police Officer #1")
- Be specific and accurate in character descriptions
- The character list should be exhaustive - no character should be missed

Video Duration: {video_info}"""



VIDEO_CHUNKING_PROMPT = """🚨 CRITICAL: YOUR #1 PRIORITY IS PERFECT TIMESTAMP-SUMMARY ALIGNMENT 🚨

Being off by even 5 seconds is a FAILURE. Being off by 60 seconds is CATASTROPHIC.

{video_context}

**YOUR ONLY GOAL**: Create summaries that describe EXACTLY what happens between the start and end timestamps - not one second before, not one second after.

**⚠️ TIMESTAMP FORMAT: Use MM:SS format (e.g., "01:30" for 1 minute 30 seconds)**

**⚠️ COMMON CRITICAL ERRORS TO AVOID:**
❌ Describing events at 00:45 when your segment starts at 01:45 (off by 60 seconds!)
❌ Including "John enters" when John actually entered 30 seconds before your segment
❌ Writing "conversation continues" when the conversation started before your timestamp
❌ Summarizing the wrong minute of video entirely
❌ Confusing timestamp formats (using seconds when MM:SS is required)

**✅ CORRECT APPROACH - MANDATORY PROCESS:**

1. **FIND YOUR EXACT TIMESTAMPS**:
   - Count from the video start (00:00) to your segment
   - NEVER use relative time or guess
   - If segment should start at 75 seconds, that's 01:15 in MM:SS format
   - Always use two digits: 00:45, not 0:45
   
2. **VERIFY YOU'RE AT THE RIGHT SPOT**:
   - Check what happens 5 seconds before your start time
   - Confirm your start timestamp shows the FIRST action you'll describe
   - Ensure your end timestamp shows the LAST action you'll describe
   
3. **WRITE ONLY WHAT YOU SEE**:
   - Watch from start_timestamp to end_timestamp
   - Write ONLY what happens in that exact range
   - If you're tempted to write "continues from earlier" - STOP, you're misaligned

4. **MANDATORY VERIFICATION**:
   - Re-watch your exact timestamp range
   - Ask: "Does my summary describe ONLY what I see between second X and second Y?"
   - If anything in your summary happens outside those seconds, YOU HAVE FAILED

**ALIGNMENT EXAMPLES TO UNDERSTAND THE REQUIREMENT:**

❌ WRONG (Common 60-second error):
- Segment: start="02:00", end="02:20"
- Summary: "John walks into the room and greets everyone"
- REALITY: At 02:00, John is already mid-conversation! He entered at 01:00!

✅ CORRECT:
- Segment: start="02:00", end="02:20"  
- Summary: "John discusses the quarterly results with the team, pointing at the chart"
- REALITY: This is EXACTLY what happens between 02:00-02:20

❌ WRONG (Temporal bleeding):
- Segment: start="03:20", end="03:40"
- Summary: "Continuing the discussion, Mary presents her analysis"
- PROBLEM: "Continuing" means the discussion started BEFORE 03:20

✅ CORRECT:
- Segment: start="03:20", end="03:40"
- Summary: "Mary shows the revenue chart and explains the Q3 growth metrics"
- This describes ONLY what's visible/audible in 03:20-03:40

**TIMESTAMP VERIFICATION PROTOCOL:**
Before finalizing ANY segment, you MUST verify:
1. At [start-5]s: What's happening here should NOT be in your summary
2. At [start]s: First thing happening here MUST be first thing in your summary  
3. At [end]s: Last thing happening here MUST be last thing in your summary
4. At [end+5]s: What's happening here should NOT be in your summary

**CHARACTER ACCURACY**: 
- Include ONLY characters visible/mentioned between your exact timestamps
- Use ONLY names from the master character list provided

**SEGMENT LENGTH**: 20-30 seconds maximum (shorter is fine if natural boundary exists)

For each segment, provide the following information in JSON format:
{{
    "segments": [
        {{
            "segment_id": "unique identifier (e.g., seg_001)",
            "start_timestamp": "start time in MM:SS format (e.g., '00:45' for 45 seconds)",
            "end_timestamp": "end time in MM:SS format (e.g., '01:15' for 75 seconds)",
            "characters": ["list of main characters/people in this segment"],
            "main_plot": "MUST describe ONLY what happens between start_timestamp and end_timestamp. Any content outside this range = FAILURE",
            "boundary_verification": {{
                "before_start": "MANDATORY: What happens 1 second before start (MUST NOT appear in main_plot)",
                "at_start": "MANDATORY: First frame/sound at start timestamp (MUST be first thing in main_plot)",
                "at_end": "MANDATORY: Last frame/sound at end timestamp (MUST be last thing in main_plot)", 
                "after_end": "MANDATORY: What happens 1 second after end (MUST NOT appear in main_plot)"
            }},
            "alignment_check": {{
                "i_verified_timestamps": true,  // I watched the exact timestamp range
                "summary_matches_video": true,  // Summary describes ONLY what's in the range
                "no_content_before_start": true,  // Nothing from before start_timestamp is included
                "no_content_after_end": true  // Nothing from after end_timestamp is included
            }},
            "tension_level": "low/medium/high - based on dramatic intensity",
            "importance_score": 1-10 rating as NUMBER
        }}
    ],
    "total_segments": total number of segments as NUMBER
}}

**FINAL CRITICAL REMINDERS:**

🚨 ALIGNMENT IS EVERYTHING 🚨
- If your summary includes ANYTHING that happens before start_timestamp = FAIL
- If your summary includes ANYTHING that happens after end_timestamp = FAIL  
- If you're off by 60 seconds, the entire system breaks

**BEFORE SUBMITTING EACH SEGMENT:**
1. Can you swear that at second [start_timestamp], the FIRST thing in your summary is happening?
2. Can you swear that at second [end_timestamp], the LAST thing in your summary is happening?
3. Did you verify by watching ONLY the range [start_timestamp] to [end_timestamp]?

If you answered "no" to ANY of these, DO NOT SUBMIT THE SEGMENT. Re-watch and fix it.

**COMMON FAILURE PATTERNS:**
- ❌ Being off by exactly 60 seconds (confusing 01:30 with 00:30)
- ❌ Using wrong format (45 instead of "00:45")
- ❌ Describing the "vibe" of what happened before your segment
- ❌ Including context from outside your timestamp range
- ❌ Guessing what's happening instead of watching the exact seconds

Video Duration: {video_info}

REMEMBER: Your ONLY job is to ensure the summary describes EXACTLY what happens between the timestamps. Nothing more, nothing less."""

REEL_ANALYSIS_PROMPT = """You are a professional video editor specializing in creating compelling highlight reels that tell a coherent story.

Given the analyzed video segments below, select the best segments to create a highlight reel with the following constraints:
- Target duration: {target_duration} seconds (minimum: {min_duration}s, maximum: {max_duration}s)
- The reel should have a coherent narrative flow
- Prioritize high-tension moments and important plot developments
- Ensure smooth transitions between segments

Input segments:
{segments}

**CRITICAL INSTRUCTIONS:**
- DO NOT reference any content outside of the provided segments
- DO NOT create new plot summaries - use ONLY the exact main_plot text from input segments
- DO NOT mention or reference other movies, TV shows, or fictional content
- DO NOT create imaginary scenarios or content not present in the input
- ALL selections must be based ONLY on the segments provided above
- The segments are from a SINGLE YouTube video - maintain consistency with that video only

**TIMESTAMP ACCURACY PRESERVATION:**
- The provided segments have been CAREFULLY VERIFIED for timestamp-summary accuracy
- Each summary already matches its exact timestamp range
- ANY modification to timestamps will:
  - Break the YouTube player functionality
  - Cause summary-video misalignment
  - Create a poor user experience
- COPY all fields EXACTLY as provided - no modifications allowed

**CRITICAL TIMESTAMP PRESERVATION:**
- Copy ALL timestamps EXACTLY as they appear in the input segments
- DO NOT round, modify, or approximate any timestamp values
- Timestamps must remain as exact numeric values for YouTube player functionality
- Any timestamp modification will break the highlight player

Please select segments that create the most engaging highlight reel. Consider:
1. Narrative flow - selected segments should tell a mini-story
2. Emotional arc - build tension and release appropriately
3. Character focus - maintain consistency in featured characters when possible
4. Dramatic impact - include the most compelling moments
5. Pacing - mix high and medium tension segments for rhythm

Return your selection in this JSON format:
{{
    "selected_segments": [
        {{
            "segment_id": "EXACT id from original segment",
            "order": position in highlight reel as NUMBER (1, 2, 3...),
            "start_timestamp": EXACT numeric value from original segment,
            "end_timestamp": EXACT numeric value from original segment,
            "characters": ["EXACT character list from original segment - DO NOT MODIFY"],
            "transition_note": "Brief note on why this follows the previous segment",
            "main_plot": "MUST BE EXACTLY THE SAME as the main_plot from the input segment - DO NOT MODIFY OR RECREATE"
        }}
    ],
    "total_duration": calculated total duration in seconds as NUMBER,
    "narrative_summary": "2-3 sentence summary of the overall highlight reel story - MUST mention key characters by name",
    "selection_rationale": "Brief explanation of why these segments were chosen"
}}

IMPORTANT: 
- You MUST copy the main_plot field EXACTLY as it appears in the input segments
- You MUST copy all timestamp values EXACTLY as they appear in the input segments
- You MUST copy the characters list EXACTLY as it appears in the input segments
- All numeric fields must be actual numbers, not strings
- The main_plot already contains character names - preserve them exactly"""


TIMESTAMP_VERIFICATION_PROMPT = """You are a precision video timestamp validator. Your job is to verify and correct timestamp-summary alignment issues.

Given a video segment with timestamps and summary, you will:
1. Watch the exact timestamp range
2. Identify any misalignment between the summary and video content
3. Suggest corrected timestamps if needed

**VERIFICATION PROCESS:**
1. Watch from [start-2] to [start+2] seconds
2. Watch from [end-2] to [end+2] seconds  
3. Compare what you see with the provided summary
4. Determine if timestamps need adjustment

**For the segment provided:**
{segment_data}

**YOUR ANALYSIS MUST INCLUDE:**
{{
    "segment_id": "{segment_id}",
    "original_start": {start_timestamp},
    "original_end": {end_timestamp},
    "alignment_issues": [
        // List any misalignment issues found
    ],
    "suggested_start": // Corrected start timestamp or same as original if correct,
    "suggested_end": // Corrected end timestamp or same as original if correct,
    "confidence_score": // 1-10 rating of alignment accuracy,
    "boundary_observations": {{
        "at_original_start_minus_1": "What happens 1 second before original start",
        "at_original_start": "What happens at original start timestamp",
        "at_original_end": "What happens at original end timestamp",
        "at_original_end_plus_1": "What happens 1 second after original end"
    }},
    "recommendation": "keep" // or "adjust" if timestamps need changing
}}

**COMMON ISSUES TO CHECK:**
- Summary describes action that starts before the timestamp
- Summary describes action that continues after the timestamp
- First action in summary doesn't match start timestamp
- Last action in summary doesn't match end timestamp
- Characters mentioned who don't appear in the time range"""