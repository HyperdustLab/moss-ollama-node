#!/usr/bin/env python3
"""
Simple script for testing Nacos instance list API
Corresponds to curl command: curl -svm 8 "http://nacos.hyperagi.network/nacos/v1/ns/instance/list?serviceName=test"
"""
import requests
import json

def test_nacos_instance_list():
    """Test Nacos instance list interface"""
    url = "http://nacos.hyperagi.network/nacos/v1/ns/instance/list"
    params = {
        "serviceName": "test"
    }
    
    print("🧪 Testing Nacos instance list API")
    print("=" * 50)
    print(f"🌐 Request URL: {url}")
    print(f"📝 Request parameters: {params}")
    print(f"⏰ Timeout: 8 seconds")
    print()
    
    try:
        # Send GET request with 8-second timeout
        response = requests.get(url, params=params, timeout=8)
        
        print(f"✅ Request successful!")
        print(f"📊 Status code: {response.status_code}")
        print(f"📄 Response headers: {dict(response.headers)}")
        print()
        
        if response.text:
            print("📦 Response content:")
            print(response.text)
            print()
            
            # Try to parse JSON
            try:
                data = response.json()
                print("🔍 Parsed JSON data:")
                print(json.dumps(data, indent=2, ensure_ascii=False))
            except ValueError:
                print("⚠️  Response is not valid JSON format")
        else:
            print("📭 Response content is empty")
            
    except requests.exceptions.Timeout:
        print("⏰ Request timeout (8 seconds)")
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Connection error: {e}")
    except Exception as e:
        print(f"❌ Request exception: {e}")

if __name__ == "__main__":
    test_nacos_instance_list()
