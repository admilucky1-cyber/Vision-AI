"""
Vision AI v2.0 - Image & Diagram Generation
=============================================
Multi-engine diagram and chart generation.

Priority:
1. Google Image Search (Real images from the web)
2. Plotly (Clean charts)
3. Matplotlib (Physics graphs)
4. Hugging Face Multi-Model AI (FLUX, SD3.5, FLUX Schnell)
5. Graphviz (Structural diagrams)
6. ASCII Art (Text fallback)
"""

import os
import re
import base64
import io
import logging
import asyncio
import requests
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime

# ==========================================================
# LOGGING SETUP
# ==========================================================
logger = logging.getLogger("vision-ai.image_gen")

# ==========================================================
# OPTIONAL LIBRARY LOADING (Each engine degrades gracefully)
# ==========================================================

# Matplotlib
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    MATPLOTLIB_AVAILABLE = True
except ImportError as e:
    logger.warning(f"matplotlib unavailable, chart generation disabled: {e}")
    MATPLOTLIB_AVAILABLE = False

# Numpy
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    np = None
    logger.warning("numpy unavailable, some charts may be disabled")

# Pandas
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    pd = None
    logger.warning("pandas unavailable, Plotly charts will be disabled.")

# Plotly
try:
    import plotly.express as px
    import plotly.io as pio
    PLOTLY_AVAILABLE = True
except ImportError as e:
    PLOTLY_AVAILABLE = False
    logger.warning(f"plotly unavailable, plotly charts disabled: {e}")

# Graphviz
try:
    import graphviz
    GRAPHVIZ_AVAILABLE = True
except ImportError as e:
    logger.warning(f"graphviz unavailable, flowchart/org-chart diagrams disabled: {e}")
    GRAPHVIZ_AVAILABLE = False

# PIL (Pillow) - For image safety checks
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.warning("PIL unavailable, image validation disabled")

# ==========================================================
# CONFIGURATION
# ==========================================================
HF_TOKEN = os.getenv("HF_TOKEN")
MIN_IMAGE_SIZE = 8000  # Minimum valid image size in bytes
MAX_IMAGE_SIZE = 20 * 1024 * 1024  # 20MB max

# Google Custom Search API Config
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_ENGINE_ID = os.getenv("GOOGLE_ENGINE_ID")

# ==========================================================
# QUALITY STANDARDS
# ==========================================================
QUALITY_COLORS = {
    'navy': '#1a5276', 'red': '#e74c3c', 'green': '#27ae60',
    'blue': '#2980b9', 'orange': '#f39c12', 'purple': '#8e44ad',
    'dark': '#2c3e50', 'gray': '#95a5a6', 'light': '#ecf0f1',
}

# ==========================================================
# CONVERSION HELPERS
# ==========================================================

def fig_to_base64_formats(fig) -> Dict[str, Any]:
    """Return PNG (required) + optional SVG for export."""
    out = {"png": None, "svg": None}
    try:
        import io, base64
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight", facecolor=fig.get_facecolor())
        buf.seek(0)
        out["png"] = base64.b64encode(buf.read()).decode("utf-8")
        buf2 = io.BytesIO()
        fig.savefig(buf2, format="svg", bbox_inches="tight", facecolor=fig.get_facecolor())
        buf2.seek(0)
        out["svg"] = base64.b64encode(buf2.read()).decode("utf-8")
    except Exception as e:
        logger.warning(f"fig multi-format export: {e}")
        out["png"] = fig_to_base64(fig)
    finally:
        try:
            import matplotlib.pyplot as plt
            plt.close(fig)
        except Exception:
            pass
    return out


def fig_to_base64(fig) -> str:
    """Convert matplotlib figure to base64 PNG."""
    try:
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=200, facecolor='white', edgecolor='none', bbox_inches='tight')
        buf.seek(0)
        img = base64.b64encode(buf.read()).decode('utf-8')
        plt.close(fig)
        return img
    except Exception as e:
        logger.error(f"Matplotlib conversion failed: {e}")
        raise

def plotly_to_base64(fig) -> str:
    """Convert plotly figure to base64 PNG."""
    try:
        img_bytes = fig.to_image(format="png")
        return base64.b64encode(img_bytes).decode('utf-8')
    except Exception as e1:
        try:
            # Fallback to kaleido
            import plotly.io as pio
            pio.kaleido.scope.default_format = 'png'
            img_bytes = pio.kaleido.scope.transform(fig, format='png')
            return base64.b64encode(img_bytes).decode('utf-8')
        except Exception as e2:
            raise Exception(f"Plotly image conversion failed: {e1}, {e2}")

