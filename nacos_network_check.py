#!/usr/bin/env python3
"""
Nacos network connectivity check script
Used for troubleshooting Nacos registration issues
"""
import socket
import requests
import os
import sys
from urllib.parse import urlparse
import time

def check_dns_resolution(host):
    """Check DNS resolution"""
    print(f"🔍 Checking DNS resolution: {host}")
    try:
        result = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
        ips = sorted({x[4][0] for x in result})
        print(f"✅ DNS resolution successful: {host} -> {ips}")
        return True, ips
    except Exception as e:
        print(f"❌ DNS resolution failed: {host} - {e}")
        return False, []

def check_tcp_connection(host, port, timeout=5):
    """Check TCP connection"""
    print(f"🔗 Checking TCP connection: {host}:{port}")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            print(f"✅ TCP connection successful: {host}:{port}")
            return True
        else:
            print(f"❌ TCP connection failed: {host}:{port} (error code: {result})")
            return False
    except Exception as e:
        print(f"❌ TCP connection exception: {host}:{port} - {e}")
        return False

def check_http_endpoint(url, timeout=10):
    """Check HTTP endpoint"""
    print(f"🌐 Checking HTTP endpoint: {url}")
    try:
        response = requests.get(url, timeout=timeout)
        print(f"✅ HTTP request successful: {url} (status code: {response.status_code})")
        print(f"   Response headers: {dict(response.headers)}")
        if response.text:
            print(f"   Response content: {response.text[:200]}...")
        return True, response
    except requests.exceptions.Timeout:
        print(f"⏰ HTTP request timeout: {url}")
        return False, None
    except requests.exceptions.ConnectionError as e:
        print(f"❌ HTTP connection error: {url} - {e}")
        return False, None
    except Exception as e:
        print(f"❌ HTTP request exception: {url} - {e}")
        return False, None

def check_nacos_health_endpoints(base_url):
    """Check Nacos health check endpoints"""
    endpoints = [
        "/nacos/v1/console/health",
        "/v1/console/health", 
        "/nacos/v1/ns/health",
        "/v1/ns/health",
        "/nacos/",
        "/"
    ]
    
    print(f"🏥 Checking Nacos health endpoints (base URL: {base_url})")
    success_count = 0
    
    for endpoint in endpoints:
        url = f"{base_url.rstrip('/')}{endpoint}"
        success, response = check_http_endpoint(url)
        if success:
            success_count += 1
    
    print(f"📊 Health endpoint check result: {success_count}/{len(endpoints)} successful")
    return success_count > 0

def get_nacos_instance_list(base_url, service_name="test", timeout=8):
    """Get Nacos service instance list"""
    url = f"{base_url.rstrip('/')}/nacos/v1/ns/instance/list"
    params = {
        "serviceName": service_name
    }
    
    print(f"📋 Getting service instance list: {service_name}")
    print(f"🌐 Request URL: {url}")
    print(f"📝 Request parameters: {params}")
    
    try:
        response = requests.get(url, params=params, timeout=timeout)
        print(f"✅ Request successful (status code: {response.status_code})")
        print(f"📄 Response headers: {dict(response.headers)}")
        
        if response.text:
            print(f"📦 Response content:")
            print(response.text)
            
            # Try to parse JSON response
            try:
                data = response.json()
                print(f"🔍 Parsed data: {data}")
                return True, data
            except ValueError:
                print("⚠️  Response is not valid JSON format")
                return True, response.text
        else:
            print("📭 Response content is empty")
            return True, None
            
    except requests.exceptions.Timeout:
        print(f"⏰ Request timeout: {url} (timeout: {timeout} seconds)")
        return False, None
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Connection error: {url} - {e}")
        return False, None
    except Exception as e:
        print(f"❌ Request exception: {url} - {e}")
        return False, None

def check_local_port(port, host="0.0.0.0"):
    """Check if local port is available"""
    print(f"🔌 Checking local port: {host}:{port}")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind((host, port))
        sock.close()
        print(f"✅ Local port available: {host}:{port}")
        return True
    except Exception as e:
        print(f"❌ Local port unavailable: {host}:{port} - {e}")
        return False

