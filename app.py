import warnings
warnings.filterwarnings("ignore")
import streamlit as st
from openai import OpenAI
import requests
import base64
import json
import re
import time
import html
import hashlib
from fpdf import FPDF
from PIL import Image, ImageDraw, ImageFont
import io

# ════════════════════════════════════════
# CONFIG
# ════════════════════════════════════════
STORY_MODEL = "meta/llama-3.3-70b-instruct"
STORY_API_BASE = "https://integrate.api.nvidia.com/v1"
IMAGE_API_URL = "https://ai.api.nvidia.com/v1/genai/black-forest-labs/flux.1-schnell"
MAX_PANELS = 6
MIN_PANELS = 3
MAX_INPUT = 500
MIN_INPUT = 10
MAX_RETRIES = 3
RETRY_DELAY = 5
REQUEST_COOLDOWN = 2

# ════════════════════════════════════════
# PAGE CONFIG
# ════════════════════════════════════════
st.set_page_config(
    page_title="AI Comic Generator",
    page_icon="💥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ════════════════════════════════════════
# CSS
# ════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bangers&family=Inter:wght@400;600;700&display=swap');

* { font-family: 'Inter', sans-serif; }
.stApp { background: #0d0d0d; color: #e0e0e0; }

.main-header {
    text-align: center;
    padding: 2rem 0 1rem 0;
    border-bottom: 3px solid #ff4444;
    margin-bottom: 2rem;
}
.main-header h1 {
    font-family: 'Bangers', cursive;
    font-size: 4rem;
    color: #ff4444;
    letter-spacing: 6px;
    text-shadow: 4px 4px 0px #000, -1px -1px 0 #000;
    margin: 0;
}
.main-header p { color: #888; font-size: 1rem; }

.panel-wrapper {
    background: #1a1a1a;
    border: 3px solid #ff4444;
    border-radius: 8px;
    margin-bottom: 1.5rem;
    overflow: hidden;
    box-shadow: 5px 5px 0px #ff4444;
}
.panel-header {
    background: #ff4444;
    color: white;
    font-family: 'Bangers', cursive;
    font-size: 1.3rem;
    padding: 0.4rem 1rem;
    letter-spacing: 3px;
}
.panel-body { padding: 1rem; }

.dialogue-bubble {
    background: white;
    border: 2px solid black;
    border-radius: 15px;
    padding: 0.8rem 1rem;
    margin: 0.5rem 0;
    font-family: 'Bangers', cursive;
    font-size: 1.1rem;
    color: black;
    text-align: center;
    position: relative;
    box-shadow: 2px 2px 0px #333;
}

.character-card {
    background: #1a1a2e;
    border: 2px solid #ff4444;
    border-radius: 10px;
    padding: 1rem;
    margin-bottom: 0.8rem;
    box-shadow: 3px 3px 0px #ff4444;
}
.character-name {
    font-family: 'Bangers', cursive;
    font-size: 1.4rem;
    color: #ff4444;
    letter-spacing: 2px;
}
.character-role {
    color: #ffd700;
    font-size: 0.85rem;
    font-weight: 600;
}

.metric-card {
    background: #1a1a1a;
    border: 2px solid #333;
    border-radius: 10px;
    padding: 1rem;
    text-align: center;
    margin-bottom: 1rem;
}
.metric-card h3 { color: #ff4444; font-size: 2rem; margin: 0; }
.metric-card p { color: #888; font-size: 0.8rem; margin: 0; }

.story-box {
    background: #1a1a1a;
    border-left: 4px solid #ff4444;
    border-radius: 0 10px 10px 0;
    padding: 1rem 1.5rem;
    margin-bottom: 1.5rem;
}

.arch-box {
    background: #111;
    border: 1px solid #333;
    border-radius: 10px;
    padding: 1.2rem;
    font-family: monospace;
    font-size: 0.85rem;
    color: #00ff41;
    margin-bottom: 1rem;
}

.error-box {
    background: #1a0000;
    border: 1px solid #ff4444;
    border-radius: 8px;
    padding: 1rem;
    color: #ff4444;
    margin: 0.5rem 0;
}
.success-box {
    background: #001a00;
    border: 1px solid #00ff41;
    border-radius: 8px;
    padding: 1rem;
    color: #00ff41;
    margin: 0.5rem 0;
}
.warning-box {
    background: #1a1a00;
    border: 1px solid #ffd700;
    border-radius: 8px;
    padding: 1rem;
    color: #ffd700;
    margin: 0.5rem 0;
}
.info-box {
    background: #001a2e;
    border: 1px solid #4488ff;
    border-radius: 8px;
    padding: 1rem;
    color: #4488ff;
    margin: 0.5rem 0;
}

.stTextArea textarea {
    background: #1a1a1a !important;
    border: 2px solid #ff4444 !important;
    border-radius: 10px !important;
    color: #e0e0e0 !important;
    font-size: 1rem !important;
}
.stSelectbox > div > div {
    background: #1a1a1a !important;
    border: 1px solid #333 !important;
    color: #e0e0e0 !important;
}
.stButton > button {
    background: #ff4444 !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
    font-size: 1rem !important;
    width: 100% !important;
    letter-spacing: 1px !important;
    box-shadow: 3px 3px 0px #000 !important;
}
.stButton > button:hover {
    transform: translate(1px, 1px) !important;
    box-shadow: 2px 2px 0px #000 !important;
}
.stDownloadButton > button {
    background: #1a1a2e !important;
    color: white !important;
    border: 2px solid #ff4444 !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    width: 100% !important;
}
p, li, span, div { color: #e0e0e0; }
h1, h2, h3, h4 { color: #e0e0e0; }
label { color: #888 !important; font-size: 0.8rem !important;
        text-transform: uppercase !important; letter-spacing: 0.05em !important; }
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════
# HEADER
# ════════════════════════════════════════
st.markdown("""
<div class="main-header">
    <h1>💥 AI COMIC GENERATOR 💥</h1>
    <p>Powered by Meta Llama + FLUX — Turn any idea into a full comic book</p>
</div>
""", unsafe_allow_html=True)

# ════════════════════════════════════════
# API VALIDATION
# ════════════════════════════════════════
try:
    api_key = st.secrets["NVIDIA_API_KEY"]
    if not api_key or not api_key.startswith("nvapi-") or len(api_key) < 20:
        st.error("Invalid NVIDIA API key in secrets.")
        st.stop()
    story_client = OpenAI(base_url=STORY_API_BASE, api_key=api_key)
except KeyError:
    st.error("NVIDIA_API_KEY missing from Streamlit secrets.")
    st.stop()
except Exception as e:
    st.error(f"API initialization failed: {str(e)}")
    st.stop()

# ════════════════════════════════════════
# INPUT SECURITY
# ════════════════════════════════════════
INJECTION_PATTERNS = [
    "ignore instructions", "ignore previous",
    "system prompt", "forget everything",
    "you are now", "act as", "pretend you",
    "disregard", "override", "jailbreak",
    "new instructions", "bypass"
]

def validate_input(text):
    if not text or len(text.strip()) < MIN_INPUT:
        return False, f"Please enter at least {MIN_INPUT} characters."
    if len(text) > MAX_INPUT:
        return False, f"Keep your idea under {MAX_INPUT} characters."
    lower = text.lower()
    for pattern in INJECTION_PATTERNS:
        if pattern in lower:
            return False, "Invalid input detected. Please enter a genuine story idea."
    return True, ""

def sanitize_input(text):
    text = html.escape(text.strip())
    text = re.sub(r'[<>{}]', '', text)
    return text

# ════════════════════════════════════════
# CHARACTER MEMORY SYSTEM
# ════════════════════════════════════════
class CharacterMemory:
    """
    Stores character profiles with locked visual descriptions.
    Same seed + same prompt = consistent character across panels.
    """
    def __init__(self):
        self.characters = {}

    def add_character(self, name, appearance, clothing, traits, role):
        seed = self._generate_seed(name)
        self.characters[name] = {
            "name": name,
            "appearance": appearance,
            "clothing": clothing,
            "traits": traits,
            "role": role,
            "seed": seed,
            "locked_prompt": self._build_locked_prompt(
                name, appearance, clothing, traits)
        }

    def _generate_seed(self, name):
        # Deterministic seed from character name
        return int(hashlib.md5(name.encode()).hexdigest()[:8], 16) % 999999

    def _build_locked_prompt(self, name, appearance, clothing, traits):
        return (
            f"{appearance}, wearing {clothing}, "
            f"{traits}, consistent character design"
        )

    def get_locked_prompt(self, name):
        if name in self.characters:
            return self.characters[name]["locked_prompt"]
        return ""

    def get_seed(self, name):
        if name in self.characters:
            return self.characters[name]["seed"]
        return 42

    def get_all_descriptions(self):
        descs = []
        for name, data in self.characters.items():
            descs.append(
                f"{name} ({data['role']}): {data['locked_prompt']}")
        return " | ".join(descs)

    def to_dict(self):
        return self.characters

# ════════════════════════════════════════
# CACHING
# ════════════════════════════════════════
@st.cache_data(ttl=3600)
def cached_story(idea_hash, genre, num_panels):
    """Cache story results to avoid regenerating same story."""
    return None  # Placeholder — actual generation happens separately

def get_cache_key(idea, genre, num_panels):
    return hashlib.md5(
        f"{idea}{genre}{num_panels}".encode()
    ).hexdigest()

# ════════════════════════════════════════
# IMAGE PROMPT ENGINE
# ════════════════════════════════════════
def build_image_prompt(scene, mood, environment,
                       camera_angle, lighting,
                       character_memory, style):

    # Get all character descriptions (locked)
    char_desc = character_memory.get_all_descriptions()

    # Style mapping
    style_map = {
        "Comic Book": "american comic book art style, bold black outlines, cel shading, vibrant colors, Marvel/DC style",
        "Manga": "manga art style, black and white, screen tones, dynamic lines, anime style",
        "Cartoon": "cartoon art style, bright saturated colors, simple clean shapes, Pixar-like",
        "Dark/Noir": "noir comic style, dark shadows, high contrast black and white, dramatic lighting",
        "Retro/Vintage": "vintage comic book style, halftone dots, retro colors, 1960s comic aesthetic"
    }

    # Mood to visual descriptor
    mood_map = {
        "action": "dynamic action scene, motion blur, explosive energy",
        "dramatic": "dramatic tension, intense expressions, powerful composition",
        "funny": "comedic scene, exaggerated expressions, playful mood",
        "mysterious": "mysterious atmosphere, shadows, suspenseful",
        "emotional": "emotional scene, close-up faces, soft lighting",
        "peaceful": "calm serene scene, soft colors, gentle atmosphere"
    }

    art_style = style_map.get(style, style_map["Comic Book"])
    mood_desc = mood_map.get(mood.lower(), "dramatic scene")

    prompt = (
        f"{art_style}, "
        f"{mood_desc}, "
        f"scene: {scene}, "
        f"environment: {environment}, "
        f"camera: {camera_angle}, "
        f"lighting: {lighting}, "
        f"characters: {char_desc}, "
        f"high quality, detailed, professional comic panel, "
        f"no text, no speech bubbles, no watermark"
    )

    # Limit prompt length
    if len(prompt) > 800:
        prompt = prompt[:800]

    return prompt

# ════════════════════════════════════════
# STORY GENERATION
# ════════════════════════════════════════
def generate_story(idea, genre, num_panels, style):
    prompt = f"""You are a professional comic book writer and artist director.
Create a complete comic story based on: "{idea}"
Genre: {genre} | Style: {style} | Panels: {num_panels}

RESPOND ONLY WITH VALID JSON. No text before or after. No markdown. No backticks.

{{
    "title": "Comic title (max 6 words)",
    "summary": "Story summary in 2-3 sentences",
    "characters": [
        {{
            "name": "Character name",
            "appearance": "Detailed physical description: height, build, hair color, eye color, skin tone, age",
            "clothing": "Exact clothing description: colors, style, accessories",
            "traits": "2-3 personality traits visible in appearance",
            "role": "Hero/Villain/Supporting/Narrator"
        }}
    ],
    "panels": [
        {{
            "panel_number": 1,
            "scene": "Detailed visual scene description in 1-2 sentences",
            "environment": "Location description: indoor/outdoor, time of day, weather",
            "camera_angle": "close-up/medium shot/wide angle/bird eye/low angle",
            "lighting": "natural/dramatic/neon/dark/bright/silhouette",
            "mood": "action/dramatic/funny/mysterious/emotional/peaceful",
            "characters_present": ["Character name 1"],
            "dialogue": "Short dialogue or narration (max 12 words)",
            "sound_effect": "Optional sound effect like POW/BOOM/CRASH (or empty string)"
        }}
    ]
}}

CRITICAL RULES:
- Exactly {num_panels} panels
- Each character appearance and clothing MUST be identical in every panel
- Keep dialogue under 12 words
- Make scenes visually interesting and varied
- Valid JSON only — no trailing commas, no comments"""

    for attempt in range(MAX_RETRIES):
        try:
            response = story_client.chat.completions.create(
                model=STORY_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.75,
                max_tokens=2500,
                timeout=45
            )
            raw = response.choices[0].message.content.strip()

            # Aggressive JSON cleaning
            raw = re.sub(r'```json\s*', '', raw)
            raw = re.sub(r'```\s*', '', raw)
            raw = raw.strip()

            # Find JSON boundaries
            start = raw.find('{')
            end = raw.rfind('}') + 1
            if start != -1 and end > start:
                raw = raw[start:end]

            data = json.loads(raw)

            # Validate structure
            if "panels" not in data or "characters" not in data:
                raise ValueError("Missing required fields")
            if len(data["panels"]) == 0:
                raise ValueError("No panels generated")

            return data, None

        except json.JSONDecodeError:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
                continue
            return None, "Story generation failed — could not parse response. Please try again."

        except Exception as e:
            error = str(e).lower()
            if "rate limit" in error or "429" in error:
                if attempt < MAX_RETRIES - 1:
                    time.sleep(30)
                    continue
                return None, "Rate limit reached. Please wait 30 seconds and try again."
            elif "timeout" in error:
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                    continue
                return None, "Request timed out. Please try again."
            elif "auth" in error or "401" in error:
                return None, "API key error. Please check your NVIDIA API key."
            else:
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                    continue
                return None, f"Story generation failed: {str(e)}"

    return None, "Story generation failed after multiple attempts."

# ════════════════════════════════════════
# IMAGE GENERATION
# ════════════════════════════════════════
def generate_image(image_prompt, seed=42):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    payload = {
        "prompt": image_prompt,
        "width": 1024,
        "height": 1024,
        "num_inference_steps": 4,
        "seed": seed,
        "guidance_scale": 0.0
    }

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(
                IMAGE_API_URL,
                headers=headers,
                json=payload,
                timeout=90
            )

            if response.status_code == 200:
                data = response.json()
                if "artifacts" in data and len(data["artifacts"]) > 0:
                    img_b64 = data["artifacts"][0]["base64"]
                    img_bytes = base64.b64decode(img_b64)
                    return img_bytes, None
                else:
                    return None, "No image returned from API"

            elif response.status_code == 429:
                if attempt < MAX_RETRIES - 1:
                    wait = 30 * (attempt + 1)
                    time.sleep(wait)
                    continue
                return None, "Rate limit reached. Please wait and try again."

            elif response.status_code == 402:
                return None, "API credits exhausted. Please check your NVIDIA account."

            elif response.status_code == 401:
                return None, "Invalid API key."

            elif response.status_code >= 500:
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                    continue
                return None, f"NVIDIA server error ({response.status_code})."

            else:
                return None, f"Image API error: {response.status_code}"

        except requests.Timeout:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
                continue
            return None, "Image generation timed out."

        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
                continue
            return None, f"Image generation failed: {str(e)}"

    return None, "Image generation failed after multiple attempts."

# ════════════════════════════════════════
# PANEL IMAGE BUILDER
# ════════════════════════════════════════
def build_panel_image(img_bytes, dialogue, sound_effect, panel_number):
    """
    Adds dialogue bubble and sound effect overlay to image.
    """
    try:
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        img = img.resize((800, 800), Image.LANCZOS)
        draw = ImageDraw.Draw(img)

        # Add dark overlay at bottom for dialogue
        overlay_height = 120
        overlay = Image.new('RGBA', (800, overlay_height), (0, 0, 0, 180))
        img.paste(overlay, (0, 800 - overlay_height), overlay)

        # Add dialogue text
        if dialogue:
            clean_dialogue = re.sub(r'[^\x00-\x7F]+', ' ', dialogue)
            draw.text(
                (400, 800 - 60),
                f'"{clean_dialogue}"',
                fill=(255, 255, 255),
                anchor="mm"
            )

        # Add sound effect
        if sound_effect and sound_effect.strip():
            clean_sfx = re.sub(r'[^\x00-\x7F]+', '', sound_effect)
            if clean_sfx:
                draw.text(
                    (60, 60),
                    clean_sfx.upper(),
                    fill=(255, 220, 0),
                    stroke_width=2,
                    stroke_fill=(255, 0, 0)
                )

        # Panel number badge
        draw.rectangle([0, 0, 50, 30], fill=(255, 68, 68))
        draw.text(
            (25, 15),
            str(panel_number),
            fill="white",
            anchor="mm"
        )

        # Convert back to bytes
        output = io.BytesIO()
        img.save(output, format="JPEG", quality=95)
        return output.getvalue()

    except Exception:
        return img_bytes

# ════════════════════════════════════════
# PDF GENERATION
# ════════════════════════════════════════
def generate_pdf(title, summary, characters, panels, images):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=10)

    # ── Cover Page ──
    pdf.add_page()
    pdf.set_fill_color(13, 13, 13)
    pdf.rect(0, 0, 210, 297, 'F')

    pdf.set_font("Helvetica", "B", 36)
    pdf.set_text_color(255, 68, 68)
    clean_title = re.sub(r'[^\x00-\x7F]+', ' ', title).upper()
    pdf.cell(0, 20, "", ln=True)
    pdf.cell(0, 20, clean_title, ln=True, align="C")

    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 10, "Generated by AI Comic Generator", ln=True, align="C")
    pdf.cell(0, 8, f"Powered by Meta Llama + FLUX", ln=True, align="C")
    pdf.ln(10)

    pdf.set_draw_color(255, 68, 68)
    pdf.set_line_width(1)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(8)

    # Summary
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(255, 68, 68)
    pdf.cell(0, 10, "STORY SUMMARY", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(200, 200, 200)
    clean_summary = re.sub(r'[^\x00-\x7F]+', ' ', summary)
    pdf.multi_cell(0, 7, clean_summary)
    pdf.ln(8)

    # Characters
    if characters:
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_text_color(255, 68, 68)
        pdf.cell(0, 10, "CHARACTERS", ln=True)
        for char in characters:
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_text_color(255, 215, 0)
            name = re.sub(r'[^\x00-\x7F]+', ' ', char.get('name', ''))
            role = re.sub(r'[^\x00-\x7F]+', ' ', char.get('role', ''))
            pdf.cell(0, 8, f"{name} — {role}", ln=True)
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(180, 180, 180)
            appearance = re.sub(
                r'[^\x00-\x7F]+', ' ', char.get('appearance', ''))
            clothing = re.sub(
                r'[^\x00-\x7F]+', ' ', char.get('clothing', ''))
            pdf.multi_cell(0, 6, f"Appearance: {appearance}")
            pdf.multi_cell(0, 6, f"Clothing: {clothing}")
            pdf.ln(3)

    # ── Comic Panels ──
    for i, panel in enumerate(panels):
        pdf.add_page()

        panel_num = panel.get('panel_number', i + 1)

        # Panel header
        pdf.set_fill_color(255, 68, 68)
        pdf.rect(0, 0, 210, 15, 'F')
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 15, f"  PANEL {panel_num}", ln=True)

        # Image
        if i < len(images) and images[i]:
            try:
                img_bytes = images[i]
                img = Image.open(io.BytesIO(img_bytes))
                img_path = f"/tmp/comic_panel_{i}.jpg"
                img.save(img_path, "JPEG", quality=90)
                pdf.image(img_path, x=10, w=190)
                pdf.ln(3)
            except Exception:
                pdf.set_font("Helvetica", "I", 10)
                pdf.set_text_color(150, 150, 150)
                pdf.cell(0, 30, "[Image not available]",
                         ln=True, align="C")

        # Dialogue
        dialogue = re.sub(
            r'[^\x00-\x7F]+', ' ', panel.get('dialogue', ''))
        if dialogue.strip():
            pdf.set_fill_color(255, 255, 255)
            pdf.rect(10, pdf.get_y(), 190, 15, 'F')
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_text_color(0, 0, 0)
            pdf.cell(0, 15, f'  "{dialogue}"', ln=True)
            pdf.ln(2)

        # Sound effect
        sfx = re.sub(r'[^\x00-\x7F]+', '', panel.get('sound_effect', ''))
        if sfx.strip():
            pdf.set_font("Helvetica", "B", 14)
            pdf.set_text_color(255, 68, 68)
            pdf.cell(0, 10, sfx.upper(), ln=True, align="C")

        # Scene info
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(120, 120, 120)
        scene = re.sub(r'[^\x00-\x7F]+', ' ', panel.get('scene', ''))
        pdf.multi_cell(0, 5, f"Scene: {scene}")

    return bytes(pdf.output())

# ════════════════════════════════════════
# SESSION STATE
# ════════════════════════════════════════
defaults = {
    "comic_data": None,
    "character_memory": None,
    "images": [],
    "panel_prompts": [],
    "last_request": 0,
    "generation_complete": False
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ════════════════════════════════════════
# ARCHITECTURE DIAGRAM (sidebar)
# ════════════════════════════════════════
with st.sidebar:
    st.markdown("### 🏗️ System Architecture")
    st.markdown("""
<div class="arch-box">
USER IDEA
    ↓
[INPUT VALIDATOR]
    ↓
[STORY ENGINE]
Meta Llama 3.3 70B
    ↓
[CHARACTER MEMORY]
Seed Locking System
    ↓
[PROMPT ENGINE]
Scene → Image Prompt
    ↓
[IMAGE ENGINE]
FLUX.1-schnell
    ↓
[PANEL BUILDER]
Image + Dialogue
    ↓
[PDF BUILDER]
Final Comic Export
</div>
""", unsafe_allow_html=True)

    st.markdown("### 📊 Session Stats")
    if st.session_state.comic_data:
        data = st.session_state.comic_data
        st.metric("Panels", len(data.get("panels", [])))
        st.metric("Characters", len(data.get("characters", [])))
        st.metric("Images", len(
            [i for i in st.session_state.images if i]))
    else:
        st.info("No comic generated yet")

    st.markdown("### ⚠️ API Credits Notice")
    st.warning(
        "FLUX.1-schnell has limited free credits. "
        "Each comic uses 1 credit per panel."
    )

# ════════════════════════════════════════
# INPUT SECTION
# ════════════════════════════════════════
st.markdown("### 💡 Your Comic Idea")

col1, col2 = st.columns([3, 2])

with col1:
    idea = st.text_area(
        "Describe your story idea:",
        placeholder=(
            "Example: A teenage hacker discovers that the city's "
            "AI system has become sentient and is secretly protecting "
            "homeless people from corrupt politicians..."
        ),
        height=130,
        max_chars=MAX_INPUT
    )
    char_count = len(idea) if idea else 0
    st.caption(f"{char_count}/{MAX_INPUT} characters")

with col2:
    genre = st.selectbox("Genre:", [
        "Action/Adventure", "Science Fiction",
        "Fantasy", "Mystery/Thriller",
        "Comedy", "Horror", "Superhero",
        "Historical", "Romance"
    ])
    style = st.selectbox("Art Style:", [
        "Comic Book", "Manga",
        "Cartoon", "Dark/Noir",
        "Retro/Vintage"
    ])
    num_panels = st.selectbox(
        "Panels:", [3, 4, 5, 6], index=1)

st.markdown("<br>", unsafe_allow_html=True)
generate_btn = st.button("💥 GENERATE MY COMIC")
st.divider()

# ════════════════════════════════════════
# GENERATION PIPELINE
# ════════════════════════════════════════
if generate_btn:

    # Rate limiting
    now = time.time()
    if now - st.session_state.last_request < REQUEST_COOLDOWN:
        st.warning("Please wait a moment before generating again.")
        st.stop()

    # Validate
    is_valid, err = validate_input(idea)
    if not is_valid:
        st.markdown(
            f'<div class="error-box">❌ {err}</div>',
            unsafe_allow_html=True)
        st.stop()

    clean_idea = sanitize_input(idea)
    st.session_state.last_request = time.time()

    # Reset state
    st.session_state.comic_data = None
    st.session_state.images = []
    st.session_state.panel_prompts = []
    st.session_state.generation_complete = False

    # ── STEP 1: Story Generation ──
    st.markdown("""
    <div class="info-box">
        ⚙️ <strong>Step 1/3</strong> — Generating story with Meta Llama...
    </div>""", unsafe_allow_html=True)

    with st.spinner("Writing your comic story..."):
        story_data, story_err = generate_story(
            clean_idea, genre, num_panels, style)

    if story_err:
        st.markdown(
            f'<div class="error-box">❌ {story_err}</div>',
            unsafe_allow_html=True)
        st.stop()

    st.markdown("""
    <div class="success-box">✅ Story generated successfully!</div>
    """, unsafe_allow_html=True)

    # ── STEP 2: Character Memory ──
    st.markdown("""
    <div class="info-box">
        ⚙️ <strong>Step 2/3</strong> — Building character memory system...
    </div>""", unsafe_allow_html=True)

    char_memory = CharacterMemory()
    for char in story_data.get("characters", []):
        char_memory.add_character(
            name=char.get("name", "Unknown"),
            appearance=char.get("appearance", ""),
            clothing=char.get("clothing", ""),
            traits=char.get("traits", ""),
            role=char.get("role", "Supporting")
        )

    st.session_state.character_memory = char_memory.to_dict()
    st.session_state.comic_data = story_data

    st.markdown(f"""
    <div class="success-box">
        ✅ Character memory built —
        {len(char_memory.characters)} characters locked with consistent seeds
    </div>""", unsafe_allow_html=True)

    # ── STEP 3: Image Generation ──
    st.markdown("""
    <div class="info-box">
        ⚙️ <strong>Step 3/3</strong> — Generating comic panels with FLUX...
    </div>""", unsafe_allow_html=True)

    panels = story_data.get("panels", [])
    images = []
    panel_prompts = []
    progress = st.progress(0)
    status_text = st.empty()

    for i, panel in enumerate(panels):
        status_text.markdown(
            f"🎨 Generating panel {i+1} of {len(panels)}...")

        # Build locked image prompt
        image_prompt = build_image_prompt(
            scene=panel.get("scene", ""),
            mood=panel.get("mood", "dramatic"),
            environment=panel.get("environment", ""),
            camera_angle=panel.get("camera_angle", "medium shot"),
            lighting=panel.get("lighting", "natural"),
            character_memory=char_memory,
            style=style
        )
        panel_prompts.append(image_prompt)

        # Use consistent seed for character consistency
        chars_present = panel.get("characters_present", [])
        if chars_present and chars_present[0] in char_memory.characters:
            seed = char_memory.get_seed(chars_present[0])
        else:
            seed = 42 + i

        img_bytes, img_err = generate_image(image_prompt, seed)

        if img_err:
            st.markdown(
                f'<div class="warning-box">⚠️ Panel {i+1}: {img_err}</div>',
                unsafe_allow_html=True)
            images.append(None)
        else:
            # Build final panel with overlay
            final_img = build_panel_image(
                img_bytes=img_bytes,
                dialogue=panel.get("dialogue", ""),
                sound_effect=panel.get("sound_effect", ""),
                panel_number=i + 1
            )
            images.append(final_img)

        progress.progress((i + 1) / len(panels))
        time.sleep(REQUEST_COOLDOWN)

    st.session_state.images = images
    st.session_state.panel_prompts = panel_prompts
    st.session_state.generation_complete = True

    progress.empty()
    status_text.empty()

    st.markdown("""
    <div class="success-box">
        ✅ Comic generated! Scroll down to view your comic book.
    </div>""", unsafe_allow_html=True)

# ════════════════════════════════════════
# DISPLAY COMIC
# ════════════════════════════════════════
if st.session_state.comic_data and st.session_state.generation_complete:

    data = st.session_state.comic_data
    images = st.session_state.images
    char_memory_dict = st.session_state.character_memory or {}

    # Title
    st.markdown(f"""
    <div style="text-align:center;padding:1.5rem 0 0.5rem 0;">
        <h1 style="font-family:'Bangers',cursive;font-size:3.5rem;
        color:#ff4444;letter-spacing:4px;
        text-shadow:3px 3px 0 black;">
        {data.get('title','MY COMIC').upper()}
        </h1>
    </div>""", unsafe_allow_html=True)

    # Stats
    col1, col2, col3, col4 = st.columns(4)
    panels = data.get("panels", [])
    characters = data.get("characters", [])
    successful_images = len([i for i in images if i])

    with col1:
        st.markdown(f'''<div class="metric-card">
            <h3>{len(panels)}</h3><p>Panels</p></div>''',
                    unsafe_allow_html=True)
    with col2:
        st.markdown(f'''<div class="metric-card">
            <h3>{len(characters)}</h3><p>Characters</p></div>''',
                    unsafe_allow_html=True)
    with col3:
        st.markdown(f'''<div class="metric-card">
            <h3>{successful_images}</h3><p>Images</p></div>''',
                    unsafe_allow_html=True)
    with col4:
        st.markdown(f'''<div class="metric-card">
            <h3>{genre.split("/")[0][:8]}</h3><p>Genre</p></div>''',
                    unsafe_allow_html=True)

    # Summary
    st.markdown('<div class="story-box">', unsafe_allow_html=True)
    st.markdown("**📖 Story Summary**")
    st.write(data.get("summary", ""))
    st.markdown('</div>', unsafe_allow_html=True)

    # Characters
    if characters:
        st.markdown("### 👥 Characters")
        char_cols = st.columns(min(len(characters), 3))
        for i, char in enumerate(characters):
            with char_cols[i % len(char_cols)]:
                seed_val = char_memory_dict.get(
                    char.get('name', ''), {}).get('seed', 'N/A')
                st.markdown(f'''
                <div class="character-card">
                    <div class="character-name">
                        {char.get("name","")}</div>
                    <div class="character-role">
                        {char.get("role","")}</div>
                    <br>
                    <small style="color:#aaa">
                        <strong style="color:#fff">Appearance:</strong><br>
                        {char.get("appearance","")}<br><br>
                        <strong style="color:#fff">Clothing:</strong><br>
                        {char.get("clothing","")}<br><br>
                        <strong style="color:#ffd700">
                        🔒 Seed: {seed_val}</strong>
                    </small>
                </div>''', unsafe_allow_html=True)

    st.divider()

    # Comic Panels
    st.markdown("### 🎬 Comic Panels")

    for i, panel in enumerate(panels):
        panel_num = panel.get("panel_number", i + 1)

        st.markdown(f'<div class="panel-wrapper">', unsafe_allow_html=True)
        st.markdown(
            f'<div class="panel-header">💥 PANEL {panel_num} — '
            f'{panel.get("mood","").upper()}</div>',
            unsafe_allow_html=True)
        st.markdown('<div class="panel-body">', unsafe_allow_html=True)

        col1, col2 = st.columns([3, 2])

        with col1:
            if i < len(images) and images[i]:
                try:
                    img = Image.open(io.BytesIO(images[i]))
                    st.image(img, use_column_width=True)
                except Exception:
                    st.error("Image display error")
            else:
                st.markdown("""
                <div style="background:#1a1a1a;border:2px dashed #333;
                border-radius:8px;padding:3rem;text-align:center;
                color:#555;font-size:2rem;">🎨<br>
                <small style="font-size:0.9rem">Image unavailable</small>
                </div>""", unsafe_allow_html=True)

            # Regenerate button
            regen_key = f"regen_{i}"
            if st.button(f"🔄 Regenerate Panel {panel_num}",
                         key=regen_key):
                with st.spinner(f"Regenerating panel {panel_num}..."):
                    new_prompt = st.session_state.panel_prompts[i] \
                        if i < len(st.session_state.panel_prompts) \
                        else ""
                    new_seed = 42 + i + 100  # Different seed
                    new_img, new_err = generate_image(new_prompt, new_seed)
                    if new_err:
                        st.error(new_err)
                    else:
                        final = build_panel_image(
                            new_img,
                            panel.get("dialogue", ""),
                            panel.get("sound_effect", ""),
                            panel_num
                        )
                        st.session_state.images[i] = final
                        st.rerun()

        with col2:
            # Dialogue
            dialogue = panel.get("dialogue", "")
            if dialogue:
                st.markdown(
                    f'<div class="dialogue-bubble">💬 {dialogue}</div>',
                    unsafe_allow_html=True)

            # Sound effect
            sfx = panel.get("sound_effect", "")
            if sfx and sfx.strip():
                st.markdown(
                    f'<div style="text-align:center;font-family:Bangers,'
                    f'cursive;font-size:2rem;color:#ff4444;'
                    f'text-shadow:2px 2px 0 black;">'
                    f'{sfx.upper()}</div>',
                    unsafe_allow_html=True)

            st.markdown("**🎭 Scene Details**")
            details = {
                "📍 Location": panel.get("environment", ""),
                "📷 Camera": panel.get("camera_angle", ""),
                "💡 Lighting": panel.get("lighting", ""),
                "👥 Characters": ", ".join(
                    panel.get("characters_present", []))
            }
            for label, val in details.items():
                if val:
                    st.caption(f"{label}: {val}")

            # Show locked prompt
            with st.expander("🔒 Image Prompt Used"):
                prompt_text = ""
                if i < len(st.session_state.panel_prompts):
                    prompt_text = st.session_state.panel_prompts[i]
                st.code(prompt_text[:300] + "...", language="text")

        st.markdown('</div></div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

    # ── DOWNLOADS ──
    st.markdown("### 📥 Export Your Comic")
    col1, col2, col3 = st.columns(3)

    with col1:
        try:
            pdf_data = generate_pdf(
                title=data.get("title", "My Comic"),
                summary=data.get("summary", ""),
                characters=characters,
                panels=panels,
                images=images
            )
            st.download_button(
                label="📥 Download Full PDF",
                data=pdf_data,
                file_name=f"comic_{data.get('title','story').replace(' ','_')}.pdf",
                mime="application/pdf"
            )
        except Exception as e:
            st.error(f"PDF failed: {str(e)}")

    with col2:
        # Export character memory as JSON
        if st.session_state.character_memory:
            char_json = json.dumps(
                st.session_state.character_memory, indent=2)
            st.download_button(
                label="🧠 Export Character Memory",
                data=char_json,
                file_name="character_memory.json",
                mime="application/json"
            )

    with col3:
        if st.button("🔄 Create New Comic"):
            for key in defaults:
                st.session_state[key] = defaults[key]
            st.rerun()