# ==========================================================
# 🚀 GOOGLE REAL IMAGE SEARCH
# ==========================================================
async def search_real_image(query: str) -> Dict[str, Any]:
    """Searches Google for a real, high-quality image."""
    if not GOOGLE_API_KEY or not GOOGLE_ENGINE_ID:
        logger.warning("Google API keys missing")
        return {"success": False, "error": "Google API keys missing"}

    try:
        headers = {"User-Agent": "VisionAI/2.0"}
        
        # Try with diagram search first
        search_terms = [
            f"{query} diagram",
            f"{query} chart",
            f"{query} illustration",
            f"{query} graph"
        ]
        
        for term in search_terms:
            url = f"https://www.googleapis.com/customsearch/v1?key={GOOGLE_API_KEY}&cx={GOOGLE_ENGINE_ID}&q={term}&searchType=image&num=1&imgSize=large&safe=active"

            res = await asyncio.to_thread(requests.get, url, headers=headers, timeout=10)
            data = res.json()

            if "items" in data and len(data["items"]) > 0:
                image_url = data["items"][0]["link"]

                # Validate image URL
                if not image_url.startswith(('http://', 'https://')):
                    continue

                img_res = await asyncio.to_thread(requests.get, image_url, headers=headers, timeout=10)
                if img_res.status_code == 200:
                    # Check image size
                    content = img_res.content
                    if len(content) < MIN_IMAGE_SIZE:
                        logger.warning(f"Image too small: {len(content)} bytes")
                        continue
                    if len(content) > MAX_IMAGE_SIZE:
                        logger.warning(f"Image too large: {len(content)} bytes")
                        continue
                        
                    img_b64 = base64.b64encode(content).decode('utf-8')
                    return {
                        "success": True, 
                        "image_data": img_b64, 
                        "provider": "Google Image Search",
                        "source_url": image_url
                    }
        
        return {"success": False, "error": "No suitable images found"}
    except requests.exceptions.Timeout:
        return {"success": False, "error": "Google search timed out"}
    except Exception as e:
        logger.error(f"Google search error: {e}")
        return {"success": False, "error": str(e)}

# ==========================================================
# PLOTLY RENDERERS (STATISTICAL CHARTS)
# ==========================================================
def draw_bar_chart(data: Optional[Dict] = None) -> Dict[str, Any]:
    """Generate bar chart."""
    if not (PLOTLY_AVAILABLE and PANDAS_AVAILABLE):
        return {"success": False, "error": "Plotly/pandas not installed"}
    try:
        if data is None:
            data = {'Category': ['A', 'B', 'C', 'D'], 'Values': [23, 45, 56, 78]}
        df = pd.DataFrame(data)
        fig = px.bar(df, x='Category', y='Values', title='Bar Chart', color='Category')
        fig.update_layout(
            template='plotly_white',
            showlegend=False,
            xaxis_title="Categories",
            yaxis_title="Values"
        )
        return {"success": True, "image_data": plotly_to_base64(fig), "provider": "Plotly"}
    except Exception as e:
        logger.error(f"Bar chart error: {e}")
        return {"success": False, "error": str(e)}

def draw_pie_chart(data: Optional[Dict] = None) -> Dict[str, Any]:
    """Generate pie chart."""
    if not (PLOTLY_AVAILABLE and PANDAS_AVAILABLE):
        return {"success": False, "error": "Plotly/pandas not installed"}
    try:
        if data is None:
            data = {'Category': ['X', 'Y', 'Z'], 'Values': [30, 50, 20]}
        df = pd.DataFrame(data)
        fig = px.pie(df, values='Values', names='Category', title='Pie Chart')
        fig.update_layout(template='plotly_white')
        return {"success": True, "image_data": plotly_to_base64(fig), "provider": "Plotly"}
    except Exception as e:
        logger.error(f"Pie chart error: {e}")
        return {"success": False, "error": str(e)}

def draw_line_chart(data: Optional[Dict] = None) -> Dict[str, Any]:
    """Generate line chart."""
    if not (PLOTLY_AVAILABLE and PANDAS_AVAILABLE):
        return {"success": False, "error": "Plotly/pandas not installed"}
    try:
        if data is None:
            data = {'Year': [2019, 2020, 2021, 2022, 2023], 'Sales': [150, 230, 180, 275, 340]}
        df = pd.DataFrame(data)
        fig = px.line(df, x='Year', y='Sales', title='Line Chart', markers=True)
        fig.update_layout(
            template='plotly_white',
            xaxis_title="Year",
            yaxis_title="Sales"
        )
        return {"success": True, "image_data": plotly_to_base64(fig), "provider": "Plotly"}
    except Exception as e:
        logger.error(f"Line chart error: {e}")
        return {"success": False, "error": str(e)}

# ==========================================================
# MATPLOTLIB RENDERERS (PHYSICS & MATH)
# ==========================================================

def draw_iv_graph(ohmic: bool = True) -> Dict[str, Any]:
    """Physics I–V characteristic: current vs voltage (matplotlib)."""
    if not MATPLOTLIB_AVAILABLE:
        return {"success": False, "error": "matplotlib not installed"}
    try:
        fig, ax = plt.subplots(figsize=(8, 5), dpi=160)
        fig.patch.set_facecolor("#0f172a")
        ax.set_facecolor("#111827")
        V = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        if ohmic:
            I = [v / 10.0 for v in V]  # 10 ohm resistor
            ax.plot(V, I, color="#22d3ee", linewidth=3, marker="o", markersize=5, label="Ohmic (R = 10 Ω)")
            title = "I–V Graph (Ohmic conductor)"
            note = "Straight line through origin → Ohm's law (I = V/R)"
        else:
            # Simple diode-like curve
            import math
            I = [0.02 * (math.exp(0.45 * v) - 1) for v in V]
            ax.plot(V, I, color="#f472b6", linewidth=3, marker="o", markersize=5, label="Non-ohmic (e.g. diode)")
            title = "I–V Graph (Non-ohmic device)"
            note = "Curved response → resistance not constant"
        ax.set_xlabel("Voltage V (volts)", color="#e2e8f0", fontsize=12)
        ax.set_ylabel("Current I (amperes)", color="#e2e8f0", fontsize=12)
        ax.set_title(title, color="#f8fafc", fontsize=14, fontweight="bold", pad=12)
        ax.tick_params(colors="#94a3b8")
        for spine in ax.spines.values():
            spine.set_color("#334155")
        ax.grid(True, alpha=0.25, color="#64748b")
        ax.legend(facecolor="#1e293b", edgecolor="#334155", labelcolor="#e2e8f0")
        ax.text(0.02, 0.98, note, transform=ax.transAxes, va="top", color="#94a3b8", fontsize=9)
        fig.tight_layout()
        fmts = fig_to_base64_formats(fig)
        return {
            "success": True,
            "image_data": fmts.get("png") or fig_to_base64(fig),
            "svg_data": fmts.get("svg"),
            "provider": "Matplotlib",
            "diagram_type": "iv_graph",
            "keyword": "I-V graph",
            "exports": ["png", "svg"] if fmts.get("svg") else ["png"],
        }
    except Exception as e:
        logger.error(f"I-V graph error: {e}")
        return {"success": False, "error": str(e)}


