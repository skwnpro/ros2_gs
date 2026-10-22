#!/usr/bin/env python3
"""joystick_interface_node — penerjemah Radiomaster Boxer menjadi perintah.

Membaca topic /joy (dari joy_node) dan menerbitkan:
  * /robot_command  (brushkart_msgs/OperatorCommand)
        Perintah gerak untuk robot — satu-satunya keluaran yang menyeberang
        ke underwater robot lewat command_gateway_node.
  * /camera_select  (std_msgs/UInt8)
        Pilihan tampilan kamera untuk GUI di ground station.
        0 = mati, 1 = kamera depan, 2 = kamera belakang.
        Topic ini LOKAL ground station — tidak dikirim ke robot.

PETA KONTROL RADIOMASTER BOXER
Diukur dengan jstest-gtk (lihat catatan "Joystick_input_test" di vault):

  Axis 0  stick kanan kiri-kanan   kiri = +1,     kanan = -1
  Axis 1  stick kanan atas-bawah   atas = -1,     bawah = +1
  Axis 2  stick kiri  atas-bawah   atas = -1,     bawah = +1
  Axis 3  stick kiri  kiri-kanan   kanan = -1,    kiri  = +1
  Axis 4  SA (2 posisi)            atas = 0,      bawah = -1
  Axis 5  SB (3 posisi)            atas = +1,     tengah = 0,  bawah = -1
  Axis 6  SC (3 posisi)            atas = +1,     tengah = 0,  bawah = -1
  Button 0  SE (latching)          emergency stop
  Button 1  SF (momentary)         thruster assist (tahan untuk thruster)

ALOKASI FUNGSI
  Stick kiri        -> drive & steering (hidrolik)
  Stick kanan       -> 4 thruster DC (digital), digerbang tombol assist
  SA                -> brush on/off
  SB                -> mode: atas = OFF, tengah = MANUAL, bawah = AUTO
  SC                -> kamera: atas = mati, tengah = depan, bawah = belakang
  SE                -> emergency stop
  SF (ditahan)      -> thruster assist

KONVENSI ARAH (sesuai OperatorCommand.msg):
  drive > 0 = maju, steering > 0 = belok kanan.
  Karena stick kiri terbaca negatif saat ke atas / ke kanan, kedua nilai
  di bawah ini dibalik tandanya (drive = -axis2, steering = -axis3).
"""

import rclpy
from rclpy.node import Node

from sensor_msgs.msg import Joy
from std_msgs.msg import UInt8

from brushkart_msgs.msg import OperatorCommand


# --- Indeks axis & button pada message /joy (hasil tes jstest-gtk) ---
AXIS_THRUSTER_X = 0
AXIS_THRUSTER_Y = 1
AXIS_DRIVE = 2
AXIS_STEERING = 3
AXIS_BRUSH = 4
AXIS_MODE = 5
AXIS_CAMERA = 6

BUTTON_ESTOP = 0
BUTTON_THRUSTER_ASSIST = 1

# Nilai keluaran /camera_select
CAMERA_OFF = 0
CAMERA_FRONT = 1
CAMERA_BACK = 2


