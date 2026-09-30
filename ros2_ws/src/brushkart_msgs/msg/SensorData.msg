# SensorData.msg

std_msgs/Header header 

# Pressure
float32 pressure_mbar
float32 temperature_c
float32 depth_m

# Orientation
float32 roll_deg
float32 pitch_deg
float32 yaw_deg

# Accelerometer
float32 accel_x
float32 accel_y
float32 accel_z

# Gyroscope
float32 gyro_x
float32 gyro_y
float32 gyro_z

# Healt
bool imu_ok
bool pressure_ok
