# Nacos 注册问题排查指南

## 🚀 快速开始

### 1. 环境变量验证

```bash
python validate_env.py
```

### 2. 网络连通性检查

```bash
python nacos_network_check.py
```

### 3. 使用增强调试版本

```bash
python nacos_client_debug.py
```

## 🔍 详细排查步骤

### 步骤 1: 环境变量检查

**必需的环境变量:**

```bash
export NACOS_SERVER="http://nacos.hyperagi.network:80"
export PUBLIC_IP="你的公网IP"
export PORT="11434"
export SERVICE_NAME="你的服务名"
export WALLET_ADDRESS="你的以太坊钱包地址"
```

**可选的环境变量:**

```bash
export NACOS_USERNAME="用户名"  # 如果Nacos需要认证
export NACOS_PASSWORD="密码"    # 如果Nacos需要认证
export NACOS_GROUP="DEFAULT_GROUP"  # 服务分组
export NACOS_CLUSTER="集群名"        # 集群名称
export NODE="节点标识"               # 节点标识，默认使用PUBLIC_IP
```

**常见问题:**

- ❌ `WALLET_ADDRESS` 格式错误 → 确保是有效的以太坊地址
- ❌ `PUBLIC_IP` 为空 → 设置正确的公网 IP 地址
- ❌ `SERVICE_NAME` 包含特殊字符 → 只使用字母、数字、连字符和下划线

### 步骤 2: 网络连通性检查

**DNS 解析问题:**

```bash
# 测试DNS解析
nslookup nacos.hyperagi.network
# 或
dig nacos.hyperagi.network
```

**TCP 连接问题:**

```bash
# 测试TCP连接
telnet nacos.hyperagi.network 80
# 或
nc -zv nacos.hyperagi.network 80
```

**HTTP 端点问题:**

```bash
# 测试HTTP端点
curl -v http://nacos.hyperagi.network:80/nacos/v1/console/health
curl -v http://nacos.hyperagi.network:80/v1/console/health
```

**常见网络问题:**

- ❌ DNS 解析失败 → 检查 DNS 设置，尝试使用公共 DNS (8.8.8.8)
- ❌ TCP 连接超时 → 检查防火墙设置，确认端口 80/443 未被阻止
- ❌ HTTP 请求失败 → 检查代理设置，确认网络策略

### 步骤 3: 端口占用检查

**检查本地端口:**

```bash
# Windows
netstat -ano | findstr :11434
# Linux/Mac
lsof -i :11434
```

**常见端口问题:**

- ❌ 端口被占用 → 更换端口或停止占用进程
- ❌ 权限不足 → 使用管理员权限运行

### 步骤 4: 详细日志分析

**启用详细日志:**

```bash
export LOG_LEVEL="DEBUG"
export LOG_FILE="nacos_debug.log"
python nacos_client_debug.py
```

**关键日志信息:**

- 🔍 DNS 解析结果
- 🔗 TCP 连接状态
- 🌐 HTTP 探针结果
- 🔄 注册尝试过程
- 💓 心跳状态
- ❌ 错误详情

## 🛠️ 常见问题解决方案

### 问题 1: DNS 解析失败

**症状:** `DNS FAIL: nacos.hyperagi.network not resolvable`

**解决方案:**

1. 检查网络连接
2. 更换 DNS 服务器:
   ```bash
   # Windows
   netsh interface ip set dns "以太网" static 8.8.8.8
   # Linux
   echo "nameserver 8.8.8.8" >> /etc/resolv.conf
   ```
3. 尝试使用 IP 地址直接连接:
   ```bash
   export NACOS_SERVER="http://IP地址:80"
   ```

### 问题 2: TCP 连接超时

**症状:** `TCP FAIL: nacos.hyperagi.network:80 not reachable`

**解决方案:**

1. 检查防火墙设置
2. 检查代理配置
3. 尝试不同端口 (443 for HTTPS)
4. 检查网络策略和路由

### 问题 3: HTTP 请求失败

**症状:** `HTTP PROBE failed on all known health endpoints`

**解决方案:**

1. 检查 Nacos 服务器状态
2. 尝试不同的健康检查端点
3. 检查认证配置
4. 验证服务器地址格式

### 问题 4: 服务注册失败

**症状:** `Registered failed: ...`

**解决方案:**

1. 检查服务名称是否已存在
2. 验证 IP 和端口配置
3. 检查 Nacos 认证信息
4. 确认分组和集群配置

### 问题 5: 心跳失败

**症状:** `Heartbeat FAIL`

**解决方案:**

1. 检查网络稳定性
2. 调整心跳间隔
3. 检查 Nacos 服务器负载
4. 验证服务实例状态

## 🔧 高级调试技巧

### 1. 使用 Wireshark 抓包

```bash
# 过滤Nacos相关流量
tcp.port == 80 and host nacos.hyperagi.network
```

### 2. 使用 tcpdump 监控

```bash
# 监控网络流量
tcpdump -i any host nacos.hyperagi.network
```

### 3. 检查系统资源

```bash
# 检查内存和CPU使用
top
htop
```

### 4. 验证 Python 环境

```bash
# 检查依赖包版本
pip list | grep nacos
pip list | grep flask
pip list | grep eth-utils
```

## 📊 监控和告警

### 健康检查端点

```bash
# 检查服务状态
curl http://localhost:11434/health

# 获取调试信息
curl http://localhost:11434/debug
```

### 日志监控

```bash
# 实时查看日志
tail -f nacos_debug.log

# 过滤错误日志
grep "ERROR\|FAIL" nacos_debug.log
```

## 🚨 紧急故障处理

### 1. 服务无法启动

- 检查环境变量
- 验证网络连通性
- 查看错误日志

### 2. 注册后立即断开

- 检查心跳配置
- 验证网络稳定性
- 调整重连参数

### 3. 多实例冲突

- 检查 IP 和端口配置
- 验证服务名称唯一性
- 确认分组和集群设置

## 📞 获取帮助

如果以上方法都无法解决问题，请提供以下信息:

1. **环境信息:**

   - 操作系统版本
   - Python 版本
   - 依赖包版本

2. **配置信息:**

   - 环境变量设置
   - 网络配置
   - 防火墙设置

3. **错误日志:**

   - 完整的错误堆栈
   - 网络检查结果
   - 调试日志文件

4. **复现步骤:**
   - 详细的操作步骤
   - 预期结果 vs 实际结果
   - 问题出现的频率

## 🔗 相关资源

- [Nacos 官方文档](https://nacos.io/zh-cn/docs/quick-start.html)
- [Python Nacos SDK](https://github.com/nacos-group/nacos-sdk-python)
- [Flask 文档](https://flask.palletsprojects.com/)
- [以太坊地址验证](https://eth-utils.readthedocs.io/)