def draw_speed_time_graph() -> Dict[str, Any]:
    """Generate speed-time graph."""
    if not MATPLOTLIB_AVAILABLE:
        return {"success": False, "error": "matplotlib not installed"}
    try:
        fig, ax = plt.subplots(figsize=(10, 6))
        t, v = [0, 200, 500, 600], [0, 60, 60, 0]
        ax.plot(t, v, QUALITY_COLORS['navy'], linewidth=3)
        ax.fill_between(t, v, alpha=0.1, color='#3498db')
        ax.set_xlabel('Time (s)', fontsize=14, fontweight='bold')
        ax.set_ylabel('Speed (m/s)', fontsize=14, fontweight='bold')
        ax.set_title('Speed-Time Graph', fontsize=18, fontweight='bold', pad=15)
        ax.set_xlim(0, 650)
        ax.set_ylim(0, 75)
        ax.grid(True, alpha=0.3)
        return {"success": True, "image_data": fig_to_base64(fig), "provider": "Matplotlib"}
    except Exception as e:
        logger.error(f"Speed-time graph error: {e}")
        return {"success": False, "error": str(e)}

def draw_force_diagram() -> Dict[str, Any]:
    """Generate free body diagram."""
    if not MATPLOTLIB_AVAILABLE:
        return {"success": False, "error": "matplotlib not installed"}
    try:
        fig, ax = plt.subplots(figsize=(8, 8))
        ax.set_xlim(-3.5, 3.5)
        ax.set_ylim(-3.5, 3.5)
        ax.set_aspect('equal')
        ax.axis('off')

        box = patches.FancyBboxPatch((-1.2, -1.2), 2.4, 2.4, boxstyle="round,pad=0.1",
                                     facecolor=QUALITY_COLORS['light'], edgecolor=QUALITY_COLORS['dark'], linewidth=3)
        ax.add_patch(box)
        ax.text(0, 0, 'OBJECT', ha='center', va='center', fontsize=15, fontweight='bold')

        arrows = [
            (0, -1.4, 0, -1.6, QUALITY_COLORS['red'], 'Weight(mg)', 0.3, -2.5),
            (0, 1.4, 0, 1.6, QUALITY_COLORS['green'], 'Normal(N)', 0.3, 2.4),
            (-1.4, 0, -1.6, 0, QUALITY_COLORS['orange'], 'Friction(f)', -3.2, 0.3),
            (1.4, 0, 1.6, 0, QUALITY_COLORS['blue'], 'Applied(F)', 1.6, 0.3),
        ]
        for x1, y1, x2, y2, color, label, tx, ty in arrows:
            ax.arrow(x1, y1, x2, y2, head_width=0.18, head_length=0.25, fc=color, ec=color, linewidth=3, alpha=0.9)
            ax.text(tx, ty, label, fontsize=13, color=color, fontweight='bold', ha='center')

        ax.set_title('Free Body Diagram', fontsize=18, fontweight='bold', pad=25)
        return {"success": True, "image_data": fig_to_base64(fig), "provider": "Matplotlib"}
    except Exception as e:
        logger.error(f"Force diagram error: {e}")
        return {"success": False, "error": str(e)}

# ==========================================================
# GRAPHVIZ RENDERERS (STRUCTURAL DIAGRAMS)
# ==========================================================
def draw_flowchart() -> Dict[str, Any]:
    """Generate flowchart diagram."""
    if not GRAPHVIZ_AVAILABLE:
        return {"success": False, "error": "graphviz not installed"}
    try:
        dot = graphviz.Digraph(comment='Process Flow', format='png')
        dot.attr(rankdir='TB', size='8,8', dpi='200')
        dot.node('start', 'Start', shape='ellipse', fillcolor='#7b68ee', fontcolor='white', style='filled')
        dot.node('step1', 'Step 1', shape='box', style='rounded,filled', fillcolor='#ecf0f1')
        dot.node('step2', 'Step 2', shape='box', style='rounded,filled', fillcolor='#ecf0f1')
        dot.node('decision', 'Decision?', shape='diamond', fillcolor='#f39c12', fontcolor='white', style='filled')
        dot.node('step3', 'Step 3', shape='box', style='rounded,filled', fillcolor='#ecf0f1')
        dot.node('end', 'End', shape='ellipse', fillcolor='#27ae60', fontcolor='white', style='filled')
        dot.edge('start', 'step1')
        dot.edge('step1', 'step2')
        dot.edge('step2', 'decision')
        dot.edge('decision', 'step3', label='Yes')
        dot.edge('decision', 'end', label='No')
        dot.edge('step3', 'end')
        img_bytes = dot.pipe()
        return {"success": True, "image_data": base64.b64encode(img_bytes).decode('utf-8'), "provider": "Graphviz"}
    except Exception as e:
        logger.error(f"Flowchart error: {e}")
        return {"success": False, "error": str(e)}

