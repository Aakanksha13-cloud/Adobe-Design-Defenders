from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from compliance import router as compliance_router
from pydantic import BaseModel
import requests
import httpx
import json
import secrets
import os
import tempfile
import re
import time
import base64
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from dataclasses import dataclass
from google import genai
from google.genai import types

# ============================================
# IMAGE ANALYSIS CLASSES
# ============================================

@dataclass
class PostData:
    """Data structure for a social media post"""
    image_path: str
    likes: int
    
    def to_dict(self):
        return {"image_path": self.image_path, "likes": self.likes}


class RateLimiter:
    """Advanced rate limiter with sliding window"""
    
    def __init__(self, max_requests_per_minute: int = 5, min_delay_seconds: float = 12.0):
        self.max_requests = max_requests_per_minute
        self.min_delay = min_delay_seconds
        self.request_times = []
        self.last_request_time = None
    
    def wait_if_needed(self):
        """Wait if we're approaching rate limit"""
        now = datetime.now()
        
        if self.last_request_time:
            time_since_last = (now - self.last_request_time).total_seconds()
            if time_since_last < self.min_delay:
                wait_time = self.min_delay - time_since_last
                print(f"  [*] Minimum delay: waiting {wait_time:.1f} seconds...")
                time.sleep(wait_time)
                now = datetime.now()
        
        self.request_times = [t for t in self.request_times 
                             if now - t < timedelta(minutes=1)]
        
        if len(self.request_times) >= self.max_requests:
            oldest = self.request_times[0]
            wait_time = 61 - (now - oldest).total_seconds()
            if wait_time > 0:
                print(f"  [*] Rate limit protection: waiting {wait_time:.1f} seconds...")
                time.sleep(wait_time)
                self.request_times = []
        
        self.request_times.append(datetime.now())
        self.last_request_time = datetime.now()


