"""Authoritative context selection; UI displays the returned content."""
GUIDANCE = {
    "beginner": {
        "title": "Start with the first molar",
        "description": "Find tooth 16 in the upper-right quadrant. Isolate it, turn the specimen and explore the layers one at a time.",
        "prompts": ["FDI 16 means the upper-right first permanent molar.", "The crown is the part normally visible above the gum.", "Choose a layer to learn what lies beneath the surface."],
    },
    "experienced": {
        "title": "Explore structure and relationships",
        "description": "Use a self-directed inspection of FDI 16. Relate external form to the internal tissues, then document one spatial observation.",
        "prompts": ["Compare crown form and root arrangement from different angles.", "Describe how dentin surrounds the pulp space.", "How does the selected viewpoint change what a mirror could reveal?"],
    },
    "demonstrator": {
        "title": "Lead a guided explanation",
        "description": "Keep the tooth identity and active tool visible. Use the layers as discussion prompts for the group.",
        "prompts": ["Ask the group to explain FDI 16 before isolating it.", "Reveal the tissue layers and invite learners to name each one.", "Pause at a useful viewpoint and compare learners' observations."],
    },
}
LAYERS = {
    "surface": ("External form", "Rotate the specimen to compare the crown and roots."),
    "enamel": ("Enamel", "Enamel forms the hard outer covering of the crown."),
    "dentin": ("Dentin", "Dentin lies beneath enamel in the crown and surrounds the pulp space."),
    "pulp": ("Pulp", "The pulp is soft tissue within the internal pulp space; this view is schematic."),
}


def content_for(state: dict) -> dict:
    base = GUIDANCE[state["profile"]["level"]]
    session = state["session"]
    layer_title, layer_text = LAYERS[session["layer"]]
    recovery = None
    if session["paused"]:
        recovery = "Tracking is interrupted. Return your shoulder and wrist to view, then explicitly resume." if session["pause_reason"] == "tracking" else "Your scene is retained. Resume when you are ready."
    tool = session["tool"]
    return {
        **base,
        "layer_title": layer_title,
        "layer_text": layer_text,
        "task": "Choose tooth 16 from the map." if session["selected_tooth"] is None else "Isolate the selected tooth." if not session["isolated"] else "Inspect the specimen, explore its layers, then position the mirror.",
        "tool_help": "Rotate the specimen using the view controls." if tool == "hand" else f"Position the virtual {tool}, then confirm placement. This is an interaction exercise.",
        "recovery": recovery,
        "rule": f"profile:{state['profile']['level']};layer:{session['layer']};tool:{tool};paused:{session['paused']}",
    }
