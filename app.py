import streamlit as st
from openai import OpenAI
import re
from fpdf import FPDF
from io import BytesIO

# ================= CONFIG =================
st.set_page_config(page_title="AI Comic Generator", layout="wide")

# ================= API =================
def get_client():
    try:
        api_key = st.secrets["NVIDIA_API_KEY"]
    except:
        api_key = st.text_input("Enter NVIDIA API Key", type="password")

    if not api_key:
        st.warning("API key required")
        st.stop()

    return OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=api_key
    )

# ================= STORY PARSER =================
def parse_story(text, max_panels=10):
    panels = re.split(r'(?:Panel\s*\d+:)', text, flags=re.IGNORECASE)
    panels = [p.strip() for p in panels if p.strip()]
    return panels[:max_panels]

# ================= AI GENERATION =================
def generate_panels(client, story, panel_count):
    try:
        response = client.chat.completions.create(
            model="meta/llama-3.3-70b-instruct",
            messages=[
                {
                    "role": "system",
                    "content": "You are a comic generator. Convert story into panels with dialogue."
                },
                {
                    "role": "user",
                    "content": f"Create {panel_count} comic panels from this:\n{story}"
                }
            ],
            temperature=0.7,
            max_tokens=2000
        )

        return response.choices[0].message.content

    except Exception as e:
        st.error(f"AI Error: {str(e)}")
        return None

# ================= PDF =================
def create_pdf(panels):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=10)

    for i, panel in enumerate(panels, 1):
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.multi_cell(0, 10, f"Panel {i}\n\n{panel}")

    buffer = BytesIO()
    pdf.output(buffer)
    buffer.seek(0)
    return buffer

# ================= UI =================

st.title("🎭 AI Comic Generator")

story = st.text_area(
    "Enter your story",
    height=250,
    placeholder="Panel 1: A boy walks into a dark alley..."
)

panel_count = st.slider("Number of Panels", 1, 20, 5)

if st.button("Generate Comic"):
    if len(story.strip()) < 20:
        st.warning("Story too short")
        st.stop()

    client = get_client()

    with st.spinner("Generating comic..."):
        result = generate_panels(client, story, panel_count)

    if result:
        panels = parse_story(result, panel_count)

        st.success("Comic Generated")

        for i, p in enumerate(panels, 1):
            st.markdown(f"### Panel {i}")
            st.write(p)

        pdf = create_pdf(panels)

        st.download_button(
            label="Download PDF",
            data=pdf,
            file_name="comic.pdf",
            mime="application/pdf"
        )
