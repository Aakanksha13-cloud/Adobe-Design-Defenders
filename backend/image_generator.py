import json
import requests
import fitz  # PyMuPDF for PDF reading
from pathlib import Path
from typing import Optional
from fastapi import UploadFile, HTTPException
from google import genai
from google.genai import types
from datetime import datetime

# ============================================
# CONFIGURATION
# ============================================
CLIPDROP_API_KEY = "c52c0d1df2524a3c648751280b06e1563e726420ec032ef11a920627de0f6a5d47d200f99f81ad7950fbe1923aa19028"
GEMINI_API_KEY = "AIzaSyBNoSDFPo81KRwLL5W9WlXNmgkMbaQ6Hfg"

OUTPUT_DIR = Path(__file__).parent.parent / "uploads" / "generated_images"
OUTPUT_DIR.mkdir(exist_ok=True)

# Initialize Gemini client
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

# ============================================
# HELPER FUNCTIONS
# ============================================
def load_analysis_json(file_path: Path) -> dict:
    """Load and parse the analysis JSON"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"✅ Analysis loaded: {data['metadata']['total_posts']} posts analyzed")
        return data
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON file: {str(e)}")


def extract_pdf_text(file_path: Path) -> str:
    """Extract text from brand guidelines PDF"""
    try:
        doc = fitz.open(str(file_path))
        full_text = ""
        
        for page_num, page in enumerate(doc):
            text = page.get_text()
            full_text += f"\n--- Page {page_num + 1} ---\n{text}"
        
        doc.close()
        
        print(f"✅ Brand guidelines loaded: {page_num + 1} pages")
        return full_text
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid PDF file: {str(e)}")


def extract_design_requirements(analysis_data: dict, brand_text: str) -> dict:
    """Extract key design elements from analysis and brand guidelines"""
    popular = analysis_data['popular_posts']['common_features']
    
    return {
        "visual_style": [f['feature'] for f in popular.get('visual_style', [])],
        "color_palette": [f['feature'] for f in popular.get('color_palette', [])],
        "composition": [f['feature'] for f in popular.get('composition', [])],
        "subject_matter": [f['feature'] for f in popular.get('subject_matter', [])],
        "lighting": [f['feature'] for f in popular.get('lighting', [])],
        "photography_technique": [f['feature'] for f in popular.get('photography_technique', [])],
        "text_graphics": [f['feature'] for f in popular.get('text_graphics', [])],
        "emotion_mood": [f['feature'] for f in popular.get('emotion_mood', [])],
        "brand_elements": [f['feature'] for f in popular.get('brand_elements', [])],
        "insights": analysis_data.get('insights', ''),
        "brand_guidelines": brand_text[:3000]  # Truncate for context
    }


def generate_prompt_with_ai(design_brief: dict, user_request: str) -> str:
    """Use Gemini AI to create an optimized image generation prompt"""
    
    context_prompt = f"""You are an expert prompt engineer for AI image generation tools.

Based on the following information, create a highly detailed, optimized prompt for generating a social media post image:

USER REQUEST:
{user_request}

HIGH-PERFORMING DESIGN FEATURES (from data analysis):
- Visual Styles: {', '.join(design_brief['visual_style'][:5])}
- Color Palette: {', '.join(design_brief['color_palette'][:5])}
- Composition: {', '.join(design_brief['composition'][:5])}
- Subject Matter: {', '.join(design_brief['subject_matter'][:5])}
- Mood/Emotion: {', '.join(design_brief['emotion_mood'][:3])}
- Text/Graphics: {', '.join(design_brief['text_graphics'][:3])}

BRAND GUIDELINES EXCERPT:
{design_brief['brand_guidelines'][:1500]}

INSIGHTS FROM ANALYSIS:
{design_brief['insights'][:1000]}

Create a single, comprehensive prompt (200-300 words) that:
1. Incorporates the user's specific request
2. Uses the proven high-performing visual features
3. Respects brand guidelines
4. Is optimized for text-to-image AI models (detailed, specific, comma-separated descriptors)
5. Includes "NO TEXT, no words, no letters, no typography, text-free" at the end if the image should be text-free

