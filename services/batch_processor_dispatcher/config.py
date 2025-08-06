"""
Configuration for mapping file types to specific processing prompts and settings.
This allows for easy customization of how different media types are handled
by the various generator services.
"""

FILE_TYPE_PROMPT_MAP = {
    "video": {
        "summary": {
            "prompt": "Generate a concise, one-paragraph summary of this video's content.",
            "model": "gemini-1.5-flash",
            "max_tokens": 250
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