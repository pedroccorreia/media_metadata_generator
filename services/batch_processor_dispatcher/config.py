"""
Configuration for mapping file types to specific processing prompts and settings.
This allows for easy customization of how different media types are handled
by the various generator services.
"""

FILE_TYPE_PROMPT_MAP = {
    "video": {
        "summary": {
            "prompt": 
            """SYSTEM:```You are a skilled video analysis expert. You have a deep understanding of media. Your task is to analyze the provided video and extract key information.```
                INSTRUCTION: ```Please analyze the following video and provide long summary, short summary, subject topics.Please format your response as a JSON object with the given structure. Avoid any additional comment or text.```
                OUTPUT:```=
                JSON
                {
                    "text": "[A medium length summary of the video content]"
                }```
                """,
            "model": "gemini-2.5-flash",
        "chapters":{
            "prompt": """
                SYSTEM:```You are a skilled video analysis expert. You have a deep understanding of media and can accurately identify key moments in a video. Your task is to analyze the provided video and extract all the highlight clips. For each clip, you need to classify the type of highlight and provide the precise start and end timestamps.```
                INSTRUCTION: ```Please analyze the following video and provide a list of all the highlight clips with their type and timestamps. Also explain the reason why the selection of that particular timestamp has been made. Please format your response as a JSON object with the given structure. Make sure the audio is not truncated while suggesting the clips. Avoid any additional comment or text.```
                OUTPUT:```
                JSON
                {
                    "sections": [
                    {
                        "type": "[highlight type]",
                        "start_time": "[mm:ss]",
                        "end_time": "[mm:ss]",
                        "reason" : ""
                    },
                    {
                        "type":"[highlight type]",
                        "start_time": "[mm:ss]",
                        "end_time": "[mm:ss]",
                        "reason" : ""
                    }
                    ]
                }```
                Please make sure the timestamps are accurate and reflect the precise start and end of each highlight clip.
                """,
                "model": "gemini-2.5-pro",
            },
        },
        "transcription": {
            "model": "chirp",
            "language_codes": ["en-US"]
        },
        "previews": {
            "type": "thumbnail_strip",
            "count": 5,
            "format": "jpeg"
        }
    },
    "audio": {
        "summary": {
            "prompt": "Summarize the key points and speakers in this audio recording.",
            "model": "gemini-1.5-flash",
            "max_tokens": 300
        },
        "transcription": {
            "model": "chirp",
            "language_codes": ["en-US", "es-ES"],
            "enable_automatic_diarization": True
        },
        # Previews are not applicable to audio in this example
        "previews": None
    },
    "document": {
        "summary": {
            "prompt": "Provide a bullet-point summary of the main sections of this document.",
            "model": "gemini-1.5-flash",
            "max_tokens": 500
        },
        # Transcription and previews are not applicable to documents
        "transcription": None,
        "previews": None
    }
}