def draw_org_chart() -> Dict[str, Any]:
    """Generate organizational chart."""
    if not GRAPHVIZ_AVAILABLE:
        return {"success": False, "error": "graphviz not installed"}
    try:
        dot = graphviz.Digraph(comment='Org Chart', format='png')
        dot.attr(rankdir='TB', size='8,8', dpi='200')
        dot.node('CEO', 'CEO', shape='ellipse', fillcolor='#e74c3c', fontcolor='white', style='filled')
        dot.node('CTO', 'CTO', fillcolor='#3498db', fontcolor='white', style='filled')
        dot.node('CFO', 'CFO', fillcolor='#2ecc71', fontcolor='white', style='filled')
        dot.node('Dev', 'Dev Team', shape='box', style='rounded,filled', fillcolor='#ecf0f1')
        dot.node('Ops', 'Ops Team', shape='box', style='rounded,filled', fillcolor='#ecf0f1')
        dot.node('Acc', 'Accounting', shape='box', style='rounded,filled', fillcolor='#ecf0f1')
        dot.edge('CEO', 'CTO')
        dot.edge('CEO', 'CFO')
        dot.edge('CTO', 'Dev')
        dot.edge('CTO', 'Ops')
        dot.edge('CFO', 'Acc')
        img_bytes = dot.pipe()
        return {"success": True, "image_data": base64.b64encode(img_bytes).decode('utf-8'), "provider": "Graphviz"}
    except Exception as e:
        logger.error(f"Org chart error: {e}")
        return {"success": False, "error": str(e)}

