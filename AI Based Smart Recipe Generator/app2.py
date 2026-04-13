# app.py
import os
import math
import random
from io import BytesIO
from textwrap import dedent

import streamlit as st
from PIL import Image
from dotenv import load_dotenv

# Install google.generativeai and reportlab in environment:
# pip install google-generative-ai reportlab streamlit pillow python-dotenv

import google.generativeai as genai
from google.api_core import exceptions as google_exceptions

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# -----------------------
# ENV & GEMINI SETUP
# -----------------------
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if GOOGLE_API_KEY:
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
    except Exception as e:
        # configure rarely fails, but if it does show a warning later
        print("Warning while configuring gemini:", e)
else:
    print("No GOOGLE_API_KEY found in environment. Image mode will warn in UI.")

# -----------------------
# HELPERS: Ingredient parsing + quantity scaling
# -----------------------

def clean_ingredients(raw_text: str):
    items = [x.strip() for x in raw_text.split(",")]
    items = [x for x in items if x]
    return items

# rough per-serving defaults (in grams / ml / counts / tsp / tbsp)
# these are heuristics for basic scaling
PER_SERVING_DEFAULTS = {
    # solids in grams or counts
    "potato": ("g", 150),
    "tomato": ("g", 70),
    "onion": ("g", 50),
    "carrot": ("g", 70),
    "chicken": ("g", 150),
    "rice": ("g", 80),
    "pasta": ("g", 90),
    "egg": ("count", 1),
    "milk": ("ml", 100),
    "oil": ("ml", 10),
    "butter": ("g", 10),
    "salt": ("tsp", 0.5),
    "sugar": ("tsp", 1),
    "pepper": ("tsp", 0.25),
    "garlic": ("clove", 1),
    "ginger": ("g", 5),
    "spices": ("tsp", 1),
    "mint": ("g", 5),
    "peas": ("g", 50)
}

def estimate_quantity(ingredient: str, servings: int):
    key = ingredient.lower()
    # try to match key tokens
    for k in PER_SERVING_DEFAULTS:
        if k in key:
            unit, per = PER_SERVING_DEFAULTS[k]
            total = per * servings
            return format_quantity(total, unit)

    # fallback: treat as tbsp per serving
    total_tbsp = 1 * servings
    return format_quantity(total_tbsp, "tbsp")

def format_quantity(value, unit):
    """
    Format quantity reasonably:
     - grams: round to nearest 5g
     - ml: round to nearest 5ml
     - tsp/tbsp: convert if large enough to tbsp/cup (simple)
     - count: show integer
    """
    if unit == "g":
        v = int(round(value / 5.0) * 5)
        return f"{v} g"
    if unit == "ml":
        v = int(round(value / 5.0) * 5)
        return f"{v} ml"
    if unit == "count":
        return f"{int(round(value))} pcs"
    if unit == "clove":
        return f"{int(round(value))} clove(s)"
    if unit == "tsp":
        # if >= 3 tsp convert to tbsp
        if value >= 3:
            tbsp = value / 3.0
            return f"{round(tbsp,1)} tbsp"
        return f"{round(value,2)} tsp"
    if unit == "tbsp":
        # if >= 16 tbsp convert to cups approx
        if value >= 16:
            cups = value / 16.0
            return f"{round(cups,2)} cup(s)"
        return f"{round(value,2)} tbsp"
    # default
    return f"{round(value,2)} {unit}"

def generate_ingredients_list(ingredients, servings):
    if not ingredients:
        ingredients = ["salt", "pepper", "oil"]
    lines = [f"- Serves: {servings}"]
    for ing in ingredients:
        qty = estimate_quantity(ing, servings)
        # Capitalize ingredient name nicely
        name = ing.strip().title()
        lines.append(f"- {qty} {name}")
    return "\n".join(lines)

# -----------------------
# Recipe text generation (simple)
# -----------------------

def generate_recipe_name(ingredients, cuisine, meal_type, suggested_name=None):
    if suggested_name:
        base = suggested_name
    elif ingredients:
        base = f"{ingredients[0].title()} {meal_type}"
    else:
        base = f"Chef's Special {meal_type}"
    if cuisine and cuisine != "Any":
        base = f"{cuisine} {base}"
    return base

