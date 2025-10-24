#!/usr/bin/env python3
"""
增强版Nacos客户端 - 带详细调试日志
用于排查Nacos注册问题
"""
import logging
import os
import socket
import threading
import signal
import inspect
import json
import time
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from flask import Flask, jsonify
from nacos import NacosClient
from eth_utils import is_address

# -----------------------------
# 增强的日志配置
# -----------------------------
def setup_enhanced_logging():
    """设置增强的日志配置"""
    log_level = os.getenv("LOG_LEVEL", "DEBUG")
    
    # 创建自定义格式
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(threadName)-12s | %(name)-20s | %(message)s'
    )
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # 文件处理器（可选）
    log_file = os.getenv("LOG_FILE", "")
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logging.getLogger().addHandler(file_handler)
        print(f"📝 日志将同时写入文件: {log_file}")
    
    # 设置根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    root_logger.addHandler(console_handler)
    
    # 设置特定模块的日志级别
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    
    print(f"🔍 日志级别设置为: {log_level}")
    return root_logger

# 初始化日志
logger = setup_enhanced_logging()

app = Flask(__name__)

# -----------------------------
# Configuration (ENV)
# -----------------------------
NACOS_SERVER = os.getenv("NACOS_SERVER", "http://nacos.hyperagi.network:80")
NACOS_HTTP_TIMEOUT = float(os.getenv("NACOS_HTTP_TIMEOUT", "5.0"))

PUBLIC_IP = os.getenv("PUBLIC_IP", "")
PORT = int(os.getenv("PORT", 11434))

SERVICE_NAME = os.getenv("SERVICE_NAME", "")
WALLET_ADDRESS = os.getenv("WALLET_ADDRESS", "")
NODE = os.getenv("NODE", PUBLIC_IP)

NACOS_USERNAME = os.getenv("NACOS_USERNAME", "")
NACOS_PASSWORD = os.getenv("NACOS_PASSWORD", "")

# Retry / heartbeat
MAX_RECONNECT_DELAY = int(os.getenv("MAX_RECONNECT_DELAY", 300))
INITIAL_RECONNECT_DELAY = int(os.getenv("INITIAL_RECONNECT_DELAY", 5))
HEARTBEAT_INTERVAL = int(os.getenv("HEARTBEAT_INTERVAL", 5))

# 可选：分组/集群
NACOS_GROUP = os.getenv("NACOS_GROUP", "DEFAULT_GROUP")
NACOS_CLUSTER = os.getenv("NACOS_CLUSTER", "")

# -----------------------------
# Global state
# -----------------------------
is_connected = False
reconnect_lock = threading.Lock()
stop_event = threading.Event()
client = None
connection_stats = {
    'total_attempts': 0,
    'successful_connections': 0,
    'failed_connections': 0,
    'last_success_time': None,
    'last_error': None,
    'heartbeat_success_count': 0,
    'heartbeat_fail_count': 0
}

# -----------------------------
# 增强的调试工具
# -----------------------------
def log_environment_info():
    """记录环境信息"""
    logger.info("🔧 环境配置信息:")
    logger.info(f"   NACOS_SERVER: {NACOS_SERVER}")
    logger.info(f"   PUBLIC_IP: {PUBLIC_IP}")
    logger.info(f"   PORT: {PORT}")
    logger.info(f"   SERVICE_NAME: {SERVICE_NAME}")
    logger.info(f"   WALLET_ADDRESS: {WALLET_ADDRESS[:10]}...{WALLET_ADDRESS[-6:] if WALLET_ADDRESS else 'None'}")
    logger.info(f"   NODE: {NODE}")
    logger.info(f"   NACOS_GROUP: {NACOS_GROUP}")
    logger.info(f"   NACOS_CLUSTER: {NACOS_CLUSTER or 'None'}")
    logger.info(f"   NACOS_USERNAME: {NACOS_USERNAME or 'None'}")
    logger.info(f"   NACOS_PASSWORD: {'***' if NACOS_PASSWORD else 'None'}")

