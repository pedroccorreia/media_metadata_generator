""" Schemas for Gemini's structured output """

ASSET_CATEGORIZATION_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "character": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "name": {
                        "type": "STRING"
                    },
                    "description": {
                        "type": "STRING"
                    }
                }
            }
        },
        "concept": {
            "type": "ARRAY",
            "items": {
                "type": "STRING"
            }
        },
        "scenario": {
            "type": "ARRAY",
            "items": {
                "type": "STRING"
            }
        },
        "setting": {
            "type": "ARRAY",
            "items": {
                "type": "STRING"
            }
        },
        "subject": {
            "type": "ARRAY",
            "items": {
                "type": "STRING"
            }
        },
        "practice": {
            "type": "ARRAY",
            "items": {
                "type": "STRING"
            }
        },
        "theme": {
            "type": "ARRAY",
            "items": {
                "type": "STRING"
            }
        },
        "video_mood": {
            "type": "ARRAY",
            "items": {
                "type": "STRING"
            }
        }
    }
}

SUMMARY_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "summary": {
            "type": "STRING"
        },
        "itemized_summary": {
            "type": "ARRAY",
            "items": {
                "type": "STRING"
            },
            "maxItems": 3
        },
        "subject_topics": {
            "type": "ARRAY",
            "items": {
                "type": "STRING"
            },
            "maxItems": 5
        },
        "people": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "person": {
                        "type": "STRING"
                    },
                    "role": {
                        "type": "STRING"
                    }
                }
            },
            "maxItems": 10
        }
    }
}

KEY_SECTIONS_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "sections": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "type": {
                        "type": "STRING"
                    },
                    "start_time": {
                        "type": "STRING"
                    },
                    "end_time": {
                        "type": "STRING"
                    },
                    "reason": {
                        "type": "STRING"
                    }
                }
            }
        }
    }
}