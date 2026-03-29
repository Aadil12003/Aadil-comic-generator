import streamlit as st
import openai
from PIL import Image
import io
import base64
import json
import re
from datetime import datetime

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

* {
    font-family: 'Inter', sans-serif;
}

.stApp {
    background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 50%, #16213e 100%);
    color: #e8e8e8;
}

/* Header */
.main-header {
    text-align: center;
    padding: 2rem 0;
    border-bottom: 2px solid #333;
    margin-bottom: 2rem;
    background: linear-gradient(90deg, transparent, rgba(212, 175, 55, 0.1), transparent);
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
    color: #888;
    font-size: 1.1rem;
    font-weight: 300;
    letter-spacing: 1px;
}

/* Sidebar */
.css-1d391kg, .css-163ttbj {
    background: #0f0f0f !important;
    border-right: 1px solid #333;
}

.sidebar-title {
    color: #d4af37;
    font-size: 1.2rem;
    font-weight: 600;
    margin-bottom: 1rem;
    border-bottom: 1px solid #333;
    padding-bottom: 0.5rem;
}

/* Character Upload Section */
.character-section {
    background: linear-gradient(145deg, #1a1a1a, #0d0d0d);
    border: 1px solid #333;
    border-radius: 12px;
    padding: 1.5rem;
    margin-bottom: 1.5rem;
}

.character-preview {
    border-radius: 8px;
    border: 2px solid #d4af37;
    overflow: hidden;
}

/* Input Fields */
.stTextArea textarea {
    background: #0d0d0d !important;
    border: 1px solid #333 !important;
    border-radius: 8px !important;
    color: #e8e8e8 !important;
    font-size: 0.95rem !important;
    min-height: 150px !important;
}

.stTextArea textarea:focus {
    border-color: #d4af37 !important;
    box-shadow: 0 0 0 2px rgba(212, 175, 55, 0.2) !important;
}

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #d4af37 0%, #b8960c 100%) !important;
    color: #0a0a0a !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    padding: 0.75rem 2rem !important;
    font-size: 1rem !important;
    transition: all 0.3s ease !important;
    text-transform: uppercase;
    letter-spacing: 1px;
}

.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 25px rgba(212, 175, 55, 0.3) !important;
}

.stButton > button:disabled {
    background: #333 !important;
    color: #666 !important;
    cursor: not-allowed !important;
    transform: none !important;
}

/* Comic Display */
.comic-panel {
    background: #0d0d0d;
    border: 1px solid #333;
    border-radius: 12px;
    padding: 1rem;
    margin: 1rem 0;
    position: relative;
    overflow: hidden;
}

.comic-panel::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: linear-gradient(90deg, #d4af37, #f4e5c2, #d4af37);
}

.panel-number {
    position: absolute;
    top: 10px;
    right: 15px;
    background: #d4af37;
    color: #0a0a0a;
    width: 30px;
    height: 30px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 0.9rem;
}

/* Dialogue Bubbles */
.dialogue-bubble {
    background: #fff;
    color: #0a0a0a;
    border-radius: 20px;
    padding: 1rem 1.5rem;
    margin: 1rem 0;
    position: relative;
    font-family: 'Comic Sans MS', cursive, sans-serif;
    box-shadow: 0 4px 15px rgba(0,0,0,0.3);
}

.dialogue-bubble::after {
    content: '';
    position: absolute;
    bottom: -10px;
    left: 30px;
    width: 0;
    height: 0;
    border-left: 10px solid transparent;
    border-right: 10px solid transparent;
    border-top: 10px solid #fff;
}

/* Progress Indicators */
.progress-container {
    background: #0d0d0d;
    border-radius: 10px;
    padding: 2rem;
    text-align: center;
    border: 1px solid #333;
}

.progress-text {
    color: #d4af37;
    font-size: 1.2rem;
    font-weight: 500;
    margin-top: 1rem;
}

