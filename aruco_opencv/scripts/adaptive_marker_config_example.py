#!/usr/bin/env python3
"""
Example: Programmatically switch ArUco marker configuration based on detection distance.

This demonstrates adaptive marker configuration for optimal detection at different ranges:
- Close range (< 2m): Use 5X5_250 with small markers (0.19m)
- Long range (>= 2m): Use 6X6_250 with large markers (0.30m)
"""

import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from rcl_interfaces.srv import SetParameters
from rcl_interfaces.msg import Parameter as ParameterMsg
from rcl_interfaces.msg import ParameterType, ParameterValue
from aruco_opencv_msgs.msg import ArucoDetection
from geometry_msgs.msg import PoseStamped
import math


class AdaptiveMarkerConfig(Node):
    """
    Adaptively switches ArUco configuration based on detection quality/distance.
    """
    
    def __init__(self):
        super().__init__('adaptive_marker_config')
        
        # Parameters
        self.declare_parameter('aruco_node_name', '/tello1/aruco_tracker')
        self.declare_parameter('detection_topic', '/tello1/aruco_detections')
        self.declare_parameter('distance_threshold', 2.0)  # meters
        
        self.aruco_node = self.get_parameter('aruco_node_name').value
        self.detection_topic = self.get_parameter('detection_topic').value
        self.distance_threshold = self.get_parameter('distance_threshold').value
        
        # Current configuration
        self.current_dict = '5X5_250'
        self.current_size = 0.19
        self.is_long_range_mode = False
        
        # Subscription
        self.detection_sub = self.create_subscription(
            ArucoDetection,
            self.detection_topic,
            self.detection_callback,
            10
        )
        
        # Service client for parameter setting
        self.param_client = self.create_client(
            SetParameters,
            f'{self.aruco_node}/set_parameters'
        )
        
        self.get_logger().info(f'Adaptive config node started')
        self.get_logger().info(f'Monitoring: {self.detection_topic}')
        self.get_logger().info(f'Target node: {self.aruco_node}')
        self.get_logger().info(f'Distance threshold: {self.distance_threshold}m')
    
    def detection_callback(self, msg: ArucoDetection):
        """Process detection messages and adapt configuration."""
        
        if not msg.markers:
            # No markers detected
            return
        
        # Calculate average distance to detected markers
        total_distance = 0.0
        for marker in msg.markers:
            distance = math.sqrt(
                marker.pose.position.x ** 2 +
                marker.pose.position.y ** 2 +
                marker.pose.position.z ** 2
            )
            total_distance += distance
        
        avg_distance = total_distance / len(msg.markers)
        
        # Determine if we need to switch modes
        should_be_long_range = avg_distance >= self.distance_threshold
        
        if should_be_long_range != self.is_long_range_mode:
            if should_be_long_range:
                self.switch_to_long_range()
            else:
                self.switch_to_short_range()
    
    def switch_to_long_range(self):
        """Switch to large markers for long-range detection."""
        self.get_logger().info('Switching to LONG RANGE mode (6X6_250, 0.30m)')
        self.set_config('6X6_250', 0.30)
        self.is_long_range_mode = True
    
    def switch_to_short_range(self):
        """Switch to small markers for short-range navigation."""
        self.get_logger().info('Switching to SHORT RANGE mode (5X5_250, 0.19m)')
        self.set_config('5X5_250', 0.19)
        self.is_long_range_mode = False
    
    def set_config(self, dict_name: str, marker_size: float):
        """Set ArUco configuration parameters."""
        
        if not self.param_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().warn('Parameter service not available')
            return
        
        # Build parameter messages
        params = [
            ParameterMsg(
                name='marker_dict',
                value=ParameterValue(
                    type=ParameterType.PARAMETER_STRING,
                    string_value=dict_name
                )
            ),
            ParameterMsg(
                name='marker_size',
                value=ParameterValue(
                    type=ParameterType.PARAMETER_DOUBLE,
                    double_value=marker_size
                )
            )
        ]
        
        request = SetParameters.Request()
        request.parameters = params
        
        future = self.param_client.call_async(request)
        future.add_done_callback(self.param_set_callback)
        
        self.current_dict = dict_name
        self.current_size = marker_size
    
    def param_set_callback(self, future):
        """Handle parameter setting response."""
        try:
            response = future.result()
            if response.results[0].successful:
                self.get_logger().info('✓ Configuration updated')
            else:
                self.get_logger().error(
                    f'✗ Configuration failed: {response.results[0].reason}'
                )
        except Exception as e:
            self.get_logger().error(f'Parameter service call failed: {str(e)}')


def main(args=None):
    rclpy.init(args=args)
    
    node = AdaptiveMarkerConfig()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
