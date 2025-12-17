"""
Unit Tests for CGMiner Client
CGMiner客户端单元测试

Uses mock TCP server to simulate CGMiner responses
"""

import pytest
import socket
import threading
import json
import time
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, '.')

from services.cgminer_client import (
    CGMinerClient, CGMinerError, 
    get_normalized_telemetry, quick_probe,
    ALLOWED_COMMANDS
)


class MockCGMinerServer:
    """Mock TCP server simulating CGMiner API"""
    
    def __init__(self, host='127.0.0.1', port=0):
        self.host = host
        self.port = port
        self.server_socket = None
        self.running = False
        self.responses = {}
        self._thread = None
    
    def set_response(self, command: str, response: dict):
        """Set response for a command"""
        self.responses[command] = response
    
    def start(self):
        """Start the mock server"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.port = self.server_socket.getsockname()[1]
        self.server_socket.listen(5)
        self.server_socket.settimeout(1.0)
        self.running = True
        
        self._thread = threading.Thread(target=self._serve)
        self._thread.daemon = True
        self._thread.start()
        time.sleep(0.1)
    
    def _serve(self):
        """Server loop"""
        while self.running:
            try:
                client_socket, addr = self.server_socket.accept()
                client_socket.settimeout(1.0)
                
                data = client_socket.recv(1024)
                if data:
                    request = json.loads(data.decode('utf-8'))
                    command = request.get('command', '')
                    
                    response = self.responses.get(command, {
                        'STATUS': [{'STATUS': 'E', 'Msg': 'Unknown command'}]
                    })
                    
                    response_bytes = json.dumps(response).encode('utf-8') + b'\x00'
                    client_socket.sendall(response_bytes)
                
                client_socket.close()
            except socket.timeout:
                continue
            except Exception:
                break
    
    def stop(self):
        """Stop the mock server"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        if self._thread:
            self._thread.join(timeout=2)


@pytest.fixture
def mock_server():
    """Fixture providing a mock CGMiner server"""
    server = MockCGMinerServer()
    server.set_response('summary', {
        'STATUS': [{'STATUS': 'S', 'Msg': 'Summary'}],
        'SUMMARY': [{
            'GHS 5s': 95.5,
            'GHS av': 94.2,
            'Elapsed': 86400,
            'Accepted': 1000,
            'Rejected': 5
        }]
    })
    server.set_response('stats', {
        'STATUS': [{'STATUS': 'S'}],
        'STATS': [{
            'temp1': 65.0,
            'temp2': 68.0,
            'temp3': 67.0,
            'fan1': 4200,
            'fan2': 4100
        }]
    })
    server.set_response('pools', {
        'STATUS': [{'STATUS': 'S'}],
        'POOLS': [{
            'URL': 'stratum+tcp://pool.example.com:3333',
            'User': 'worker1',
            'Status': 'Alive',
            'Stratum Active': True
        }]
    })
    server.set_response('version', {
        'STATUS': [{'STATUS': 'S'}],
        'VERSION': [{'CGMiner': '4.11.1', 'API': '3.7'}]
    })
    
    server.start()
    yield server
    server.stop()


class TestCGMinerClientValidation:
    """Test input validation"""
    
    def test_valid_ip_address(self):
        client = CGMinerClient('192.168.1.100')
        assert client.host == '192.168.1.100'
    
    def test_valid_hostname(self):
        client = CGMinerClient('miner-01.local')
        assert client.host == 'miner-01.local'
    
    def test_invalid_ip_address(self):
        with pytest.raises(ValueError):
            CGMinerClient('999.999.999.999')
    
    def test_empty_host(self):
        with pytest.raises(ValueError):
            CGMinerClient('')
    
    def test_valid_port(self):
        client = CGMinerClient('192.168.1.1', port=4029)
        assert client.port == 4029
    
    def test_invalid_port_zero(self):
        with pytest.raises(ValueError):
            CGMinerClient('192.168.1.1', port=0)
    
    def test_invalid_port_too_high(self):
        with pytest.raises(ValueError):
            CGMinerClient('192.168.1.1', port=70000)


