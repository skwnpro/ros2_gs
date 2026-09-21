import rclpy

from rclpy.node import Node
from sensor_msgs.msg import Joy
from brushkart_msgs.msg import OperatorCommand

class JoystickInterfaceNode(Node):
 
	def __init__(self):
		super().__init__('joystick_interface_node')
		self.publisher_ = self.create_publisher(
		OperatorCommand,
		'/robot_command',
		10
		)

		self.subscription = self.create_subscription(
			Joy,
			'/joy',
			self.joy_callback,
			10
		)

	def joy_callback(self, msg):
		self.get_logger().info("JOY RECEIVED")
		cmd = OperatorCommand()
		cmd.drive = -msg.axes[2]
		cmd.steering = -msg.axes[3]
		cmd.thruster = -msg.axes[1]
		cmd.brush_enable = (msg.axes[4] == -1)
		cmd.estop = bool(msg.buttons[0])
		self.publisher_.publish(cmd)

def main(args=None):
	rclpy.init(args=args)
	node = JoystickInterfaceNode()
	rclpy.spin(node)
	node.destroy_node()
	rclpy.shutdown()

if __name__ == '__main__':
	main()
