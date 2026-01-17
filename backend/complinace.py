import os
from google import genai
from google.genai import types

class BrandComplianceChecker:
    def __init__(self, api_key=None):
        """Initialize the Brand Compliance Checker"""
        if api_key:
            os.environ['GOOGLE_API_KEY'] = api_key
        self.client = genai.Client()
        self.brand_guidelines = ""
        
    def load_brand_guidelines(self, txt_or_pdf_path):
        """Load brand guidelines from text file or PDF"""
        try:
            # For simplicity, using .txt files (you can add PyPDF2 for PDF support)
            with open(txt_or_pdf_path, 'r', encoding='utf-8') as file:
                self.brand_guidelines = file.read()
                print(f"✓ Successfully loaded brand guidelines from {txt_or_pdf_path}")
                print(f"✓ Guidelines length: {len(self.brand_guidelines)} characters\n")
                return self.brand_guidelines
        except Exception as e:
            print(f"✗ Error reading file: {e}")
            return None
    
    def check_compliance(self, image_path, detailed=True):
        """
        Check if image complies with brand guidelines
        
        Args:
            image_path: Path to image file
            detailed: If True, provides detailed analysis
        """
        if not self.brand_guidelines:
            raise ValueError("Brand guidelines not loaded. Call load_brand_guidelines() first.")
        
        try:
            # Read image
            with open(image_path, 'rb') as f:
                image_bytes = f.read()
            
            # Determine MIME type
            mime_type = self._get_mime_type(image_path)
            
            # Create compliance check prompt
            prompt = self._create_compliance_prompt(detailed)
            
            print("🔍 Analyzing image against brand guidelines...")
            
            # Generate analysis
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
    
    def _get_mime_type(self, image_path):
        """Determine MIME type from file extension"""
        ext = image_path.lower().split('.')[-1]
        mime_types = {
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'gif': 'image/gif',
            'webp': 'image/webp'
        }
        return mime_types.get(ext, 'image/jpeg')
    
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
        # Determine compliance from the status line
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
    
    def print_result(self, result):
        """Pretty print the compliance check result"""
        print("\n" + "="*70)
        if result.get("error"):
            print(f"❌ ERROR: {result['error']}")
        else:
            if result['compliant']:
                print("✅ COMPLIANCE CHECK PASSED")
            else:
                print("❌ COMPLIANCE CHECK FAILED")
            print("="*70)
            print(result['raw_analysis'])
        print("="*70 + "\n")


# USAGE EXAMPLE AND TESTING
if __name__ == "__main__":
    
    # Set your Google API key here
    API_KEY = 'AIzaSyAZSxDDRAnU6qs5imoyfyo1yWIyepqxpaM'  # Replace with your actual API key
    
    print("🚀 BRAND COMPLIANCE CHECKER TEST\n")
    print("="*70)
    
    # Initialize checker
    checker = BrandComplianceChecker(api_key=API_KEY)
    
    # Path to the uploaded Coca-Cola image
    test_image = 'images (1).jpg'
    
    print("\n📋 TEST 1: Coca-Cola Image vs Coca-Cola Guidelines (SHOULD PASS)")
    print("="*70)
    checker.load_brand_guidelines('coca_cola_brand_guidelines.txt')
    result1 = checker.check_compliance(test_image, detailed=True)
    checker.print_result(result1)
    
    print("\n" + "🔄"*35 + "\n")
    
    print("\n📋 TEST 2: Coca-Cola Image vs Pepsi Guidelines (SHOULD FAIL)")
    print("="*70)
    checker.load_brand_guidelines('pepsi_brand_guidelines.txt')
    result2 = checker.check_compliance(test_image, detailed=True)
    checker.print_result(result2)
    
    # Summary
    print("\n" + "📊 SUMMARY")
    print("="*70)
    print(f"Test 1 (Coca-Cola Guidelines): {'✅ PASSED' if result1['compliant'] else '❌ FAILED'}")
    print(f"Test 2 (Pepsi Guidelines):     {'✅ PASSED' if result2['compliant'] else '❌ FAILED'}")
    print("\nExpected: Test 1 PASS, Test 2 FAIL")
    print("="*70)