class ImageFeatureAnalyzer:
    """Analyzes images using Gemini API to find common visual features"""
    
    def __init__(self, api_key: str, max_retries: int = 5, base_delay: int = 20):
        self.client = genai.Client(api_key=api_key)
        self.model_id = 'gemini-3-flash-preview'
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.rate_limiter = RateLimiter(max_requests_per_minute=5, min_delay_seconds=12.0)
        
    def _get_mime_type(self, image_path: str) -> str:
        ext = Path(image_path).suffix.lower()
        mime_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp'
        }
        return mime_types.get(ext, 'image/jpeg')
    
    def read_image_file(self, image_path: str) -> types.Part:
        with open(image_path, 'rb') as f:
            image_data = f.read()
        
        return types.Part.from_bytes(
            data=image_data,
            mime_type=self._get_mime_type(image_path)
        )
    
    def _retry_with_backoff(self, func, *args, **kwargs):
        for attempt in range(self.max_retries):
            try:
                self.rate_limiter.wait_if_needed()
                result = func(*args, **kwargs)
                return result
                
            except Exception as e:
                error_str = str(e).lower()
                
                is_rate_limit = any(err in error_str for err in [
                    '429', 'resource_exhausted', 'quota', 'rate limit',
                    'too many requests', 'limit exceeded'
                ])
                
                if is_rate_limit:
                    if attempt < self.max_retries - 1:
                        delay = self.base_delay * (3 ** attempt)
                        print(f"  [!] Rate limit hit. Retry {attempt + 1}/{self.max_retries} after {delay}s...")
                        time.sleep(delay)
                    else:
                        print(f"  [X] Max retries reached after rate limiting.")
                        return None
                else:
                    print(f"  [X] Error: {str(e)[:150]}")
                    return None
        
        return None
    
    def analyze_single_image(self, image_path: str) -> Dict:
        prompt = """You are a visual design analysis expert for social media content.

Analyze this image and extract the graphical and visual features present in it.
Focus only on what is visually present in the image.

Extract features related to:
* Visual Style (overall aesthetic and design feel)
* Color Palette (dominant colors, contrast, brightness, saturation)
* Composition (layout structure, balance, focal areas, spacing)
* Subject Matter (types of visual elements shown)
* Lighting (brightness, shadows, natural or artificial lighting)
* Photography / Design Techniques (illustration, flat design, depth, gradients, filters)
* Text and Graphics Usage (presence, density, typography style, overlays)
* Emotion / Mood (general tone conveyed by the visuals)
* Brand or Stylistic Elements (recurring visual patterns or signatures)

Return the result in strict JSON format with these exact keys:
{
    "visual_style": [],
    "color_palette": [],
    "composition": [],
    "subject_matter": [],
    "lighting": [],
    "photography_technique": [],
    "text_graphics": [],
    "emotion_mood": [],
    "brand_elements": []
}

For each key, provide a list of short, clear descriptive phrases about the visual features present.
Use only JSON format. Do not include any explanations outside the JSON."""
        
        def _make_request():
            image_part = self.read_image_file(image_path)
            
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=[prompt, image_part]
            )
            
            response_text = response.text.strip()
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            return json.loads(response_text.strip())
        
        return self._retry_with_backoff(_make_request)
    
    def categorize_posts_by_popularity(self, posts: List[PostData], 
                                       top_percentage: float = 0.3) -> Tuple[List[PostData], List[PostData]]:
        sorted_posts = sorted(posts, key=lambda x: x.likes, reverse=True)
        split_index = max(1, int(len(sorted_posts) * top_percentage))
        
        popular_posts = sorted_posts[:split_index]
        less_popular_posts = sorted_posts[split_index:]
        
        return popular_posts, less_popular_posts
    
    def analyze_posts_batch(self, posts: List[PostData]) -> List[Dict]:
        results = []
        
        for i, post in enumerate(posts):
            print(f"\n[{i+1}/{len(posts)}] Analyzing: {post.image_path} ({post.likes} likes)")
            
            features = self.analyze_single_image(post.image_path)
            
            if features:
                results.append({
                    'post': post.to_dict(),
                    'features': features
                })
                print(f"  [+] Analysis complete")
            else:
                print(f"  [!] Skipped due to errors")
        
        return results
    
    def find_common_features(self, analyzed_posts: List[Dict], threshold: float = 0.3) -> Dict:
        if not analyzed_posts:
            return {}
        
        feature_frequency = {}
        total_posts = len(analyzed_posts)
        
        for post_data in analyzed_posts:
            features = post_data['features']
            
            for category, items in features.items():
                if category not in feature_frequency:
                    feature_frequency[category] = {}
                
                for item in items:
                    item_lower = str(item).lower().strip()
                    if item_lower not in feature_frequency[category]:
                        feature_frequency[category][item_lower] = 0
                    feature_frequency[category][item_lower] += 1
        
        common_features = {}
        
        for category, items in feature_frequency.items():
            common_features[category] = []
            
            for item, count in items.items():
                percentage = count / total_posts
                if percentage >= threshold:
                    common_features[category].append({
                        'feature': item,
                        'frequency': count,
                        'percentage': round(percentage * 100, 1)
                    })
            
            common_features[category].sort(key=lambda x: x['frequency'], reverse=True)
        
        return common_features
    
    def generate_insights_report(self, popular_features: Dict, 
                                 less_popular_features: Dict) -> str:
        prompt = f"""You are a social media visual strategy expert.

Based on the following feature analysis of social media posts:

HIGH-PERFORMING POSTS FEATURES:
{json.dumps(popular_features, indent=2)}

LOWER-PERFORMING POSTS FEATURES:
{json.dumps(less_popular_features, indent=2)}

Provide a comprehensive analysis that:
1. Identifies the TOP 5-7 most distinctive visual features that appear in high-performing posts
2. Highlights key visual differences between high-performing and lower-performing posts
3. Provides actionable recommendations for creating visually engaging content
4. Explains why certain visual elements may resonate better with audiences

Format your response as a structured report with clear sections and specific insights."""

        def _make_request():
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt
            )
            return response.text
        
        result = self._retry_with_backoff(_make_request)
        return result if result else "Unable to generate insights due to API limitations."
    
    def run_complete_analysis(self, posts: List[PostData], 
                             top_percentage: float = 0.3,
                             feature_threshold: float = 0.3) -> Dict:
        print(f"\n{'='*70}")
        print("STARTING IMAGE ANALYSIS")
        print(f"{'='*70}\n")
        
        print(f"Total posts: {len(posts)}")
        popular_posts, less_popular_posts = self.categorize_posts_by_popularity(
            posts, top_percentage
        )
        print(f"Popular posts (top {int(top_percentage*100)}%): {len(popular_posts)}")
        print(f"Less popular posts: {len(less_popular_posts)}")
        
        print(f"\n{'='*70}")
        print("ANALYZING HIGH-PERFORMING POSTS")
        print(f"{'='*70}")
        popular_analyzed = self.analyze_posts_batch(popular_posts)
        
        print(f"\n{'='*70}")
        print("ANALYZING LOWER-PERFORMING POSTS")
        print(f"{'='*70}")
        less_popular_analyzed = self.analyze_posts_batch(less_popular_posts)
        
        print(f"\n{'='*70}")
        print("EXTRACTING COMMON FEATURES")
        print(f"{'='*70}\n")
        popular_common = self.find_common_features(popular_analyzed, threshold=feature_threshold)
        less_popular_common = self.find_common_features(less_popular_analyzed, threshold=feature_threshold)
        
        print(f"\n{'='*70}")
        print("GENERATING INSIGHTS REPORT")
        print(f"{'='*70}\n")
        insights = self.generate_insights_report(popular_common, less_popular_common)
        
        return {
            'popular_posts': {
                'count': len(popular_posts),
                'analyzed': len(popular_analyzed),
                'posts': [p.to_dict() for p in popular_posts],
                'common_features': popular_common
            },
            'less_popular_posts': {
                'count': len(less_popular_posts),
                'analyzed': len(less_popular_analyzed),
                'posts': [p.to_dict() for p in less_popular_posts],
                'common_features': less_popular_common
            },
            'insights': insights,
            'metadata': {
                'top_percentage': top_percentage,
                'feature_threshold': feature_threshold,
                'total_posts': len(posts),
                'timestamp': datetime.now().isoformat()
            }
        }


