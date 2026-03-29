import streamlit as st
import requests
import base64
import json
import re
import textwrap
import time
from fpdf import FPDF
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

# ==========================================
# 1. STUDIO CONFIGURATION & SECRETS
# ==========================================
st.set_page_config(page_title="Pro AI Comic Studio", page_icon="📓", layout="wide")

try:
    API_KEY = st.secrets["NVIDIA_API_KEY"]
except Exception:
    API_KEY = None

st.markdown("""
    <style>
    .stApp { background-color: #0b0f19; color: #ffffff; }
    .stSidebar { background-color: #111827; }
    .panel-box { border: 1px solid #374151; padding: 15px; border-radius: 12px; background-color: #1f2937; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3); margin-bottom: 20px; }
    h1, h2, h3 { color: #f87171; font-family: 'Arial Black', sans-serif; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. SESSION STATE MANAGEMENT
# ==========================================
if 'comic_ready' not in st.session_state:
    st.session_state.comic_ready = False
if 'final_images' not in st.session_state:
    st.session_state.final_images = []
if 'script_data' not in st.session_state:
    st.session_state.script_data = []
if 'pdf_bytes' not in st.session_state:
    st.session_state.pdf_bytes = None
if 'gif_bytes' not in st.session_state:
    st.session_state.gif_bytes = None

# ==========================================
# 3. SIDEBAR (TOOLS & SETTINGS)
# ==========================================
with st.sidebar:
    st.header("🛠️ Director's Tools")
    
    if not API_KEY:
        st.error("⚠️ NVIDIA_API_KEY is missing from Streamlit Secrets!")
    
    num_panels = st.number_input("Number of Panels", min_value=1, value=4, step=1)
    
    st.markdown("### 🎨 Art Direction")
    art_style = st.selectbox(
        "Comic Style", 
        ["Modern American Comic (Marvel/DC)", "Classic Vintage Comic", "Japanese Manga (Black & White)", "Dark Noir Graphic Novel", "Vibrant Cyberpunk", "Watercolor Storybook"]
    )
    
    st.markdown("### 🖼️ Character Reference (Optional)")
    reference_image = st.file_uploader("Upload a face/character reference", type=['png', 'jpg', 'jpeg'])
    if reference_image:
        st.success("Reference image loaded! It will guide the character design.")

# ==========================================
# 4. CORE AI FUNCTIONS (UPGRADED)
# ==========================================
def fetch_from_api_with_retry(url, headers, payload, max_retries=3):
    """Robust API caller that handles 504 timeouts and retries automatically."""
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                time.sleep(2 * (attempt + 1)) 
                continue
            else:
                raise Exception(f"API Failed after {max_retries} attempts. Error: {e}")

def add_comic_caption(img, text):
    """Pro lettering engine: Dynamic height, centered text, comic styling."""
    width, height = img.size
    
    # 1. Intelligent Font Loading
    try:
        # Tries your custom font first
        font = ImageFont.truetype("Bangers-Regular.ttf", 36) 
    except IOError:
        try:
            # Fallback to standard bold Linux font (looks much better than default)
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", 26)
        except IOError:
            # Absolute last resort
            font = ImageFont.load_default()
            
    # 2. Text Wrapping
    wrapped_text = textwrap.fill(text, width=45)
    
    # 3. Dynamic Height Calculation (Pillow 10+ compatible)
    dummy_img = Image.new('RGB', (1, 1))
    dummy_draw = ImageDraw.Draw(dummy_img)
    bbox = dummy_draw.textbbox((0, 0), wrapped_text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Add padding so it breathes well
    caption_height = max(140, text_height + 80) 
    
    # 4. Create the final canvas with a subtle comic paper tint
    new_img = Image.new('RGB', (width, height + caption_height), '#FFFBEB') 
    new_img.paste(img, (0, 0))
    draw = ImageDraw.Draw(new_img)
    
    # 5. Draw a thick black comic panel border separator
    draw.line([(0, height), (width, height)], fill="black", width=6)
    
    # 6. Center the text perfectly inside the new caption box
    text_x = (width - text_width) / 2
    text_y = height + ((caption_height - text_height) / 2) - 10
    
    draw.multiline_text((text_x, text_y), wrapped_text, fill="black", font=font, align="center")
    
    return new_img

def generate_comic_script(idea, style, panels):
    """Calls NVIDIA LLaMA 3 with an aggressive Master-Writer prompt."""
    url = "https://integrate.api.nvidia.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    
    system_prompt = f"""
    You are an Eisner-Award winning comic book writer. Convert the user's idea into a gripping {panels}-panel story.
    
    STORYTELLING RULES (CRITICAL):
    1. Pacing: Panel 1 introduces the hook, middle panels escalate tension, the final panel hits a powerful climax or cliffhanger.
    2. Show, Don't Tell: Write incredibly detailed visual `image_prompts`. Make the artist do the heavy lifting.
    3. Punchy Text: The `caption` MUST be short (MAXIMUM 20 words per panel). Use gritty, heroic, or dramatic comic-book narration. NO long paragraphs.
    4. Character Consistency: Define exact appearance (clothes, hair, face) and repeat it identically in every prompt.
    
    JSON FORMATTING RULES:
    1. Output ONLY a valid JSON array.
    2. Start your response with [ and end with ].
    3. DO NOT use double quotes (") inside your string values. Use single quotes (') instead.
    
    JSON STRUCTURE:
    [
      {{
        "scene_number": 1,
        "caption": "Short, dramatic narration box (max 20 words).",
        "image_prompt": "{style} style, high quality. [Exact Character Description]. [Action]. [Lighting/Camera Angle]."
      }}
    ]
    """
    
    payload = {
        "model": "meta/llama-3.1-8b-instruct",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"My comic idea: {idea}"}
        ],
        "temperature": 0.4, # Slightly higher for better creative storytelling
        "max_tokens": 1500
    }
    
    response = fetch_from_api_with_retry(url, headers, payload)
    raw_text = response.json().get("choices", [{}])[0].get("message", {}).get("content", "")
    
    if not raw_text or not raw_text.strip():
        raise Exception("NVIDIA returned an empty response. Try a different story prompt!")
    
    clean_text = re.sub(r'```json\s*', '', raw_text)
    clean_text = re.sub(r'```', '', clean_text).strip()
    
    match = re.search(r'\[.*\]', clean_text, re.DOTALL)
    if match:
        clean_text = match.group(0)
        
    try:
        return json.loads(clean_text)
    except json.JSONDecodeError as e:
        print(f"FAILED TO PARSE JSON. RAW AI OUTPUT WAS:\n{raw_text}")
        raise Exception(f"The AI writer made a formatting error. Please click 'Produce My Comic' again! (Details: {e})")

def generate_image(prompt, ref_image=None):
    """Calls NVIDIA SDXL to generate the panel."""
    url = "https://ai.api.nvidia.com/v1/genai/stabilityai/stable-diffusion-xl"
    headers = {"Authorization": f"Bearer {API_KEY}", "Accept": "application/json"}
    
    payload = {
        "text_prompts": [{"text": prompt, "weight": 1}],
        "cfg_scale": 6,
        "sampler": "K_DPM_2_ANCESTRAL",
        "seed": 0,
        "steps": 30
    }
    
    if ref_image:
        ref_bytes = ref_image.getvalue()
        base64_ref = base64.b64encode(ref_bytes).decode('utf-8')
        payload["init_image"] = base64_ref
        payload["image_strength"] = 0.35 
    
    response = fetch_from_api_with_retry(url, headers, payload)
    b64_data = response.json()["artifacts"][0]["base64"]
    return Image.open(BytesIO(base64.b64decode(b64_data)))

# ==========================================
# 5. MAIN DASHBOARD
# ==========================================
st.title("📓 Professional AI Comic Studio")
st.markdown("Write a prompt. Our AI directs the scenes, illustrates the art, and letters the pages.")

user_idea = st.text_area("📖 What is the story about?", "A rogue AI decides it wants to become a chef in a cyberpunk city, but the local mafia steals its recipes.", height=120)

if st.button("🚀 Produce My Comic", use_container_width=True, type="primary"):
    if not API_KEY:
        st.error("Cannot generate: API Key is missing. Check your Streamlit Secrets.")
    else:
        try:
            with st.status("🎬 Pre-Production: Writing script & designing characters...", expanded=True) as status:
                st.session_state.script_data = generate_comic_script(user_idea, art_style, num_panels)
                st.write("✅ Script locked in! Sending to illustration team...")
                
                temp_images = []
                for i, scene in enumerate(st.session_state.script_data):
                    status.update(label=f"🖌️ Illustrating & Lettering Panel {i+1} of {num_panels}...", state="running")
                    
                    base_img = generate_image(scene["image_prompt"], reference_image)
                    final_img = add_comic_caption(base_img, scene["caption"])
                    temp_images.append(final_img)
                
                st.session_state.final_images = temp_images
                status.update(label="🎉 Comic Production Complete!", state="complete")

            # Prepare Downloads
            pdf = FPDF()
            for i, img in enumerate(st.session_state.final_images):
                pdf.add_page()
                temp_path = f"temp_final_{i}.png"
                img.save(temp_path)
                pdf.image(temp_path, x=20, y=20, w=170)
            st.session_state.pdf_bytes = bytes(pdf.output())

            gif_buffer = BytesIO()
            st.session_state.final_images[0].save(
                gif_buffer, format="GIF", save_all=True, append_images=st.session_state.final_images[1:], duration=2500, loop=0
            )
            st.session_state.gif_bytes = gif_buffer.getvalue()

            st.session_state.comic_ready = True

        except Exception as e:
            st.error(f"Production Halted! Error details: {e}")
            st.session_state.comic_ready = False

# ==========================================
# 6. DISPLAY RESULTS & DOWNLOADS
# ==========================================
if st.session_state.comic_ready:
    st.markdown("---")
    cols = st.columns(2) 
    
    for i, (scene, img) in enumerate(zip(st.session_state.script_data, st.session_state.final_images)):
        col_index = i % 2
        with cols[col_index]:
            st.markdown("<div class='panel-box'>", unsafe_allow_html=True)
            st.image(img, use_container_width=True)
            st.markdown(f"**Scene {scene.get('scene_number', i+1)}**")
            with st.expander("Technical Prompt"):
                st.caption(scene.get("image_prompt", "No prompt found."))
            st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("### 📥 Download Deliverables")
    export_col1, export_col2 = st.columns(2)
    
    with export_col1:
        st.download_button("📄 Download PDF Book", data=st.session_state.pdf_bytes, file_name="ai_comic_book.pdf", mime="application/pdf", use_container_width=True)

    with export_col2:
        st.download_button("🎞️ Download Animated Video (GIF)", data=st.session_state.gif_bytes, file_name="comic_motion.gif", mime="image/gif", use_container_width=True)
        
    st.markdown("---")
    if st.button("🔄 Start New Comic", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