def generate_steps(ingredients, cuisine, meal_type, cooking_time, dish_name=None):
    if not ingredients:
        ingredients = ["your chosen ingredients"]
    method = "saute" if any("oil" in i.lower() for i in ingredients) else "mix"
    name_text = dish_name if dish_name else meal_type.lower()
    steps = [
        "1. Prepare all ingredients by washing, peeling, and chopping as needed.",
        f"2. Heat a pan and {method} the base ingredients (like onions, garlic, or aromatics) if available.",
        f"3. Add the main ingredients: {', '.join(ingredients)}.",
        f"4. Season with salt, pepper, and any spices that match {cuisine} cuisine.",
        f"5. Cook for about {cooking_time} minutes, stirring occasionally.",
        f"6. Taste and adjust seasoning. Serve hot as a delicious {name_text}."
    ]
    if cuisine and cuisine != "Any":
        steps.append(f"7. For extra authenticity, add classic {cuisine} garnishes or sides (e.g., herbs, bread, or rice).")
    return "\n".join(steps)

def generate_recipe(ingredients_list, cuisine, meal_type, servings, cooking_time, dish_name=None):
    title = generate_recipe_name(ingredients_list, cuisine, meal_type, suggested_name=dish_name)
    ingredients_block = generate_ingredients_list(ingredients_list, servings)
    steps_block = generate_steps(ingredients_list, cuisine, meal_type, cooking_time, dish_name=dish_name)
    recipe_markdown = f"""
## {title}

**Cuisine:** {cuisine}  
**Meal Type:** {meal_type}  
**Approx. Cooking Time:** {cooking_time} minutes  

### Ingredients
{ingredients_block}

### Steps
{steps_block}
"""
    return title, dedent(recipe_markdown)

# -----------------------
# GEMINI VISION: IMAGE -> DISH + INGREDIENTS
# -----------------------

def parse_ingredients_from_text(text: str):
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    ingredients = []
    for line in lines:
        if line.startswith(("-", "*")):
            item = line[1:].strip()
            if item:
                ingredients.append(item)
    if not ingredients and lines:
        for line in lines:
            if "," in line:
                ingredients = [x.strip() for x in line.split(",") if x.strip()]
                break
    if not ingredients:
        ingredients = ["onion", "tomato", "oil", "salt"]
    return ingredients

def analyze_image_and_extract_recipe_info(image_bytes: bytes, mime_type: str):
    """
    Accepts image bytes and mime_type. Returns (dish_name, ingredients_list).
    This uses google.generativeai (Gemini). We handle errors and return fallbacks.
    """
    if not GOOGLE_API_KEY:
        return "Unknown Dish (no API key)", ["onion", "tomato", "oil", "salt"]

    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        prompt = (
            "You are a cooking assistant. Look at this food photo and respond in this EXACT format:\n"
            "Dish name: <dish name>\n"
            "Ingredients:\n"
            "- ingredient 1\n"
            "- ingredient 2\n"
            "Only food-related details, no extra explanation."
        )
        img = {"mime_type": mime_type or "image/jpeg", "data": image_bytes}
        response = model.generate_content([prompt, img])
        text = response.text.strip()
        # parse dish name
        dish_name = "Unknown Dish"
        for line in text.splitlines():
            if line.lower().startswith("dish name"):
                parts = line.split(":", 1)
                if len(parts) == 2:
                    dish_name = parts[1].strip()
                break
        ingredients = parse_ingredients_from_text(text)
        return dish_name, ingredients

    except google_exceptions.InvalidArgument as e:
        # Common: invalid API key or bad image input
        return f"Gemini Error: {e.message if hasattr(e, 'message') else str(e)}", ["onion", "tomato", "oil", "salt"]
    except Exception as e:
        # generic fallback
        return f"Unknown Dish (error)", ["onion", "tomato", "oil", "salt"]

# -----------------------
# PDF generation
# -----------------------

