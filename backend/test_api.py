"""
Simple test script to verify the API endpoints are working
Run this after starting the backend server
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_health():
    """Test health check endpoint"""
    print("\n🔍 Testing Health Check...")
    try:
        response = requests.get(f"{BASE_URL}/api/health")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        assert response.status_code == 200
        print("✅ Health check passed!")
        return True
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

def test_list_uploads():
    """Test list uploads endpoint"""
    print("\n🔍 Testing List Uploads...")
    try:
        response = requests.get(f"{BASE_URL}/api/uploads/list")
        print(f"Status Code: {response.status_code}")
        data = response.json()
        print(f"Files found: {data['count']}")
        print(f"Response: {json.dumps(data, indent=2)}")
        assert response.status_code == 200
        print("✅ List uploads passed!")
        return True
    except Exception as e:
        print(f"❌ List uploads failed: {e}")
        return False

def test_root():
    """Test root endpoint"""
    print("\n🔍 Testing Root Endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        assert response.status_code == 200
        print("✅ Root endpoint passed!")
        return True
    except Exception as e:
        print(f"❌ Root endpoint failed: {e}")
        return False

def main():
    print("=" * 60)
    print("🚀 Testing Content Publisher Backend API")
    print("=" * 60)
    
    results = []
    results.append(("Health Check", test_health()))
    results.append(("Root Endpoint", test_root()))
    results.append(("List Uploads", test_list_uploads()))
    
    print("\n" + "=" * 60)
    print("📊 Test Summary")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    print(f"\nTotal: {passed}/{total} tests passed")
    print("=" * 60)

if __name__ == "__main__":
    print("\n⚠️  Make sure the backend server is running!")
    print("Start it with: uvicorn main:app --reload --port 8000\n")
    input("Press Enter to start tests...")
    main()