def check_environment_variables():
    """Check environment variables"""
    print("🔧 Checking environment variables:")
    
    required_vars = {
        'NACOS_SERVER': 'Nacos server address',
        'PUBLIC_IP': 'Public IP address', 
        'SERVICE_NAME': 'Service name',
        'WALLET_ADDRESS': 'Wallet address',
        'PORT': 'Service port'
    }
    
    optional_vars = {
        'NACOS_USERNAME': 'Nacos username',
        'NACOS_PASSWORD': 'Nacos password',
        'NACOS_GROUP': 'Nacos group',
        'NACOS_CLUSTER': 'Nacos cluster',
        'NODE': 'Node identifier'
    }
    
    all_good = True
    
    for var, desc in required_vars.items():
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: {value} ({desc})")
        else:
            print(f"❌ {var}: Not set ({desc}) - Required")
            all_good = False
    
    for var, desc in optional_vars.items():
        value = os.getenv(var)
        if value:
            print(f"ℹ️  {var}: {value} ({desc})")
        else:
            print(f"⚠️  {var}: Not set ({desc}) - Optional")
    
    return all_good

def parse_nacos_server(server_str):
    """Parse Nacos server address"""
    if not server_str:
        return []
    
    servers = []
    for server in server_str.split(','):
        server = server.strip()
        if not server:
            continue
            
        # Add protocol prefix
        if '://' not in server:
            server = f"http://{server}"
        
        parsed = urlparse(server)
        host = parsed.hostname
        port = parsed.port or (443 if parsed.scheme == 'https' else 80)
        servers.append((parsed.scheme, host, port, server))
    
    return servers

def main():
    print("🚀 Nacos network connectivity check tool")
    print("=" * 50)
    
    # Check environment variables
    env_ok = check_environment_variables()
    print()
    
    if not env_ok:
        print("❌ Environment variable check failed, please set required environment variables")
        sys.exit(1)
    
    # Get Nacos server address
    nacos_server = os.getenv("NACOS_SERVER", "http://nacos.hyperagi.network:80")
    print(f"🎯 Target Nacos server: {nacos_server}")
    print()
    
    # Parse server address
    servers = parse_nacos_server(nacos_server)
    if not servers:
        print("❌ Unable to parse Nacos server address")
        sys.exit(1)
    
    # Check each server
    overall_success = True
    
    for scheme, host, port, full_url in servers:
        print(f"🔍 Checking server: {full_url}")
        print("-" * 30)
        
        # DNS resolution
        dns_ok, ips = check_dns_resolution(host)
        if not dns_ok:
            overall_success = False
            continue
        
        # TCP connection
        tcp_ok = check_tcp_connection(host, port)
        if not tcp_ok:
            overall_success = False
            continue
        
        # HTTP endpoint check
        http_ok = check_nacos_health_endpoints(full_url)
        if not http_ok:
            overall_success = False
        
        # Get service instance list
        print("📋 Testing service instance list retrieval:")
        instance_success, instance_data = get_nacos_instance_list(full_url, "test", timeout=8)
        if not instance_success:
            overall_success = False
        
        print()
    
    # Check local port
    port = int(os.getenv("PORT", 11434))
    local_port_ok = check_local_port(port)
    if not local_port_ok:
        overall_success = False
    
    print("=" * 50)
    if overall_success:
        print("🎉 All checks passed! Network connectivity is normal")
        print("💡 If registration still fails, please check:")
        print("   - Nacos server authentication configuration")
        print("   - Firewall settings")
        print("   - Proxy settings")
        print("   - Whether service name already exists")
    else:
        print("❌ Check found issues, please fix according to error messages above")
        print("💡 Common solutions:")
        print("   - Check network connection")
        print("   - Confirm Nacos server address is correct")
        print("   - Check if firewall is blocking connections")
        print("   - Try using different ports")

def test_nacos_instance_list():
    """Test Nacos instance list interface"""
    print("🧪 Testing Nacos instance list interface")
    print("=" * 50)
    
    # Use specified URL
    base_url = "http://nacos.hyperagi.network"
    service_name = "test"
    
    print(f"🎯 Target server: {base_url}")
    print(f"📋 Service name: {service_name}")
    print()
    
    # Call function to get instance list
    success, data = get_nacos_instance_list(base_url, service_name, timeout=8)
    
    print("=" * 50)
    if success:
        print("🎉 Interface call successful!")
        if data:
            print("📊 Returned data:")
            print(data)
    else:
        print("❌ Interface call failed!")
        print("💡 Please check:")
        print("   - Whether network connection is normal")
        print("   - Whether Nacos server is accessible")
        print("   - Whether service name is correct")

if __name__ == "__main__":
    import sys
    
    # Check command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Run test mode
        test_nacos_instance_list()
    else:
        # Run complete check
        main()