def log_network_info():
    """记录网络信息"""
    logger.info("🌐 网络信息:")
    try:
        # 获取本机IP
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        logger.info(f"   主机名: {hostname}")
        logger.info(f"   本机IP: {local_ip}")
        logger.info(f"   公网IP: {PUBLIC_IP}")
        
        # 检查端口占用
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(('0.0.0.0', PORT))
            logger.info(f"   端口 {PORT}: 可用")
        except OSError as e:
            logger.warning(f"   端口 {PORT}: 被占用 - {e}")
        finally:
            sock.close()
            
    except Exception as e:
        logger.error(f"   网络信息获取失败: {e}")

def log_nacos_server_info():
    """记录Nacos服务器信息"""
    logger.info("🎯 Nacos服务器信息:")
    
    servers = [s.strip() for s in NACOS_SERVER.split(',') if s.strip()]
    for i, server in enumerate(servers, 1):
        logger.info(f"   服务器 {i}: {server}")
        
        # 解析服务器地址
        if '://' not in server:
            server = f"http://{server}"
        
        parsed = urlparse(server)
        host = parsed.hostname
        port = parsed.port or (443 if parsed.scheme == 'https' else 80)
        
        # DNS解析测试
        try:
            ips = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
            ip_list = sorted({x[4][0] for x in ips})
            logger.info(f"     DNS解析: {host} -> {ip_list}")
        except Exception as e:
            logger.error(f"     DNS解析失败: {host} - {e}")
        
        # TCP连接测试
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex((host, port))
            sock.close()
            if result == 0:
                logger.info(f"     TCP连接: {host}:{port} - 成功")
            else:
                logger.warning(f"     TCP连接: {host}:{port} - 失败 (错误码: {result})")
        except Exception as e:
            logger.warning(f"     TCP连接: {host}:{port} - 异常: {e}")

# -----------------------------
# Utilities (保持原有功能)
# -----------------------------
def _parse_host_port(server: str) -> tuple[str, int]:
    if "://" not in server:
        parsed = urlparse(f"http://{server}")
    else:
        parsed = urlparse(server)

    host = parsed.hostname or server
    port = parsed.port or (80 if parsed.scheme in ("", "http") else 443)
    return host, port

def check_dns_resolvable(host: str) -> bool:
    try:
        infos = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
        addrs = sorted({x[4][0] for x in infos})
        logger.info(f"DNS解析成功: {host} -> {addrs}")
        return True
    except Exception as e:
        logger.error(f"DNS解析失败: {host} - {e}")
        return False

def check_tcp_connect(host: str, port: int, timeout=3) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            logger.info(f"TCP连接成功: {host}:{port}")
            return True
    except Exception as e:
        logger.error(f"TCP连接失败: {host}:{port} - {e}")
        return False

def check_port_available(port: int, host="0.0.0.0") -> bool:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((host, port))
        s.close()
        logger.info(f"端口可用: {host}:{port}")
        return True
    except Exception as e:
        logger.error(f"端口不可用: {host}:{port} - {e}")
        return False

def _build_base_url(server: str) -> str:
    if "://" not in server:
        return f"http://{server}"
    return server

def _probe_nacos_http(server: str):
    """增强的HTTP探针"""
    base = _build_base_url(server).rstrip("/")
    endpoints = ["/nacos/v1/console/health", "/v1/console/health", "/nacos/", "/"]
    
    logger.info(f"🔍 HTTP探针测试: {base}")
    
    for path in endpoints:
        url = f"{base}{path}"
        try:
            req = Request(url, method="GET")
            start_time = time.time()
            with urlopen(req, timeout=NACOS_HTTP_TIMEOUT) as resp:
                duration = time.time() - start_time
                body = resp.read(128).decode("utf-8", errors="ignore")
                logger.info(f"HTTP探针成功: {url} (状态: {resp.status}, 耗时: {duration:.2f}s)")
                logger.debug(f"响应内容: {body}")
                return
        except HTTPError as e:
            logger.warning(f"HTTP探针失败: {url} - HTTP {e.code}")
        except URLError as e:
            logger.warning(f"HTTP探针失败: {url} - 网络错误: {e.reason}")
        except Exception as e:
            logger.warning(f"HTTP探针失败: {url} - 异常: {e}")
    
    logger.warning("所有HTTP探针端点都失败")

