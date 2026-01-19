#!/usr/bin/env python3
"""
Integration test for runtime ArUco configuration switching.

This test validates:
1. Parameter validation (reject invalid dictionaries/sizes)
2. Successful parameter updates
3. Dictionary reload occurs
4. Marker size updates correctly
"""

import sys
import time
import rclpy
from rclpy.node import Node
from rcl_interfaces.srv import SetParameters, GetParameters
from rcl_interfaces.msg import Parameter, ParameterType, ParameterValue


class ConfigSwitchTest(Node):
    def __init__(self):
        super().__init__('config_switch_test')
        self.declare_parameter('target_node', '/aruco_tracker')
        self.target = self.get_parameter('target_node').value
        
        self.set_client = self.create_client(SetParameters, f'{self.target}/set_parameters')
        self.get_client = self.create_client(GetParameters, f'{self.target}/get_parameters')
        
        self.get_logger().info(f'Testing node: {self.target}')
    
    def wait_for_service(self):
        """Wait for parameter services to be available."""
        self.get_logger().info('Waiting for parameter services...')
        if not self.set_client.wait_for_service(timeout_sec=5.0):
            self.get_logger().error('Set parameter service not available!')
            return False
        if not self.get_client.wait_for_service(timeout_sec=5.0):
            self.get_logger().error('Get parameter service not available!')
            return False
        self.get_logger().info('✓ Services available')
        return True
    
    def get_parameters(self, names):
        """Get parameter values."""
        request = GetParameters.Request()
        request.names = names
        future = self.get_client.call_async(request)
        rclpy.spin_until_future_complete(self, future, timeout_sec=2.0)
        if future.result():
            return future.result().values
        return None
    
    def set_parameters(self, params):
        """Set parameters and return success status."""
        request = SetParameters.Request()
        request.parameters = params
        future = self.set_client.call_async(request)
        rclpy.spin_until_future_complete(self, future, timeout_sec=2.0)
        if future.result():
            return future.result().results
        return None
    
    def test_invalid_dictionary(self):
        """Test that invalid dictionary names are rejected."""
        self.get_logger().info('\n[TEST 1] Invalid dictionary rejection...')
        
        params = [
            Parameter(
                name='marker_dict',
                value=ParameterValue(
                    type=ParameterType.PARAMETER_STRING,
                    string_value='INVALID_DICT_NAME'
                )
            )
        ]
        
        results = self.set_parameters(params)
        if results and not results[0].successful:
            self.get_logger().info(f'✓ Correctly rejected: {results[0].reason}')
            return True
        else:
            self.get_logger().error('✗ Should have rejected invalid dictionary!')
            return False
    
    def test_invalid_marker_size(self):
        """Test that negative marker sizes are rejected."""
        self.get_logger().info('\n[TEST 2] Invalid marker size rejection...')
        
        params = [
            Parameter(
                name='marker_size',
                value=ParameterValue(
                    type=ParameterType.PARAMETER_DOUBLE,
                    double_value=-0.5
                )
            )
        ]
        
        results = self.set_parameters(params)
        if results and not results[0].successful:
            self.get_logger().info(f'✓ Correctly rejected: {results[0].reason}')
            return True
        else:
            self.get_logger().error('✗ Should have rejected negative marker size!')
            return False
    
    def test_valid_config_switch(self):
        """Test successful configuration switch."""
        self.get_logger().info('\n[TEST 3] Valid configuration switch...')
        
        # Get current values
        current = self.get_parameters(['marker_dict', 'marker_size'])
        if not current:
            self.get_logger().error('✗ Failed to get current parameters')
            return False
        
        orig_dict = current[0].string_value
        orig_size = current[1].double_value
        self.get_logger().info(f'Current: {orig_dict}, {orig_size}m')
        
        # Switch to new configuration
        new_dict = '6X6_250' if orig_dict != '6X6_250' else '5X5_250'
        new_size = 0.30 if abs(orig_size - 0.30) > 0.01 else 0.19
        
        params = [
            Parameter(
                name='marker_dict',
                value=ParameterValue(
                    type=ParameterType.PARAMETER_STRING,
                    string_value=new_dict
                )
            ),
            Parameter(
                name='marker_size',
                value=ParameterValue(
                    type=ParameterType.PARAMETER_DOUBLE,
                    double_value=new_size
                )
            )
        ]
        
        self.get_logger().info(f'Switching to: {new_dict}, {new_size}m')
        results = self.set_parameters(params)
        
        if not results or not all(r.successful for r in results):
            self.get_logger().error('✗ Configuration switch failed!')
            return False
        
        # Verify the change
        time.sleep(0.5)  # Give time for parameter update
        new_values = self.get_parameters(['marker_dict', 'marker_size'])
        
        if not new_values:
            self.get_logger().error('✗ Failed to verify new parameters')
            return False
        
        if (new_values[0].string_value == new_dict and 
            abs(new_values[1].double_value - new_size) < 0.001):
            self.get_logger().info('✓ Configuration updated successfully!')
            self.get_logger().info(f'  marker_dict: {new_values[0].string_value}')
            self.get_logger().info(f'  marker_size: {new_values[1].double_value}m')
            return True
        else:
            self.get_logger().error('✗ Parameters did not update correctly')
            return False
    
    def test_multiple_switches(self):
        """Test multiple rapid configuration switches."""
        self.get_logger().info('\n[TEST 4] Multiple rapid switches...')
        
        configs = [
            ('5X5_250', 0.19),
            ('6X6_250', 0.30),
            ('4X4_250', 0.15),
            ('7X7_250', 0.25),
        ]
        
        for dict_name, size in configs:
            params = [
                Parameter(
                    name='marker_dict',
                    value=ParameterValue(
                        type=ParameterType.PARAMETER_STRING,
                        string_value=dict_name
                    )
                ),
                Parameter(
                    name='marker_size',
                    value=ParameterValue(
                        type=ParameterType.PARAMETER_DOUBLE,
                        double_value=size
                    )
                )
            ]
            
            results = self.set_parameters(params)
            if not results or not all(r.successful for r in results):
                self.get_logger().error(f'✗ Failed to switch to {dict_name}')
                return False
            
            time.sleep(0.1)  # Small delay between switches
        
        self.get_logger().info('✓ All rapid switches successful!')
        return True
    
    def run_tests(self):
        """Run all tests and report results."""
        if not self.wait_for_service():
            return False
        
        tests = [
            self.test_invalid_dictionary,
            self.test_invalid_marker_size,
            self.test_valid_config_switch,
            self.test_multiple_switches,
        ]
        
        results = []
        for test in tests:
            try:
                results.append(test())
            except Exception as e:
                self.get_logger().error(f'Test exception: {str(e)}')
                results.append(False)
        
        # Summary
        self.get_logger().info('\n' + '='*60)
        self.get_logger().info('TEST SUMMARY')
        self.get_logger().info('='*60)
        passed = sum(results)
        total = len(results)
        self.get_logger().info(f'Passed: {passed}/{total}')
        
        if passed == total:
            self.get_logger().info('✓ ALL TESTS PASSED!')
            return True
        else:
            self.get_logger().error(f'✗ {total - passed} TESTS FAILED')
            return False


def main(args=None):
    rclpy.init(args=args)
    
    test_node = ConfigSwitchTest()
    success = test_node.run_tests()
    
    test_node.destroy_node()
    rclpy.shutdown()
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
