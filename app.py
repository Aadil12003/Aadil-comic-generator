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

# Custom CSS - Professional Dark Theme
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

/* Download Section - Gold Border */
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

.download-btn-pdf {
    background: linear-gradient(135deg, #ff4444 0%, #cc0000 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    font-weight: 700 !important;
    padding: 1rem 2rem !important;
    font-size: 1.1rem !important;
}

.download-btn-video {
    background: linear-gradient(135deg, #4444ff 0%, #0000cc 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    font-weight: 700 !important;
    padding: 1rem 2rem !important;
    font-size: 1.1rem !important;
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

# Generation Logic
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
            
            # Parse panels
            raw_panels = re.split(r'\n\s*(?:Panel|PANEL)?\s*\d+[\.:\)]?\s*', story_input)
            raw_panels = [p.strip() for p in raw_panels if p.strip()]
            
            if len(raw_panels) < 2:
                raw_panels = [p.strip() for p in story_input.split('\n\n') if p.strip()]
            
            raw_panels = raw_panels[:panel_count]
            
            # Fill if needed
            while len(raw_panels) < panel_count:
                if raw_panels:
                    longest = max(raw_panels, key=len)
                    idx = raw_panels.index(longest)
                    mid = len(longest) // 2
                    raw_panels[idx:idx+1] = [longest[:mid], longest[mid:]]
                else:
                    raw_panels.append(f"Scene {len(raw_panels) + 1}")
            
            generated_panels = []
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for idx, panel_text in enumerate(raw_panels[:panel_count]):
                status_text.markdown(f'<div class="progress-text">Panel {idx + 1}/{panel_count}: {panel_text[:40]}...</div>', unsafe_allow_html=True)
                
                style_prompts = {
                    "Modern Comic (Marvel/DC)": "modern American comic style, bold dynamic lines, professional coloring, cinematic",
                    "Manga/Anime": "manga style, detailed inking, expressive features, dynamic composition",
                    "Noir/Detective": "film noir style, high contrast shadows, gritty atmospheric, dramatic lighting",
                    "Fantasy/Illustrated": "detailed fantasy illustration, rich cinematic colors, epic scale, painterly",
                    "Minimalist/Indie": "indie comic style, clean artistic lines, thoughtful composition, muted palette",
                    "Vintage/Classic": "1950s comic style, vintage coloring, classic retro aesthetic, nostalgic"
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
                
                if char_base64:
                    full_prompt = f"""Comic panel {idx+1}. {style_desc}, {color_desc}. {char_prompt}SCENE: {panel_text}. Professional comic art, no text in image, detailed quality."""
                else:
                    full_prompt = f"""Comic panel {idx+1}. {style_desc}, {color_desc}. SCENE: {panel_text}. Professional comic art, no text in image, detailed quality, consistent characters throughout story."""
                
                try:
                    response = client.images.generate(
                        model="black-forest-labs/flux-dev",
                        prompt=full_prompt,
                        n=1,
                        size="1024x1024",
                        quality="standard"
                    )
                    
                    if response.data:
                        generated_panels.append({
                            'text': panel_text,
                            'image_url': response.data[0].url if hasattr(response.data[0], 'url') else None,
                            'panel_num': idx + 1
                        })
                except Exception as e:
                    generated_panels.append({
                        'text': panel_text,
                        'image_url': None,
                        'panel_num': idx + 1,
                        'error': str(e)
                    })
                
                progress_bar.progress((idx + 1) / panel_count)
            
            st.session_state.comic_panels = generated_panels
            st.session_state.generated = True
            status_text.empty()
            progress_bar.empty()
            
            st.success(f"✓ Generated {len(generated_panels)} panels!")
            
        except Exception as e:
            st.error(f"Error: {str(e)}")

# Display Comic
if st.session_state.generated and st.session_state.comic_panels:
    st.markdown("<hr>", unsafe_allow_html=True)
    st.subheader("🎭 Your Generated Comic")
    
    panels = st.session_state.comic_panels
    
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
                        st.error("⚠ Failed")
                    
                    display_text = panel["text"][:180] + "..." if len(panel["text"]) > 180 else panel["text"]
                    st.markdown(f'<div class="dialogue-bubble">{display_text}</div>', unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)

    # FUNCTIONAL DOWNLOAD SECTION - PDF & VIDEO ONLY
    st.markdown('<div class="download-section">', unsafe_allow_html=True)
    st.markdown('<div class="download-title">💾 Download Your Comic</div>', unsafe_allow_html=True)
    
    # Create PDF function
    def create_comic_pdf(panels, style, color_scheme):
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        
        # Title page
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 24)
        pdf.set_text_color(212, 175, 55)  # Gold
        pdf.cell(0, 20, "Aadil's AI Comic Generator", ln=True, align="C")
        pdf.ln(10)
        
        pdf.set_font("Helvetica", "", 12)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 10, f"Style: {style}", ln=True, align="C")
        pdf.cell(0, 10, f"Color Scheme: {color_scheme}", ln=True, align="C")
        pdf.cell(0, 10, f"Total Panels: {len(panels)}", ln=True, align="C")
        pdf.cell(0, 10, f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align="C")
        pdf.ln(20)
        
        # Download images and add to PDF
        successful_panels = []
        
        for panel in panels:
            if panel.get('image_url'):
                try:
                    response = requests.get(panel['image_url'], timeout=30)
                    if response.status_code == 200:
                        img = Image.open(io.BytesIO(response.content))
                        
                        # Convert to RGB if necessary
                        if img.mode != 'RGB':
                            img = img.convert('RGB')
                        
                        # Save temp image
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp:
                            img.save(tmp.name, 'JPEG', quality=95)
                            tmp_path = tmp.name
                        
                        # Add to PDF
                        pdf.add_page()
                        pdf.set_font("Helvetica", "B", 16)
                        pdf.set_text_color(212, 175, 55)
                        pdf.cell(0, 10, f"Panel {panel['panel_num']}", ln=True)
                        pdf.ln(5)
                        
                        # Add image (fit to page width)
                        pdf.image(tmp_path, x=10, y=25, w=190)
                        
                        # Add description below
                        pdf.ln(105)
                        pdf.set_font("Helvetica", "", 11)
                        pdf.set_text_color(50, 50, 50)
                        
                        # Clean text for PDF
                        clean_text = panel['text'].encode('latin-1', 'replace').decode('latin-1')
                        pdf.multi_cell(0, 8, clean_text)
                        
                        # Cleanup temp file
                        os.unlink(tmp_path)
                        successful_panels.append(panel['panel_num'])
                        
                except Exception as e:
                    # Add text-only page if image fails
                    pdf.add_page()
                    pdf.set_font("Helvetica", "B", 16)
                    pdf.set_text_color(212, 175, 55)
                    pdf.cell(0, 10, f"Panel {panel['panel_num']}", ln=True)
                    pdf.ln(10)
                    pdf.set_font("Helvetica", "", 11)
                    pdf.set_text_color(100, 100, 100)
                    clean_text = panel['text'].encode('latin-1', 'replace').decode('latin-1')
                    pdf.multi_cell(0, 8, clean_text)
                    pdf.ln(10)
                    pdf.set_text_color(255, 0, 0)
                    pdf.cell(0, 10, "[Image generation failed for this panel]", ln=True)
        
        # Save PDF to bytes
        pdf_bytes = pdf.output(dest='S').encode('latin-1')
        return pdf_bytes
    
    # Create video function (MP4 slideshow)
    def create_comic_video(panels):
        try:
            import cv2
            import numpy as np
            
            frames = []
            fps = 0.5  # 2 seconds per panel
            
            for panel in panels:
                # Create canvas
                canvas = np.zeros((720, 1280, 3), dtype=np.uint8)
                canvas[:] = (26, 26, 26)  # Dark background #1a1a1a
                
                # Add panel number
                cv2.putText(canvas, f"Panel {panel['panel_num']}", (50, 50), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1.5, (212, 175, 55), 3)
                
                # Try to load image
                if panel.get('image_url'):
                    try:
                        response = requests.get(panel['image_url'], timeout=30)
                        if response.status_code == 200:
                            img_array = np.frombuffer(response.content, np.uint8)
                            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                            
                            if img is not None:
                                # Resize to fit canvas
                                target_height = 500
                                scale = target_height / img.shape[0]
                                new_width = int(img.shape[1] * scale)
                                img = cv2.resize(img, (new_width, target_height))
                                
                                # Center image
                                x_offset = (1280 - new_width) // 2
                                y_offset = 80
                                canvas[y_offset:y_offset+target_height, x_offset:x_offset+new_width] = img
                    except:
                        pass
                
                # Add text at bottom
                text = panel['text'][:100] + "..." if len(panel['text']) > 100 else panel['text']
                y_pos = 620
                words = text.split()
                line = ""
                for word in words:
                    test_line = line + word + " "
                    if len(test_line) * 15 > 1100:
                        cv2.putText(canvas, line, (50, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (240, 240, 240), 2)
                        y_pos += 35
                        line = word + " "
                    else:
                        line = test_line
                if line:
                    cv2.putText(canvas, line, (50, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (240, 240, 240), 2)
                
                # Hold frame for 3 seconds (90 frames at 30fps)
                for _ in range(90):
                    frames.append(canvas.copy())
            
            # Write video
            if frames:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
                    out = cv2.VideoWriter(tmp.name, cv2.VideoWriter_fourcc(*'mp4v'), 30, (1280, 720))
                    for frame in frames:
                        out.write(frame)
                    out.release()
                    
                    # Read bytes
                    with open(tmp.name, 'rb') as f:
                        video_bytes = f.read()
                    os.unlink(tmp.name)
                    return video_bytes
            return None
        except Exception as e:
            st.error(f"Video creation failed: {str(e)}")
            return None
    
    # Simple video alternative (animated GIF-style MP4 using PIL)
    def create_simple_video(panels):
        try:
            frames = []
            duration = 3000  # 3 seconds per panel in ms
            
            for panel in panels:
                # Create image canvas
                canvas = Image.new('RGB', (1280, 720), color=(26, 26, 26))
                
                # Try to get panel image
                panel_img = None
                if panel.get('image_url'):
                    try:
                        response = requests.get(panel['image_url'], timeout=30)
                        if response.status_code == 200:
                            panel_img = Image.open(io.BytesIO(response.content))
                            if panel_img.mode != 'RGB':
                                panel_img = panel_img.convert('RGB')
                            # Resize
                            panel_img.thumbnail((800, 500), Image.Resampling.LANCZOS)
                    except:
                        pass
                
                # Paste image
                if panel_img:
                    x = (1280 - panel_img.width) // 2
                    y = 100
                    canvas.paste(panel_img, (x, y))
                
                # Add text
                from PIL import ImageDraw, ImageFont
                draw = ImageDraw.Draw(canvas)
                
                # Panel number
                try:
                    font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
                    font_text = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
                except:
                    font_title = ImageFont.load_default()
                    font_text = ImageFont.load_default()
                
                draw.text((50, 30), f"Panel {panel['panel_num']}", fill=(212, 175, 55), font=font_title)
                
                # Description
                text = panel['text'][:120] + "..." if len(panel['text']) > 120 else panel['text']
                y_text = 620
                draw.text((50, y_text), text, fill=(240, 240, 240), font=font_text)
                
                # Save frame multiple times for duration
                for _ in range(90):  # 3 seconds at 30fps
                    frames.append(canvas)
            
            # Save as MP4 using imageio
            import imageio
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
                writer = imageio.get_writer(tmp.name, fps=30, quality=8)
                for frame in frames:
                    writer.append_data(np.array(frame))
                writer.close()
                
                with open(tmp.name, 'rb') as f:
                    video_bytes = f.read()
                os.unlink(tmp.name)
                return video_bytes
                
        except Exception as e:
            return None
    
    dl_col1, dl_col2 = st.columns(2)
    
    with dl_col1:
        st.markdown("#### 📕 PDF Comic Book")
        st.caption("Download as printable PDF with all panels and story")
        
        if st.button("📥 Download PDF", key="pdf_btn", use_container_width=True):
            with st.spinner("Creating PDF..."):
                try:
                    pdf_data = create_comic_pdf(panels, comic_style, color_scheme)
                    if pdf_data:
                        st.download_button(
                            "⬇️ Click to Save PDF",
                            pdf_data,
                            file_name=f"Aadil_Comic_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                except Exception as e:
                    st.error(f"PDF creation failed: {str(e)}")
    
    with dl_col2:
        st.markdown("#### 🎬 Video Comic")
        st.caption("Download as MP4 video slideshow of your comic")
        
        if st.button("📥 Download Video", key="video_btn", use_container_width=True):
            with st.spinner("Creating video (this may take a minute)..."):
                try:
                    # Try simple video first
                    video_data = create_simple_video(panels)
                    if video_data:
                        st.download_button(
                            "⬇️ Click to Save MP4",
                            video_data,
                            file_name=f"Aadil_Comic_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4",
                            mime="video/mp4",
                            use_container_width=True
                        )
                    else:
                        st.error("Video creation failed. Try PDF instead.")
                except Exception as e:
                    st.error(f"Video error: {str(e)}")
    
    st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown("""
<div class="footer">
    <p style="font-size: 0.9rem; color: #888;"><strong style="color: #d4af37;">Aadil's AI Comic Generator</strong> © 2024</p>
    <p style="font-size: 0.8rem; color: #666;">Create unlimited comics • Download as PDF or Video</p>
</div>
""", unsafe_allow_html=True)
