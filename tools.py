"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


# Default Groq model used by the LLM-backed tools.
_MODEL = "llama-3.3-70b-versatile"


def call_llm(prompt: str, temperature: float = 0.7) -> str:
    """
    Send a single prompt to the Groq LLM and return its text response.

    Args:
        prompt:      The user prompt to send.
        temperature: Higher values (e.g. 0.9) make output more varied;
                     lower values make it more focused.

    Returns:
        The model's response text as a string.
    """
    client = _get_groq_client()
    response = client.chat.completions.create(
        model=_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
    )
    return response.choices[0].message.content


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        A list of matching listing dicts, sorted by relevance (best match first).
        Returns an empty list if nothing matches — does NOT raise an exception.

    Each listing dict has the following fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand, platform

    TODO:
        1. Load all listings with load_listings().
        2. Filter by max_price and size (if provided).
        3. Score each remaining listing by keyword overlap with `description`.
        4. Drop any listings with a score of 0 (no relevant matches).
        5. Sort by score, highest first, and return the listing dicts.

    Before writing code, fill in the Tool 1 section of planning.md.
    """

    listings = load_listings()

    # Filter by max_price and size (if provided)
    filtered = [
        item for item in listings
        if (max_price is None or item["price"] <= max_price) and
           (size is None or size.lower() in item["size"].lower())
    ]

    # Score each remaining listing by keyword overlap with `description`
    scored = []
    for item in filtered:
        score = sum(
            1 for keyword in description.lower().split()
            if keyword in item["title"].lower() or keyword in item["description"].lower()
        )
        if score > 0:
            item["score"] = score
            scored.append(item)

    # Drop any listings with a score of 0 (no relevant matches)
    scored = [item for item in scored if item.get("score", 0) > 0]

    # Sort by score, highest first, and return the listing dicts
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.

    Returns:
        A non-empty string with outfit suggestions.
        If the wardrobe is empty, offer general styling advice for the item
        rather than raising an exception or returning an empty string.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If empty: call the LLM with a prompt for general styling ideas
           (what kinds of items pair well, what vibe it suits, etc.).
        3. If not empty: format the wardrobe items into a prompt and ask
           the LLM to suggest specific outfit combinations using the new item
           and named pieces from the wardrobe.
        4. Return the LLM's response as a string.

    Before writing code, fill in the Tool 2 section of planning.md.
    """
    if not wardrobe['items']:
        # Empty wardrobe: ask for general styling advice for the item.
        prompt = (
            f"Given the thrifted item: {new_item['title']} - {new_item['description']}, "
            f"what are some general styling ideas? What kinds of items pair well with it, "
            f"and what vibe does it suit?"
        )
    else:
        # Format the wardrobe items into a prompt. Wardrobe items have the
        # fields: name, category, colors, style_tags, notes.
        wardrobe_items = "\n".join(
            f"- {item['name']} ({item['category']}, "
            f"colors: {', '.join(item['colors'])}, "
            f"style: {', '.join(item['style_tags'])})"
            for item in wardrobe['items']
        )
        prompt = (
            f"Given the thrifted item: {new_item['title']} - {new_item['description']}, "
            f"and the following wardrobe items:\n{wardrobe_items}\n"
            f"Suggest 1–2 complete outfits that include the new item and named pieces "
            f"from the wardrobe."
        )

    return call_llm(prompt)


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2–4 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, return a descriptive error message
        string — do NOT raise an exception.

    The caption should:
    - Feel casual and authentic (like a real OOTD post, not a product description)
    - Mention the item name, price, and platform naturally (once each)
    - Capture the outfit vibe in specific terms
    - Sound different each time for different inputs (use higher LLM temperature)

    TODO:
        1. Guard against an empty or whitespace-only outfit string.
        2. Build a prompt that gives the LLM the item details and the outfit,
           and asks for a caption matching the style guidelines above.
        3. Call the LLM and return the response.

    Before writing code, fill in the Tool 3 section of planning.md.
    """

    if not outfit.strip():
        return "Error: No outfit suggestion available to create a fit card."

    # Build a prompt for the LLM
    prompt = f"Create a casual and authentic Instagram/TikTok caption for the following outfit suggestion:\n{outfit}\n\nThe thrifted item details are as follows:\n- Title: {new_item['title']}\n- Price: ${new_item['price']}\n- Platform: {new_item['platform']}\n\nThe caption should feel casual and authentic, mention the item name, price, and platform naturally, capture the outfit vibe in specific terms, and sound different each time for different inputs."

    # Call the LLM with higher temperature so captions vary between runs
    return call_llm(prompt, temperature=0.9)
