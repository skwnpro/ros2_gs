# ros2_gs — Brush Kart Ground Station

Program **ground station** robot underwater Brush Kart: mini PC dengan
Ubuntu Desktop 24.04 + ROS 2 Jazzy. Pasangannya: repo `ros2_ur`
(underwater robot, Raspberry Pi 4B). Dokumentasi project lengkap ada
di vault Obsidian `ocid_second_brain` (folder "ROS 2").

## Package di workspace ini

| Package | Isi |
|---|---|
| `brushkart_joystick` | `joystick_interface_node` — penerjemah Radiomaster Boxer |
| `brushkart_gateway` | `command_gateway_node` — gerbang keselamatan perintah → relay |
| `brushkart_state` | `robot_state_node` — agregator kesehatan robot |
| `brushkart_msgs` | Definisi message bersama (**harus identik** dengan salinan di `ros2_ur`, kecuali `RobotState.msg` yang khusus repo ini) |
| `brushkart_gs_bringup` | Launch file seluruh stack ground station |

## Menjalankan

```bash
cd ros2_ws
colcon build --symlink-install
source install/setup.bash
ros2 launch brushkart_gs_bringup gs.launch.py
```

Prasyarat: Radiomaster Boxer terhubung via USB (`ros-jazzy-joy`
terinstal — joy_node dijalankan oleh launch file).

## Peta kontrol Radiomaster Boxer

| Kontrol | Fungsi |
|---|---|
| Stick kiri | Drive (atas/bawah) & steering (kiri/kanan) hidrolik |
| Stick kanan | 4 thruster DC digital (aktif hanya selama SF ditahan) |
| SA (axis 4) | Brush on/off |
| SB (axis 5) | Mode: atas = OFF, tengah = MANUAL, bawah = AUTO |
| SC (axis 6) | Tampilan kamera di GUI: atas = mati, tengah = depan, bawah = belakang (topic `/camera_select`, lokal GS) |
| SE (button 0) | Emergency stop (latching) |
| SF (button 1) | Thruster assist (momentary, tahan) |

Catatan mode AUTO: semi-auto belum diimplementasikan — selama itu
gateway memperlakukan AUTO sama seperti OFF (robot diam). Konvensi
arah, nilai axis mentah, dan tabel kebenaran thruster didokumentasikan
di kepala file `joystick_interface_node.py` dan `OperatorCommand.msg`
— keduanya adalah sumber kebenaran, jangan diubah sepihak.

## Kontrak topic utama

| Topic | Arah | Isi |
|---|---|---|
| `/joy` | joy_node → joystick_interface | Input mentah Boxer |
| `/robot_command` | GS → robot (via gateway) | `brushkart_msgs/OperatorCommand` |
| `/relay_operator` | gateway → robot, periodik 20 Hz | `brushkart_msgs/RelayOperator` (heartbeat) |
| `/sensor_data`, `/network_status` | robot → GS | Telemetri |
| `/robot_state` | robot_state → GUI | `brushkart_msgs/RobotState` |
| `/camera_select` | joystick_interface → GUI (lokal GS) | Pilihan tampilan kamera |