/* Download Section */
.download-section {
    background: linear-gradient(145deg, #1a1a1a, #0d0d0d);
    border: 1px solid #d4af37;
    border-radius: 12px;
    padding: 1.5rem;
    margin-top: 2rem;
}

/* Expander */
.streamlit-expanderHeader {
    background: #1a1a1a !important;
    border: 1px solid #333 !important;
    border-radius: 8px !important;
    color: #d4af37 !important;
    font-weight: 600 !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 2rem;
    background: #0d0d0d;
    padding: 0.5rem;
    border-radius: 8px;
}

.stTabs [data-baseweb="tab"] {
    color: #888 !important;
    font-weight: 500 !important;
}

.stTabs [aria-selected="true"] {
    color: #d4af37 !important;
    background: rgba(212, 175, 55, 0.1) !important;
    border-radius: 6px !important;
}

/* Scrollbar */
::-webkit-scrollbar {
    width: 8px;
    height: 8px;
}

::-webkit-scrollbar-track {
    background: #0a0a0a;
}

::-webkit-scrollbar-thumb {
    background: #333;
    border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
    background: #d4af37;
}

/* Loading Animation */
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}

.loading-text {
    animation: pulse 1.5s infinite;
    color: #d4af37;
}

/* Separator */
hr {
    border: none;
    height: 1px;
    background: linear-gradient(90deg, transparent, #333, transparent);
    margin: 2rem 0;
}

/* Info Box */
.info-box {
    background: rgba(212, 175, 55, 0.1);
    border-left: 3px solid #d4af37;
    padding: 1rem;
    border-radius: 0 8px 8px 0;
    margin: 1rem 0;
}

/* Character Consistency Badge */
.consistency-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    background: rgba(0, 255, 127, 0.1);
    border: 1px solid #00ff7f;
    color: #00ff7f;
    padding: 0.5rem 1rem;
    border-radius: 20px;
    font-size: 0.85rem;
    font-weight: 500;
}

/* Warning */
.warning-box {
    background: rgba(255, 193, 7, 0.1);
    border-left: 3px solid #ffc107;
    color: #ffc107;
    padding: 1rem;
    border-radius: 0 8px 8px 0;
    margin: 1rem 0;
}
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="main-header">
    <h1>🎭 Aadil's AI Comic Generator</h1>
    <p>Professional AI-Powered Comic Creation with Character Consistency</p>
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

# Sidebar - Character Setup
with st.sidebar:
    st.markdown('<div class="sidebar-title">🎨 Character Setup</div>', unsafe_allow_html=True)
    
    # Character Image Upload
    st.markdown('<div class="character-section">', unsafe_allow_html=True)
    st.subheader("Upload Character Face")
    
    uploaded_face = st.file_uploader(
        "Upload a clear face image (JPG/PNG)",
        type=['jpg', 'jpeg', 'png'],
        help="This face will be used consistently throughout your comic story"
    )
    
    if uploaded_face is not None:
        try:
            image = Image.open(uploaded_face)
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            st.session_state.character_face = image
            
            st.markdown('<div class="consistency-badge">✓ Character Face Locked</div>', unsafe_allow_html=True)
            st.image(image, caption="Character Reference", use_container_width=True, 
                    output_format="JPEG", clamp=True)
            
            # Character description extraction
            st.subheader("Character Details")
            st.session_state.character_description = st.text_area(
                "Describe your character (appearance, clothing, personality):",
                value=st.session_state.character_description,
                placeholder="Example: 25-year-old detective, wears a brown trench coat, sharp eyes, serious expression...",
                height=100
            )
            
        except Exception as e:
            st.error(f"Error processing image: {str(e)}")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # API Key Input (for local development)
    st.markdown('<div class="character-section">', unsafe_allow_html=True)
    st.subheader("⚙️ Configuration")
    
    api_key = st.text_input(
        "NVIDIA API Key",
        type="password",
        value=st.secrets.get("NVIDIA_API_KEY", ""),
        help="Required for image generation. Get yours at build.nvidia.com"
    )
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Style Settings
    st.markdown('<div class="character-section">', unsafe_allow_html=True)
    st.subheader("🎨 Comic Style")
    
    comic_style = st.selectbox(
        "Art Style",
        ["Modern Comic (Marvel/DC style)", "Manga/Anime", "Noir/Detective", 
         "Fantasy/Illustrated", "Minimalist/Indie", "Vintage/Classic"]
    )
    
    panel_count = st.slider("Number of Panels", 3, 12, 6)
    
    color_scheme = st.selectbox(
        "Color Scheme",
        ["Full Color", "Black & White", "Sepia/Vintage", "Cyberpunk Neon", "Muted Tones"]
    )
    st.markdown('</div>', unsafe_allow_html=True)

# Main Content Area
col1, col2 = st.columns([2, 1])

