MODEL_GEMINI_PRO = "gemini-pro"
MODEL_GEMINI_PRO_VISION = "gemini-pro-vision"

def build_history(raw_history):
    history = []
    for content in raw_history:
        history.append({
            "parts": [content["user"]],
            "role": "user",
        })
        history.append({
            "parts": [content["model"]],
            "role": "model",
        })
    return history