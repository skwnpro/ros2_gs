#!/usr/bin/env python3
"""command_gateway_node — gerbang keselamatan antara operator dan relay.

Membaca /robot_command (brushkart_msgs/OperatorCommand) dan menerbitkan
/relay_operator (brushkart_msgs/RelayOperator) ke relay_operator_node.

Tanggung jawab node ini:
  1. Menerjemahkan perintah analog (drive/steering) menjadi relay on/off
     dengan deadband di sekitar titik netral stick.
  2. Menjadi HEARTBEAT: /relay_operator diterbitkan terus-menerus pada
     laju tetap, bukan hanya saat ada perintah baru. Dengan begitu
     relay_operator_node bisa membedakan "operator diam" dari
     "pengirim mati".
  3. Menolak perintah basi: bila /robot_command berhenti datang lebih
     lama dari `command_timeout_s`, semua relay dimatikan.
  4. Menghormati prioritas: e-stop > mode OFF > mode AUTO (belum
     tersedia) > perintah manual.
  5. Menggerbang thruster dengan tombol assist, dan (opsional) membatasi
     lama maksimum sebuah relay gerak menyala terus-menerus lewat
     parameter `max_continuous_on_s`.

KONVENSI ARAH (sesuai OperatorCommand.msg):
  drive > 0 = maju -> relay2_forward
  steering > 0 = belok kanan -> relay5_right
"""

import time

import rclpy
from rclpy.node import Node

from brushkart_msgs.msg import OperatorCommand
from brushkart_msgs.msg import RelayOperator


class CommandGatewayNode(Node):

    def __init__(self):
        super().__init__('command_gateway_node')

        # --- Parameter (bisa diubah dari launch file / CLI) ---
        self.declare_parameter('deadband', 0.30)
        self.declare_parameter('publish_rate_hz', 20.0)
        self.declare_parameter('command_timeout_s', 0.5)
        # 0.0 = nonaktif. Aktifkan setelah durasi aman aktuator diketahui.
        self.declare_parameter('max_continuous_on_s', 0.0)

        self.deadband = self.get_parameter('deadband').value
        self.command_timeout = self.get_parameter('command_timeout_s').value
        self.max_on = self.get_parameter('max_continuous_on_s').value
        rate = self.get_parameter('publish_rate_hz').value

        self.command_sub = self.create_subscription(
            OperatorCommand, '/robot_command', self.command_callback, 10)
        self.relay_pub = self.create_publisher(
            RelayOperator, '/relay_operator', 10)

        # Perintah terakhir + kapan diterimanya (jam monotonik).
        self.last_command = None
        self.last_rx_time = None

        # Pelacak max-on-time: {nama_output: waktu mulai menyala}
        self._on_since = {}
        # Output yang sedang diblokir sampai perintahnya berubah.
        self._blocked = set()
        # Keadaan terakhir yang diterbitkan, untuk log perubahan saja.
        self._last_published = None

        self.timer = self.create_timer(1.0 / rate, self.publish_relay)

        self.get_logger().info('Command Gateway Node Started')

    # ------------------------------------------------------------------
    # Penerimaan perintah
    # ------------------------------------------------------------------

    def command_callback(self, msg):
        self.last_command = msg
        self.last_rx_time = time.monotonic()

    # ------------------------------------------------------------------
    # Penerjemahan perintah -> relay
    # ------------------------------------------------------------------

    def _relay_dari_perintah(self, cmd):
        """Terjemahkan satu OperatorCommand menjadi RelayOperator.

        Fungsi murni (tanpa efek samping) agar mudah diuji.
        """
        relay = RelayOperator()

        if cmd.estop:
            relay.estop = True
            return relay

        # Mode selain MANUAL tidak menggerakkan apa pun untuk saat ini.
        # AUTO sengaja diperlakukan sama sampai semi-auto benar-benar ada:
        # lebih aman robot diam daripada bergerak tanpa kendali.
        if cmd.mode != OperatorCommand.MODE_MANUAL:
            return relay

        # Brush mengikuti perintah langsung.
        relay.relay1_brush = cmd.brush_enable

        # Drive — positif = maju (konvensi OperatorCommand.msg).
        if cmd.drive > self.deadband:
            relay.relay2_forward = True
        elif cmd.drive < -self.deadband:
            relay.relay3_retreat = True

        # Steering — positif = belok kanan.
        if cmd.steering > self.deadband:
            relay.relay5_right = True
        elif cmd.steering < -self.deadband:
            relay.relay4_left = True

        # Thruster — hanya menyala selama tombol assist ditahan.
        if cmd.thruster_assist:
            relay.relay7_thruster1 = cmd.thruster_1
            relay.relay8_thruster2 = cmd.thruster_2
            relay.relay9_thruster3 = cmd.thruster_3
            relay.relay10_thruster4 = cmd.thruster_4

        # relay6_light belum dipakai.
        return relay

    # ------------------------------------------------------------------
    # Batas lama menyala (max-on-time)
    # ------------------------------------------------------------------

    # Output gerak yang dibatasi durasinya (brush dikecualikan: memang
    # dirancang menyala lama selama pembersihan).
    _OUTPUT_GERAK = (
        'relay2_forward', 'relay3_retreat',
        'relay4_left', 'relay5_right',
        'relay7_thruster1', 'relay8_thruster2',
        'relay9_thruster3', 'relay10_thruster4',
    )

    def _terapkan_max_on_time(self, relay, sekarang):
        if self.max_on <= 0.0:
            return
        for nama in self._OUTPUT_GERAK:
            if not getattr(relay, nama):
                # Perintah mati -> lupakan riwayat & blokirnya.
                self._on_since.pop(nama, None)
                self._blocked.discard(nama)
                continue
            if nama in self._blocked:
                setattr(relay, nama, False)
                continue
            mulai = self._on_since.setdefault(nama, sekarang)
            if sekarang - mulai > self.max_on:
                setattr(relay, nama, False)
                self._blocked.add(nama)
                self.get_logger().warning(
                    f'{nama} dimatikan: menyala terus lebih dari '
                    f'{self.max_on:.0f} detik (max-on-time)')

    # ------------------------------------------------------------------
    # Siklus penerbitan (heartbeat)
    # ------------------------------------------------------------------

    def publish_relay(self):
        sekarang = time.monotonic()

        perintah_basi = (
            self.last_rx_time is None
            or sekarang - self.last_rx_time > self.command_timeout)

        if perintah_basi:
            # Tidak ada perintah segar -> robot harus diam.
            relay = RelayOperator()
        else:
            relay = self._relay_dari_perintah(self.last_command)
            self._terapkan_max_on_time(relay, sekarang)

        self.relay_pub.publish(relay)

        # Log hanya saat keadaan berubah, bukan setiap siklus.
        ringkasan = self._ringkas(relay)
        if ringkasan != self._last_published:
            self._last_published = ringkasan
            if perintah_basi and self.last_rx_time is not None:
                self.get_logger().warning(
                    'Perintah operator berhenti — semua relay dimatikan')
            self.get_logger().info(ringkasan)

    @staticmethod
    def _ringkas(relay):
        aktif = [nama for nama in (
            'relay1_brush', 'relay2_forward', 'relay3_retreat',
            'relay4_left', 'relay5_right', 'relay6_light',
            'relay7_thruster1', 'relay8_thruster2',
            'relay9_thruster3', 'relay10_thruster4')
            if getattr(relay, nama)]
        if relay.estop:
            return 'Relay: EMERGENCY STOP'
        return 'Relay aktif: ' + (', '.join(aktif) if aktif else '(semua mati)')


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
