#!/usr/bin/env python3
"""
Nacos API test script using urllib
Corresponds to curl command: curl -svm 8 "http://nacos.hyperagi.network/nacos/v1/ns/instance/list?serviceName=test"
No additional dependencies required, uses Python standard library
"""
import urllib.request
import urllib.parse
import urllib.error
import json
import sys


def test_nacos_api():
    """Test Nacos API call"""
    
    # Corresponds to the curl command you provided
    base_url = "http://nacos.hyperagi.network/nacos/v1/ns/instance/list"
    params = {
        'serviceName': 'test'
    }
    
    # Build complete URL
    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    
    print("🚀 Testing Nacos API call")
    print("=" * 50)
    print(f"📡 Request URL: {url}")
    print()
    
    try:
        # Create request object
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'NacosAPITest/1.0')
        
        # Send request with 8-second timeout (corresponds to curl's -m 8 parameter)
        with urllib.request.urlopen(req, timeout=8) as response:
            print(f"📊 Response status code: {response.status}")
            print(f"📋 Response headers:")
            for key, value in response.headers.items():
                print(f"   {key}: {value}")
            print()
            
            # Read response content
            response_data = response.read().decode('utf-8')
            
            if response.status == 200:
                try:
                    # Try to parse JSON response
                    data = json.loads(response_data)
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
                    else:
                        print("ℹ️  No service instances found")
                        
                except json.JSONDecodeError:
                    print("⚠️  Response is not valid JSON format")
                    print(f"📄 Raw response content:")
                    print(response_data)
                    
            else:
                print(f"❌ Request failed: HTTP {response.status}")
                print(f"📄 Error response content:")
                print(response_data)
                
    except urllib.error.HTTPError as e:
        print(f"❌ HTTP error: {e.code} - {e.reason}")
        try:
            error_data = e.read().decode('utf-8')
            print(f"📄 Error response content: {error_data}")
        except:
            pass
            
    except urllib.error.URLError as e:
        print(f"❌ URL error: {e.reason}")
        
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
        
        base_url = "http://nacos.hyperagi.network/nacos/v1/ns/instance/list"
        params = {'serviceName': service_name}
        url = f"{base_url}?{urllib.parse.urlencode(params)}"
        
        try:
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'NacosAPITest/1.0')
            
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode('utf-8'))
                    if 'hosts' in data and data['hosts']:
                        print(f"✅ Found {len(data['hosts'])} instances")
                    else:
                        print("ℹ️  No instances found")
                else:
                    print(f"❌ HTTP {response.status}")
                    
        except Exception as e:
            print(f"❌ Error: {e}")


if __name__ == "__main__":
    # Execute main test
    test_nacos_api()
    
    # Optional: test other service names
    # test_with_different_service_names()
    
    print("\n" + "=" * 50)
    print("🎉 Test completed")
