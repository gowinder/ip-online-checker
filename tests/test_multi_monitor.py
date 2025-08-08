#!/usr/bin/env python3

import unittest
import os
import tempfile
import yaml
import datetime
from unittest.mock import patch, MagicMock
from multi_monitor import NetworkMonitor, MultiNetworkMonitor


class TestNetworkMonitor(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.target_config = {
            'ip': '192.168.1.1',
            'mac': '',
            'enable': True,
            'ping_interval': 1,
            'offline_threshold': 2,
            'online_threshold': 2
        }
        
        self.global_config = {
            'global_ping_interval': 5,
            'global_offline_threshold': 60,
            'global_heartbeat_interval': 300,
            'slack': {
                'enabled': False,
                'webhook_url': '',
                'channel': ''
            }
        }
        
        # Create a temporary directory for logs
        self.test_log_dir = tempfile.mkdtemp()
        
    def test_network_monitor_initialization(self):
        """Test NetworkMonitor initialization with target config."""
        monitor = NetworkMonitor(self.target_config, self.global_config, self.test_log_dir)
        
        # Check that attributes are set correctly
        self.assertEqual(monitor.target_ip, '192.168.1.1')
        self.assertEqual(monitor.ping_interval, 1)
        self.assertEqual(monitor.offline_threshold, 2)
        self.assertTrue(monitor.enable)
        
        # Check that log file path is generated correctly
        expected_log_file = os.path.join(self.test_log_dir, 'mon_192_168_1_1.log')
        self.assertEqual(monitor.log_file, expected_log_file)
        
    def test_network_monitor_with_defaults(self):
        """Test NetworkMonitor initialization with minimal config."""
        minimal_target_config = {
            'ip': '192.168.1.2'
        }
        
        monitor = NetworkMonitor(minimal_target_config, self.global_config, self.test_log_dir)
        
        # Should use global defaults for missing values
        self.assertEqual(monitor.ping_interval, 5)  # from global config
        self.assertEqual(monitor.offline_threshold, 60)  # from global config
        self.assertTrue(monitor.enable)  # default value
        
    def test_format_duration(self):
        """Test duration formatting."""
        monitor = NetworkMonitor(self.target_config, self.global_config, self.test_log_dir)
        
        # Test seconds only
        start = datetime.datetime(2023, 1, 1, 12, 0, 0)
        end = datetime.datetime(2023, 1, 1, 12, 0, 30)
        self.assertEqual(monitor.format_duration(start, end), "30秒")
        
        # Test minutes and seconds
        end = datetime.datetime(2023, 1, 1, 12, 2, 30)
        self.assertEqual(monitor.format_duration(start, end), "2分钟30秒")
        
        # Test hours, minutes and seconds
        end = datetime.datetime(2023, 1, 1, 15, 2, 30)
        self.assertEqual(monitor.format_duration(start, end), "3小时2分钟30秒")
        
    @patch('subprocess.run')
    def test_ping_target_ip_success(self, mock_run):
        """Test ping_target method with successful IP ping."""
        # Mock successful ping
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        monitor = NetworkMonitor(self.target_config, self.global_config, self.test_log_dir)
        result = monitor.ping_target()
        
        # Verify ping was called with correct arguments
        mock_run.assert_called_once_with(
            ['ping', '-c', '1', '-W', '1', '192.168.1.1'],
            capture_output=True
        )
        self.assertTrue(result)
        
    @patch('subprocess.run')
    def test_ping_target_ip_failure(self, mock_run):
        """Test ping_target method with failed IP ping."""
        # Mock failed ping
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_run.return_value = mock_result
        
        monitor = NetworkMonitor(self.target_config, self.global_config, self.test_log_dir)
        result = monitor.ping_target()
        
        self.assertFalse(result)
        
    @patch('subprocess.run')
    def test_ping_target_mac_success(self, mock_run):
        """Test ping_target method with successful MAC check."""
        # Configure monitor to use MAC
        mac_config = self.target_config.copy()
        mac_config['mac'] = '00:11:22:33:44:55'
        
        # Mock ARP table containing the MAC
        mock_result = MagicMock()
        mock_result.stdout = "00:11:22:33:44:55"
        mock_run.return_value = mock_result
        
        monitor = NetworkMonitor(mac_config, self.global_config, self.test_log_dir)
        result = monitor.ping_target()
        
        # Verify arp was called
        mock_run.assert_called_once_with(['arp', '-a'], capture_output=True, text=True)
        self.assertTrue(result)


class TestMultiNetworkMonitor(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create a temporary config file
        self.test_config = {
            'targets': [
                {
                    'ip': '192.168.1.1',
                    'enable': True,
                    'ping_interval': 1
                },
                {
                    'ip': '192.168.1.2',
                    'enable': False,
                    'ping_interval': 2
                }
            ],
            'global_ping_interval': 5,
            'log_path': '/tmp/test_logs'
        }
        
        # Create temporary file
        self.temp_config_file = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
        yaml.dump(self.test_config, self.temp_config_file)
        self.temp_config_file.close()
        
    def tearDown(self):
        """Clean up after each test method."""
        os.unlink(self.temp_config_file.name)
        
    def test_multi_network_monitor_initialization(self):
        """Test MultiNetworkMonitor initialization."""
        monitor = MultiNetworkMonitor(self.temp_config_file.name)
        
        # Check that targets are loaded
        self.assertEqual(len(monitor.targets), 2)
        self.assertEqual(len(monitor.monitors), 2)
        
        # Check that first monitor has correct config
        first_monitor = monitor.monitors[0]
        self.assertEqual(first_monitor.target_ip, '192.168.1.1')
        self.assertTrue(first_monitor.enable)
        self.assertEqual(first_monitor.ping_interval, 1)
        
        # Check that second monitor has correct config
        second_monitor = monitor.monitors[1]
        self.assertEqual(second_monitor.target_ip, '192.168.1.2')
        self.assertFalse(second_monitor.enable)
        self.assertEqual(second_monitor.ping_interval, 2)


if __name__ == '__main__':
    unittest.main()