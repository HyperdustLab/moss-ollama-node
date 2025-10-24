#!/usr/bin/env python3
"""
Nacos HTTP API Client
Used for directly calling Nacos REST API interfaces
"""
import requests
import json
import os
import sys
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin, urlencode


class NacosAPIClient:
    """Nacos HTTP API Client"""
    
    def __init__(self, base_url: str = "http://nacos.hyperagi.network", 
                 username: str = "", password: str = ""):
        """
        Initialize Nacos API client
        
        Args:
            base_url: Nacos server base URL
            username: Username (optional)
            password: Password (optional)
        """
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.session = requests.Session()
        
        # Set default timeout
        self.session.timeout = 10
        
        # If authentication info is provided, set authentication
        if username and password:
            self.session.auth = (username, password)
    
    def _make_request(self, method: str, endpoint: str, params: Dict = None, 
                     data: Dict = None, headers: Dict = None) -> requests.Response:
        """
        Send HTTP request
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint
            params: URL parameters
            data: Request body data
            headers: Request headers
            
        Returns:
            requests.Response: Response object
        """
        url = urljoin(self.base_url, endpoint)
        
        # Default request headers
        default_headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'NacosAPIClient/1.0'
        }
        if headers:
            default_headers.update(headers)
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                data=data,
                headers=default_headers
            )
            return response
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
            raise
    
    def get_service_instance_list(self, service_name: str, group_name: str = "DEFAULT_GROUP",
                                namespace_id: str = "", healthy_only: bool = False) -> Dict[str, Any]:
        """
        Get service instance list
        
        Args:
            service_name: Service name
            group_name: Group name, default is DEFAULT_GROUP
            namespace_id: Namespace ID, default is empty
            healthy_only: Whether to return only healthy instances
            
        Returns:
            Dict: Response data containing instance list
        """
        endpoint = "/nacos/v1/ns/instance/list"
        
        params = {
            'serviceName': service_name,
            'groupName': group_name
        }
        
        if namespace_id:
            params['namespaceId'] = namespace_id
        
        if healthy_only:
            params['healthyOnly'] = 'true'
        
        print(f"🔍 Getting service instance list: {service_name}")
        print(f"   Group: {group_name}")
        print(f"   Namespace: {namespace_id or 'default'}")
        print(f"   Show only healthy instances: {healthy_only}")
        
        try:
            response = self._make_request('GET', endpoint, params=params)
            
            print(f"📡 Request URL: {response.url}")
            print(f"📊 Response status: {response.status_code}")
            print(f"📋 Response headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"✅ Request successful")
                    print(f"📄 Response content: {json.dumps(data, indent=2, ensure_ascii=False)}")
                    return data
                except json.JSONDecodeError:
                    print(f"⚠️  Response is not valid JSON format")
                    print(f"📄 Raw response: {response.text}")
                    return {'error': 'Invalid JSON response', 'raw': response.text}
            else:
                print(f"❌ Request failed: HTTP {response.status_code}")
                print(f"📄 Error response: {response.text}")
                return {'error': f'HTTP {response.status_code}', 'message': response.text}
                
        except Exception as e:
            print(f"❌ Request exception: {e}")
            return {'error': str(e)}
    
    def get_service_detail(self, service_name: str, group_name: str = "DEFAULT_GROUP",
                          namespace_id: str = "") -> Dict[str, Any]:
        """
        Get service details
        
        Args:
            service_name: Service name
            group_name: Group name
            namespace_id: Namespace ID
            
        Returns:
            Dict: Service detail data
        """
        endpoint = "/nacos/v1/ns/service"
        
        params = {
            'serviceName': service_name,
            'groupName': group_name
        }
        
        if namespace_id:
            params['namespaceId'] = namespace_id
        
        print(f"🔍 Get service details: {service_name}")
        
        try:
            response = self._make_request('GET', endpoint, params=params)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Service details retrieved successfully")
                print(f"📄 Service details: {json.dumps(data, indent=2, ensure_ascii=False)}")
                return data
            else:
                print(f"❌ Get service details失败: HTTP {response.status_code}")
                print(f"📄 Error response: {response.text}")
                return {'error': f'HTTP {response.status_code}', 'message': response.text}
                
        except Exception as e:
            print(f"❌ Get service details异常: {e}")
            return {'error': str(e)}
    
    def register_instance(self, service_name: str, ip: str, port: int,
                         group_name: str = "DEFAULT_GROUP", namespace_id: str = "",
                         metadata: Dict = None, healthy: bool = True,
                         enabled: bool = True, ephemeral: bool = True) -> Dict[str, Any]:
        """
        Register service instance
        
        Args:
            service_name: Service name
            ip: Instance IP
            port: Instance port
            group_name: Group name
            namespace_id: Namespace ID
            metadata: Metadata
            healthy: Whether healthy
            enabled: Whether enabled
            ephemeral: Whether ephemeral instance
            
        Returns:
            Dict: Registration result
        """
        endpoint = "/nacos/v1/ns/instance"
        
        data = {
            'serviceName': service_name,
            'ip': ip,
            'port': port,
            'groupName': group_name,
            'healthy': str(healthy).lower(),
            'enabled': str(enabled).lower(),
            'ephemeral': str(ephemeral).lower()
        }
        
        if namespace_id:
            data['namespaceId'] = namespace_id
        
        if metadata:
            data['metadata'] = json.dumps(metadata)
        
        print(f"📝 Register service instance: {service_name} -> {ip}:{port}")
        
        try:
            response = self._make_request('POST', endpoint, data=data)
            
            if response.status_code == 200:
                print(f"✅ Instance registered successfully")
                return {'success': True, 'message': 'Instance registered successfully'}
            else:
                print(f"❌ Instance registration failed: HTTP {response.status_code}")
                print(f"📄 Error response: {response.text}")
                return {'error': f'HTTP {response.status_code}', 'message': response.text}
                
        except Exception as e:
            print(f"❌ Instance registration exception: {e}")
            return {'error': str(e)}
    
    def deregister_instance(self, service_name: str, ip: str, port: int,
                           group_name: str = "DEFAULT_GROUP", namespace_id: str = "") -> Dict[str, Any]:
        """
        Deregister service instance
        
        Args:
            service_name: Service name
            ip: Instance IP
            port: Instance port
            group_name: Group name
            namespace_id: Namespace ID
            
        Returns:
            Dict: Deregistration result
        """
        endpoint = "/nacos/v1/ns/instance"
        
        params = {
            'serviceName': service_name,
            'ip': ip,
            'port': port,
            'groupName': group_name
        }
        
        if namespace_id:
            params['namespaceId'] = namespace_id
        
        print(f"🗑️  Deregister service instance: {service_name} -> {ip}:{port}")
        
        try:
            response = self._make_request('DELETE', endpoint, params=params)
            
            if response.status_code == 200:
                print(f"✅ Instance deregistered successfully")
                return {'success': True, 'message': 'Instance deregistered successfully'}
            else:
                print(f"❌ Instance deregistration failed: HTTP {response.status_code}")
                print(f"📄 Error response: {response.text}")
                return {'error': f'HTTP {response.status_code}', 'message': response.text}
                
        except Exception as e:
            print(f"❌ Instance deregistration exception: {e}")
            return {'error': str(e)}
    
    def send_heartbeat(self, service_name: str, ip: str, port: int,
                      group_name: str = "DEFAULT_GROUP", namespace_id: str = "",
                      metadata: Dict = None) -> Dict[str, Any]:
        """
        Send heartbeat
        
        Args:
            service_name: Service name
            ip: Instance IP
            port: Instance port
            group_name: Group name
            namespace_id: Namespace ID
            metadata: Metadata
            
        Returns:
            Dict: Heartbeat result
        """
        endpoint = "/nacos/v1/ns/instance/beat"
        
        data = {
            'serviceName': service_name,
            'ip': ip,
            'port': port,
            'groupName': group_name
        }
        
        if namespace_id:
            data['namespaceId'] = namespace_id
        
        if metadata:
            data['metadata'] = json.dumps(metadata)
        
        print(f"💓 Send heartbeat: {service_name} -> {ip}:{port}")
        
        try:
            response = self._make_request('PUT', endpoint, data=data)
            
            if response.status_code == 200:
                print(f"✅ Heartbeat sent successfully")
                return {'success': True, 'message': 'Heartbeat sent successfully'}
            else:
                print(f"❌ Heartbeat sending failed: HTTP {response.status_code}")
                print(f"📄 Error response: {response.text}")
                return {'error': f'HTTP {response.status_code}', 'message': response.text}
                
        except Exception as e:
            print(f"❌ Heartbeat sending exception: {e}")
            return {'error': str(e)}


def main():
    """Main function - demonstrate API calls"""
    print("🚀 Nacos HTTP API Client Demo")
    print("=" * 50)
    
    # Get configuration from environment variables
    base_url = os.getenv("NACOS_SERVER", "http://nacos.hyperagi.network")
    username = os.getenv("NACOS_USERNAME", "")
    password = os.getenv("NACOS_PASSWORD", "")
    service_name = os.getenv("SERVICE_NAME", "test")
    
    print(f"🎯 Nacos server: {base_url}")
    print(f"👤 Username: {username or 'Not set'}")
    print(f"🔑 Password: {'Set' if password else 'Not set'}")
    print(f"📋 Service name: {service_name}")
    print()
    
    # Create API client
    client = NacosAPIClient(base_url, username, password)
    
    # Demo: Get service instance list
    print("📋 Demo: Getting service instance list")
    print("-" * 30)
    result = client.get_service_instance_list(service_name)
    
    if 'error' in result:
        print(f"❌ Failed to get instance list: {result['error']}")
    else:
        print(f"✅ Successfully got instance list")
        if 'hosts' in result:
            instances = result['hosts']
            print(f"📊 Found {len(instances)} instances:")
            for i, instance in enumerate(instances, 1):
                print(f"   {i}. {instance.get('ip', 'N/A')}:{instance.get('port', 'N/A')} "
                      f"(Health: {instance.get('healthy', 'N/A')}, "
                      f"Enabled: {instance.get('enabled', 'N/A')})")
    
    print()
    
    # 演示：Get service details
    print("📋 演示：Get service details")
    print("-" * 30)
    detail_result = client.get_service_detail(service_name)
    
    if 'error' in detail_result:
        print(f"❌ Get service details失败: {detail_result['error']}")
    else:
        print(f"✅ 成功Get service details")
    
    print()
    print("=" * 50)
    print("🎉 Demo completed")


if __name__ == "__main__":
    main()
