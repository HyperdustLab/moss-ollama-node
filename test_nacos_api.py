#!/usr/bin/env python3
"""
Simple Nacos API test script
Corresponds to curl command: curl -svm 8 "http://nacos.hyperagi.network/nacos/v1/ns/instance/list?serviceName=test"
"""
import requests
import json
import sys


def test_nacos_api():
    """Test Nacos API call"""
    
    # Corresponds to the curl command you provided
    url = "http://nacos.hyperagi.network/nacos/v1/ns/instance/list"
    params = {
        'serviceName': 'test'
    }
    
    print("🚀 Testing Nacos API call")
    print("=" * 50)
    print(f"📡 Request URL: {url}")
    print(f"📋 Request parameters: {params}")
    print()
    
    try:
        # Send GET request with 8-second timeout (corresponds to curl's -m 8 parameter)
        response = requests.get(url, params=params, timeout=8)
        
        print(f"📊 Response status code: {response.status_code}")
        print(f"📋 Response headers:")
        for key, value in response.headers.items():
            print(f"   {key}: {value}")
        print()
        
        if response.status_code == 200:
            try:
                # Try to parse JSON response
                data = response.json()
                print("✅ Request successful!")
                print(f"📄 JSON response content:")
                print(json.dumps(data, indent=2, ensure_ascii=False))
                
                # If there's instance data, show detailed information
                if 'hosts' in data and isinstance(data['hosts'], list):
                    instances = data['hosts']
                    print(f"\n📊 Found {len(instances)} service instances:")
                    for i, instance in enumerate(instances, 1):
                        print(f"   {i}. IP: {instance.get('ip', 'N/A')}")
                        print(f"      Port: {instance.get('port', 'N/A')}")
                        print(f"      Health status: {instance.get('healthy', 'N/A')}")
                        print(f"      Enabled status: {instance.get('enabled', 'N/A')}")
                        print(f"      Weight: {instance.get('weight', 'N/A')}")
                        if 'metadata' in instance:
                            print(f"      Metadata: {instance['metadata']}")
                        print()
                        
            except json.JSONDecodeError:
                print("⚠️  Response is not valid JSON format")
                print(f"📄 Raw response content:")
                print(response.text)
                
        else:
            print(f"❌ Request failed: HTTP {response.status_code}")
            print(f"📄 Error response content:")
            print(response.text)
            
    except requests.exceptions.Timeout:
        print("⏰ Request timeout (8 seconds)")
        
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Connection error: {e}")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Request exception: {e}")
        
    except Exception as e:
        print(f"❌ Unknown error: {e}")


def test_with_different_service_names():
    """Test different service names"""
    
    service_names = ['test', 'default', 'nacos', 'service']
    
    print("\n🔍 Testing different service names")
    print("=" * 50)
    
    for service_name in service_names:
        print(f"\n📋 Testing service name: {service_name}")
        print("-" * 30)
        
        url = "http://nacos.hyperagi.network/nacos/v1/ns/instance/list"
        params = {'serviceName': service_name}
        
        try:
            response = requests.get(url, params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if 'hosts' in data and data['hosts']:
                    print(f"✅ Found {len(data['hosts'])} instances")
                else:
                    print("ℹ️  No instances found")
            else:
                print(f"❌ HTTP {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error: {e}")


if __name__ == "__main__":
    # Check if requests library is available
    try:
        import requests
    except ImportError:
        print("❌ Missing requests library, please install: pip install requests")
        sys.exit(1)
    
    # Execute main test
    test_nacos_api()
    
    # Optional: test other service names
    # test_with_different_service_names()
    
    print("\n" + "=" * 50)
    print("🎉 Test completed")
