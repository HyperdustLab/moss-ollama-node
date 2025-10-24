# Nacos HTTP API Client

This project provides multiple Python scripts to call Nacos HTTP API interfaces, specifically corresponding to the curl command you mentioned:

```bash
curl -svm 8 "http://nacos.hyperagi.network/nacos/v1/ns/instance/list?serviceName=test"
```

## File Description

### 1. `nacos_api_client.py` - Complete API Client

This is a fully functional Nacos HTTP API client with the following features:

- ✅ Get service instance list
- ✅ Get service details
- ✅ Register service instance
- ✅ Deregister service instance
- ✅ Send heartbeat
- ✅ Complete error handling
- ✅ Support authentication (username/password)

**Usage:**

```bash
python nacos_api_client.py
```

**Environment Variable Configuration:**

```bash
export NACOS_SERVER="http://nacos.hyperagi.network"
export NACOS_USERNAME="your_username"  # Optional
export NACOS_PASSWORD="your_password"  # Optional
export SERVICE_NAME="test"
```

### 2. `test_nacos_api.py` - Test Script Using requests Library

Specifically designed to test the API interface you mentioned, using the requests library.

**Usage:**

```bash
pip install requests
python test_nacos_api.py
```

### 3. `test_nacos_simple.py` - Test Script Using Standard Library

Uses Python standard library (urllib), no additional dependencies required.

**Usage:**

```bash
python test_nacos_simple.py
```

### 4. `run_test.bat` - Windows Batch File

Windows batch file for running tests in Windows environment.

**Usage:**

```bash
run_test.bat
```

## Main Features

### Get Service Instance List

Corresponding to your curl command, get all instances of the specified service:

```python
from nacos_api_client import NacosAPIClient

client = NacosAPIClient("http://nacos.hyperagi.network")
result = client.get_service_instance_list("test")
```

### Other API Operations

```python
# Get service details
detail = client.get_service_detail("test")

# Register instance
client.register_instance("test", "192.168.1.100", 8080)

# Deregister instance
client.deregister_instance("test", "192.168.1.100", 8080)

# Send heartbeat
client.send_heartbeat("test", "192.168.1.100", 8080)
```

## Output Example

After running the script, you will see output similar to the following:

```
🚀 Testing Nacos API call
==================================================
📡 Request URL: http://nacos.hyperagi.network/nacos/v1/ns/instance/list?serviceName=test

📊 Response status code: 200
📋 Response headers:
   Content-Type: application/json;charset=UTF-8
   Content-Length: 1234
   ...

✅ Request successful!
📄 JSON response content:
{
  "name": "test",
  "groupName": "DEFAULT_GROUP",
  "clusters": "...",
  "cacheMillis": 10000,
  "hosts": [
    {
      "ip": "192.168.1.100",
      "port": 8080,
      "weight": 1.0,
      "healthy": true,
      "enabled": true,
      "ephemeral": true,
      "clusterName": "DEFAULT",
      "serviceName": "test",
      "metadata": {}
    }
  ]
}

📊 Found 1 service instance:
   1. IP: 192.168.1.100
      Port: 8080
      Health status: True
      Enabled status: True
      Weight: 1.0
      Metadata: {}
```

## Error Handling

The script includes complete error handling and will display:

- Network connection errors
- HTTP status code errors
- JSON parsing errors
- Timeout errors

## Dependency Requirements

- **nacos_api_client.py**: Requires `requests` library
- **test_nacos_api.py**: Requires `requests` library
- **test_nacos_simple.py**: Uses only Python standard library, no additional dependencies required

Install requests library:

```bash
pip install requests
```

## Notes

1. Ensure network can access `nacos.hyperagi.network`
2. If Nacos server requires authentication, please set corresponding username and password
3. Service name "test" may need to be modified according to actual situation
4. Script will display detailed request and response information for easy debugging