# ==========================================================
# 🚀 PROFESSIONAL HUGGING FACE GENERATOR (Multi-Model)
# ==========================================================
async def generate_with_hf(prompt: str, model_index: int = 0) -> Dict[str, Any]:
    """
    Generate an image using multiple Hugging Face models.
    Automatically handles queue waiting and fallback models.

    Supported Free Models:
    - black-forest-labs/FLUX.1-dev (Primary)
    - stabilityai/stable-diffusion-3.5-large (High Quality Backup)
    - black-forest-labs/FLUX.1-schnell (Fast Fallback)
    """
    if not HF_TOKEN:
        logger.error("HF_TOKEN not set in .env")
        return {"success": False, "error": "HF_TOKEN not set in .env"}

    MODELS = (
        "black-forest-labs/FLUX.1-dev",
        "stabilityai/stable-diffusion-3.5-large",
        "black-forest-labs/FLUX.1-schnell"
    )
    
    API_BASE = "https://api-inference.huggingface.co/models"
    
    # Enhanced prompt for better results
    enhanced_prompt = f"Professional educational infographic diagram: {prompt}. Clean white background, sharp English labels, textbook quality."

    # ✅ Use a session for better performance and retry handling
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "application/json"
    })

    try:
        attempted_models = []
        for i in range(model_index, len(MODELS)):
            model_id = MODELS[i]
            url = f"{API_BASE}/{model_id}"
            payload = {"inputs": enhanced_prompt}

            try:
                logger.info(f"🖼️ Generating image with {model_id}...")
                response = await asyncio.to_thread(session.post, url, json=payload, timeout=90)

                # Handle Hugging Face "Model is loading" queue (503)
                if response.status_code == 503:
                    wait_time = int(response.headers.get("X-Wait-Time", 5))
                    logger.info(f"⏳ {model_id} is loading. Waiting {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                    response = await asyncio.to_thread(session.post, url, json=payload, timeout=90)

                if response.status_code == 200:
                    # Check content type
                    content_type = response.headers.get("Content-Type", "")
                    if "application/json" in content_type:
                        error_data = response.json()
                        if "error" in error_data:
                            logger.warning(f"{model_id} returned error: {error_data['error']}")
                            continue

                    image_base64 = base64.b64encode(response.content).decode('utf-8')
                    
                    # Validate image size
                    if len(image_base64) > MIN_IMAGE_SIZE:
                        logger.info(f"✅ Image generated with {model_id}")
                        return {
                            "success": True,
                            "image_data": image_base64,
                            "provider": f"Hugging Face ({model_id})"
                        }
                    else:
                        logger.warning(f"⚠️ {model_id} returned an image that was too small. Trying next model...")
                else:
                    logger.warning(f"⚠️ {model_id} returned status {response.status_code}. Trying next model...")

            except requests.exceptions.Timeout:
                logger.warning(f"⏱️ {model_id} timed out. Trying next model...")
            except requests.exceptions.RequestException as e:
                logger.error(f"❌ Request error with {model_id}: {e}. Trying next model...")
            except Exception as e:
                logger.error(f"❌ Unexpected error with {model_id}: {e}. Trying next model...")
            finally:
                attempted_models.append(model_id)

        logger.error("All Hugging Face models failed")
        return {"success": False, "error": "All Hugging Face models failed. Please try a simpler prompt.", "attempted_models": attempted_models}
    finally:
        session.close()

async def generate_with_flux(prompt: str) -> Dict[str, Any]:
    """Legacy wrapper for backward compatibility."""
    return await generate_with_hf(prompt, model_index=0)

# ==========================================================
# DIAGRAM DETECTION
# ==========================================================
DIAGRAM_KEYWORDS = [
    ("ai-diagram", [
        "electric field", "magnetic field", "field force", "physics field",
        "field lines", "field diagram", "circuit diagram", "ray diagram",
        "optics", "wave diagram", "energy level", "atomic structure",
        "molecular", "biology diagram", "anatomy", "cell diagram",
        "schematic", "labelled diagram", "labeled diagram",
        "from the note", "from the pdf", "from the image", "explain with diagram",
        "physics", "newton", "1880", "1080", "educational image", "high-quality resolution",
        "high quality resolution", "clear and explained",
    ]),
    ("speed-time", ["speed-time", "speed time graph", "velocity-time"]),
    ("force-diagram", ["free body", "free-body", "fbd", "free body diagram"]),
    ("flowchart", ["flowchart", "flow chart", "process flow", "algorithm flowchart"]),
    ("bar-chart", ["bar chart", "bar graph", "column chart"]),
    ("pie-chart", ["pie chart", "pie graph"]),
    ("line-chart", ["line chart", "line graph", "trend chart"]),
    ("org-chart", ["org chart", "organizational chart", "hierarchy chart"]),
]

def detect_diagram_types(answer_text: str) -> List[Tuple[str, str]]:
    """Detect diagram types mentioned in text."""
    detected = []
    lower = (answer_text or "").lower()
    for d_type, keywords in DIAGRAM_KEYWORDS:
        if any(kw in lower for kw in keywords):
            detected.append((d_type, keywords[0]))
    if not detected and any(w in lower for w in ("diagram", "figure", "sketch", "illustrate")):
        detected.append(("ai-diagram", "diagram"))
    return detected[:3]


def build_educational_prompt(user_message: str, context: str = "", subject: str = "general") -> str:
    """Textbook-quality diagram prompt from user request + notes/PDF context."""
    um = (user_message or "").strip()
    ctx = (context or "").strip()[:1500]
    subj = (subject or "general").strip()
    parts = [
        "Professional educational textbook diagram, clean white background,",
        "sharp black English labels, high contrast, accurate science drawing,",
        "no watermark, no decorative clutter, publication quality.",
        f"Topic: {subj}.",
        f"Request: {um}.",
    ]
    if ctx:
        parts.append(f"Accurate details from notes/solution:\n{ctx}")
    return " ".join(parts)

# ==========================================================
# MAIN GENERATOR
# ==========================================================
async def generate_diagram_image(diagram_type: str, custom_prompt: Optional[str] = None) -> Dict[str, Any]:
    """
    Generate a diagram image based on type.
    Charts → local matplotlib. Educational science → Colab/HF AI (not ASCII).
    """
    # 1. Local chart/FBD renderers only for true chart types
    if diagram_type == "bar-chart":
        return draw_bar_chart()
    if diagram_type == "pie-chart":
        return draw_pie_chart()
    if diagram_type == "line-chart":
        return draw_line_chart()
    if diagram_type == "speed-time":
        return draw_speed_time_graph()
    if diagram_type == "force-diagram":
        # Prefer AI if a custom educational prompt was provided (e.g. electric field)
        if custom_prompt and any(
            k in custom_prompt.lower()
            for k in ("electric", "magnetic", "field", "physics", "charge")
        ):
            pass  # fall through to AI
        else:
            return draw_force_diagram()
    if diagram_type == "flowchart":
        return draw_flowchart()
    if diagram_type == "org-chart":
        return draw_org_chart()

    # 2. AI educational diagram (Colab worker first, then HF)
    prompt = custom_prompt or (
        f"Professional educational textbook diagram: {diagram_type.replace('-', ' ')}. "
        f"Clean white background, clear English labels only, no watermark, high contrast."
    )
    try:
        result = await generate_creative_image(prompt)
        if result.get("success") and result.get("image_data") and not result.get("is_text"):
            result["diagram_type"] = diagram_type
            return result
    except Exception as e:
        logger.warning(f"AI diagram failed: {e}")

    try:
        result = await generate_with_hf(prompt, model_index=0)
        if result.get("success"):
            return result
    except Exception as e:
        logger.warning(f"HF diagram failed: {e}")

    # 3. Optional Google (opt-in)
    use_google = os.getenv("DIAGRAM_USE_GOOGLE", "false").lower() in ("1", "true", "yes")
    if use_google and GOOGLE_API_KEY and GOOGLE_ENGINE_ID:
        try:
            search_query = f"{prompt[:120]} educational diagram textbook labeled"
            result = await search_real_image(search_query)
            if result.get("success"):
                return result
        except Exception as e:
            logger.warning(f"Google search fallback error: {e}")

    # 4. Do NOT return bad ASCII for science diagrams — clear error
    if diagram_type in ("ai-diagram", "force-diagram") or "field" in (custom_prompt or "").lower():
        return {
            "success": False,
            "error": "Could not render diagram. Ensure HF_TOKEN or Colab GPU Boost is available.",
        }
    return await generate_ascii_art(diagram_type)


async def generate_ascii_art(diagram_type: str) -> Dict[str, Any]:
    """Generate ASCII art as a fallback when all other methods fail."""
    ascii_art = {
        "flowchart": """
        +---------+     +---------+
        |  Start  | --> | Step 1  |
        +---------+     +---------+
                            |
                            v
                    +-----------+
                    | Decision  |
                    +-----------+
                    /          \\
                   Yes         No
                  /            \\
                 v              v
            +---------+    +---------+
            | Step 2  |    |   End   |
            +---------+    +---------+
        """,
        "org-chart": """
                  CEO
                 /  \\
               CTO    CFO
              /  \\     \\
            Dev   Ops  Acc
        """,
        "speed-time": """
        Speed
          ^
        60 |      _____
           |     /     \\
        30 |    /       \\
           |   /         \\
         0 |__/___________\\__> Time
             200   500   600
        """,
    }
    
    art = ascii_art.get(diagram_type, f"Diagram: {diagram_type}")
    return {
        "success": True,
        "image_data": base64.b64encode(art.encode('utf-8')).decode('utf-8'),
        "provider": "ASCII Art",
        "is_text": True
    }

def user_wants_diagram(user_message: str) -> bool:
    """True when user explicitly asks for a visual / image / diagram."""
    if not user_message:
        return False
    m = user_message.lower()
    keys = (
        "draw", "diagram", "chart", "graph", "plot", "illustrate",
        "show me a figure", "generate image", "generate a diagram",
        "make a flowchart", "org chart", "pie chart", "bar chart",
        "speed-time", "free body", "force diagram", "i-v", "i–v", "current and voltage", "voltage and current", "ohm", "characteristic curve",
        "create a", "create an", "create image", "create a picture",
        "generate a picture", "generate an image", "make an image",
        "make a picture", "image of", "picture of", "photo of",
        "draw me", "paint", "artwork", "logo of", "illustration",
        "falcon", "render", "visualize", "visualise",
        "photorealistic", "photography of", "architectural photography",
        "wide-angle view", "8k", "ultra-high definition",
    )
    if any(k in m for k in keys):
        return True
    if len(m) > 80 and any(
        w in m
        for w in (
            "dome", "mosque", "minaret", "courtyard", "marble", "sunset",
            "landscape", "building", "architecture", "skyline", "mountain",
            "masjid", "nabawi",
        )
    ):
        return True
    return False


def user_wants_creative_image(user_message: str) -> bool:
    """Creative/photo-style image (not a chart/flowchart)."""
    if not user_message:
        return False
    m = user_message.lower().strip()
    # Word-boundary checks — bare "graph"/"plot" false-positive inside "photography"
    charty_re = re.compile(
        r"\b("
        r"chart|flowchart|org\s*chart|pie\s*chart|bar\s*chart|"
        r"force\s*diagram|speed[\s-]*time|free\s*body|"
        r"line\s*graph|bar\s*graph|scatter\s*plot|plot\s+a\b"
        r")\b",
        re.I,
    )
    if charty_re.search(m):
        return False
    creative = (
        "image of", "picture of", "photo of", "create a", "create an",
        "generate image", "generate a picture", "generate an image",
        "make an image", "make a picture", "draw me", "paint",
        "artwork", "logo of", "illustration of", "render a",
        "draw a ", "draw an ", "draw the ", "draw image", "eagle image",
        "generate a photo", "show me an image", "show me a picture",
        "photorealistic", "photography of", "architectural photography",
        "generate a photorealistic", "create a photorealistic",
        "wide-angle view showcasing", "ultra-high definition",
    )
    if any(c in m for c in creative):
        return True
    if ("image" in m or "picture" in m or "photo" in m) and any(
        w in m for w in ("create", "generate", "make", "draw", "show")
    ):
        return True
    if m.startswith("draw ") or m.strip() in ("draw it", "draw this", "draw that") or " draw " in f" {m} ":
        return True
    # Pasted full scene prompt (architecture / landmarks / nature)
    if len(m) > 100 and any(
        w in m
        for w in (
            "dome", "mosque", "minaret", "courtyard", "marble columns",
            "sunset", "twilight", "landscape", "architecture", "skyline",
            "masjid", "nabawi", "kaaba", "haram",
        )
    ):
        return True
    return False


async def generate_all_diagrams(
    answer_text: str,
    subject: str = "general",
    user_message: str = "",
) -> List[Dict[str, Any]]:
    """
    Generate diagrams only when the user asked for one (or DIAGRAM_ALWAYS=true).
    Avoids sticking unrelated stock/generic images onto every physics answer.
    """
    always = os.getenv("DIAGRAM_ALWAYS", "false").lower() in ("1", "true", "yes")
    wants = always or user_wants_diagram(user_message)
    if not wants:
        logger.info("Skipping diagrams — user did not request a figure")
        return []

    images = []
    intent = (user_message or answer_text or "")[:500]
    # Include answer/notes context for accurate problem diagrams (PDF/notes solve)
    edu_prompt = build_educational_prompt(user_message, context=answer_text or "", subject=subject)

    # Physics I–V / current-voltage → matplotlib (fast, no Colab needed)
    um = (user_message or "").lower()
    if any(k in um for k in (
        "current and voltage", "voltage and current", "i-v", "i–v",
        "i/v graph", "iv graph", "i-v graph", "ohm's law graph", "ohms law graph",
        "characteristic curve", "creat graph", "create graph",
    )) and any(k in um for k in ("current", "voltage", "i-v", "i–v", "ohm", "graph", "plot")):
        logger.info("I-V graph request → matplotlib")
        r = draw_iv_graph(ohmic=("diode" not in um and "non-ohmic" not in um and "non ohmic" not in um and "bulb" not in um))
        if r.get("success"):
            r["keyword"] = "I-V graph"
            return [r]
        logger.warning(f"I-V graph failed: {r.get('error')}")

    # Creative / photo-style request → Colab/HF (not ASCII)
    if user_wants_creative_image(user_message):
        logger.info(f"Creative image request: {intent[:80]}")
        result = await generate_creative_image(intent)
        if result.get("success") and not result.get("is_text"):
            result["keyword"] = "creative"
            result["diagram_type"] = "creative"
            images.append(result)
            return images
        logger.warning(f"Creative image failed: {result.get('error')}")

    source = user_message if user_wants_diagram(user_message) else answer_text
    diagram_types = detect_diagram_types(source) or detect_diagram_types(answer_text)

    # Physics / educational "draw a … diagram" with no chart match → AI diagram
    if not diagram_types and user_wants_diagram(user_message):
        diagram_types = [("ai-diagram", "diagram")]

    if not diagram_types:
        logger.info("No diagram types detected")
        return []

    for diagram_type, keyword in diagram_types[:2]:
        logger.info(f"Generating {diagram_type} diagram")
        if diagram_type == "ai-diagram" or diagram_type == "force-diagram":
            custom = edu_prompt
        else:
            custom = f"{subject} {keyword}: {intent}".strip()
        result = await generate_diagram_image(diagram_type, custom_prompt=custom)
        if result.get("success"):
            result["keyword"] = keyword
            result["diagram_type"] = diagram_type
            images.append(result)
            logger.info(f"✅ {diagram_type} generated successfully")
        else:
            logger.warning(f"Failed to generate {diagram_type}: {result.get('error')}")
    return images



def _is_educational_anatomy(text: str) -> bool:
    t = (text or "").lower()
    # Never treat architecture / landmarks as anatomy
    if any(
        w in t
        for w in (
            "mosque", "masjid", "minaret", "dome", "nabawi", "kaaba",
            "architecture", "building", "courtyard", "marble column",
            "landscape", "mountain", "lake", "city",
        )
    ):
        return False
    keys = (
        "anatomy", "anatomical", "medical student", "physiology",
        "skeleton", "muscular system", "circulatory", "nervous system",
        "penis", "genital", "genitalia", "scrotum", "testis", "testicle",
        "prostate", "urethra", "corpus cavernosum", "corpus spongiosum",
        "sagittal", "cross-section", "cross section",
    )
    return any(k in t for k in keys)


def clean_image_prompt(raw: str) -> str:
    """Keep the user's visual intent; strip chat fluff that confuses image models."""
    p = (raw or "").strip()
    if not p:
        return "detailed illustration"
    low = p.lower()
    for prefix in (
        "create a high resolution image which",
        "create a high-resolution image which",
        "create an image that",
        "create a image that",
        "create an image of",
        "create a image of",
        "generate an image of",
        "generate a image of",
        "generate an image that",
        "draw me an image of",
        "draw an image of",
        "draw a picture of",
        "make an image of",
        "make a picture of",
        "please ",
    ):
        if low.startswith(prefix):
            p = p[len(prefix):].strip()
            low = p.lower()
    p = re.sub(
        r"^(?:that |which )?(?:demonstrates|shows|represents|depicts)\s+",
        "",
        p,
        flags=re.I,
    ).strip()
    p = re.sub(r"\band it works in my app online\b", "", p, flags=re.I).strip()
    p = re.sub(r"\s{2,}", " ", p).strip(" ,.-")
    if len(p) < 3:
        p = (raw or "illustration").strip()

    if _is_educational_anatomy(raw) or _is_educational_anatomy(p):
        return (
            f"Educational medical anatomy textbook illustration of {p}, "
            f"accurate human anatomy, sagittal or labeled diagram as appropriate, "
            f"clinical diagram style, clear anatomical labels, white background, "
            f"professional medical education for students, realistic proportions, "
            f"not sexualized, not pornographic, not abstract art, not a medical device"
        )

    # Architecture / landmark: keep the full scene prompt (do not over-shorten)
    if any(
        w in low
        for w in (
            "mosque", "masjid", "minaret", "nabawi", "architecture",
            "photorealistic", "dome", "courtyard", "marble",
        )
    ):
        return (
            f"{p}, photorealistic exterior of a magnificent mosque with elegant dome and tall minarets, "
            f"intricate Islamic geometric patterns, marble and sandstone, golden hour sunlight, "
            f"wide-angle architectural photography, sharp details, realistic proportions, 8k UHD, "
            f"no abstract symbols, no diagrams, no text overlays, matches the prompt exactly"
        )

    return f"{p}, highly detailed, coherent composition, matches the prompt exactly, no unrelated subjects"


# ==========================================================
# Smart Image Router (v3.0)
# ==========================================================
class SmartImageRouter:
    """
    Image generation policy (v3.0.9):
    - PRIMARY: Colab Boost with *downloaded* local models only (SDXL-turbo / Flux on worker).
    - Optional RunPod GPU worker (also local weights).
    - Does NOT use Gemini, Groq, OpenRouter, or other chat API keys for images.
    - Cloud HF / Pollinations only if IMAGE_ALLOW_CLOUD=1 (off by default).
    """

    def __init__(self) -> None:
        self.last_provider: Optional[str] = None

    async def generate(self, prompt: str) -> Dict[str, Any]:
        strict = (prompt or "").strip()
        if not strict:
            return {"success": False, "error": "Empty image prompt"}

        allow_cloud = (os.getenv("IMAGE_ALLOW_CLOUD") or "0").strip().lower() in ("1", "true", "yes")

        # 1) Colab GPU — downloaded models only
        try:
            from services.colab_worker import is_enabled as _colab_on, generate_image as _colab_img
            if _colab_on():
                # T4-friendly defaults plugged into the live path
                got = _colab_img(strict, width=512, height=512, steps=4)
                if got and got.get("success"):
                    self.last_provider = "colab"
                    got.setdefault("provider", "Colab local model")
                    return got
                logger.warning("Colab image returned no success: %s", (got or {}).get("error"))
            else:
                logger.info("Colab Boost not live — set COLAB_WORKER_URL or register worker from Boost")
        except Exception as e:
            logger.warning("SmartImageRouter Colab: %s", e)

        # 2) RunPod (optional dedicated GPU with local weights)
        try:
            from services.runpod_worker import is_enabled as _rp_on, generate_image as _rp_img
            if _rp_on():
                got = _rp_img(strict)
                if got and got.get("success"):
                    self.last_provider = "runpod"
                    got.setdefault("provider", "RunPod local model")
                    return got
        except Exception as e:
            logger.warning("SmartImageRouter RunPod: %s", e)

        # 3) Cloud fallbacks ONLY if explicitly enabled (never use chat API keys)
        if allow_cloud:
            if HF_TOKEN:
                try:
                    got = await generate_with_hf_creative(strict)
                    if got and got.get("success"):
                        self.last_provider = "huggingface"
                        return got
                except Exception as e:
                    logger.warning("SmartImageRouter HF: %s", e)
            try:
                from services.flux_image import generate_pollinations_image
                got = await generate_pollinations_image(strict)
                if got and got.get("success"):
                    self.last_provider = "pollinations"
                    return got
            except Exception as e:
                logger.warning("SmartImageRouter Pollinations: %s", e)

        return {
            "success": False,
            "error": (
                "Image generation uses Colab downloaded models only. "
                "Open Colab Boost, wait until /worker/health shows warmed:true, then retry. "
                "Chat API keys (Gemini/Groq/OpenRouter) are never used for images. "
                "Set IMAGE_ALLOW_CLOUD=1 only if you want HF/Pollinations fallback."
            ),
            "url": None,
        }


smart_image_router = SmartImageRouter()


async def generate_creative_image(prompt: str) -> Dict[str, Any]:
    """Generate a real image via SmartImageRouter (Colab → HF → Pollinations)."""
    return await smart_image_router.generate(prompt)


async def generate_with_hf_creative(prompt: str) -> Dict[str, Any]:
    """HF inference with creative prompt (no textbook-diagram suffix)."""
    if not HF_TOKEN:
        return {"success": False, "error": "HF_TOKEN not set in .env"}

    MODELS = (
        "black-forest-labs/FLUX.1-schnell",  # fast free-friendly first
        "black-forest-labs/FLUX.1-dev",
        "stabilityai/stable-diffusion-3.5-large",
    )
    API_BASE = "https://api-inference.huggingface.co/models"
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "application/json",
    })
    try:
        for model_id in MODELS:
            url = f"{API_BASE}/{model_id}"
            payload = {"inputs": prompt}
            try:
                logger.info(f"🖼️ Creative gen with {model_id}...")
                response = await asyncio.to_thread(session.post, url, json=payload, timeout=90)
                if response.status_code == 503:
                    wait_time = min(int(response.headers.get("X-Wait-Time", 8)), 25)
                    await asyncio.sleep(wait_time)
                    response = await asyncio.to_thread(session.post, url, json=payload, timeout=90)
                if response.status_code == 200:
                    ct = response.headers.get("Content-Type", "")
                    if "application/json" in ct:
                        err = response.json()
                        logger.warning(f"{model_id} json error: {err}")
                        continue
                    image_base64 = base64.b64encode(response.content).decode("utf-8")
                    if len(image_base64) > MIN_IMAGE_SIZE:
                        return {
                            "success": True,
                            "image_data": image_base64,
                            "provider": f"Hugging Face ({model_id})",
                        }
                else:
                    logger.warning(f"{model_id} status {response.status_code}: {response.text[:200]}")
            except Exception as e:
                logger.warning(f"{model_id} error: {e}")
        return {"success": False, "error": "All HF creative models failed. Check HF_TOKEN and model access."}
    finally:
        session.close()

