# OperatorCommand.msg
# Perintah operator dari ground station ke robot.
# Diterbitkan joystick_interface_node, dibaca command_gateway_node.
#
# KONVENSI ARAH (sumber kebenaran — jangan diubah sepihak):
#   drive    > 0 = maju        (stick kiri ke atas)
#   steering > 0 = belok kanan (stick kiri ke kanan)
# Nilai drive/steering dalam rentang -1.0 .. 1.0.

std_msgs/Header header

# Gerak utama hidrolik
float32 drive
float32 steering

# Brush — SA, switch 2 posisi (bawah = ON)
bool brush_enable

# Emergency stop — SE, switch latching. Prioritas tertinggi:
# selama true, semua output wajib mati.
bool estop

# Thruster DC brushed x4 — satu arah, digital (on/off).
# Peta stick kanan -> thruster ada di joystick_interface_node.
# thruster_assist (SF, pushbutton momentary) adalah tombol pengaman:
# thruster hanya boleh menyala selama tombol ini ditahan.
bool thruster_assist
bool thruster_1
bool thruster_2
bool thruster_3
bool thruster_4

# Mode operasi — SB, switch 3 posisi.
uint8 MODE_OFF=0
uint8 MODE_MANUAL=1
uint8 MODE_AUTO=2
uint8 mode