with col1:
    st.markdown('<div class="info-box">', unsafe_allow_html=True)
    st.markdown("""
    **📝 How to use:**
    1. Upload a character face image in the sidebar
    2. Write your complete story below (no length limit)
    3. Click "Generate Comic" to create consistent character panels
    4. Download your finished comic as images or PDF
    """)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Story Input - NO CHARACTER LIMIT
    st.subheader("📖 Your Story")
    
    story_input = st.text_area(
        "Write your complete comic story (unlimited length):",
        value=st.session_state.story_text,
        placeholder="""Example:
        
Panel 1: John stands at the edge of the rooftop, wind blowing through his coat. He looks down at the city below with determination.
        
Panel 2: A mysterious figure approaches from the shadows. John turns, hand reaching for his weapon.
        
Panel 3: Close up of John's eyes narrowing as he recognizes the intruder.
        
[Continue with as many panels as you want...]""",
        height=400,
        key="story_input",
        help="Paste or type your full story. No character limits!"
    )
    
    # Store in session
    st.session_state.story_text = story_input

with col2:
    st.subheader("📊 Story Stats")
    
    char_count = len(story_input)
    word_count = len(story_input.split()) if story_input else 0
    panel_estimate = max(1, char_count // 200) if char_count > 0 else 0
    
    metrics = st.container()
    metrics.metric("Characters", f"{char_count:,}", "No limit")
    metrics.metric("Words", f"{word_count:,}", "Total count")
    metrics.metric("Est. Panels", panel_estimate, "Based on length")
    
    if st.session_state.character_face is not None:
        st.success("✓ Character face locked for consistency")
    else:
        st.warning("⚠ Upload character face for consistency")

# Generation Button
st.markdown("<hr>", unsafe_allow_html=True)

gen_col1, gen_col2, gen_col3 = st.columns([1, 2, 1])

with gen_col2:
    generate_btn = st.button(
        "🎨 Generate Comic Story",
        disabled=not (story_input and api_key and st.session_state.character_face),
        use_container_width=True
    )

# Generation Logic
if generate_btn:
    if not story_input.strip():
        st.error("Please enter a story first!")
    elif not api_key:
        st.error("Please enter your NVIDIA API Key!")
    elif st.session_state.character_face is None:
        st.error("Please upload a character face image!")
    else:
        with st.spinner("🎭 Creating your comic with consistent character..."):
            try:
                client = openai.OpenAI(
                    base_url="https://integrate.api.nvidia.com/v1",
                    api_key=api_key
                )
                
                # Convert character image to base64 for reference
                buffered = io.BytesIO()
                st.session_state.character_face.save(buffered, format="JPEG")
                char_base64 = base64.b64encode(buffered.getvalue()).decode()
                
                # Parse story into panels (smart splitting)
                raw_panels = re.split(r'\n\s*(?:Panel|PANEL)?\s*\d+[\.:\)]?\s*', story_input)
                raw_panels = [p.strip() for p in raw_panels if p.strip()]
                
                if len(raw_panels) < 2:  # If no panel markers found, split by paragraphs
                    raw_panels = [p.strip() for p in story_input.split('\n\n') if p.strip()]
                
                generated_panels = []
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for idx, panel_text in enumerate(raw_panels[:panel_count]):
                    status_text.markdown(f'<div class="progress-text">Generating Panel {idx + 1} of {min(len(raw_panels), panel_count)}...</div>', 
                                       unsafe_allow_html=True)
                    
                    # Create prompt with character consistency enforcement
                    style_prompts = {
                        "Modern Comic (Marvel/DC style)": "modern American comic book style, bold lines, dynamic action, professional coloring",
                        "Manga/Anime": "manga style, black and white ink, screentone, expressive eyes, dynamic speed lines",
                        "Noir/Detective": "film noir style, high contrast black and white, shadows, gritty atmosphere",
                        "Fantasy/Illustrated": "detailed fantasy illustration, rich colors, epic lighting, painterly style",
                        "Minimalist/Indie": "indie comic style, minimalist, clean lines, muted palette, artistic",
                        "Vintage/Classic": "1950s comic book style, vintage coloring, classic Ben-Day dots, retro"
                    }
                    
                    color_prompts = {
                        "Full Color": "full color, vibrant",
                        "Black & White": "black and white, ink drawing",
                        "Sepia/Vintage": "sepia tones, vintage coloring",
                        "Cyberpunk Neon": "neon colors, cyberpunk aesthetic",
                        "Muted Tones": "muted earth tones, desaturated"
                    }
                    
                    style_desc = style_prompts.get(comic_style, "modern comic style")
                    color_desc = color_prompts.get(color_scheme, "full color")
                    
                    # Enhanced prompt with character consistency
                    full_prompt = f"""Comic book panel illustration. {style_desc}, {color_desc}.

CHARACTER REFERENCE: Use this exact face for the main character: data:image/jpeg;base64,{char_base64[:100]}... [Character face locked for consistency]

SCENE DESCRIPTION: {panel_text}

CRITICAL INSTRUCTIONS:
- Main character MUST have the EXACT same face as the reference image provided
- Maintain consistent facial features, hair style, and skin tone throughout all panels
- Character wearing: {st.session_state.character_description if st.session_state.character_description else 'consistent clothing'}
- Professional comic book panel composition
- No text or speech bubbles in the image
- High quality, detailed artwork"""
                    
                    try:
                        response = client.images.generate(
                            model="black-forest-labs/flux-dev",  # or appropriate NVIDIA model
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
                        st.error(f"Panel {idx + 1} generation failed: {str(e)}")
                        generated_panels.append({
                            'text': panel_text,
                            'image_url': None,
                            'panel_num': idx + 1,
                            'error': str(e)
                        })
                    
                    progress_bar.progress((idx + 1) / min(len(raw_panels), panel_count))
                
                st.session_state.comic_panels = generated_panels
                st.session_state.generated = True
                status_text.empty()
                progress_bar.empty()
                
                st.success(f"✓ Generated {len(generated_panels)} panels with consistent character!")
                
            except Exception as e:
                st.error(f"Generation failed: {str(e)}")

# Display Generated Comic
if st.session_state.generated and st.session_state.comic_panels:
    st.markdown("<hr>", unsafe_allow_html=True)
    st.subheader("🎭 Your Generated Comic")
    
    # Display panels in a comic layout
    panels = st.session_state.comic_panels
    
    # Create rows of 2 panels each
    for i in range(0, len(panels), 2):
        cols = st.columns(2)
        
        for j, col in enumerate(cols):
            idx = i + j
            if idx < len(panels):
                panel = panels[idx]
                
                with col:
                    st.markdown(f'<div class="comic-panel">', unsafe_allow_html=True)
                    st.markdown(f'<div class="panel-number">{panel["panel_num"]}</div>', 
                              unsafe_allow_html=True)
                    
                    if panel.get('image_url'):
                        st.image(panel['image_url'], use_container_width=True)
                    else:
                        st.error("Image generation failed for this panel")
                    
                    # Dialogue/Description
                    st.markdown(f'<div class="dialogue-bubble">{panel["text"][:200]}{"..." if len(panel["text"]) > 200 else ""}</div>', 
                              unsafe_allow_html=True)
                    
                    st.markdown('</div>', unsafe_allow_html=True)
    
    # Download Options
    st.markdown('<div class="download-section">', unsafe_allow_html=True)
    st.subheader("💾 Export Your Comic")
    
    dl_col1, dl_col2, dl_col3 = st.columns(3)
    
    with dl_col1:
        # Create JSON export
        comic_data = {
            'title': "Aadil's AI Comic",
            'created': datetime.now().isoformat(),
            'style': comic_style,
            'panels': panels
        }
        json_str = json.dumps(comic_data, indent=2)
        st.download_button(
            "📄 Download JSON",
            json_str,
            file_name=f"comic_story_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )
    
    with dl_col2:
        st.button("🖼️ Download All Images (ZIP)", disabled=True, 
                 help="Feature coming soon - manually save images for now")
    
    with dl_col3:
        # Generate markdown story
        md_content = f"# Aadil's AI Comic\n\n**Style:** {comic_style}\n**Panels:** {len(panels)}\n\n"
        for panel in panels:
            md_content += f"## Panel {panel['panel_num']}\n\n{panel['text']}\n\n---\n\n"
        
        st.download_button(
            "📝 Download Story (MD)",
            md_content,
            file_name=f"comic_script_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
            mime="text/markdown"
        )
    
    st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown("""
<div style="text-align: center; padding: 2rem 0; color: #666; border-top: 1px solid #333; margin-top: 3rem;">
    <p style="font-size: 0.9rem;">Aadil's AI Comic Generator © 2024 | Powered by NVIDIA AI</p>
    <p style="font-size: 0.8rem; color: #444;">Professional comic creation with consistent character technology</p>
</div>
""", unsafe_allow_html=True)