app = FastAPI(
    title="Content Publisher Backend",
    description="Backend API for Adobe Express Content Publisher Add-on",
    version="1.0.0"
)

# CORS - Allow your add-on to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Include compliance router
app.include_router(compliance_router, prefix="/api/compliance", tags=["compliance"])

# Mount uploads folder to serve generated images
uploads_path = Path(__file__).parent.parent / "uploads"
app.mount("/uploads", StaticFiles(directory=str(uploads_path)), name="uploads")

# =====================
# AI CHATBOT FOR DESIGN
# =====================

GEMINI_API_KEY = "AIzaSyAZSxDDRAnU6qs5imoyfyo1yWIyepqxpaM"

SYSTEM_PROMPT = """You are an Adobe Express add-on code generator. You MUST follow these CRITICAL RULES when generating code.js.

## IMMUTABLE STRUCTURE (NEVER CHANGE THESE):
1. Line 1: `import addOnSandboxSdk from "add-on-sdk-document-sandbox";` - MUST BE EXACTLY THIS, NOT "add-on-sdk-sandbox"!
2. Line 2: `import { editor, colorUtils } from "express-document-sdk";` - EXACTLY as shown
3. Line 4: `const { runtime } = addOnSandboxSdk.instance;` - EXACTLY as shown
3. Line 6: `function start() {` - Function name MUST be "start"
4. Line 8: `const sandboxApi = {` - Variable name MUST be "sandboxApi"
5. Line 9: `createShape: () => {` - Function name MUST be "createShape" (this is called from index.js)
6. LAST TWO LINES inside createShape function MUST BE:
   ```
   const insertionParent = editor.context.insertionParent;
   insertionParent.children.append(SHAPE_VARIABLE);
   ```
7. Line before end of start(): `runtime.exposeApi(sandboxApi);` - EXACTLY as shown
8. FINAL LINE: `start();` - EXACTLY as shown

## MODIFIABLE SECTION (ONLY CHANGE THIS):
Between the start of createShape() and the last two lines, you can:
- Create ANY shape (ellipse, rectangle, path, text, etc.)
- Set ANY dimensions, colors, positions, strokes, fills
- Use ANY Adobe Express Document SDK functions

## CRITICAL RULES:
- NEVER change function names: start, createShape, sandboxApi
- NEVER remove runtime lines
- NEVER remove start() call at end
- ALWAYS end createShape with insertionParent lines
- ONLY modify shape creation code
- ALWAYS wrap code in ```javascript code block
- ALWAYS use "add-on-sdk-document-sandbox" NOT "add-on-sdk-sandbox"!

## EXAMPLE OUTPUT (draw a circle):

```javascript
import addOnSandboxSdk from "add-on-sdk-document-sandbox";
import { editor, colorUtils } from "express-document-sdk";

const { runtime } = addOnSandboxSdk.instance;

function start() {
    const sandboxApi = {
        createShape: () => {
            const circle = editor.createEllipse();
            circle.rx = 100;
            circle.ry = 100;
            circle.translation = { x: 200, y: 200 };
            const fillColor = colorUtils.fromHex("#667eea");
            circle.fill = editor.makeColorFill(fillColor);

            const insertionParent = editor.context.insertionParent;
            insertionParent.children.append(circle);
        }
    };
    runtime.exposeApi(sandboxApi);
}
start();
```

REMEMBER: ALWAYS use "add-on-sdk-document-sandbox" in the import!
"""

