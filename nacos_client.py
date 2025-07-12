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
node = os.getenv("NODE", public_ip)

# 重连配置
MAX_RECONNECT_ATTEMPTS = 10
INITIAL_RECONNECT_DELAY = 5  # 初始重连延迟（秒）
MAX_RECONNECT_DELAY = 300    # 最大重连延迟（秒）
HEARTBEAT_INTERVAL = 5       # 心跳间隔（秒）

# 全局状态变量
is_connected = False
reconnect_lock = threading.Lock()
stop_reconnect = threading.Event()

# 验证环境变量
if not wallet_address or not is_address(wallet_address):
    raise ValueError("Invalid or empty WALLET_ADDRESS environment variable")
if not public_ip:
    raise ValueError("PUBLIC_IP environment variable is not set or is empty")
if not service_name:
    raise ValueError("SERVICE_NAME environment variable is not set or is empty")

def create_nacos_client():
    """创建Nacos客户端"""
    return NacosClient(
        nacos_server, 
        namespace="", 
        username=os.getenv("NACOS_USERNAME", ""), 
        password=os.getenv("NACOS_PASSWORD", "")
    )

# 初始化客户端
client = create_nacos_client()

def register_service():
    """注册服务到Nacos"""
    metadata = {"walletAddress": wallet_address, "node": node}
    for attempt in range(5):
        try:
            response = client.add_naming_instance(
                service_name, public_ip, port, metadata=metadata
            )
            global is_connected
            is_connected = True
            logging.info("Service registered successfully with Nacos")
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
            is_connected = False

    raise RuntimeError("Failed to register with Nacos after several attempts")

def attempt_reconnect():
    """尝试重新连接Nacos服务器"""
    global client, is_connected
    
    with reconnect_lock:
        if stop_reconnect.is_set():
            return False
            
        logging.info("Attempting to reconnect to Nacos server...")
        try:
            # 创建新的客户端实例
            client = create_nacos_client()
            
            # 尝试重新注册服务
            metadata = {"walletAddress": wallet_address, "node": node}
            
            response = client.add_naming_instance(
                service_name, public_ip, port, metadata=metadata
            )
            
            is_connected = True
            logging.info("Successfully reconnected to Nacos server")
            return True
            
        except Exception as e:
            is_connected = False
            logging.error(f"Reconnection attempt failed: {e}")
            return False

def exponential_backoff_delay(attempt):
    """计算指数退避延迟时间"""
    delay = min(INITIAL_RECONNECT_DELAY * (2 ** attempt), MAX_RECONNECT_DELAY)
    return delay

def reconnect_worker():
    """重连工作线程"""
    attempt = 0
    
    while not stop_reconnect.is_set():
        if not is_connected:
            if attempt_reconnect():
                attempt = 0  # 重置重连计数
                logging.info("Reconnection successful, resuming normal operation")
            else:
                attempt += 1
                delay = exponential_backoff_delay(attempt)
                logging.warning(f"Reconnection failed, attempt {attempt}. Retrying in {delay} seconds...")
                time.sleep(delay)
        else:
            # 连接正常，等待一段时间再检查
            time.sleep(HEARTBEAT_INTERVAL)

def send_heartbeat():
    """发送心跳信号"""
    global is_connected
    metadata = {"walletAddress": wallet_address, "node": node}
    consecutive_failures = 0
    
    while not stop_reconnect.is_set():
        if is_connected:
            try:
                client.send_heartbeat(
                    service_name, public_ip, port, metadata=metadata
                )
                logging.info("Heartbeat sent successfully.")
                consecutive_failures = 0  # 重置失败计数
            except Exception as e:
                consecutive_failures += 1
                logging.error(f"Failed to send heartbeat: {e}")
                
                # 如果连续失败超过3次，标记为断开连接
                if consecutive_failures >= 3:
                    is_connected = False
                    logging.warning("Multiple heartbeat failures detected, marking connection as lost")
                    consecutive_failures = 0
        else:
            logging.debug("Connection lost, skipping heartbeat")
            
        time.sleep(HEARTBEAT_INTERVAL)

def graceful_shutdown():
    """优雅关闭"""
    logging.info("Initiating graceful shutdown...")
    stop_reconnect.set()
    
    # 尝试注销服务
    if is_connected:
        try:
            client.remove_naming_instance(service_name, public_ip, port)
            logging.info("Service deregistered successfully")
        except Exception as e:
            logging.error(f"Failed to deregister service: {e}")

if __name__ == '__main__':
    try:
        register_service()
        
        # 启动重连工作线程
        reconnect_thread = threading.Thread(target=reconnect_worker, daemon=True)
        reconnect_thread.start()
        
        # 启动心跳线程
        heartbeat_thread = threading.Thread(target=send_heartbeat, daemon=True)
        heartbeat_thread.start()
        
        # 启动Flask应用
        app.run(host='0.0.0.0', port=5000)
        
    except KeyboardInterrupt:
        logging.info("Received interrupt signal")
    except Exception as e:
        logging.error(f"Application error: {e}")
    finally:
        graceful_shutdown()