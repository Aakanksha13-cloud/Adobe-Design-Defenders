"""
Compliance Module - Handles all compliance checks, brand image and brand guidelines uploads
"""
from fastapi import APIRouter, File, UploadFile, HTTPException
from pathlib import Path
from datetime import datetime
import shutil
from PIL import Image
import io
import os
from google import genai
from google.genai import types
from PyPDF2 import PdfReader
import requests
import base64
from serpapi import GoogleSearch

router = APIRouter()

# Define uploads directory path
UPLOADS_DIR = Path(__file__).parent.parent / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

# Define brand images subdirectory
BRAND_IMAGES_DIR = UPLOADS_DIR / "brand_images"
BRAND_IMAGES_DIR.mkdir(exist_ok=True)

print(f"📁 Uploads directory: {UPLOADS_DIR}")
print(f"📁 Brand images directory: {BRAND_IMAGES_DIR}")

# Initialize Gemini AI and API keys
GEMINI_API_KEY = 'AIzaSyBoO7q1XMga94SRjCpQpQP29KFCyoqh09c'
IMGBB_API_KEY = '229e8aefe398b932dca167b4434c6cd0'
SERPAPI_KEY = 'ef21699f744310e005d5d3c18cedfa6cf8252b304da2e148e2fa35850810ecc4'
os.environ['GOOGLE_API_KEY'] = GEMINI_API_KEY


class BrandComplianceChecker:
    def __init__(self):
        """Initialize the Brand Compliance Checker"""
        self.client = genai.Client()
        self.brand_guidelines = ""
        
    def load_brand_guidelines(self, txt_or_pdf_path):
        """Load brand guidelines from text file or PDF"""
        try:
            file_path = Path(txt_or_pdf_path)
            
            # Check if file is PDF
            if file_path.suffix.lower() == '.pdf':
                reader = PdfReader(txt_or_pdf_path)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                self.brand_guidelines = text
                print(f"✓ Loaded PDF with {len(reader.pages)} pages")
            else:
                # Handle as text file
                with open(txt_or_pdf_path, 'r', encoding='utf-8') as file:
                    self.brand_guidelines = file.read()
                print(f"✓ Loaded text file")
            
            return True
        except Exception as e:
            print(f"Error reading brand guidelines: {e}")
            return False
    
    def check_compliance(self, image_bytes, mime_type, detailed=True):
        """Check if image complies with brand guidelines"""
        if not self.brand_guidelines:
            raise ValueError("Brand guidelines not loaded.")
        
        try:
            prompt = self._create_compliance_prompt(detailed)
            
            response = self.client.models.generate_content(
                model='gemini-3-flash-preview',
                contents=[
                    types.Part.from_bytes(
                        data=image_bytes,
                        mime_type=mime_type,
                    ),
                    prompt
                ]
            )
            
            result = self._parse_response(response.text)
            return result
            
        except Exception as e:
            return {"error": f"Compliance check failed: {str(e)}", "compliant": False}
    
    def _create_compliance_prompt(self, detailed):
        """Create the compliance checking prompt"""
        prompt = f"""You are a brand compliance reviewer. Analyze this image against the following brand guidelines:

BRAND GUIDELINES:
{self.brand_guidelines}

REVIEW APPROACH:
- Be LENIENT and REASONABLE when the image matches the brand's core identity
- Focus on the OVERALL brand impression and feeling
- Mark as COMPLIANT if the image clearly represents the brand correctly
- Small creative variations or artistic choices are ENCOURAGED
- Only mark NON-COMPLIANT for clear, serious violations of core brand rules
- Be STRICT ONLY when the image clearly shows a competing brand or violates fundamental requirements

Check these aspects:
1. Core brand identity (logo, colors, product)
2. Overall brand feeling and mood
3. Major violations only (wrong brand, wrong colors, competing products)
4. Creative elements (be lenient - creativity is good!)

Provide your response in EXACTLY this format:

COMPLIANCE STATUS: [COMPLIANT/NON-COMPLIANT/NEEDS REVIEW]

VIOLATIONS FOUND:
- [List ONLY serious violations, or write "None - image represents the brand well"]

COMPLIANT ASPECTS:
- [List what matches the guidelines - be generous]

RECOMMENDATIONS:
- [Minor suggestions only, or write "None - approved as is"]

OVERALL SCORE: [X/10]

SUMMARY: [One sentence - focus on whether the brand is represented correctly]
"""
        
        if detailed:
            prompt += "\n\nBe encouraging and positive if the image clearly represents the brand."
        
        return prompt
    
    def _parse_response(self, response_text):
        """Parse the AI response into structured format"""
        status_line = ""
        for line in response_text.split('\n'):
            if 'COMPLIANCE STATUS:' in line.upper():
                status_line = line.upper()
                break
        
        compliant = False
        if "COMPLIANT" in status_line and "NON-COMPLIANT" not in status_line:
            compliant = True
        
        return {
            "raw_analysis": response_text,
            "compliant": compliant,
            "status": status_line
        }


