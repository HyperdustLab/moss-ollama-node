#!/usr/bin/env python3
"""
Environment variable validation script
Used to validate environment variable configuration required by Nacos client
"""
import os
import sys
import re
from eth_utils import is_address

def validate_wallet_address(address):
    """验证以太坊钱包地址"""
    if not address:
        return False, "钱包地址为空"
    
    if not is_address(address):
        return False, f"无效的钱包地址格式: {address}"
    
    return True, "钱包地址格式正确"

def validate_ip_address(ip):
    """验证IP地址"""
    if not ip:
        return False, "IP地址为空"
    
    # IPv4验证
    ipv4_pattern = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
    if re.match(ipv4_pattern, ip):
        return True, "IPv4地址格式正确"
    
    # IPv6验证（简化版）
    ipv6_pattern = r'^(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$'
    if re.match(ipv6_pattern, ip):
        return True, "IPv6地址格式正确"
    
    return False, f"无效的IP地址格式: {ip}"

def validate_port(port_str):
    """验证端口号"""
    if not port_str:
        return False, "端口号为空"
    
    try:
        port = int(port_str)
        if 1 <= port <= 65535:
            return True, f"端口号有效: {port}"
        else:
            return False, f"端口号超出范围: {port} (应在1-65535之间)"
    except ValueError:
        return False, f"无效的端口号格式: {port_str}"

def validate_service_name(name):
    """验证服务名称"""
    if not name:
        return False, "服务名称为空"
    
    # 服务名称应该只包含字母、数字、连字符和下划线
    if re.match(r'^[a-zA-Z0-9_-]+$', name):
        return True, "服务名称格式正确"
    else:
        return False, f"服务名称包含无效字符: {name} (只允许字母、数字、连字符和下划线)"

def validate_nacos_server(server):
    """验证Nacos服务器地址"""
    if not server:
        return False, "Nacos服务器地址为空"
    
    # 支持多个服务器地址（逗号分隔）
    servers = [s.strip() for s in server.split(',') if s.strip()]
    
    for srv in servers:
        # 检查是否包含协议
        if '://' not in srv:
            srv = f"http://{srv}"
        
        # 简单的URL格式验证
        if not re.match(r'^https?://[a-zA-Z0-9.-]+(:\d+)?(/.*)?$', srv):
            return False, f"无效的Nacos服务器地址格式: {srv}"
    
    return True, f"Nacos服务器地址格式正确: {len(servers)}个服务器"

def validate_nacos_credentials():
    """验证Nacos认证信息"""
    username = os.getenv("NACOS_USERNAME", "")
    password = os.getenv("NACOS_PASSWORD", "")
    
    if not username and not password:
        return True, "未设置认证信息（使用匿名访问）"
    elif username and password:
        return True, "认证信息已设置"
    else:
        return False, "认证信息不完整：用户名和密码必须同时设置或同时为空"

def validate_nacos_group(group):
    """验证Nacos分组"""
    if not group:
        return True, "使用默认分组"
    
    if re.match(r'^[a-zA-Z0-9_-]+$', group):
        return True, "分组名称格式正确"
    else:
        return False, f"分组名称包含无效字符: {group}"

def validate_nacos_cluster(cluster):
    """验证Nacos集群"""
    if not cluster:
        return True, "未设置集群（使用默认集群）"
    
    if re.match(r'^[a-zA-Z0-9_-]+$', cluster):
        return True, "集群名称格式正确"
    else:
        return False, f"集群名称包含无效字符: {cluster}"

