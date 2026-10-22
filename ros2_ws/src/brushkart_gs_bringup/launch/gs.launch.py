"""Launch seluruh stack GROUND STATION Brush Kart dalam satu perintah.

Jalankan dari workspace ros2_gs:
    ros2 launch brushkart_gs_bringup gs.launch.py

Node yang dinyalakan:
  1. joy_node                 — pembaca Radiomaster Boxer (package joy)
  2. joystick_interface_node  — penerjemah stick menjadi /robot_command
  3. command_gateway_node     — gerbang keselamatan -> /relay_operator
  4. robot_state_node         — agregator kesehatan -> /robot_state

GUI telemetri belum termasuk (belum dibuat); /robot_state dan
/camera_select sudah tersedia untuk dikonsumsi GUI kapan pun siap.
"""

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([

        # autorepeat_rate WAJIB diisi: tanpa pengulangan, /joy hanya
        # terbit saat stick bergerak. command_gateway_node akan
        # menganggap perintah basi dan mematikan relay setiap operator
        # menahan stick diam lebih dari command_timeout_s.
        Node(
            package='joy',
            executable='joy_node',
            name='joy_node',
            parameters=[{
                'device_id': 0,
                'deadzone': 0.05,
                'autorepeat_rate': 20.0,
            }],
        ),

        Node(
            package='brushkart_joystick',
            executable='joystick_interface_node',
            name='joystick_interface_node',
            output='screen',
        ),

        Node(
            package='brushkart_gateway',
            executable='command_gateway_node',
            name='command_gateway_node',
            output='screen',
        ),

        Node(
            package='brushkart_state',
            executable='robot_state_node',
            name='robot_state_node',
            output='screen',
        ),
    ])