# Initialize the checker
checker = BrandComplianceChecker()


# Copyright checking functions
def upload_to_imgbb(image_path):
    """Upload image to ImgBB and get public URL"""
    print("📤 Uploading to ImgBB...")
    
    try:
        with open(image_path, "rb") as file:
            url = "https://api.imgbb.com/1/upload"
            payload = {
                "key": IMGBB_API_KEY,
                "image": base64.b64encode(file.read()),
            }
            res = requests.post(url, payload)
            
            if res.status_code == 200:
                image_url = res.json()['data']['url']
                print(f"✅ Uploaded to ImgBB: {image_url}")
                return image_url
            else:
                print(f"❌ ImgBB Error: {res.text}")
                return None
    except Exception as e:
        print(f"❌ Upload error: {e}")
        return None


def check_copyright_sources(image_url):
    """Perform reverse image search and check for copyright sources"""
    
    COPYRIGHT_SITES = [
        'shutterstock.com', 'gettyimages.com', 'istockphoto.com',
        'adobe.stock', 'depositphotos.com', 'dreamstime.com',
        'alamy.com', '123rf.com', 'stocksy.com', 'pond5.com',
        'pixabay.com', 'unsplash.com', 'pexels.com', 'freepik.com',
        'vecteezy.com', 'canva.com', 'envato.com', 'creativemarket.com'
    ]
    
    print("=" * 70)
    print("🔍 REVERSE IMAGE SEARCH - COPYRIGHT DETECTION")
    print("=" * 70)
    print(f"\nSearching for: {image_url}\n")
    
    params = {
        "engine": "google_reverse_image",
        "image_url": image_url,
        "api_key": SERPAPI_KEY
    }
    
    try:
        search = GoogleSearch(params)
        results = search.get_dict()
        
        if "error" in results:
            print(f"❌ API Error: {results['error']}")
            return None
        
        image_results = results.get("image_results", [])
        
        if not image_results:
            print("⚠️ No image results found")
            return {
                'total_results': 0,
                'copyright_results': [],
                'all_results': []
            }
        
        print(f"✅ Found {len(image_results)} total results\n")
        
        # Check for copyright sources
        copyright_found = []
        
        for i, result in enumerate(image_results, 1):
            link = result.get('link', '')
            source = result.get('source', '')
            title = result.get('title', '')
            
            matched_site = None
            for site in COPYRIGHT_SITES:
                if site.lower() in link.lower() or site.lower() in source.lower():
                    matched_site = site
                    break
            
            if matched_site:
                copyright_found.append({
                    'position': i,
                    'site': matched_site,
                    'link': link,
                    'source': source,
                    'title': title
                })
        
        print(f"🚨 Found {len(copyright_found)} copyright sources")
        
        # Print found copyright sources for debugging
        if copyright_found:
            print("\n⚠️  COPYRIGHT SOURCES DETECTED:")
            for item in copyright_found[:5]:
                print(f"   [{item['position']}] {item['site']} - {item['title'][:60]}...")
            if len(copyright_found) > 5:
                print(f"   ... and {len(copyright_found) - 5} more")
        else:
            print("\n✅ No copyright sources detected in results")
        
        print("\n📋 Top 5 sources found:")
        for i, result in enumerate(image_results[:5], 1):
            source = result.get('source', 'Unknown')
            print(f"   {i}. {source}")
        
        return {
            'total_results': len(image_results),
            'copyright_results': copyright_found,
            'all_results': image_results[:10]  # Top 10 results
        }
        
    except Exception as e:
        print(f"❌ SerpAPI Error: {e}")
        return None


