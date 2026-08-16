import subprocess
import json
import sys

init_payload = json.dumps({
    'jsonrpc': '2.0',
    'id': 1,
    'method': 'initialize',
    'params': {
        'protocolVersion': '2024-11-05',
        'capabilities': {},
        'clientInfo': {'name': 'test-client', 'version': '1.0.0'}
    }
}) + '\n'

initialized_notification = json.dumps({
    'jsonrpc': '2.0',
    'method': 'notifications/initialized'
}) + '\n'

tools_list_payload = json.dumps({
    'jsonrpc': '2.0',
    'id': 2,
    'method': 'tools/list',
    'params': {}
}) + '\n'

input_data = init_payload + initialized_notification + tools_list_payload

proc = subprocess.Popen(
    ['uv', 'run', 'python', '-m', 'server.main', '--transport', 'stdio'],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    cwd=r'C:\Users\KIIT\OneDrive\Desktop\DSA PROJECT MCP'
)
stdout, stderr = proc.communicate(input=input_data, timeout=20)
print('STDOUT:', stdout[:3000], flush=True)
print('STDERR:', stderr[:500], flush=True)
