#!/usr/bin/env python3
"""robot_state_node — agregator kesehatan robot untuk ground station.

Membaca:
  * /sensor_data    (brushkart_msgs/SensorData)    dari underwater robot
  * /network_status (brushkart_msgs/NetworkStatus) dari underwater robot

Menerbitkan /robot_state (brushkart_msgs/RobotState) pada 2 Hz.

Aturan kesehatan:
  * Data yang sudah berhenti datang melewati batas waktu dianggap BASI
    dan diperlakukan sebagai fault — data terakhir tidak boleh membuat
    robot terlihat sehat selamanya.
  * Node ini selalu menerbitkan state, termasuk sebelum data pertama
    tiba (fault "menunggu data"), supaya konsumen (GUI) bisa
    membedakan "robot mati" dari "state belum jalan".

PERHATIAN nama field: RobotState.msg memakai field `connection`
(bukan `connected`). NetworkStatus.msg yang memakai `connected`.
"""

import time

import rclpy
from rclpy.node import Node

from brushkart_msgs.msg import NetworkStatus
from brushkart_msgs.msg import RobotState
from brushkart_msgs.msg import SensorData


class RobotStateNode(Node):

    def __init__(self):
        super().__init__('robot_state_node')

        # Batas umur data sebelum dianggap basi (detik).
        # /sensor_data terbit 10 Hz, /network_status 1 Hz.
        self.declare_parameter('sensor_timeout_s', 1.0)
        self.declare_parameter('network_timeout_s', 3.0)
        self.sensor_timeout = self.get_parameter('sensor_timeout_s').value
        self.network_timeout = self.get_parameter('network_timeout_s').value

        self.sensor_data = None
        self.network_data = None
        self.sensor_rx_time = None
        self.network_rx_time = None

        self.sensor_sub = self.create_subscription(
            SensorData, '/sensor_data', self.sensor_callback, 10)
        self.network_sub = self.create_subscription(
            NetworkStatus, '/network_status', self.network_callback, 10)
        self.robot_state_pub = self.create_publisher(
            RobotState, '/robot_state', 10)

        # Terbitkan state 2 Hz.
        self.timer = self.create_timer(0.5, self.publish_robot_state)

        self.get_logger().info('Robot State Node Started')

    # ------------------------------------------------------------------
    # Penerimaan data (catat isi + waktu terimanya)
    # ------------------------------------------------------------------

    def sensor_callback(self, msg):
        self.sensor_data = msg
        self.sensor_rx_time = time.monotonic()

    def network_callback(self, msg):
        self.network_data = msg
        self.network_rx_time = time.monotonic()

    # ------------------------------------------------------------------
    # Penilaian kesehatan
    # ------------------------------------------------------------------

    @staticmethod
    def _segar(rx_time, sekarang, batas):
        """True bila data pernah diterima dan belum melewati batas umur."""
        return rx_time is not None and sekarang - rx_time <= batas

    def publish_robot_state(self):
        sekarang = time.monotonic()
        msg = RobotState()
        msg.stamp = self.get_clock().now().to_msg()

        sensor_segar = self._segar(
            self.sensor_rx_time, sekarang, self.sensor_timeout)
        network_segar = self._segar(
            self.network_rx_time, sekarang, self.network_timeout)

        faults = []

        # --- Kesehatan sensor ---
        if self.sensor_data is None:
            faults.append('MENUNGGU DATA SENSOR')
        elif not sensor_segar:
            faults.append('DATA SENSOR BASI')
        msg.imu_ok = bool(
            sensor_segar and self.sensor_data and self.sensor_data.imu_ok)
        msg.pressure_ok = bool(
            sensor_segar and self.sensor_data
            and self.sensor_data.pressure_ok)
        if sensor_segar and self.sensor_data:
            if not self.sensor_data.imu_ok:
                faults.append('IMU FAULT')
            if not self.sensor_data.pressure_ok:
                faults.append('PRESSURE FAULT')

        # --- Kesehatan jaringan / koneksi ---
        if self.network_data is None:
            faults.append('MENUNGGU DATA JARINGAN')
        elif not network_segar:
            faults.append('DATA JARINGAN BASI')
        msg.connection = bool(
            network_segar and self.network_data
            and self.network_data.connected)
        msg.network_ok = msg.connection
        if network_segar and self.network_data \
                and not self.network_data.connected:
            faults.append('DISCONNECTED')

        # --- Kesimpulan ---
        msg.robot_ok = bool(
            msg.connection and msg.imu_ok
            and msg.pressure_ok and msg.network_ok)
        msg.fault = not msg.robot_ok
        msg.fault_message = 'OK' if not faults else ', '.join(faults)

        self.robot_state_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = RobotStateNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