def analyze_copyright_with_ai(copyright_data):
    """Use Gemini AI to analyze copyright findings"""
    
    client = genai.Client()
    
    copyright_count = len(copyright_data['copyright_results'])
    total_results = copyright_data['total_results']
    
    # Build summary for AI
    summary = f"""COPYRIGHT ANALYSIS REQUEST

Total Results Found: {total_results}
Copyright/Stock Sites Detected: {copyright_count}

"""
    
    if copyright_data['copyright_results']:
        summary += "COPYRIGHT SOURCES DETECTED:\n"
        for item in copyright_data['copyright_results'][:5]:
            summary += f"- {item['site']}: {item['title'][:100]}\n"
    
    summary += "\nTOP SOURCES:\n"
    for i, result in enumerate(copyright_data['all_results'][:5], 1):
        summary += f"{i}. {result.get('source', 'Unknown')}: {result.get('title', 'No title')[:80]}\n"
    
    prompt = f"""{summary}

You are a copyright compliance expert. Analyze the above reverse image search results.

Provide your response in EXACTLY this format:

COPYRIGHT STATUS: [SAFE/RISKY/COPYRIGHTED]

VERDICT:
- [Clear verdict in one sentence]

RISK LEVEL: [LOW/MEDIUM/HIGH]

DETAILS:
- [Explain the findings]
- [List specific copyright sources if found]
- [Explain the risk]

RECOMMENDATIONS:
- [What user should do]
- [How to proceed safely]

SUMMARY: [One sentence final verdict]"""
    
    try:
        response = client.models.generate_content(
            model='gemini-3-flash-preview',
            contents=prompt
        )
        
        return response.text
        
    except Exception as e:
        print(f"❌ Gemini AI Error: {e}")
        return None


@router.post("/compliance-check")
async def compliance_check(file: UploadFile = File(...)):
    """
    Handle compliance check - receives exported PNG from canvas
    Analyzes against brand guidelines using Gemini AI
    """
    try:
        # Generate unique filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"compliance_check_{timestamp}.png"
        file_path = UPLOADS_DIR / filename
        
        # Read file content for analysis
        file_content = await file.read()
        file_size_mb = len(file_content) / (1024 * 1024)
        
        # Save the exported PNG
        with open(file_path, "wb") as buffer:
            buffer.write(file_content)
        
        print(f"✅ Compliance check PNG saved: {filename}")
        print(f"📊 File size: {file_size_mb:.2f} MB")
        
        # Get image dimensions
        img = Image.open(io.BytesIO(file_content))
        width, height = img.size
        print(f"🖼️  Resolution: {width}x{height}")
        
        # Find brand guidelines in uploads folder
        guideline_files = list(UPLOADS_DIR.glob("brand_guidelines*"))
        
        if not guideline_files:
            print("⚠️  No brand guidelines found in uploads folder")
            return {
                "success": False,
                "error": "No brand guidelines found",
                "message": "Please upload brand guidelines first using the Brand Guidelines button",
                "compliance": {
                    "status": "error",
                    "message": "Cannot perform compliance check without brand guidelines",
                    "emoji": "⚠️"
                }
            }
        
        # Use the most recent brand guidelines file
        guideline_file = max(guideline_files, key=lambda p: p.stat().st_mtime)
        print(f"📋 Using brand guidelines: {guideline_file.name}")
        
        # Load brand guidelines
        if not checker.load_brand_guidelines(str(guideline_file)):
            raise HTTPException(status_code=500, detail="Failed to load brand guidelines")
        
        # Run AI compliance check
        print("🤖 Running AI compliance check with Gemini...")
        mime_type = "image/png"
        ai_result = checker.check_compliance(file_content, mime_type, detailed=True)
        
        if "error" in ai_result:
            raise HTTPException(status_code=500, detail=ai_result["error"])
        
        # Determine status
        is_compliant = ai_result["compliant"]
        
        if is_compliant:
            status = "passed"
            message = "✅ COMPLIANT - Image meets brand guidelines"
            emoji = "✅"
        else:
            status = "failed"
            message = "❌ NON-COMPLIANT - Image violates brand guidelines"
            emoji = "❌"
        
        print(f"{emoji} Compliance Status: {status.upper()}")
        print(f"📊 AI Analysis:\n{ai_result['raw_analysis'][:200]}...")
        
        compliance_result = {
            "status": status,
            "message": message,
            "emoji": emoji,
            "compliant": is_compliant,
            "ai_analysis": ai_result["raw_analysis"],
            "status_line": ai_result["status"],
            "details": {
                "filename": filename,
                "path": str(file_path),
                "size_mb": round(file_size_mb, 2),
                "resolution": f"{width}x{height}",
                "color_mode": img.mode,
                "timestamp": timestamp,
                "guideline_used": guideline_file.name
            }
        }
        
        return {
            "success": True,
            "compliance": compliance_result
        }
        
    except Exception as e:
        print(f"❌ Compliance check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/brand-image")