def validate_timeout_settings():
    """验证超时设置"""
    timeout_vars = {
        'NACOS_HTTP_TIMEOUT': 'HTTP超时时间',
        'MAX_RECONNECT_DELAY': '最大重连延迟',
        'INITIAL_RECONNECT_DELAY': '初始重连延迟',
        'HEARTBEAT_INTERVAL': '心跳间隔'
    }
    
    results = []
    all_valid = True
    
    for var, desc in timeout_vars.items():
        value = os.getenv(var, "")
        if not value:
            results.append(f"ℹ️  {var}: 使用默认值 ({desc})")
            continue
        
        try:
            float_val = float(value)
            if float_val > 0:
                results.append(f"✅ {var}: {value} ({desc})")
            else:
                results.append(f"❌ {var}: {value} - 必须大于0 ({desc})")
                all_valid = False
        except ValueError:
            results.append(f"❌ {var}: {value} - 无效的数值格式 ({desc})")
            all_valid = False
    
    return all_valid, results

def main():
    print("🔧 Nacos环境变量验证工具")
    print("=" * 50)
    
    # 必需的环境变量
    required_vars = {
        'WALLET_ADDRESS': validate_wallet_address,
        'PUBLIC_IP': validate_ip_address,
        'SERVICE_NAME': validate_service_name,
        'NACOS_SERVER': validate_nacos_server,
        'PORT': validate_port
    }
    
    # 可选的环境变量
    optional_vars = {
        'NACOS_GROUP': validate_nacos_group,
        'NACOS_CLUSTER': validate_nacos_cluster,
        'NODE': lambda x: (True, f"节点标识: {x}" if x else "使用PUBLIC_IP作为节点标识")
    }
    
    all_valid = True
    
    print("📋 检查必需的环境变量:")
    print("-" * 30)
    
    for var, validator in required_vars.items():
        value = os.getenv(var, "")
        if value:
            is_valid, message = validator(value)
            if is_valid:
                print(f"✅ {var}: {message}")
            else:
                print(f"❌ {var}: {message}")
                all_valid = False
        else:
            print(f"❌ {var}: 未设置")
            all_valid = False
    
    print("\n📋 检查可选的环境变量:")
    print("-" * 30)
    
    for var, validator in optional_vars.items():
        value = os.getenv(var, "")
        is_valid, message = validator(value)
        if is_valid:
            print(f"ℹ️  {var}: {message}")
        else:
            print(f"⚠️  {var}: {message}")
    
    print("\n🔐 检查认证配置:")
    print("-" * 30)
    
    cred_valid, cred_message = validate_nacos_credentials()
    if cred_valid:
        print(f"✅ 认证配置: {cred_message}")
    else:
        print(f"❌ 认证配置: {cred_message}")
        all_valid = False
    
    print("\n⏱️  检查超时设置:")
    print("-" * 30)
    
    timeout_valid, timeout_results = validate_timeout_settings()
    for result in timeout_results:
        print(result)
    
    if not timeout_valid:
        all_valid = False
    
    print("\n" + "=" * 50)
    
    if all_valid:
        print("🎉 所有环境变量验证通过！")
        print("\n💡 建议的完整环境变量配置:")
        print("-" * 30)
        
        # 显示当前配置
        config_vars = [
            'NACOS_SERVER', 'PUBLIC_IP', 'PORT', 'SERVICE_NAME', 
            'WALLET_ADDRESS', 'NACOS_USERNAME', 'NACOS_PASSWORD',
            'NACOS_GROUP', 'NACOS_CLUSTER', 'NODE'
        ]
        
        for var in config_vars:
            value = os.getenv(var, "")
            if value:
                # 敏感信息脱敏
                if 'PASSWORD' in var:
                    display_value = '*' * len(value)
                else:
                    display_value = value
                print(f"export {var}='{display_value}'")
        
        print("\n🚀 可以运行 nacos_client.py 进行服务注册")
    else:
        print("❌ 环境变量验证失败，请修复上述问题")
        print("\n💡 常见问题解决方案:")
        print("   - 确保所有必需的环境变量都已设置")
        print("   - 检查IP地址和端口号格式是否正确")
        print("   - 验证钱包地址是否为有效的以太坊地址")
        print("   - 确认Nacos服务器地址格式正确")
        sys.exit(1)

if __name__ == "__main__":
    main()
