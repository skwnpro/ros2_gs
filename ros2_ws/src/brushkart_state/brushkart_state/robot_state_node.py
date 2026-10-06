#!/usr/bin/env python3

import rclpy

from rclpy.node import Node

from brushkart_msgs.msg import SensorData

from brushkart_msgs.msg import NetworkStatus

from brushkart_msgs.msg import RobotState

class RobotStateNode(Node):

    def __init__(self):

        super().__init__('robot_state_node')

        self.sensor_data = None

        self.network_data = None

        # Subscriber Sensor

        self.sensor_sub = self.create_subscription(

            SensorData,

            '/sensor_data',

            self.sensor_callback,

            10

        )

        # Subscriber Network

        self.network_sub = self.create_subscription(

            NetworkStatus,

            '/network_status',

            self.network_callback,

            10

        )

        # Publisher Robot State

        self.robot_state_pub = self.create_publisher(

            RobotState,

            '/robot_state',

            10

        )

        # Publish 2 Hz

        self.timer = self.create_timer(

            0.5,

            self.publish_robot_state

        )

        self.get_logger().info(

            'Robot State Node Started'

        )

    def sensor_callback(self, msg):

        self.sensor_data = msg

    def network_callback(self, msg):

        self.network_data = msg

    def publish_robot_state(self):

        if self.sensor_data is None:

            return

        if self.network_data is None:

            return

        msg = RobotState()

        # Timestamp

        msg.stamp = self.get_clock().now().to_msg()

        # Connection Status

        msg.connected = self.network_data.connected

        # Sensor Health

        msg.imu_ok = self.sensor_data.imu_ok

        msg.pressure_ok = self.sensor_data.pressure_ok

        # Network Health

        msg.network_ok = self.network_data.connected

        # Overall Robot Health

        msg.robot_ok = (

            msg.connected and

            msg.imu_ok and

            msg.pressure_ok and

            msg.network_ok

        )

        # Fault Flag

        msg.fault = not msg.robot_ok

        # Fault Message

        faults = []

        if not msg.connected:

            faults.append("DISCONNECTED")

        if not msg.imu_ok:

            faults.append("IMU_FAULT")

        if not msg.pressure_ok:

            faults.append("PRESSURE_FAULT")

        if not msg.network_ok:

            faults.append("NETWORK_FAULT")

        if len(faults) == 0:

            msg.fault_message = "OK"

        elif len(faults) == 1:

            msg.fault_message = faults[0]

        else:

            msg.fault_message = ",".join(faults)

        # Publish

        self.robot_state_pub.publish(msg)

        # Debug Log

        self.get_logger().info(

            f'robot_ok={msg.robot_ok} '

            f'fault={msg.fault} '

            f'message={msg.fault_message}'

        )

def main(args=None):

    rclpy.init(args=args)

    node = RobotStateNode()

    try:

        rclpy.spin(node)

    except KeyboardInterrupt:

        pass

    node.destroy_node()

    rclpy.shutdown()

if __name__ == '__main__':

    main()