class JoystickInterfaceNode(Node):

    def __init__(self):
        super().__init__('joystick_interface_node')

        # Ambang posisi stick kanan untuk menyalakan thruster (0..1).
        self.declare_parameter('thruster_threshold', 0.5)
        self.thruster_threshold = self.get_parameter(
            'thruster_threshold').value

        self.command_pub = self.create_publisher(
            OperatorCommand, '/robot_command', 10)
        self.camera_pub = self.create_publisher(
            UInt8, '/camera_select', 10)

        self.joy_sub = self.create_subscription(
            Joy, '/joy', self.joy_callback, 10)

        # /camera_select hanya diterbitkan saat pilihan berubah.
        self._last_camera_select = None

        self.get_logger().info('Joystick Interface Node Started')

    # ------------------------------------------------------------------
    # Penerjemahan per kelompok kontrol
    # ------------------------------------------------------------------

    def _baca_mode(self, nilai_axis):
        """SB 3 posisi -> konstanta mode pada OperatorCommand."""
        if nilai_axis >= 0.5:
            return OperatorCommand.MODE_OFF       # SB atas
        if nilai_axis <= -0.5:
            return OperatorCommand.MODE_AUTO      # SB bawah
        return OperatorCommand.MODE_MANUAL        # SB tengah

    def _baca_kamera(self, nilai_axis):
        """SC 3 posisi -> pilihan tampilan kamera (lokal ground station)."""
        if nilai_axis >= 0.5:
            return CAMERA_OFF                     # SC atas
        if nilai_axis <= -0.5:
            return CAMERA_BACK                    # SC bawah
        return CAMERA_FRONT                       # SC tengah

    def _baca_thruster(self, x, y):
        """Stick kanan -> 4 thruster digital (pola pasangan).

        TABEL KEBENARAN (default — sesuaikan setelah geometri pemasangan
        thruster dipastikan; cukup ubah fungsi ini):

            stick atas    -> thruster 1 + 2
            stick bawah   -> thruster 3 + 4
            stick kiri    -> thruster 1 + 3
            stick kanan   -> thruster 2 + 4
            diagonal      -> gabungan (OR) dari dua arahnya
            tengah        -> semua mati

        Ingat arah bacaan stick kanan: x positif = kiri, y negatif = atas.
        """
        ambang = self.thruster_threshold
        atas = y < -ambang
        bawah = y > ambang
        kiri = x > ambang
        kanan = x < -ambang

        thruster_1 = atas or kiri
        thruster_2 = atas or kanan
        thruster_3 = bawah or kiri
        thruster_4 = bawah or kanan
        return thruster_1, thruster_2, thruster_3, thruster_4

    # ------------------------------------------------------------------
    # Callback utama
    # ------------------------------------------------------------------

    def joy_callback(self, msg):
        # Pesan /joy dari perangkat lain bisa punya jumlah axis/button
        # yang berbeda — abaikan yang tidak sesuai peta Boxer.
        if len(msg.axes) < 7 or len(msg.buttons) < 2:
            self.get_logger().warning(
                'Pesan /joy diabaikan: jumlah axis/button tidak sesuai '
                f'(axes={len(msg.axes)}, buttons={len(msg.buttons)})',
                throttle_duration_sec=5.0)
            return

        cmd = OperatorCommand()
        cmd.header.stamp = self.get_clock().now().to_msg()

        # Gerak utama — tanda dibalik agar positif = arah gerak
        # (lihat konvensi arah pada OperatorCommand.msg).
        cmd.drive = -msg.axes[AXIS_DRIVE]
        cmd.steering = -msg.axes[AXIS_STEERING]

        # Brush — SA di posisi bawah terbaca -1.
        cmd.brush_enable = msg.axes[AXIS_BRUSH] <= -0.5

        # Emergency stop — SE (latching).
        cmd.estop = msg.buttons[BUTTON_ESTOP] == 1

        # Thruster — hanya bermakna selama assist ditahan; gerbang
        # kedua ada di command_gateway_node.
        cmd.thruster_assist = msg.buttons[BUTTON_THRUSTER_ASSIST] == 1
        (cmd.thruster_1, cmd.thruster_2,
         cmd.thruster_3, cmd.thruster_4) = self._baca_thruster(
            msg.axes[AXIS_THRUSTER_X], msg.axes[AXIS_THRUSTER_Y])

        # Mode operasi — SB.
        cmd.mode = self._baca_mode(msg.axes[AXIS_MODE])

        self.command_pub.publish(cmd)

        # Pilihan kamera (SC) — lokal ground station, publish saat berubah.
        kamera = self._baca_kamera(msg.axes[AXIS_CAMERA])
        if kamera != self._last_camera_select:
            self._last_camera_select = kamera
            pesan = UInt8()
            pesan.data = kamera
            self.camera_pub.publish(pesan)


def main(args=None):
    rclpy.init(args=args)
    node = JoystickInterfaceNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
