""" Schemas necessary for previews generation """

SHORTS_SCHEMA = {
    "type": "ARRAY",
    "maxItems": 5,
    "items": {
        "type": "OBJECT",
        "properties": {
            "start_timecode": {
                "type": "STRING",
                "description": "The starting timecode for the highlight clip, in a 'mm:ss' format."
            },
            "end_timecode": {
                "type": "STRING",
                "description": "The ending timecode for the highlight clip, in a 'mm:ss' format."
            },
            "summary": {
                "type": "STRING",
                "description": "A brief summary of the content within the highlight clip."
            },
            "user_description": {
                "type": "STRING",
                "description": "A compelling paragraph designed to entice a user to watch the clip."
            },
            "emotions_triggered": {
                "type": "ARRAY",
                "items": {
                    "type": "STRING"
                },
                "maxItems": 5,
                "description": "A list of up to five emotions that the clip is likely to evoke in a viewer."
            }
        },
        "required": [
            "start_timecode",
            "end_timecode",
            "summary",
            "user_description",
            "emotions_triggered"
        ]
    }
}