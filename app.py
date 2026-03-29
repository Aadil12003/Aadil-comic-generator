import streamlit as st
import openai
from PIL import Image
import io
import base64
import re
import requests
from datetime import datetime
from fpdf import FPDF
import tempfile
import os

# Page configuration
st.set_page_config(
    page_title="Aadil's AI Comic Generator",
    page_icon="🎭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Playfair+Display:wght@600;700&display=swap');

* { font-family: 'Inter', sans-serif; }

.stApp {
    background: linear-gradient(135deg, #0f0f0f 0%, #1a1a2e 50%, #16213e 100%);
    color: #f0f0f0;
}

.main-header {
    text-align: center;
    padding: 2rem 0;
    border-bottom: 2px solid #444;
    margin-bottom: 2rem;
    background: linear-gradient(90deg, transparent, rgba(212, 175, 55, 0.15), transparent);
}

.main-header h1 {
    font-family: 'Playfair Display', serif;
    font-size: 3rem;
    font-weight: 700;
    background: linear-gradient(135deg, #d4af37 0%, #f4e5c2 50%, #d4af37 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0.5rem;
    letter-spacing: 2px;
}

.main-header p {
    color: #b0b0b0;
    font-size: 1.1rem;
    font-weight: 300;
    letter-spacing: 1px;
}

[data-testid="stSidebar"] {
    background: #151515 !important;
    border-right: 1px solid #444;
}

.sidebar-title {
    color: #d4af37;
    font-size: 1.2rem;
    font-weight: 600;
    margin-bottom: 1rem;
    border-bottom: 1px solid #444;
    padding-bottom: 0.5rem;
}

.character-section {
    background: linear-gradient(145deg, #1e1e1e, #151515);
    border: 1px solid #444;
    border-radius: 12px;
    padding: 1.5rem;
    margin-bottom: 1.5rem;
}

.character-optional {
    display: inline-block;
    background: rgba(100, 100, 100, 0.3);
    color: #888;
    padding: 0.2rem 0.6rem;
    border-radius: 12px;
    font-size: 0.75rem;
    margin-left: 0.5rem;
    font-weight: 500;
}

.stTextArea textarea {
    background: #1a1a1a !important;
    border: 1px solid #555 !important;
    border-radius: 8px !important;
    color: #ffffff !important;
    font-size: 0.95rem !important;
    min-height: 450px !important;
    line-height: 1.6 !important;
}

.stTextArea textarea:focus {
    border-color: #d4af37 !important;
    box-shadow: 0 0 0 2px rgba(212, 175, 55, 0.3) !important;
}

.stTextArea label, .stTextInput label, .stSelectbox label, .stSlider label, .stFileUploader label, .stNumberInput label {
    color: #e0e0e0 !important;
    font-weight: 500 !important;
    font-size: 0.95rem !important;
}

h2, h3, h4 { color: #f5f5f5 !important; font-weight: 600 !important; }

.stButton > button {
    background: linear-gradient(135deg, #d4af37 0%, #b8960c 100%) !important;
    color: #0a0a0a !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
    padding: 0.75rem 2rem !important;
    font-size: 1rem !important;
    transition: all 0.3s ease !important;
    text-transform: uppercase;
    letter-spacing: 1px;
}

.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 25px rgba(212, 175, 55, 0.4) !important;
}

.stButton > button:disabled {
    background: #444 !important;
    color: #888 !important;
    cursor: not-allowed !important;
    transform: none !important;
}

.comic-panel {
    background: #1a1a1a;
    border: 1px solid #444;
    border-radius: 12px;
    padding: 1rem;
    margin: 1rem 0;
    position: relative;
    overflow: hidden;
}

.comic-panel::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: linear-gradient(90deg, #d4af37, #f4e5c2, #d4af37);
}

.panel-number {
    position: absolute;
    top: 10px; right: 15px;
    background: #d4af37;
    color: #0a0a0a;
    width: 30px; height: 30px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 0.9rem;
    z-index: 10;
}

.dialogue-bubble {
    background: #ffffff;
    color: #1a1a1a !important;
    border-radius: 20px;
    padding: 1rem 1.5rem;
    margin: 1rem 0;
    position: relative;
    font-family: 'Comic Sans MS', cursive, sans-serif;
    box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    font-weight: 500;
    line-height: 1.5;
}

.dialogue-bubble::after {
    content: '';
    position: absolute;
    bottom: -10px; left: 30px;
    width: 0; height: 0;
    border-left: 10px solid transparent;
    border-right: 10px solid transparent;
    border-top: 10px solid #ffffff;
}

.info-box {
    background: rgba(212, 175, 55, 0.15);
    border-left: 4px solid #d4af37;
    padding: 1.2rem;
    border-radius: 0 8px 8px 0;
    margin: 1rem 0;
    color: #f0f0f0;
}

.stSuccess {
    background: rgba(0, 200, 83, 0.15) !important;
    border-left: 4px solid #00c853 !important;
    color: #f0f0f0 !important;
}

.stWarning {
    background: rgba(255, 193, 7, 0.15) !important;
    border-left: 4px solid #ffc107 !important;
    color: #ffc107 !important;
}

.stError {
    background: rgba(244, 67, 54, 0.15) !important;
    border-left: 4px solid #f44336 !important;
    color: #f0f0f0 !important;
}

[data-testid="stMetricValue"] {
    color: #d4af37 !important;
    font-weight: 700 !important;
}

[data-testid="stMetricLabel"] {
    color: #b0b0b0 !important;
}

.stFileUploader {
    background: #1a1a1a !important;
    border: 2px dashed #555 !important;
    border-radius: 8px !important;
    padding: 1rem !important;
}

.stFileUploader:hover {
    border-color: #d4af37 !important;
    background: rgba(212, 175, 55, 0.05) !important;
}

.stSelectbox > div > div, .stSlider > div, .stNumberInput > div {
    background: #1a1a1a !important;
    border: 1px solid #555 !important;
    color: #ffffff !important;
}

.streamlit-expanderHeader {
    background: #1e1e1e !important;
    border: 1px solid #444 !important;
    border-radius: 8px !important;
    color: #d4af37 !important;
    font-weight: 600 !important;
}

.download-section {
    background: linear-gradient(145deg, #1e1e1e, #151515);
    border: 3px solid #d4af37;
    border-radius: 16px;
    padding: 2rem;
    margin-top: 2rem;
    box-shadow: 0 10px 40px rgba(212, 175, 55, 0.1);
}

.download-title {
    color: #d4af37;
    font-size: 1.5rem;
    font-weight: 700;
    margin-bottom: 1.5rem;
    text-align: center;
}

.consistency-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    background: rgba(0, 230, 118, 0.15);
    border: 1px solid #00e676;
    color: #00e676;
    padding: 0.5rem 1rem;
    border-radius: 20px;
    font-size: 0.85rem;
    font-weight: 600;
    margin-bottom: 1rem;
}

.optional-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    background: rgba(100, 100, 100, 0.2);
    border: 1px solid #666;
    color: #aaa;
    padding: 0.5rem 1rem;
    border-radius: 20px;
    font-size: 0.85rem;
    font-weight: 500;
    margin-bottom: 1rem;
}

.progress-text {
    color: #d4af37;
    font-size: 1.2rem;
    font-weight: 500;
}

[data-testid="stImageCaption"] {
    color: #b0b0b0 !important;
}

p, span, div { color: #e0e0e0; }

strong { color: #d4af37; }

hr {
    border: none;
    height: 1px;
    background: linear-gradient(90deg, transparent, #444, transparent);
    margin: 2rem 0;
}

.footer {
    text-align: center;
    padding: 2rem 0;
    color: #666;
    border-top: 1px solid #333;
    margin-top: 3rem;
}

.stNumberInput input {
    color: #ffffff !important;
}
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="main-header">
    <h1>🎭 Aadil's AI Comic Generator</h1>
    <p>Professional AI-Powered Comic Creation with Optional Character Consistency</p>
</div>
""", unsafe_allow_html=True)

# Initialize session state
if 'character_face' not in st.session_state:
    st.session_state.character_face = None
if 'character_description' not in st.session_state:
    st.session_state.character_description = ""
if 'comic_panels' not in st.session_state:
    st.session_state.comic_panels = []
if 'story_text' not in st.session_state:
    st.session_state.story_text = ""
if 'generated' not in st.session_state:
    st.session_state.generated = False
if 'api_key' not in st.session_state:
    st.session_state.api_key = ""

# API Key Handling
def get_api_key():
    try:
        return st.secrets["NVIDIA_API_KEY"]
    except:
        if st.session_state.api_key:
            return st.session_state.api_key
    return None

# Sidebar
with st.sidebar:
    st.markdown('<div class="sidebar-title">🎨 Character Setup</div>', unsafe_allow_html=True)
    
    # Character Image Upload - OPTIONAL
    st.markdown('<div class="character-section">', unsafe_allow_html=True)
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader("Character Face")
    with col2:
        st.markdown('<span class="character-optional">OPTIONAL</span>', unsafe_allow_html=True)
    
    st.caption("Upload a face to maintain character consistency across all panels")
    
    uploaded_face = st.file_uploader(
        "Upload character face (JPG/PNG)",
        type=['jpg', 'jpeg', 'png'],
        help="Optional: This face will be used consistently throughout your comic"
    )
    
    if uploaded_face is not None:
        try:
            image = Image.open(uploaded_face)
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            st.session_state.character_face = image
            st.markdown('<div class="consistency-badge">✓ Character Face Active</div>', unsafe_allow_html=True)
            st.image(image, caption="Character Reference", use_container_width=True)
            
            st.session_state.character_description = st.text_area(
                "Character details:",
                value=st.session_state.character_description,
                placeholder="Example: 25-year-old detective, brown trench coat...",
                height=80,
                key="char_desc"
            )
        except Exception as e:
            st.error(f"Error: {str(e)}")
    else:
        st.session_state.character_face = None
        st.markdown('<div class="optional-badge">ℹ No character set - AI will create unique characters</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # API Key - Hidden
    st.markdown('<div class="character-section">', unsafe_allow_html=True)
    with st.expander("⚙️ API Configuration"):
        st.markdown('<div style="color: #888; font-size: 0.85rem; margin-bottom: 1rem;">Enter NVIDIA API Key from <a href="https://build.nvidia.com" target="_blank" style="color: #d4af37;">build.nvidia.com</a></div>', unsafe_allow_html=True)
        
        api_input = st.text_input(
            "API Key",
            type="password",
            placeholder="nvapi-...",
            key="api_key_input"
        )
        
        if api_input:
            st.session_state.api_key = api_input
            st.success("✓ API Key saved")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Style Settings
    st.markdown('<div class="character-section">', unsafe_allow_html=True)
    st.subheader("🎨 Comic Settings")
    
    comic_style = st.selectbox(
        "Art Style",
        ["Modern Comic (Marvel/DC)", "Manga/Anime", "Noir/Detective", 
         "Fantasy/Illustrated", "Minimalist/Indie", "Vintage/Classic"],
        key="style_select"
    )
    
    panel_count = st.number_input(
        "Number of Panels",
        min_value=1,
        max_value=50,
        value=6,
        step=1,
        help="Generate 1 to 50 panels",
        key="panel_count_input"
    )
    
    color_scheme = st.selectbox(
        "Color Scheme",
        ["Full Color", "Black & White", "Sepia/Vintage", "Cyberpunk Neon", "Muted Tones"],
        key="color_select"
    )
    st.markdown('</div>', unsafe_allow_html=True)

# Main Content
col1, col2 = st.columns([2, 1])

with col1:
    st.markdown('<div class="info-box">', unsafe_allow_html=True)
    st.markdown("""
    <strong>📝 How to use:</strong><br><br>
    1. <strong>Upload character face</strong> (optional) for consistency<br>
    2. <strong>Write your story</strong> - use "Panel 1:" or separate paragraphs<br>
    3. <strong>Set panel count</strong> - up to 50 panels supported<br>
    4. <strong>Configure API key</strong> in sidebar<br>
    5. <strong>Generate & Download</strong> as PDF or Video
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.subheader("📖 Your Comic Story")
    
    story_input = st.text_area(
        "Write unlimited story content:",
        value=st.session_state.story_text,
        placeholder="""Panel 1: Detective John stands on the rooftop, rain falling around him.

Panel 2: Flashback to 48 hours ago. John receives an anonymous tip.

Panel 3: The warehouse at midnight. John approaches the door, gun drawn.

[Write up to 50 panels... Unlimited length!]""",
        height=500,
        key="story_input_main"
    )
    
    st.session_state.story_text = story_input

with col2:
    st.subheader("📊 Stats")
    
    char_count = len(story_input)
    word_count = len(story_input.split()) if story_input else 0
    detected_panels = len([p for p in re.split(r'\n\s*(?:Panel|PANEL)?\s*\d+', story_input) if p.strip()])
    
    st.metric("Characters", f"{char_count:,}")
    st.metric("Words", f"{word_count:,}")
    st.metric("Detected Scenes", max(1, detected_panels))
    
    st.subheader("✓ Status")
    
    has_key = get_api_key() is not None
    has_story = len(story_input.strip()) > 20
    has_face = st.session_state.character_face is not None
    
    if has_key:
        st.success("✓ API ready")
    else:
        st.warning("⚠ API key needed")
    
    if has_story:
        st.success("✓ Story ready")
    else:
        st.warning("⚠ Story too short")
    
    if has_face:
        st.success("✓ Character set")
    else:
        st.info("ℹ No character (optional)")

# Generation
st.markdown("<hr>", unsafe_allow_html=True)

gen_col1, gen_col2, gen_col3 = st.columns([1, 2, 1])

with gen_col2:
    can_generate = has_key and has_story
    
    generate_btn = st.button(
        f"🎨 Generate {panel_count} Panel{'s' if panel_count > 1 else ''}",
        disabled=not can_generate,
        use_container_width=True
    )

# FIXED Generation Logic
if generate_btn:
    api_key = get_api_key()
    
    with st.spinner(f"🎭 Creating {panel_count} comic panels..."):
        try:
            client = openai.OpenAI(
                base_url="https://integrate.api.nvidia.com/v1",
                api_key=api_key
            )
            
            # Prepare character if available
            char_base64 = None
            char_prompt = ""
            if st.session_state.character_face is not None:
                buffered = io.BytesIO()
                st.session_state.character_face.save(buffered, format="JPEG")
                char_base64 = base64.b64encode(buffered.getvalue()).decode()
                char_desc = st.session_state.character_description or "consistent appearance"
                char_prompt = f"CHARACTER REFERENCE (USE THIS FACE): data:image/jpeg;base64,{char_base64}. Character: {char_desc}. "
            
            # FIXED: Better story parsing - clean markdown first
            # Remove code blocks, markdown formatting
            clean_story = re.sub(r'```[\s\S]*?```', '', story_input)  # Remove code blocks
            clean_story = re.sub(r'`[^`]*`', '', clean_story)  # Remove inline code
            clean_story = re.sub(r'\[.*?\]\(.*?\)', '', clean_story)  # Remove markdown links
            clean_story = re.sub(r'[#*_~]', '', clean_story)  # Remove markdown symbols
            
            # Parse panels - look for explicit panel markers first
            raw_panels = []
            
            # Try to find "Panel X:" pattern
            panel_pattern = r'(?:^|\n)\s*(?:Panel|PANEL)\s*(\d+)[:.\)]?\s*(.*?)(?=(?:\n\s*(?:Panel|PANEL)\s*\d+[:.\)]?)|$)'
            matches = re.findall(panel_pattern, clean_story, re.DOTALL | re.IGNORECASE)
            
            if matches:
                # Sort by panel number and extract text
                matches = sorted(matches, key=lambda x: int(x[0]))
                raw_panels = [p[1].strip() for p in matches if p[1].strip()]
            else:
                # Fallback: split by double newlines or numbered lists
                raw_panels = [p.strip() for p in re.split(r'\n\s*\n|\n\s*\d+[.)\]]\s*', clean_story) if p.strip()]
            
            # Limit to requested count
            raw_panels = raw_panels[:panel_count]
            
            # Fill if needed
            while len(raw_panels) < panel_count:
                if raw_panels:
                    longest = max(raw_panels, key=len)
                    idx = raw_panels.index(longest)
                    mid = len(longest) // 2
                    if len(longest) > 100:
                        raw_panels[idx:idx+1] = [longest[:mid].strip(), longest[mid:].strip()]
                    else:
                        raw_panels.append(f"Scene {len(raw_panels) + 1}")
                else:
                    raw_panels.append(f"Scene {len(raw_panels) + 1}")
            
            # Ensure we don't exceed
            raw_panels = raw_panels[:panel_count]
            
            generated_panels = []
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for idx, panel_text in enumerate(raw_panels):
                # Show progress
                preview = panel_text[:50] + "..." if len(panel_text) > 50 else panel_text
                status_text.markdown(f'<div class="progress-text">Panel {idx + 1}/{panel_count}: {preview}</div>', unsafe_allow_html=True)
                
                # Style prompts
                style_prompts = {
                    "Modern Comic (Marvel/DC)": "modern American comic book style, bold dynamic lines, professional coloring, cinematic composition, high quality",
                    "Manga/Anime": "manga anime style, detailed inking, expressive features, dynamic composition, professional quality",
                    "Noir/Detective": "film noir comic style, high contrast shadows, dramatic lighting, gritty atmospheric, cinematic",
                    "Fantasy/Illustrated": "detailed fantasy illustration, rich cinematic colors, epic scale, painterly professional quality",
                    "Minimalist/Indie": "indie comic style, clean artistic lines, thoughtful composition, muted palette, professional",
                    "Vintage/Classic": "1950s vintage comic style, classic coloring, retro aesthetic, professional quality"
                }
                
                color_prompts = {
                    "Full Color": "vibrant full color",
                    "Black & White": "black and white ink drawing",
                    "Sepia/Vintage": "sepia vintage tones",
                    "Cyberpunk Neon": "neon cyberpunk colors",
                    "Muted Tones": "desaturated earth tones"
                }
                
                style_desc = style_prompts.get(comic_style, "modern comic")
                color_desc = color_prompts.get(color_scheme, "full color")
                
                # Build prompt
                if char_base64:
                    full_prompt = f"""Comic book panel illustration. {style_desc}, {color_desc}. {char_prompt}Scene: {panel_text}. Single panel composition, no text in image, professional detailed artwork, high quality."""
                else:
                    full_prompt = f"""Comic book panel illustration. {style_desc}, {color_desc}. Scene: {panel_text}. Single panel composition, consistent characters throughout story, no text in image, professional detailed artwork, high quality."""
                
                try:
                    # FIXED: Proper API call with error handling
                    response = client.images.generate(
                        model="black-forest-labs/flux-dev",
                        prompt=full_prompt,
                        n=1,
                        size="1024x1024",
                        quality="standard"
                    )
                    
                    if response.data and len(response.data) > 0:
                        img_data = response.data[0]
                        img_url = img_data.url if hasattr(img_data, 'url') else None
                        
                        if img_url:
                            generated_panels.append({
                                'text': panel_text,
                                'image_url': img_url,
                                'panel_num': idx + 1
                            })
                        else:
                            generated_panels.append({
                                'text': panel_text,
                                'image_url': None,
                                'panel_num': idx + 1,
                                'error': 'No URL in response'
                            })
                    else:
                        generated_panels.append({
                            'text': panel_text,
                            'image_url': None,
                            'panel_num': idx + 1,
                            'error': 'Empty response data'
                        })
                        
                except Exception as e:
                    error_msg = str(e)
                    generated_panels.append({
                        'text': panel_text,
                        'image_url': None,
                        'panel_num': idx + 1,
                        'error': error_msg
                    })
                    # Don't stop - continue with other panels
                
                progress_bar.progress((idx + 1) / panel_count)
            
            st.session_state.comic_panels = generated_panels
            st.session_state.generated = True
            status_text.empty()
            progress_bar.empty()
            
            success_count = sum(1 for p in generated_panels if p.get('image_url'))
            if success_count == len(generated_panels):
                st.success(f"✓ Generated all {len(generated_panels)} panels successfully!")
            else:
                st.warning(f"⚠ Generated {success_count}/{len(generated_panels)} panels. {len(generated_panels) - success_count} failed.")
            
        except Exception as e:
            st.error(f"Generation error: {str(e)}")

# Display Comic
if st.session_state.generated and st.session_state.comic_panels:
    st.markdown("<hr>", unsafe_allow_html=True)
    st.subheader("🎭 Your Generated Comic")
    
    panels = st.session_state.comic_panels
    
    # Show error summary if any
    failed_panels = [p for p in panels if not p.get('image_url')]
    if failed_panels:
        with st.expander(f"⚠ {len(failed_panels)} panel(s) failed - Click to see details"):
            for p in failed_panels:
                st.text(f"Panel {p['panel_num']}: {p.get('error', 'Unknown error')}")
    
    cols_per_row = 2 if len(panels) <= 6 else 3
    
    for i in range(0, len(panels), cols_per_row):
        cols = st.columns(cols_per_row)
        
        for j, col in enumerate(cols):
            idx = i + j
            if idx < len(panels):
                panel = panels[idx]
                
                with col:
                    st.markdown(f'<div class="comic-panel">', unsafe_allow_html=True)
                    st.markdown(f'<div class="panel-number">{panel["panel_num"]}</div>', unsafe_allow_html=True)
                    
                    if panel.get('image_url'):
                        st.image(panel['image_url'], use_container_width=True)
                    else:
                        st.error(f"⚠ Panel {panel['panel_num']} failed")
                        if panel.get('error'):
                            st.caption(f"Error: {panel['error'][:100]}")
                    
                    display_text = panel["text"][:180] + "..." if len(panel["text"]) > 180 else panel["text"]
                    st.markdown(f'<div class="dialogue-bubble">{display_text}</div>', unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)

    # FIXED DOWNLOAD SECTION
    st.markdown('<div class="download-section">', unsafe_allow_html=True)
    st.markdown('<div class="download-title">💾 Download Your Comic</div>', unsafe_allow_html=True)
    
    # FIXED PDF Function
    def create_comic_pdf(panels, style, color_scheme):
        try:
            pdf = FPDF()
            pdf.set_auto_page_break(auto=True, margin=15)
            
            # Title page
            pdf.add_page()
            pdf.set_font("Helvetica", "B", 24)
            pdf.set_text_color(212, 175, 55)
            pdf.cell(0, 20, "Aadil's AI Comic Generator", ln=True, align="C")
            pdf.ln(10)
            
            pdf.set_font("Helvetica", "", 12)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(0, 10, f"Style: {style}", ln=True, align="C")
            pdf.cell(0, 10, f"Color Scheme: {color_scheme}", ln=True, align="C")
            pdf.cell(0, 10, f"Total Panels: {len(panels)}", ln=True, align="C")
            pdf.cell(0, 10, f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align="C")
            pdf.ln(20)
            
            # Add each panel
            for panel in panels:
                pdf.add_page()
                
                # Panel header
                pdf.set_font("Helvetica", "B", 16)
                pdf.set_text_color(212, 175, 55)
                pdf.cell(0, 10, f"Panel {panel['panel_num']}", ln=True)
                pdf.ln(5)
                
                # Add image if available
                if panel.get('image_url'):
                    try:
                        response = requests.get(panel['image_url'], timeout=30)
                        if response.status_code == 200:
                            # Save temp image
                            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp:
                                tmp.write(response.content)
                                tmp_path = tmp.name
                            
                            # Add to PDF (fit width, maintain aspect)
                            pdf.image(tmp_path, x=10, y=25, w=190)
                            
                            # Remove temp file
                            os.unlink(tmp_path)
                            
                            # Add description below image
                            pdf.ln(110)  # Space after image
                        else:
                            pdf.ln(10)
                    except Exception as img_err:
                        pdf.ln(10)
                        pdf.set_text_color(255, 0, 0)
                        pdf.cell(0, 10, "[Image failed to load]", ln=True)
                        pdf.ln(5)
                else:
                    pdf.ln(10)
                
                # Panel text
                pdf.set_font("Helvetica", "", 11)
                pdf.set_text_color(50, 50, 50)
                
                # Clean text for PDF (handle encoding)
                clean_text = panel['text']
                # Replace problematic characters
                clean_text = clean_text.replace('—', '-').replace('"', '"').replace('"', '"')
                clean_text = clean_text.replace(''', "'").replace(''', "'")
                clean_text = clean_text.encode('latin-1', 'replace').decode('latin-1')
                
                pdf.multi_cell(0, 8, clean_text)
                pdf.ln(10)
            
            # Return PDF as bytes - FIXED
            pdf_output = pdf.output(dest='S')
            if isinstance(pdf_output, str):
                return pdf_output.encode('latin-1')
            else:
                return bytes(pdf_output) if isinstance(pdf_output, (bytearray, bytes)) else pdf_output.encode('latin-1')
                
        except Exception as e:
            st.error(f"PDF creation error: {str(e)}")
            return None
    
    # Video Function (simplified)
    def create_comic_video(panels):
        try:
            import imageio
            import numpy as np
            from PIL import Image, ImageDraw, ImageFont
            
            frames = []
            
            for panel in panels:
                # Create canvas
                canvas = Image.new('RGB', (1280, 720), color=(26, 26, 26))
                draw = ImageDraw.Draw(canvas)
                
                # Try to load font
                try:
                    font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
                    font_text = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
                except:
                    font_title = ImageFont.load_default()
                    font_text = ImageFont.load_default()
                
                # Panel number
                draw.text((50, 30), f"Panel {panel['panel_num']}", fill=(212, 175, 55), font=font_title)
                
                # Try to add image
                if panel.get('image_url'):
                    try:
                        response = requests.get(panel['image_url'], timeout=30)
                        if response.status_code == 200:
                            img = Image.open(io.BytesIO(response.content))
                            if img.mode != 'RGB':
                                img = img.convert('RGB')
                            # Resize to fit
                            img.thumbnail((800, 500), Image.Resampling.LANCZOS)
                            # Paste centered
                            x = (1280 - img.width) // 2
                            y = 80
                            canvas.paste(img, (x, y))
                    except:
                        pass
                
                # Add text at bottom
                text = panel['text']
                y_pos = 620
                # Word wrap
                words = text.split()
                line = ""
                for word in words:
                    test = line + word + " "
                    bbox = draw.textbbox((0, 0), test, font=font_text)
                    if bbox[2] > 1180:
                        draw.text((50, y_pos), line, fill=(240, 240, 240), font=font_text)
                        y_pos += 30
                        line = word + " "
                    else:
                        line = test
                if line:
                    draw.text((50, y_pos), line, fill=(240, 240, 240), font=font_text)
                
                # Add frame multiple times for duration (3 seconds at 30fps = 90 frames)
                for _ in range(90):
                    frames.append(np.array(canvas))
            
            # Save video
            if frames:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
                    writer = imageio.get_writer(tmp.name, fps=30, quality=8, codec='libx264')
                    for frame in frames:
                        writer.append_data(frame)
                    writer.close()
                    
                    with open(tmp.name, 'rb') as f:
                        video_bytes = f.read()
                    os.unlink(tmp.name)
                    return video_bytes
            return None
        except Exception as e:
            st.error(f"Video error: {str(e)}")
            return None
    
    dl_col1, dl_col2 = st.columns(2)
    
    with dl_col1:
        st.markdown("#### 📕 PDF Comic Book")
        st.caption("Professional printable PDF")
        
        if st.button("📥 Create PDF", key="pdf_btn", use_container_width=True):
            with st.spinner("Creating PDF... This may take a minute"):
                pdf_data = create_comic_pdf(panels, comic_style, color_scheme)
                if pdf_data:
                    st.download_button(
                        "⬇️ Download PDF",
                        pdf_data,
                        file_name=f"Aadil_Comic_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
    
    with dl_col2:
        st.markdown("#### 🎬 Video Comic")
        st.caption("MP4 slideshow for sharing")
        
        if st.button("📥 Create Video", key="video_btn", use_container_width=True):
            with st.spinner("Creating video... This may take 2-3 minutes"):
                video_data = create_comic_video(panels)
                if video_data:
                    st.download_button(
                        "⬇️ Download MP4",
                        video_data,
                        file_name=f"Aadil_Comic_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4",
                        mime="video/mp4",
                        use_container_width=True
                    )
                else:
                    st.error("Video creation failed. Try PDF instead.")
    
    st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown("""
<div class="footer">
    <p style="font-size: 0.9rem; color: #888;"><strong style="color: #d4af37;">Aadil's AI Comic Generator</strong> © 2024</p>
    <p style="font-size: 0.8rem; color: #666;">Create unlimited comics • Download as PDF or Video</p>
</div>
""", unsafe_allow_html=True)
