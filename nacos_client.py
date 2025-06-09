import logging
import os
import time
import threading
from flask import Flask
from nacos import NacosClient
from eth_utils import is_address

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Configuration
nacos_server = os.getenv("NACOS_SERVER", "nacos.hyperagi.network:80")
public_ip = os.getenv("PUBLIC_IP", "")
port = int(os.getenv("PORT", 11434))
service_name = os.getenv("SERVICE_NAME", "")
wallet_address = os.getenv("WALLET_ADDRESS", "")

# 验证环境变量
if not wallet_address or not is_address(wallet_address):
    raise ValueError("Invalid or empty WALLET_ADDRESS environment variable")
if not public_ip:
    raise ValueError("PUBLIC_IP environment variable is not set or is empty")

# Nacos客户端设置
client = NacosClient(
    nacos_server, 
    namespace="", 
    username=os.getenv("NACOS_USERNAME", ""), 
    password=os.getenv("NACOS_PASSWORD", "")
)

def register_service():
    """注册服务到Nacos"""
    metadata = {"walletAddress": wallet_address}
    for attempt in range(5):
        try:
            response = client.add_naming_instance(
                service_name, public_ip, port, metadata=metadata
            )
            return
        except Exception as e:
            # 当注册失败时才输出详细日志
            logging.error(f"Registration attempt {attempt + 1} failed: {e}")
            logging.error(f"Failed registration details:")
            logging.error(f"Service Name: {service_name}")
            logging.error(f"Public IP: {public_ip}") 
            logging.error(f"Port: {port}")
            logging.error(f"Metadata: {metadata}")
            logging.error(f"Nacos Server: {nacos_server}")

    raise RuntimeError("Failed to register with Nacos after several attempts")

def send_heartbeat():
    """发送心跳信号"""
    metadata = {"walletAddress": wallet_address}
    while True:
        try:
            client.send_heartbeat(
                service_name, public_ip, port, metadata=metadata
            )
            logging.info("Heartbeat sent successfully.")
        except Exception as e:
            logging.error(f"Failed to send heartbeat: {e}")
        time.sleep(5)

if __name__ == '__main__':
    register_service()
    threading.Thread(target=send_heartbeat, daemon=True).start()
    app.run(host='0.0.0.0', port=5000)