class TestCGMinerClientCommands:
    """Test command execution"""
    
    def test_get_summary(self, mock_server):
        client = CGMinerClient('127.0.0.1', mock_server.port, timeout=2)
        result = client.get_summary()
        
        assert 'SUMMARY' in result
        assert result['SUMMARY'][0]['GHS 5s'] == 95.5
    
    def test_get_stats(self, mock_server):
        client = CGMinerClient('127.0.0.1', mock_server.port, timeout=2)
        result = client.get_stats()
        
        assert 'STATS' in result
        assert result['STATS'][0]['temp1'] == 65.0
    
    def test_get_pools(self, mock_server):
        client = CGMinerClient('127.0.0.1', mock_server.port, timeout=2)
        result = client.get_pools()
        
        assert 'POOLS' in result
        assert 'pool.example.com' in result['POOLS'][0]['URL']
    
    def test_latency_tracking(self, mock_server):
        client = CGMinerClient('127.0.0.1', mock_server.port, timeout=2)
        client.get_summary()
        
        assert client.last_latency_ms > 0
        assert client.last_latency_ms < 1000
    
    def test_is_alive(self, mock_server):
        client = CGMinerClient('127.0.0.1', mock_server.port, timeout=2)
        alive, latency = client.is_alive()
        
        assert alive is True
        assert latency > 0
    
    def test_unknown_command_rejected(self, mock_server):
        client = CGMinerClient('127.0.0.1', mock_server.port)
        
        with pytest.raises(ValueError, match="Unknown command"):
            client.send_command('malicious_command')
    
    def test_control_command_blocked_by_default(self, mock_server):
        client = CGMinerClient('127.0.0.1', mock_server.port)
        
        with pytest.raises(ValueError, match="Control command"):
            client.send_command('restart')


class TestNormalizedTelemetry:
    """Test normalized telemetry extraction"""
    
    def test_get_normalized_telemetry(self, mock_server):
        client = CGMinerClient('127.0.0.1', mock_server.port, timeout=2)
        telemetry = get_normalized_telemetry(client)
        
        assert telemetry['status'] == 'online'
        assert telemetry['hashrate_5s'] == 95.5
        assert telemetry['hashrate_avg'] == 94.2
        assert telemetry['uptime'] == 86400
        assert telemetry['accepted'] == 1000
        assert telemetry['rejected'] == 5
        assert telemetry['temp_avg'] > 0
        assert telemetry['temp_max'] == 68.0
        assert len(telemetry['fan_speeds']) == 2
        assert 'pool.example.com' in telemetry['pool_url']
        assert telemetry['worker'] == 'worker1'
        assert telemetry['latency_ms'] > 0
        assert 'as_of' in telemetry


class TestQuickProbe:
    """Test quick_probe function"""
    
    def test_quick_probe_success(self, mock_server):
        result = quick_probe('127.0.0.1', mock_server.port, timeout=2)
        
        assert result['result'] == 'OK'
        assert result['status'] == 'online'
        assert result['hashrate_ghs'] == 95.5
        assert result['latency_ms'] > 0
    
    def test_quick_probe_connection_refused(self):
        result = quick_probe('127.0.0.1', 59999, timeout=1)
        
        assert result['result'] == 'FAIL'
        assert result['error'] is not None


class TestErrorHandling:
    """Test error scenarios"""
    
    def test_connection_timeout(self):
        client = CGMinerClient('10.255.255.1', timeout=0.5, max_retries=1)
        
        with pytest.raises(CGMinerError) as exc_info:
            client.get_summary()
        
        assert exc_info.value.error_type in ('timeout', 'connection')
    
    def test_connection_refused(self):
        client = CGMinerClient('127.0.0.1', port=59998, timeout=1, max_retries=1)
        
        with pytest.raises(CGMinerError) as exc_info:
            client.get_summary()
        
        assert exc_info.value.error_type == 'connection'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