# -----------------------------
# Validations (保持原有功能)
# -----------------------------
def validate_env_or_die():
    if not WALLET_ADDRESS or not is_address(WALLET_ADDRESS):
        raise ValueError("Invalid or empty WALLET_ADDRESS")
    if not PUBLIC_IP:
        raise ValueError("PUBLIC_IP is required")
    if not SERVICE_NAME:
        raise ValueError("SERVICE_NAME is required")

def preflight_or_die():
    """增强的启动前置检查"""
    logger.info("🚀 开始启动前置检查")
    
    first = NACOS_SERVER.split(",")[0].strip()
    host, port = _parse_host_port(first)

    ok = True
    ok &= check_dns_resolvable(host)
    ok &= check_tcp_connect(host, port)
    ok &= check_port_available(PORT)

    logger.info(f"目标服务器: {NACOS_SERVER}")
    _probe_nacos_http(first)

    if not ok:
        raise RuntimeError("启动前置检查失败，请查看上述日志")

# -----------------------------
# Nacos client helpers (保持原有功能)
# -----------------------------
def _construct_nacos_client(servers: str) -> NacosClient:
    logger.info(f"🔧 构建Nacos客户端: {servers}")
    
    kwargs = {
        "server_addresses": servers,
        "namespace": "",
        "username": NACOS_USERNAME,
        "password": NACOS_PASSWORD,
    }
    
    sig = inspect.signature(NacosClient.__init__)
    if "default_timeout" in sig.parameters:
        kwargs["default_timeout"] = NACOS_HTTP_TIMEOUT
        logger.debug(f"设置默认超时: {NACOS_HTTP_TIMEOUT}s")
    
    logger.debug(f"客户端参数: {json.dumps({k: v if k != 'password' else '***' for k, v in kwargs.items()}, indent=2)}")
    
    return NacosClient(**kwargs)

def create_nacos_client() -> NacosClient:
    servers = ",".join(_build_base_url(s.strip()) for s in NACOS_SERVER.split(",") if s.strip())
    logger.info(f"创建Nacos客户端，服务器列表: {servers}")
    return _construct_nacos_client(servers)

def _call_with_supported_kwargs(func, *args, **kwargs):
    sig = inspect.signature(func)
    params = sig.parameters

    if "enabled" in kwargs and "enable" in params:
        kwargs["enable"] = kwargs.pop("enabled")
    elif "enabled" in kwargs and "enable" not in params:
        kwargs.pop("enabled")

    accepts_varkw = any(p.kind == p.VAR_KEYWORD for p in params.values())
    if not accepts_varkw:
        kwargs = {k: v for k, v in kwargs.items() if k in params}

    return func(*args, **kwargs)

def add_instance_compat(client, **kwargs):
    logger.debug(f"注册实例参数: {json.dumps({k: v if k != 'metadata' else str(v) for k, v in kwargs.items()}, indent=2)}")
    return _call_with_supported_kwargs(client.add_naming_instance, **kwargs)

def send_heartbeat_compat(client, **kwargs):
    logger.debug(f"发送心跳参数: {json.dumps({k: v if k != 'metadata' else str(v) for k, v in kwargs.items()}, indent=2)}")
    return _call_with_supported_kwargs(client.send_heartbeat, **kwargs)

def remove_instance_compat(client, **kwargs):
    logger.debug(f"移除实例参数: {json.dumps({k: v if k != 'metadata' else str(v) for k, v in kwargs.items()}, indent=2)}")
    return _call_with_supported_kwargs(client.remove_naming_instance, **kwargs)