async def upload_brand_image(file: UploadFile = File(...)):
    """
    Handle brand image and CSV uploads
    Saves files to uploads/brand_images folder for compliance reference
    """
    try:
        # Debug logging
        print(f"📥 Received file: {file.filename}")
        print(f"📋 Content-Type: {file.content_type}")
        
        # Get file extension
        file_extension = Path(file.filename).suffix.lower()
        print(f"📝 File extension: {file_extension}")
        
        # Validate file type - allow images and CSV
        is_image = file.content_type and file.content_type.startswith('image/')
        is_csv = file_extension == '.csv' or (file.content_type and 'csv' in file.content_type.lower())
        
        if not is_image and not is_csv:
            print(f"❌ Invalid file type: {file.content_type}, extension: {file_extension}")
            raise HTTPException(
                status_code=400, 
                detail=f"File must be an image or CSV. Got content-type: {file.content_type}, extension: {file_extension}"
            )
        
        print(f"✅ File validation passed (image: {is_image}, csv: {is_csv})")
        
        # Keep original filename
        filename = file.filename
        file_path = BRAND_IMAGES_DIR / filename
        
        # Save the file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        
        file_type = "CSV" if file_extension == '.csv' else "image"
        print(f"✅ {file_type.capitalize()} saved: uploads/brand_images/{filename}")
        print(f"📊 File size: {file_size_mb:.2f} MB")
        
        return {
            "success": True,
            "message": f"{file_type.capitalize()} uploaded to uploads/brand_images",
            "details": {
                "filename": filename,
                "path": str(file_path),
                "size_mb": round(file_size_mb, 2),
                "content_type": file.content_type
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Brand image upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/brand-guidelines")
async def upload_brand_guidelines(file: UploadFile = File(...)):
    """
    Handle brand guidelines document uploads
    Saves documents to uploads folder for compliance reference
    """
    try:
        # Validate file type
        allowed_types = [
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'text/plain'
        ]
        
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400, 
                detail="File must be PDF, DOC, DOCX, or TXT"
            )
        
        # Generate unique filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_extension = Path(file.filename).suffix
        filename = f"brand_guidelines_{timestamp}{file_extension}"
        file_path = UPLOADS_DIR / filename
        
        # Save the brand guidelines
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        
        print(f"✅ Brand guidelines saved: {filename}")
        print(f"📊 File size: {file_size_mb:.2f} MB")
        
        return {
            "success": True,
            "message": "Brand guidelines uploaded successfully",
            "details": {
                "filename": filename,
                "original_name": file.filename,
                "path": str(file_path),
                "size_mb": round(file_size_mb, 2),
                "content_type": file.content_type,
                "timestamp": timestamp
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Brand guidelines upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/uploads/list")
def list_all_uploads():
    """
    List all files in uploads folder
    """
    try:
        files = []
        if UPLOADS_DIR.exists():
            for file_path in UPLOADS_DIR.iterdir():
                if file_path.is_file() and not file_path.name.startswith('.'):
                    files.append({
                        "filename": file_path.name,
                        "size_mb": round(file_path.stat().st_size / (1024 * 1024), 2),
                        "modified": datetime.fromtimestamp(
                            file_path.stat().st_mtime
                        ).strftime("%Y-%m-%d %H:%M:%S"),
                        "type": get_file_type(file_path.name)
                    })
        
        # Sort by modified date (newest first)
        files.sort(key=lambda x: x['modified'], reverse=True)
        
        return {
            "success": True,
            "files": files,
            "count": len(files),
            "upload_dir": str(UPLOADS_DIR)
        }
        
    except Exception as e:
        print(f"❌ List uploads error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def get_file_type(filename: str) -> str:
    """Helper to determine file type from filename"""
    if "compliance_check" in filename:
        return "compliance_export"
    elif "brand_image" in filename:
        return "brand_image"
    elif "brand_guidelines" in filename:
        return "brand_guidelines"
    elif "copyright_check" in filename:
        return "copyright_check"
    else:
        return "unknown"


@router.post("/copyright-check")
async def copyright_check(file: UploadFile = File(...)):
    """
    Handle copyright check - receives exported PNG, uploads to ImgBB,
    performs reverse image search, and analyzes with Gemini AI
    """
    try:
        # Generate unique filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"copyright_check_{timestamp}.png"
        file_path = UPLOADS_DIR / filename
        
        # Read file content
        file_content = await file.read()
        file_size_mb = len(file_content) / (1024 * 1024)
        
        # Save the exported PNG
        with open(file_path, "wb") as buffer:
            buffer.write(file_content)
        
        print(f"✅ Copyright check PNG saved: {filename}")
        print(f"📊 File size: {file_size_mb:.2f} MB")
        
        # Step 1: Upload to ImgBB
        image_url = upload_to_imgbb(str(file_path))
        
        if not image_url:
            raise HTTPException(status_code=500, detail="Failed to upload image to ImgBB")
        
        # Step 2: Perform reverse image search
        print("🔍 Running reverse image search...")
        copyright_data = check_copyright_sources(image_url)
        
        if copyright_data is None:
            raise HTTPException(status_code=500, detail="Reverse image search failed")
        
        # Step 3: Analyze with Gemini AI
        print("🤖 Analyzing copyright with Gemini AI...")
        ai_analysis = analyze_copyright_with_ai(copyright_data)
        
        if not ai_analysis:
            ai_analysis = "AI analysis unavailable"
        
        # Determine status from both copyright count AND AI analysis
        copyright_count = len(copyright_data['copyright_results'])
        total_results = copyright_data['total_results']
        
        # Parse AI analysis for status
        ai_status = "unknown"
        if ai_analysis:
            ai_upper = ai_analysis.upper()
            if "COPYRIGHT STATUS: COPYRIGHTED" in ai_upper or "STATUS: COPYRIGHTED" in ai_upper:
                ai_status = "copyrighted"
            elif "COPYRIGHT STATUS: RISKY" in ai_upper or "STATUS: RISKY" in ai_upper:
                ai_status = "risky"
            elif "COPYRIGHT STATUS: SAFE" in ai_upper or "STATUS: SAFE" in ai_upper:
                ai_status = "safe"
        
        # Determine final status
        if copyright_count >= 5 or ai_status == "copyrighted":
            status = "copyrighted"
            message = f"❌ COPYRIGHTED - Found {copyright_count} stock/copyright sources"
            emoji = "❌"
        elif copyright_count > 0 or ai_status == "risky":
            status = "risky"
            message = f"⚠️ COPYRIGHT RISK - Found {copyright_count} stock/copyright sources"
            emoji = "⚠️"
        elif total_results > 0:
            status = "safe"
            message = "✅ SAFE - No obvious copyright sources detected"
            emoji = "✅"
        else:
            status = "unknown"
            message = "❓ UNKNOWN - No results found"
            emoji = "❓"
        
        print(f"{emoji} Copyright Status: {status.upper()}")
        print(f"📊 Copyright count: {copyright_count} | Total results: {total_results}")
        print(f"🤖 AI Status: {ai_status}")
        
        copyright_result = {
            "status": status,
            "message": message,
            "emoji": emoji,
            "ai_analysis": ai_analysis,
            "copyright_count": copyright_count,
            "total_results": total_results,
            "copyright_sources": copyright_data['copyright_results'],
            "details": {
                "filename": filename,
                "path": str(file_path),
                "size_mb": round(file_size_mb, 2),
                "timestamp": timestamp,
                "imgbb_url": image_url
            }
        }
        
        return {
            "success": True,
            "copyright": copyright_result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Copyright check error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