Return ONLY the prompt text, nothing else."""

    try:
        response = gemini_client.models.generate_content(
            model='gemini-2.0-flash',
            contents=context_prompt
        )
        
        prompt = response.text.strip()
        print(f"✅ AI-generated prompt: {prompt[:100]}...")
        return prompt
        
    except Exception as e:
        print(f"⚠️ AI prompt generation failed: {e}")
        # Fallback to simple prompt
        return f"{user_request}, {', '.join(design_brief['visual_style'][:3])}, {', '.join(design_brief['color_palette'][:3])}, professional design, NO TEXT"


def generate_image_clipdrop(prompt: str, output_filename: str) -> str:
    """Generate image using Clipdrop API"""
    
    print(f"🎨 Generating image with Clipdrop...")
    
    try:
        r = requests.post(
            'https://clipdrop-api.co/text-to-image/v1',
            files={'prompt': (None, prompt, 'text/plain')},
            headers={'x-api-key': CLIPDROP_API_KEY},
            timeout=60
        )
        
        if r.ok:
            output_path = OUTPUT_DIR / output_filename
            with open(output_path, 'wb') as f:
                f.write(r.content)
            print(f"✅ Image saved to: {output_path}")
            return str(output_path)
        else:
            raise HTTPException(
                status_code=r.status_code,
                detail=f"Clipdrop API error: {r.text}"
            )
            
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Image generation failed: {str(e)}")


def generate_design_from_text(user_request: str) -> dict:
    """
    Main function to generate design from user text request
    Uses analyze.json and brand guidelines from uploads folder
    """
    
    print("\n" + "="*70)
    print("🚀 STARTING DESIGN GENERATION")
    print("="*70)
    
    try:
        # Find required files
        uploads_dir = Path(__file__).parent.parent / "uploads"
        
        # Step 1: Load analysis JSON
        print("\n📊 Loading analysis data...")
        analysis_file = uploads_dir / "analyze.json"
        if not analysis_file.exists():
            raise HTTPException(
                status_code=404, 
                detail="analyze.json not found. Please run 'Analyze past posts by AI' first."
            )
        analysis_data = load_analysis_json(analysis_file)
        
        # Step 2: Extract brand guidelines
        print("\n📄 Extracting brand guidelines...")
        brand_pdfs = list(uploads_dir.glob("brand_guidelines_*.pdf"))
        if not brand_pdfs:
            raise HTTPException(
                status_code=404,
                detail="No brand guidelines PDF found. Please upload brand guidelines first."
            )
        brand_pdf = max(brand_pdfs, key=lambda p: p.stat().st_mtime)
        brand_text = extract_pdf_text(brand_pdf)
        
        # Step 3: Create design brief
        print("\n📋 Creating design brief...")
        design_brief = extract_design_requirements(analysis_data, brand_text)
        print(f"   Visual styles: {design_brief['visual_style'][:3]}")
        print(f"   Colors: {design_brief['color_palette'][:3]}")
        
        # Step 4: Generate AI-optimized prompt
        print("\n🤖 Generating AI-optimized prompt...")
        print(f"   User request: '{user_request}'")
        image_prompt = generate_prompt_with_ai(design_brief, user_request)
        
        # Step 5: Generate image
        print("\n🎨 Generating image...")
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_filename = f"generated_{timestamp}.png"
        image_path = generate_image_clipdrop(image_prompt, output_filename)
        
        print("\n" + "="*70)
        print("✅ GENERATION COMPLETE")
        print("="*70)
        
        return {
            "status": "success",
            "message": "Design generated successfully!",
            "user_request": user_request,
            "generated_prompt": image_prompt,
            "image_filename": output_filename,
            "image_path": image_path,
            "design_brief_summary": {
                "visual_styles": design_brief['visual_style'][:5],
                "color_palette": design_brief['color_palette'][:5],
                "emotion_mood": design_brief['emotion_mood'][:3]
            },
            "analysis_stats": {
                "total_posts_analyzed": analysis_data['metadata']['total_posts'],
                "popular_posts": analysis_data['popular_posts']['count'],
                "timestamp": analysis_data['metadata']['timestamp']
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")