# -----------------------------
# 增强的服务注册和心跳
# -----------------------------
def register_service() -> None:
    """增强的服务注册"""
    global is_connected, connection_stats
    
    connection_stats['total_attempts'] += 1
    
    metadata = {"walletAddress": WALLET_ADDRESS, "node": NODE}
    logger.info(f"🔄 尝试注册服务 (第{connection_stats['total_attempts']}次)")
    logger.info(f"   服务名: {SERVICE_NAME}")
    logger.info(f"   IP: {PUBLIC_IP}")
    logger.info(f"   端口: {PORT}")
    logger.info(f"   分组: {NACOS_GROUP}")
    logger.info(f"   集群: {NACOS_CLUSTER or 'None'}")
    logger.info(f"   元数据: {metadata}")

    try:
        add_instance_compat(
            client,
            service_name=SERVICE_NAME,
            ip=PUBLIC_IP,
            port=PORT,
            group_name=NACOS_GROUP,
            cluster_name=(NACOS_CLUSTER or None),
            metadata=metadata,
            ephemeral=True,
            enabled=True,
            healthy=True,
        )
        
        is_connected = True
        connection_stats['successful_connections'] += 1
        connection_stats['last_success_time'] = time.time()
        connection_stats['last_error'] = None
        
        logger.info("✅ 服务注册成功!")
        logger.info(f"   连接统计: 成功{connection_stats['successful_connections']}次, 失败{connection_stats['failed_connections']}次")
        
    except Exception as e:
        is_connected = False
        connection_stats['failed_connections'] += 1
        connection_stats['last_error'] = str(e)
        
        logger.error(f"❌ 服务注册失败: {e}")
        logger.error(f"   错误类型: {type(e).__name__}")
        logger.error(f"   连接统计: 成功{connection_stats['successful_connections']}次, 失败{connection_stats['failed_connections']}次")
        raise

def attempt_reconnect_once() -> bool:
    """增强的重连尝试"""
    global client, is_connected
    
    with reconnect_lock:
        if stop_event.is_set():
            return False
        
        logger.info("🔄 尝试重新连接...")
        try:
            client = create_nacos_client()
            register_service()
            return True
        except Exception as e:
            is_connected = False
            logger.error(f"重连失败: {e}")
            return False

def backoff_delay(attempt: int) -> int:
    delay = min(INITIAL_RECONNECT_DELAY * (2 ** max(0, attempt - 1)), MAX_RECONNECT_DELAY)
    logger.debug(f"计算退避延迟: 尝试{attempt}次 -> {delay}秒")
    return delay

def reconnect_worker():
    """增强的重连工作线程"""
    attempt = 1
    logger.info("🔄 重连工作线程启动")
    
    while not stop_event.is_set():
        if not is_connected:
            logger.info(f"🔄 重连尝试 #{attempt}")
            if attempt_reconnect_once():
                logger.info("✅ 重连成功，恢复正常运行")
                attempt = 1
            else:
                delay = backoff_delay(attempt)
                logger.warning(f"❌ 重连尝试 #{attempt} 失败，{delay}秒后重试")
                attempt += 1
                stop_event.wait(delay)
        else:
            stop_event.wait(HEARTBEAT_INTERVAL)

def heartbeat_worker():
    """增强的心跳工作线程"""
    fail_count = 0
    logger.info("💓 心跳工作线程启动")
    
    while not stop_event.is_set():
        if is_connected:
            try:
                logger.debug("💓 发送心跳...")
                send_heartbeat_compat(
                    client,
                    service_name=SERVICE_NAME,
                    ip=PUBLIC_IP,
                    port=PORT,
                    group_name=NACOS_GROUP,
                    cluster_name=(NACOS_CLUSTER or None),
                    metadata={"walletAddress": WALLET_ADDRESS, "node": NODE},
                    ephemeral=True,
                )
                
                connection_stats['heartbeat_success_count'] += 1
                fail_count = 0
                logger.debug("💓 心跳成功")
                
            except Exception as e:
                fail_count += 1
                connection_stats['heartbeat_fail_count'] += 1
                logger.error(f"💓 心跳失败 ({fail_count}): {e}")
                
                if fail_count >= 3:
                    logger.warning("💓 连续心跳失败3次，标记为断开连接")
                    global is_connected
                    is_connected = False
                    fail_count = 0
        else:
            logger.debug("💓 未连接，跳过心跳")
        
        stop_event.wait(HEARTBEAT_INTERVAL)

