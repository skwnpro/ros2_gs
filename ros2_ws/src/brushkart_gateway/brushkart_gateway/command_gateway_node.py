#!/usr/bin/env python3

import rclpy

from rclpy.node import Node

from brushkart_msgs.msg import OperatorCommand

from brushkart_msgs.msg import RelayOperator

class CommandGatewayNode(Node):

    DEADBAND = 0.30

    def __init__(self):

        super().__init__('command_gateway_node')

        self.command_sub = self.create_subscription(

            OperatorCommand,

            '/robot_command',

            self.command_callback,

            10

        )

        self.relay_pub = self.create_publisher(

            RelayOperator,

            '/relay_operator',

            10

        )

        self.get_logger().info(

            'Command Gateway Node Started'

        )

    def command_callback(self, msg):

        relay_msg = RelayOperator()

        # ==================================

        # Emergency Stop

        # ==================================

        if msg.estop:

            relay_msg.estop = True

            relay_msg.relay1_brush = False

            relay_msg.relay2_forward = False

            relay_msg.relay3_retreat = False

            relay_msg.relay4_left = False

            relay_msg.relay5_right = False

            relay_msg.relay6_light = False

            self.relay_pub.publish(relay_msg)

            self.get_logger().warn(

                'EMERGENCY STOP'

            )

            return

        relay_msg.estop = False

        # ==================================

        # Relay 1 - Brush

        # ==================================

        relay_msg.relay1_brush = msg.brush_enable

        # ==================================

        # Relay 2 & 3

        # Drive Control

        # ==================================

        relay_msg.relay2_forward = False

        relay_msg.relay3_retreat = False

        if msg.drive < -self.DEADBAND:

            relay_msg.relay2_forward = True

        elif msg.drive > self.DEADBAND:

            relay_msg.relay3_retreat = True

        # ==================================

        # Relay 4 & 5

        # Steering Control

        # ==================================

        relay_msg.relay4_left = False

        relay_msg.relay5_right = False

        if msg.steering > self.DEADBAND:

            relay_msg.relay4_left = True

        elif msg.steering < -self.DEADBAND:

            relay_msg.relay5_right = True

        # ==================================

        # Relay 6

        # Belum dipakai

        # ==================================

        relay_msg.relay6_light = False

        # ==================================

        # Publish

        # ==================================

        self.relay_pub.publish(relay_msg)

        self.get_logger().info(

            f'Brush={relay_msg.relay1_brush} '

            f'Fwd={relay_msg.relay2_forward} '

            f'Rev={relay_msg.relay3_retreat} '

            f'Left={relay_msg.relay4_left} '

            f'Right={relay_msg.relay5_right} '

            f'Estop={relay_msg.estop}'

        )

def main(args=None):

    rclpy.init(args=args)

    node = CommandGatewayNode()

    try:

        rclpy.spin(node)

    except KeyboardInterrupt:

        pass

    finally:

        node.destroy_node()

        rclpy.shutdown()

if __name__ == '__main__':

    main()