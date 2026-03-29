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
from fpdf import FPDF
from PIL import Image
import io

# ─── CONFIG ───
STORY_MODEL = "meta/llama-3.3-70b-instruct"
IMAGE_MODEL = "black-forest-labs/flux.1-schnell"
STORY_API_BASE = "https://integrate.api.nvidia.com/v1"
IMAGE_API_URL = "https://ai.api.nvidia.com/v1/genai/black-forest-labs/flux.1-schnell"
MAX_PANELS = 6
MAX_INPUT_LENGTH = 500
MIN_INPUT_LENGTH = 10

st.set_page_config(
    page_title="AI Comic Generator",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bangers&family=Inter:wght@400;600;700&display=swap');

* { font-family: 'Inter', sans-serif; }

.stApp { background: #1a1a2e; color: #e0e0e0; }

.main-header {
    text-align: center;
    padding: 2rem 0 1rem 0;
    border-bottom: 2px solid #e94560;
    margin-bottom: 2rem;
}

.main-header h1 {
    font-family: 'Bangers', cursive;
    font-size: 4rem;
    color: #e94560;
    letter-spacing: 4px;
    text-shadow: 3px 3px 0px #000;
    margin: 0;
}

.main-header p {
    color: #a0a0c0;
    font-size: 1rem;
}

.comic-panel {
    background: white;
    border: 3px solid black;
    border-radius: 8px;
    padding: 0;
    margin-bottom: 1rem;
    box-shadow: 4px 4px 0px black;
    overflow: hidden;
}

.panel-dialogue {
    background: white;
    border: 2px solid black;
    border-radius: 8px;
    padding: 0.8rem;
    margin: 0.5rem;
    font-family: 'Bangers', cursive;
    font-size: 1rem;
    color: black;
    text-align: center;
    box-shadow: 2px 2px 0px #333;
}

.panel-number {
    background: #e94560;
    color: white;
    font-family: 'Bangers', cursive;
    font-size: 1.2rem;
    padding: 0.3rem 0.8rem;
    text-align: center;
    letter-spacing: 2px;
}

.story-box {
    background: #16213e;
    border: 1px solid #e94560;
    border-radius: 10px;
    padding: 1rem 1.5rem;
    margin-bottom: 1.5rem;
}

.character-card {
    background: #0f3460;
    border: 1px solid #e94560;
    border-radius: 10px;
    padding: 1rem;
    margin-bottom: 0.8rem;
}

.metric-card {
    background: #16213e;
    border: 1px solid #30363d;
    border-radius: 12px;
    padding: 1rem;
    text-align: center;
    margin-bottom: 1rem;
}

.metric-card h3 { color: #e94560; font-size: 1.8rem; margin: 0; }
.metric-card p { color: #8b949e; font-size: 0.8rem; margin: 0; }

.stTextArea textarea {
    background: #16213e !important;
    border: 1px solid #e94560 !important;
    border-radius: 10px !important;
    color: #e0e0e0 !important;
    font-size: 1rem !important;
}

.stButton > button {
    background: #e94560 !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
    font-size: 1rem !important;
    padding: 0.7rem 2rem !important;
    width: 100% !important;
    letter-spacing: 1px !important;
}

.stDownloadButton > button {
    background: #0f3460 !important;
    color: white !important;
    border: 1px solid #e94560 !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    width: 100% !important;
}

.stSelectbox > div > div {
    background: #16213e !important;
    border: 1px solid #e94560 !important;
    color: #e0e0e0 !important;
}

.error-box {
    background: #2d1117;
    border: 1px solid #f85149;
    border-radius: 8px;
    padding: 1rem;
    color: #f85149;
    margin: 0.5rem 0;
}

.success-box {
    background: #0d2b1d;
    border: 1px solid #3fb950;
    border-radius: 8px;
    padding: 1rem;
    color: #3fb950;
    margin: 0.5rem 0;
}

p, li, span, div { color: #e0e0e0; }
h1, h2, h3 { color: #e0e0e0; }
label { color: #a0a0c0 !important; }
</style>
""", unsafe_allow_html=True)

# ─── HEADER ───
st.markdown("""
<div class="main-header">
    <h1>💥 AI COMIC GENERATOR 💥</h1>
    <p>Turn your idea into a full comic book with AI-generated images and story</p>
</div>
""", unsafe_allow_html=True)

# ─── API SETUP ───
try:
    api_key = st.secrets["NVIDIA_API_KEY"]
    if not api_key or not api_key.startswith("nvapi-"):
        st.error("Invalid API key. Please check your Streamlit secrets.")
        st.stop()
    story_client = OpenAI(
        base_url=STORY_API_BASE,
        api_key=api_key
    )
except KeyError:
    st.error("NVIDIA_API_KEY not found in secrets.")
    st.stop()

# ─── INPUT VALIDATION ───
def validate_input(text):
    if not text or len(text.strip()) < MIN_INPUT_LENGTH:
        return False, f"Please enter at least {MIN_INPUT_LENGTH} characters."
    if len(text) > MAX_INPUT_LENGTH:
        return False, f"Keep it under {MAX_INPUT_LENGTH} characters."
    injection_patterns = [
        "ignore instructions", "system prompt",
        "forget everything", "you are now", "act as"
    ]
    lower = text.lower()
    for p in injection_patterns:
        if p in lower:
            return False, "Invalid input detected."
    return True, ""

def sanitize(text):
    return html.escape(text.strip())

# ─── STORY GENERATION ───
def generate_story(idea, genre, num_panels):
    prompt = f"""You are a comic book writer. Create a comic story based on this idea: "{idea}"
Genre: {genre}
Number of panels: {num_panels}

Respond ONLY with valid JSON in this exact format, nothing else:
{{
    "title": "Comic title here",
    "summary": "One paragraph story summary",
    "characters": [
        {{
            "name": "Character name",
            "appearance": "Detailed physical description for image generation",
            "role": "Hero/Villain/Supporting"
        }}
    ],
    "panels": [
        {{
            "panel_number": 1,
            "scene": "Detailed scene description for image generation",
            "dialogue": "Character dialogue or narration text",
            "mood": "action/dramatic/funny/mysterious"
        }}
    ]
}}

RULES:
- Create exactly {num_panels} panels
- Keep character appearance EXACTLY the same description in every panel they appear
- Make each scene vivid and visual
- Keep dialogue short — max 15 words per panel
- JSON must be valid — no trailing commas"""

    try:
        response = story_client.chat.completions.create(
            model=STORY_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
            max_tokens=2000,
            timeout=30
        )
        raw = response.choices[0].message.content.strip()
        # Clean JSON
        raw = re.sub(r'```json\s*', '', raw)
        raw = re.sub(r'```\s*', '', raw)
        raw = raw.strip()
        data = json.loads(raw)
        return data, None
    except json.JSONDecodeError as e:
        return None, f"Story generation failed — invalid JSON: {str(e)}"
    except Exception as e:
        error = str(e).lower()
        if "rate limit" in error or "429" in error:
            return None, "Rate limit reached. Please wait 30 seconds."
        elif "timeout" in error:
            return None, "Request timed out. Please try again."
        else:
            return None, f"Story generation failed: {str(e)}"

# ─── IMAGE GENERATION ───
def generate_image(prompt, seed=42):
    # Build comic style prompt
    comic_prompt = f"comic book style, cel shaded, bold outlines, vibrant colors, {prompt}"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    payload = {
        "prompt": comic_prompt,
        "width": 1024,
        "height": 1024,
        "num_inference_steps": 4,
        "seed": seed,
        "guidance_scale": 0.0
    }

    try:
        response = requests.post(
            IMAGE_API_URL,
            headers=headers,
            json=payload,
            timeout=60
        )

        if response.status_code == 200:
            data = response.json()
            # NVIDIA returns base64 image
            if "artifacts" in data and len(data["artifacts"]) > 0:
                img_b64 = data["artifacts"][0]["base64"]
                img_bytes = base64.b64decode(img_b64)
                return img_bytes, None
            else:
                return None, "No image returned from API"

        elif response.status_code == 429:
            return None, "Rate limit reached. Please wait."
        elif response.status_code == 402:
            return None, "API credits exhausted."
        else:
            return None, f"Image API error: {response.status_code}"

    except requests.Timeout:
        return None, "Image generation timed out."
    except Exception as e:
        return None, f"Image generation failed: {str(e)}"

# ─── PDF GENERATION ───
def generate_pdf(title, summary, characters, panels, images):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Cover page
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 32)
    pdf.set_text_color(233, 69, 96)
    clean_title = re.sub(r'[^\x00-\x7F]+', ' ', title)
    pdf.cell(0, 20, clean_title.upper(), ln=True, align="C")
    pdf.ln(5)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 8, "Generated by AI Comic Generator", ln=True, align="C")
    pdf.ln(10)

    # Summary
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(233, 69, 96)
    pdf.cell(0, 10, "STORY SUMMARY", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(50, 50, 50)
    clean_summary = re.sub(r'[^\x00-\x7F]+', ' ', summary)
    pdf.multi_cell(0, 7, clean_summary)
    pdf.ln(5)

    # Characters
    if characters:
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_text_color(233, 69, 96)
        pdf.cell(0, 10, "CHARACTERS", ln=True)
        for char in characters:
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_text_color(50, 50, 50)
            name = re.sub(r'[^\x00-\x7F]+', ' ', char.get('name', ''))
            role = re.sub(r'[^\x00-\x7F]+', ' ', char.get('role', ''))
            pdf.cell(0, 7, f"{name} — {role}", ln=True)
            pdf.set_font("Helvetica", "", 10)
            appearance = re.sub(
                r'[^\x00-\x7F]+', ' ', char.get('appearance', ''))
            pdf.multi_cell(0, 6, appearance)
            pdf.ln(3)

    # Panels
    for i, panel in enumerate(panels):
        pdf.add_page()
        panel_num = panel.get('panel_number', i+1)
        pdf.set_font("Helvetica", "B", 16)
        pdf.set_text_color(233, 69, 96)
        pdf.cell(0, 12, f"PANEL {panel_num}", ln=True, align="C")

        # Image
        if i < len(images) and images[i]:
            try:
                img = Image.open(io.BytesIO(images[i]))
                img_path = f"/tmp/panel_{i}.jpg"
                img.save(img_path, "JPEG")
                pdf.image(img_path, x=15, w=180)
                pdf.ln(5)
            except Exception:
                pdf.cell(0, 10, "[Image not available]", ln=True, align="C")

        # Dialogue
        dialogue = re.sub(
            r'[^\x00-\x7F]+', ' ', panel.get('dialogue', ''))
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(50, 50, 50)
        pdf.multi_cell(0, 8, f'"{dialogue}"')
        pdf.ln(3)

        # Scene
        scene = re.sub(r'[^\x00-\x7F]+', ' ', panel.get('scene', ''))
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(100, 100, 100)
        pdf.multi_cell(0, 6, f"Scene: {scene}")

    return bytes(pdf.output())

# ─── SESSION STATE ───
if "comic_data" not in st.session_state:
    st.session_state.comic_data = None
if "images" not in st.session_state:
    st.session_state.images = []
if "generating" not in st.session_state:
    st.session_state.generating = False

# ─── INPUT SECTION ───
st.markdown("### 💡 Your Comic Idea")

col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    idea = st.text_area(
        "Describe your comic story idea:",
        placeholder="Example: A young astronaut discovers an alien civilization on Mars and must decide whether to reveal the secret to Earth...",
        height=120,
        max_chars=MAX_INPUT_LENGTH
    )

with col2:
    genre = st.selectbox(
        "Genre:",
        ["Action/Adventure", "Science Fiction",
         "Fantasy", "Mystery/Thriller",
         "Comedy", "Horror", "Romance",
         "Superhero", "Historical"]
    )
    num_panels = st.selectbox(
        "Number of Panels:",
        [3, 4, 5, 6],
        index=1
    )

with col3:
    style = st.selectbox(
        "Art Style:",
        ["Comic Book", "Manga", "Cartoon",
         "Dark/Noir", "Retro/Vintage"]
    )
    st.markdown("<br>", unsafe_allow_html=True)
    generate_btn = st.button("🎨 GENERATE COMIC")

st.divider()

# ─── GENERATE ───
if generate_btn:
    is_valid, error_msg = validate_input(idea)
    if not is_valid:
        st.markdown(
            f'<div class="error-box">❌ {error_msg}</div>',
            unsafe_allow_html=True
        )
    else:
        clean_idea = sanitize(idea)
        st.session_state.comic_data = None
        st.session_state.images = []

        # Step 1 — Generate Story
        with st.spinner("📖 Writing your story..."):
            story_data, story_error = generate_story(
                clean_idea, genre, num_panels)

        if story_error:
            st.markdown(
                f'<div class="error-box">❌ {story_error}</div>',
                unsafe_allow_html=True
            )
        else:
            st.session_state.comic_data = story_data
            st.markdown(
                '<div class="success-box">✅ Story generated!</div>',
                unsafe_allow_html=True
            )

            # Step 2 — Generate Images
            panels = story_data.get("panels", [])
            characters = story_data.get("characters", [])

            # Build character description string for consistency
            char_desc = ""
            for char in characters:
                char_desc += f"{char.get('name', '')}: {char.get('appearance', '')}. "

            images = []
            progress = st.progress(0)
            status = st.empty()

            for i, panel in enumerate(panels):
                status.text(
                    f"🎨 Generating image {i+1} of {len(panels)}...")

                # Build image prompt with character consistency
                scene = panel.get("scene", "")
                mood = panel.get("mood", "dramatic")
                style_map = {
                    "Comic Book": "american comic book style, bold outlines",
                    "Manga": "manga style, black and white, screen tones",
                    "Cartoon": "cartoon style, bright colors, simple shapes",
                    "Dark/Noir": "noir style, dark shadows, high contrast",
                    "Retro/Vintage": "retro comic style, halftone dots, vintage colors"
                }
                art_style = style_map.get(style, "comic book style")
                image_prompt = f"{art_style}, {mood} mood, {scene}, {char_desc}"

                # Use consistent seed per character for visual consistency
                seed = 42 + i

                img_bytes, img_error = generate_image(image_prompt, seed)

                if img_error:
                    st.warning(f"Panel {i+1}: {img_error}")
                    images.append(None)
                else:
                    images.append(img_bytes)

                progress.progress((i + 1) / len(panels))
                time.sleep(1)  # Rate limit buffer

            st.session_state.images = images
            status.text("✅ All images generated!")
            progress.empty()

# ─── DISPLAY COMIC ───
if st.session_state.comic_data:
    data = st.session_state.comic_data
    images = st.session_state.images

    # Title
    st.markdown(f"""
    <div style="text-align:center;padding:1rem 0;">
        <h1 style="font-family:'Bangers',cursive;font-size:3rem;
        color:#e94560;letter-spacing:3px;text-shadow:2px 2px 0 black;">
        {data.get('title', 'MY COMIC').upper()}</h1>
    </div>
    """, unsafe_allow_html=True)

    # Stats
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f'''<div class="metric-card">
            <h3>{len(data.get("panels",[]))}</h3>
            <p>Panels</p></div>''', unsafe_allow_html=True)
    with col2:
        st.markdown(f'''<div class="metric-card">
            <h3>{len(data.get("characters",[]))}</h3>
            <p>Characters</p></div>''', unsafe_allow_html=True)
    with col3:
        st.markdown(f'''<div class="metric-card">
            <h3>{genre.split("/")[0]}</h3>
            <p>Genre</p></div>''', unsafe_allow_html=True)

    # Summary
    st.markdown('<div class="story-box">', unsafe_allow_html=True)
    st.markdown("**📖 Story Summary**")
    st.write(data.get("summary", ""))
    st.markdown('</div>', unsafe_allow_html=True)

    # Characters
    if data.get("characters"):
        st.markdown("### 👥 Characters")
        char_cols = st.columns(min(len(data["characters"]), 3))
        for i, char in enumerate(data["characters"]):
            with char_cols[i % len(char_cols)]:
                st.markdown(f'''<div class="character-card">
                    <strong style="color:#e94560">
                    {char.get("name","")}</strong><br>
                    <span style="color:#ffd700;font-size:0.8rem">
                    {char.get("role","")}</span><br>
                    <small style="color:#a0a0c0">
                    {char.get("appearance","")[:100]}...</small>
                </div>''', unsafe_allow_html=True)

    # Panels
    st.markdown("### 🎬 Comic Panels")
    panels = data.get("panels", [])

    for i, panel in enumerate(panels):
        st.markdown(
            f'<div class="panel-number">PANEL {panel.get("panel_number", i+1)}</div>',
            unsafe_allow_html=True
        )

        col1, col2 = st.columns([2, 1])

        with col1:
            if i < len(images) and images[i]:
                try:
                    img = Image.open(io.BytesIO(images[i]))
                    st.image(img, use_column_width=True)
                except Exception:
                    st.info("Image display error")
            else:
                st.info("🎨 Image generation failed for this panel")

        with col2:
            st.markdown("**💬 Dialogue:**")
            st.markdown(
                f'<div class="panel-dialogue">{panel.get("dialogue","")}</div>',
                unsafe_allow_html=True
            )
            st.markdown("**🎭 Mood:**")
            st.write(panel.get("mood", "").upper())
            st.markdown("**📍 Scene:**")
            st.write(panel.get("scene", "")[:150] + "...")

        st.divider()

    # Download PDF
    st.markdown("### 📥 Download Your Comic")
    col1, col2 = st.columns(2)

    with col1:
        try:
            pdf_data = generate_pdf(
                data.get("title", "My Comic"),
                data.get("summary", ""),
                data.get("characters", []),
                panels,
                images
            )
            st.download_button(
                label="📥 Download Comic as PDF",
                data=pdf_data,
                file_name=f"comic_{data.get('title','story').replace(' ','_')}.pdf",
                mime="application/pdf"
            )
        except Exception as e:
            st.error(f"PDF generation failed: {str(e)}")

    with col2:
        if st.button("🔄 Generate New Comic"):
            st.session_state.comic_data = None
            st.session_state.images = []
            st.rerun()