# ==========================================================
# UTILITY FUNCTIONS
# ==========================================================
def generate_chart(data: Dict, chart_type: str = "bar") -> Dict[str, Any]:
    """Generate a chart from data."""
    if chart_type == "bar":
        return draw_bar_chart(data)
    elif chart_type == "pie":
        return draw_pie_chart(data)
    elif chart_type == "line":
        return draw_line_chart(data)
    else:
        return {"success": False, "error": f"Unsupported chart type: {chart_type}"}

def generate_diagram(diagram_type: str, custom_prompt: Optional[str] = None) -> Dict[str, Any]:
    """Sync wrapper for generate_diagram_image."""
    import asyncio
    return asyncio.run(generate_diagram_image(diagram_type, custom_prompt))

# ==========================================================
# EXPORTS
# ==========================================================
__all__ = [
    "generate_all_diagrams",
    "generate_diagram_image",
    "generate_diagram",
    "generate_chart",
    "detect_diagram_types",
    "draw_bar_chart",
    "draw_pie_chart",
    "draw_line_chart",
    "draw_speed_time_graph",
    "draw_iv_graph",
    "draw_force_diagram",
    "draw_flowchart",
    "draw_org_chart",
    "generate_with_hf",
    "generate_with_flux",
    "SmartImageRouter",
    "smart_image_router",
    "generate_creative_image",
    "search_real_image",
]

logger.info("👁️ Vision AI Image & Diagram Generation v2.0 - Ready")