def create_pdf_from_recipe(title: str, recipe_markdown: str) -> BytesIO:
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    textobject = c.beginText(40, height - 50)
    textobject.setFont("Times-Roman", 12)
    lines = recipe_markdown.split("\n")
    for line in lines:
        # remove markdown syntax
        line = line.replace("## ", "").replace("### ", "")
        # simple bullet cleanup
        if line.startswith("- "):
            line = "• " + line[2:]
        # some long lines should wrap manually: simple wrap ~90 chars
        if len(line) > 90:
            # naive wrap
            parts = [line[i:i+90] for i in range(0, len(line), 90)]
            for p in parts:
                textobject.textLine(p)
                if textobject.getY() < 40:
                    c.drawText(textobject)
                    c.showPage()
                    textobject = c.beginText(40, height - 50)
                    textobject.setFont("Times-Roman", 12)
        else:
            textobject.textLine(line)
        if textobject.getY() < 40:
            c.drawText(textobject)
            c.showPage()
            textobject = c.beginText(40, height - 50)
            textobject.setFont("Times-Roman", 12)
    c.drawText(textobject)
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

# -----------------------
# STREAMLIT UI
# -----------------------
st.set_page_config(page_title="Recipe Generator", page_icon="🍳", layout="centered")
st.title("🍳 Recipe Generator (Image → Recipe + PDF)")
st.write("Type ingredients OR upload a food photo. Servings scale up to 45 people.")

with st.sidebar:
    st.header("⚙️ Options")
    input_mode = st.radio("Input Mode", ["Type Ingredients", "Upload Food Photo"])
    cuisine = st.selectbox("Preferred Cuisine", ["Any", "Indian", "Italian", "Chinese", "Mexican", "American", "Thai", "Other"])
    meal_type = st.selectbox("Meal Type", ["Dish", "Curry", "Salad", "Pasta", "Soup", "Snack"])
    # allow up to 45 servings as you requested
    servings = st.slider("Servings (max 45)", min_value=1, max_value=45, value=2)
    cooking_time = st.slider("Cooking Time (minutes)", min_value=5, max_value=240, value=30, step=5)

recipe_title = None
recipe_markdown = None

if input_mode == "Type Ingredients":
    st.subheader("🧺 Type Ingredients (comma separated)")
    ingredients_text = st.text_area("Enter ingredients (comma separated):", placeholder="e.g. potato, tomato, onion, garlic, oil")
    if st.button("Generate Recipe (from typed ingredients)"):
        if not ingredients_text.strip():
            st.warning("Please enter at least one ingredient.")
        else:
            ingredients_list = clean_ingredients(ingredients_text)
            recipe_title, recipe_markdown = generate_recipe(ingredients_list, cuisine, meal_type, servings, cooking_time, dish_name=None)
else:
    st.subheader("📷 Upload Food Photo")
    uploaded_file = st.file_uploader("Choose an image of your dish (jpg / png)", type=["jpg", "jpeg", "png"])
    if uploaded_file is not None:
        try:
            image = Image.open(uploaded_file)
            st.image(image, caption="Uploaded Image", use_column_width=True)
        except Exception:
            st.warning("Uploaded file couldn't be opened as an image preview (still will attempt analysis).")
    if st.button("Generate Recipe from Image"):
        if uploaded_file is None:
            st.warning("Please upload an image first!")
        else:
            # get raw bytes and mime
            image_bytes = uploaded_file.getvalue()
            mime_type = uploaded_file.type
            dish_name, ingredients_list = analyze_image_and_extract_recipe_info(image_bytes, mime_type)
            # if gemini returned an error string in dish_name, show as warning
            if dish_name and dish_name.startswith("Gemini Error"):
                st.error(dish_name)
                dish_name = None
            st.info(f"Detected Dish: **{dish_name or 'Unknown'}**")
            recipe_title, recipe_markdown = generate_recipe(ingredients_list, cuisine, meal_type, servings, cooking_time, dish_name=dish_name)

# display recipe and offer PDF download
if recipe_markdown:
    st.markdown(recipe_markdown)
    pdf_buffer = create_pdf_from_recipe(recipe_title or "recipe", recipe_markdown)
    safe_title = (recipe_title or "recipe").replace(" ", "_")
    st.download_button(
        label="📄 Download Recipe as PDF",
        data=pdf_buffer,
        file_name=f"{safe_title}.pdf",
        mime="application/pdf"
    )
    st.success("Recipe ready — you can download it as a PDF.")
else:
    st.caption("No recipe generated yet.")