class DesignRequest(BaseModel):
    prompt: str

def extract_code_from_response(text):
    """Extract code blocks from Gemini's response."""
    if not text:
        return None
    
    patterns = [
        r'```(?:javascript|js|tsx|jsx|typescript|ts)\n(.*?)```',
        r'```\n(.*?)```',
    ]
    
    code_blocks = []
    for pattern in patterns:
        matches = re.findall(pattern, text, re.DOTALL)
        code_blocks.extend(matches)
    
    if code_blocks:
        return '\n\n'.join(code_blocks)
    return None

@app.post("/api/generate-design")
async def generate_design(request: DesignRequest):
    """Generate Adobe Express shape code from natural language prompt"""
    try:
        # Initialize Gemini
        gemini = genai.Client(api_key=GEMINI_API_KEY)
        model = "gemini-3-flash-preview"
        
        # Build prompt
        full_prompt = f"{SYSTEM_PROMPT}\n\nUser Request: {request.prompt}"
        
        # Generate code
        response = gemini.models.generate_content(
            model=model,
            contents=[
                types.Content(
                    role="user",
                    parts=[types.Part(text=full_prompt)]
                )
            ],
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
            ),
        )
        
        # Extract code
        response_text = response.text
        if not response_text:
            raise HTTPException(status_code=500, detail="No response from AI")
        
        code = extract_code_from_response(response_text)
        if not code:
            raise HTTPException(status_code=500, detail="No code block found in AI response")
        
        # Save to src/code.js
        code_path = Path(__file__).parent.parent / "src" / "code.js"
        with open(code_path, 'w', encoding='utf-8') as f:
            f.write(code)
        
        return {
            "success": True,
            "message": "Design code generated and saved to src/code.js",
            "code": code,
            "prompt": request.prompt
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =====================
# LINKEDIN CONFIG
# =====================

CONFIG_FILE = Path(__file__).parent / "config.json"

def load_config():
    """Load configuration from config.json"""
    if not CONFIG_FILE.exists():
        return {}
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(config_data):
    """Save configuration to config.json"""
    with open(CONFIG_FILE, "w") as f:
        json.dump(config_data, indent=2, fp=f)

def get_access_token():
    """Get access token from config.json"""
    config = load_config()
    return config.get("access_token")

# =====================
# AUTHENTICATION ROUTES
# =====================

@app.get("/auth/login")
async def auth_login():
    """
    Start LinkedIn OAuth flow
    Redirects user to LinkedIn authorization page
    """
    config = load_config()
    
    if not config.get("client_id"):
        raise HTTPException(status_code=400, detail="LinkedIn client_id not configured in config.json")
    
    CLIENT_ID = config["client_id"]
    REDIRECT_URI = config["redirect_uri"]
    
    # Generate random state for security
    state = secrets.token_urlsafe(16)
    
    # Build LinkedIn authorization URL with required scopes
    auth_url = (
        f"https://www.linkedin.com/oauth/v2/authorization?"
        f"response_type=code&"
        f"client_id={CLIENT_ID}&"
        f"redirect_uri={REDIRECT_URI}&"
        f"state={state}&"
        f"scope=openid%20profile%20email%20w_member_social"
    )
    
    return RedirectResponse(url=auth_url)

@app.get("/callback")
async def callback_redirect(code: str, state: str):
    """
    Redirect route for LinkedIn compatibility
    LinkedIn redirects here, we forward to /auth/callback
    """
    return RedirectResponse(url=f"/auth/callback?code={code}&state={state}")

@app.get("/auth/callback")
async def auth_callback(code: str, state: str):
    """
    Handle LinkedIn OAuth callback
    Exchanges authorization code for access token and saves to config.json
    """
    config = load_config()
    
    CLIENT_ID = config["client_id"]
    CLIENT_SECRET = config["client_secret"]
    REDIRECT_URI = config["redirect_uri"]
    
    # Exchange authorization code for access token
    token_url = "https://www.linkedin.com/oauth/v2/accessToken"
    
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }
    
    try:
        response = requests.post(token_url, data=data)
        response.raise_for_status()
        
        token_data = response.json()
        access_token = token_data["access_token"]
        expires_in = token_data.get("expires_in", "Unknown")
        
        # Save access token to config.json
        config["access_token"] = access_token
        save_config(config)
        
        # Verify token by getting user info
        headers = {"Authorization": f"Bearer {access_token}"}
        user_response = requests.get("https://api.linkedin.com/v2/userinfo", headers=headers)
        user_data = user_response.json()
        
        # Return HTML success page
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>LinkedIn Authentication Successful</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #0077B5 0%, #005885 100%);
                }}
                .container {{
                    background: white;
                    padding: 40px;
                    border-radius: 16px;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.3);
                    text-align: center;
                    max-width: 400px;
                }}
                .icon {{
                    font-size: 64px;
                    margin-bottom: 20px;
                }}
                h1 {{
                    color: #0077B5;
                    margin: 0 0 10px 0;
                    font-size: 24px;
                }}
                p {{
                    color: #666;
                    margin: 10px 0;
                    line-height: 1.6;
                }}
                .user-info {{
                    background: #f5f5f5;
                    padding: 15px;
                    border-radius: 8px;
                    margin: 20px 0;
                }}
                .user-name {{
                    font-weight: 600;
                    color: #333;
                    font-size: 16px;
                }}
                .close-btn {{
                    background: #0077B5;
                    color: white;
                    border: none;
                    padding: 12px 30px;
                    border-radius: 8px;
                    font-size: 14px;
                    font-weight: 600;
                    cursor: pointer;
                    margin-top: 20px;
                }}
                .close-btn:hover {{
                    background: #005885;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="icon">✅</div>
                <h1>LinkedIn Connected!</h1>
                <p>Your LinkedIn account has been successfully authenticated.</p>
                <div class="user-info">
                    <div class="user-name">{user_data.get('name', 'User')}</div>
                    <div style="color: #666; font-size: 14px; margin-top: 5px;">{user_data.get('email', '')}</div>
                </div>
                <p style="font-size: 14px;">You can now close this window and return to the add-on to post to LinkedIn.</p>
                <button class="close-btn" onclick="window.close()">Close Window</button>
            </div>
        </body>
        </html>
        """
        
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Authentication failed: {str(e)}")

# =====================
# LINKEDIN POST ROUTE
# =====================

@app.post("/post")
async def post_linkedin(
    text: str = Form(...),
    image: UploadFile = File(...)
):
    """
    Post to LinkedIn with text and image
    Requires: Authentication must be completed first (access token in config.json)
    
    Args:
        text: Text content for the post
        image: Image file to upload
    """
    # Get access token from config
    access_token = get_access_token()
    
    if not access_token:
        raise HTTPException(
            status_code=401, 
            detail="Not authenticated. Please visit /auth/login first"
        )
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
        'X-Restli-Protocol-Version': '2.0.0'
    }
    
    try:
        # Step 1: Get user ID
        user_response = requests.get("https://api.linkedin.com/v2/userinfo", headers=headers)
        user_response.raise_for_status()
        user_id = user_response.json().get('sub')
        
        if not user_id:
            raise HTTPException(status_code=400, detail="Failed to get user ID")
        
        # Step 2: Save uploaded image temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(image.filename)[1]) as temp_file:
            content = await image.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # Step 3: Register upload with LinkedIn
            register_url = "https://api.linkedin.com/v2/assets?action=registerUpload"
            
            register_data = {
                "registerUploadRequest": {
                    "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                    "owner": f"urn:li:person:{user_id}",
                    "serviceRelationships": [
                        {
                            "relationshipType": "OWNER",
                            "identifier": "urn:li:userGeneratedContent"
                        }
                    ]
                }
            }
            
            register_response = requests.post(register_url, json=register_data, headers=headers)
            register_response.raise_for_status()
            
            register_result = register_response.json()
            upload_url = register_result['value']['uploadMechanism']['com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest']['uploadUrl']
            asset_urn = register_result['value']['asset']
            
            # Step 4: Upload image to LinkedIn
            with open(temp_file_path, 'rb') as image_file:
                image_data = image_file.read()
            
            upload_headers = {'Authorization': f'Bearer {access_token}'}
            upload_response = requests.put(upload_url, data=image_data, headers=upload_headers)
            upload_response.raise_for_status()
            
            # Step 5: Create LinkedIn post
            post_url = "https://api.linkedin.com/v2/ugcPosts"
            
            post_data = {
                "author": f"urn:li:person:{user_id}",
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {
                            "text": text
                        },
                        "shareMediaCategory": "IMAGE",
                        "media": [
                            {
                                "status": "READY",
                                "media": asset_urn
                            }
                        ]
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                }
            }
            
            post_response = requests.post(post_url, json=post_data, headers=headers)
            post_response.raise_for_status()
            
            result = post_response.json()
            
            return {
                "success": True,
                "message": "Posted to LinkedIn successfully!",
                "post_id": result.get('id', 'N/A')
            }
        
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
    
    except requests.exceptions.HTTPError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"LinkedIn API error: {e.response.text}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# =====================
# UTILITY ROUTES
# =====================

@app.get("/status")
async def status():
    """Check authentication status"""
    access_token = get_access_token()
    
    if not access_token:
        return {
            "authenticated": False,
            "message": "No access token found. Please visit /auth/login"
        }
    
    # Verify token
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        response = requests.get("https://api.linkedin.com/v2/userinfo", headers=headers)
        response.raise_for_status()
        user_data = response.json()
        
        return {
            "authenticated": True,
            "user": {
                "name": user_data.get("name"),
                "email": user_data.get("email")
            }
        }
    except:
        return {
            "authenticated": False,
            "message": "Access token invalid or expired. Please visit /auth/login"
        }

# =====================
# JIRA INTEGRATION
# =====================

# Load Jira config
JIRA_CONFIG_FILE = Path(__file__).parent / "jira_config.json"

def load_jira_config():
    """Load Jira configuration from jira_config.json"""
    try:
        with open(JIRA_CONFIG_FILE, 'r') as f:
            config = json.load(f)
        return config
    except Exception as e:
        print(f"⚠️ Warning: Could not load jira_config.json: {e}")
        return {
            "jira_url": "https://your-domain.atlassian.net",
            "jira_email": "your-email@example.com",
            "jira_api_token": "your-api-token-here",
            "jira_project_key": "PROJ"
        }

jira_config = load_jira_config()
JIRA_URL = jira_config.get("jira_url")
JIRA_EMAIL = jira_config.get("jira_email")
JIRA_API_TOKEN = jira_config.get("jira_api_token")
JIRA_PROJECT_KEY = jira_config.get("jira_project_key")

class TeamNotificationRequest(BaseModel):
    text: str

@app.get("/test-jira")
async def test_jira_connection():
    """Test Jira connection"""
    try:
        print(f"\n🔍 Testing Jira connection...")
        print(f"   URL: {JIRA_URL}")
        print(f"   Email: {JIRA_EMAIL}")
        print(f"   Project: {JIRA_PROJECT_KEY}")
        
        # Create basic auth
        auth_str = f"{JIRA_EMAIL}:{JIRA_API_TOKEN}"
        auth_bytes = auth_str.encode('ascii')
        auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
        
        headers = {
            "Accept": "application/json",
            "Authorization": f"Basic {auth_b64}"
        }
        
        # Test connection with myself endpoint
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{JIRA_URL}/rest/api/3/myself",
                headers=headers,
                timeout=10.0
            )
            
            if response.status_code == 200:
                user_data = response.json()
                return {
                    "status": "success",
                    "message": "Jira connection successful!",
                    "user": user_data.get("displayName"),
                    "email": user_data.get("emailAddress")
                }
            else:
                return {
                    "status": "error",
                    "message": f"Jira connection failed: {response.status_code}",
                    "detail": response.text
                }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Connection error: {str(e)}"
        }

@app.post("/notify")
async def send_team_notification(request: TeamNotificationRequest):
    """
    Send team notification to Jira
    Creates a new issue in Jira project
    """
    try:
        print(f"\n📢 JIRA NOTIFICATION:")
        print(f"   Message: {request.text}")
        print(f"   Timestamp: {datetime.now().isoformat()}")
        print(f"   Jira URL: {JIRA_URL}")
        print(f"   Project Key: {JIRA_PROJECT_KEY}")
        print(f"   Email: {JIRA_EMAIL}")
        
        # Prepare Jira API request
        # Create basic auth
        auth_str = f"{JIRA_EMAIL}:{JIRA_API_TOKEN}"
        auth_bytes = auth_str.encode('ascii')
        auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
        
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Basic {auth_b64}"
        }
        
        # Create issue payload
        payload = {
            "fields": {
                "project": {
                    "key": JIRA_PROJECT_KEY
                },
                "summary": f"Team Notification: {request.text[:100]}",
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "text",
                                    "text": request.text
                                }
                            ]
                        }
                    ]
                },
                "issuetype": {
                    "name": "Task"  # Can be Task, Story, Bug, etc.
                }
            }
        }
        
        # Send to Jira
        print(f"🔄 Sending to Jira: {JIRA_URL}/rest/api/3/issue")
        print(f"📦 Payload: {json.dumps(payload, indent=2)}")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{JIRA_URL}/rest/api/3/issue",
                headers=headers,
                json=payload,
                timeout=30.0
            )
            
            print(f"📥 Response Status: {response.status_code}")
            print(f"📥 Response Body: {response.text[:500]}")
            
            if response.status_code in [200, 201]:
                result = response.json()
                issue_key = result.get("key", "Unknown")
                issue_url = f"{JIRA_URL}/browse/{issue_key}"
                
                print(f"✅ Jira issue created: {issue_key}")
                print(f"🔗 URL: {issue_url}")
                
                return {
                    "status": "success",
                    "message": f"Jira issue created: {issue_key}",
                    "notification": {
                        "text": request.text,
                        "timestamp": datetime.now().isoformat(),
                        "jira_issue_key": issue_key,
                        "jira_url": issue_url
                    }
                }
            else:
                try:
                    error_json = response.json()
                    error_detail = json.dumps(error_json, indent=2)
                except:
                    error_detail = response.text
                    
                print(f"❌ Jira API Error: {response.status_code}")
                print(f"   Response: {error_detail}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Jira API error ({response.status_code}): {error_detail}"
                )
                
    except httpx.RequestError as e:
        print(f"❌ Connection error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to connect to Jira: {str(e)}"
        )
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to send notification: {str(e)}")

# =====================
# SLACK INTEGRATION
# =====================

# Slack credentials
SLACK_TOKEN = "YOUR_SLACK_TOKEN_HERE"
SLACK_CHANNEL = "YOUR_SLACK_CHANNEL_HERE"
SLACK_API_URL = "https://slack.com/api/chat.postMessage"

class SlackMessageRequest(BaseModel):
    message: str

@app.post("/api/slack/send")
async def send_slack_message(request: SlackMessageRequest):
    """
    Send a message to Slack channel
    """
    headers = {
        "Authorization": f"Bearer {SLACK_TOKEN}",
        "Content-Type": "application/json; charset=utf-8"
    }
    
    payload = {
        "channel": SLACK_CHANNEL,
        "text": request.message
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                SLACK_API_URL,
                headers=headers,
                json=payload
            )
            
            response_data = response.json()
            
            if response.status_code == 200 and response_data.get("ok"):
                return {
                    "status": "success",
                    "message": "Message sent to Slack successfully!",
                    "slack_response": response_data
                }
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Slack API error: {response_data.get('error', 'Unknown error')}"
                )
                
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error connecting to Slack: {str(e)}"
        )

# =====================
# AI IMAGE GENERATOR
# =====================

@app.post("/api/generate-image")
async def generate_image_from_text(user_request: str = Form(...)):
    """
    Generate AI design image from user text request
    Uses analyze.json and brand guidelines from uploads folder
    """
    try:
        from image_generator import generate_design_from_text
        
        print(f"\n🎨 Generating image for: {user_request}")
        result = generate_design_from_text(user_request)
        
        return {
            "success": True,
            "message": result["message"],
            "image_filename": result["image_filename"],
            "image_path": result["image_path"],
            "generated_prompt": result["generated_prompt"],
            "design_summary": result["design_brief_summary"]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Image generation error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Image generation failed: {str(e)}")


# =====================
# ANALYZE PAST POSTS BY AI
# =====================

@app.post("/api/analyze-past-posts")
async def analyze_past_posts():
    """
    Analyzes past posts using CSV data from uploads/brand_images folder
    CSV should have columns: image, likes
    Calls the image analysis API and returns results
    """
    try:
        import pandas as pd
        
        # Define paths
        brand_images_dir = Path(__file__).parent.parent / "uploads" / "brand_images"
        
        if not brand_images_dir.exists():
            raise HTTPException(status_code=404, detail="Brand images folder not found")
        
        # Find CSV files in brand_images folder
        csv_files = list(brand_images_dir.glob("*.csv"))
        
        if not csv_files:
            raise HTTPException(
                status_code=404, 
                detail="No CSV file found in uploads/brand_images. Please upload a CSV with 'image' and 'likes' columns."
            )
        
        # Use the most recent CSV file
        csv_file = max(csv_files, key=lambda p: p.stat().st_mtime)
        print(f"📊 Using CSV file: {csv_file.name}")
        
        # Read CSV with pandas
        try:
            df = pd.read_csv(csv_file)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to read CSV: {str(e)}")
        
        # Validate CSV columns
        if 'image' not in df.columns or 'likes' not in df.columns:
            raise HTTPException(
                status_code=400, 
                detail=f"CSV must have 'image' and 'likes' columns. Found: {list(df.columns)}"
            )
        
        # Get image names and likes
        posts_data = []
        missing_images = []
        
        for _, row in df.iterrows():
            image_name = str(row['image']).strip()
            likes = int(row['likes'])
            
            # Check if image exists in brand_images folder
            image_path = brand_images_dir / image_name
            
            if image_path.exists():
                posts_data.append({
                    'path': str(image_path),
                    'likes': likes,
                    'name': image_name
                })
            else:
                missing_images.append(image_name)
        
        if not posts_data:
            raise HTTPException(
                status_code=404, 
                detail=f"No images found in brand_images folder. Missing: {missing_images}"
            )
        
        if missing_images:
            print(f"⚠️  Warning: {len(missing_images)} images not found: {missing_images[:5]}...")
        
        print(f"✅ Found {len(posts_data)} images to analyze")
        
        # Create PostData objects for analysis
        posts = [PostData(image_path=post['path'], likes=post['likes']) for post in posts_data]
        
        # Initialize analyzer with Gemini API key
        analyzer = ImageFeatureAnalyzer(api_key=GEMINI_API_KEY, max_retries=5, base_delay=20)
        
        # Run analysis directly
        print(f"🤖 Starting AI analysis of {len(posts)} posts...")
        result = analyzer.run_complete_analysis(
            posts,
            top_percentage=0.3,
            feature_threshold=0.3
        )
        
        # Save results to analyze.json
        output_file = Path(__file__).parent.parent / "uploads" / "analyze.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Analysis complete! Results saved to {output_file.name}")
        
        return {
            "success": True,
            "message": "Past posts analyzed successfully",
            "details": {
                "csv_used": csv_file.name,
                "total_posts_in_csv": len(df),
                "posts_analyzed": result['popular_posts']['analyzed'] + result['less_popular_posts']['analyzed'],
                "missing_images": len(missing_images),
                "results_saved_to": "uploads/analyze.json"
            },
            "results": result
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error analyzing past posts: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.get("/")
def read_root():
    return {
        "message": "Content Publisher Backend API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/api/health",
            "compliance_check": "/api/compliance/compliance-check",
            "brand_image": "/api/compliance/brand-image",
            "brand_guidelines": "/api/compliance/brand-guidelines",
            "list_uploads": "/api/compliance/uploads/list",
            "linkedin_login": "/auth/login",
            "linkedin_status": "/status",
            "linkedin_post": "/post",
            "slack_send": "/api/slack/send",
            "team_notify": "/notify",
            "analyze_past_posts": "/api/analyze-past-posts",
            "generate_image": "/api/generate-image"
        }
    }

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "Adobe Express Add-on Backend",
        "modules": ["compliance", "linkedin"]
    }