def graceful_shutdown(*_args):
    """增强的优雅关闭"""
    logger.info("🛑 开始优雅关闭...")
    stop_event.set()
    
    try:
        if client and is_connected:
            logger.info("🔄 尝试注销服务...")
            remove_instance_compat(
                client,
                service_name=SERVICE_NAME,
                ip=PUBLIC_IP,
                port=PORT,
                group_name=NACOS_GROUP,
                cluster_name=(NACOS_CLUSTER or None),
                ephemeral=True,
            )
            logger.info("✅ 服务注销成功")
        else:
            logger.info("ℹ️  无需注销服务（未连接或客户端不存在）")
    except Exception as e:
        logger.error(f"❌ 服务注销失败: {e}")
    
    # 输出连接统计
    logger.info("📊 连接统计信息:")
    logger.info(f"   总尝试次数: {connection_stats['total_attempts']}")
    logger.info(f"   成功连接次数: {connection_stats['successful_connections']}")
    logger.info(f"   失败连接次数: {connection_stats['failed_connections']}")
    logger.info(f"   心跳成功次数: {connection_stats['heartbeat_success_count']}")
    logger.info(f"   心跳失败次数: {connection_stats['heartbeat_fail_count']}")
    if connection_stats['last_success_time']:
        logger.info(f"   最后成功时间: {time.ctime(connection_stats['last_success_time'])}")
    if connection_stats['last_error']:
        logger.info(f"   最后错误: {connection_stats['last_error']}")

# -----------------------------
# Flask routes (增强)
# -----------------------------
@app.get("/health")
def health():
    """增强的健康检查端点"""
    health_data = {
        "service": SERVICE_NAME,
        "status": "UP" if is_connected else "DEGRADED",
        "public_ip": PUBLIC_IP,
        "port": PORT,
        "node": NODE,
        "nacos_server": NACOS_SERVER,
        "group": NACOS_GROUP,
        "cluster": NACOS_CLUSTER or "",
        "connection_stats": connection_stats,
        "timestamp": time.time()
    }
    
    logger.debug(f"健康检查请求: {health_data}")
    return jsonify(health_data), (200 if is_connected else 206)

@app.get("/debug")
def debug():
    """调试信息端点"""
    debug_data = {
        "environment": {
            "NACOS_SERVER": NACOS_SERVER,
            "PUBLIC_IP": PUBLIC_IP,
            "PORT": PORT,
            "SERVICE_NAME": SERVICE_NAME,
            "WALLET_ADDRESS": WALLET_ADDRESS[:10] + "..." + WALLET_ADDRESS[-6:] if WALLET_ADDRESS else None,
            "NODE": NODE,
            "NACOS_GROUP": NACOS_GROUP,
            "NACOS_CLUSTER": NACOS_CLUSTER,
            "NACOS_USERNAME": NACOS_USERNAME or None,
            "NACOS_PASSWORD": "***" if NACOS_PASSWORD else None,
        },
        "connection_stats": connection_stats,
        "is_connected": is_connected,
        "timestamp": time.time()
    }
    
    return jsonify(debug_data), 200

@app.get("/")
def root():
    return "OK", 200

# -----------------------------
# Main (增强)
# -----------------------------
def main():
    logger.info("🚀 启动增强版Nacos客户端")
    
    # 记录环境信息
    log_environment_info()
    log_network_info()
    log_nacos_server_info()
    
    # 验证和检查
    validate_env_or_die()
    preflight_or_die()

    # 注册信号处理
    signal.signal(signal.SIGINT, graceful_shutdown)
    signal.signal(signal.SIGTERM, graceful_shutdown)

    # 启动后台线程
    logger.info("🔄 启动后台工作线程")
    threading.Thread(target=reconnect_worker, name="reconnector", daemon=True).start()
    threading.Thread(target=heartbeat_worker, name="heartbeat", daemon=True).start()

    # 尝试初始连接
    try:
        logger.info("🔄 尝试初始连接...")
        global client
        client = create_nacos_client()
        register_service()
        logger.info("✅ 初始连接成功")
    except Exception as e:
        logger.warning(f"⚠️  初始连接失败，后台线程将继续重试: {e}")

    # 启动Flask应用
    logger.info(f"🌐 启动Flask应用: 0.0.0.0:{PORT}")
    logger.info(f"   健康检查: http://localhost:{PORT}/health")
    logger.info(f"   调试信息: http://localhost:{PORT}/debug")
    
    app.run(host="0.0.0.0", port=PORT, debug=False)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("👋 收到中断信号")
    except Exception as e:
        logger.error(f"💥 程序异常退出: {e}")
        raise
    finally:
        graceful_shutdown()
