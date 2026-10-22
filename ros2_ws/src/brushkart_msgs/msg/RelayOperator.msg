# RelayOperator.msg
# Perintah relay dari command_gateway_node ke relay_operator_node.
# Semua field boolean: true = relay MENYALA.
#
# Peta nomor relay -> nomor pin GPIO (BCM) hanya ada di
# relay_operator_node — file ini sengaja tidak menyebut pin.

bool relay1_brush
bool relay2_forward
bool relay3_retreat
bool relay4_left
bool relay5_right
bool relay6_light

# Thruster DC brushed x4 (satu arah, digital)
bool relay7_thruster1
bool relay8_thruster2
bool relay9_thruster3
bool relay10_thruster4

# true = e-stop aktif; relay_operator_node wajib mematikan
# semua output tanpa kecuali.
bool estop
