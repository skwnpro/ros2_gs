---
title: Brush Kart — Daftar Perubahan Branch bre/fase-0
date: 2026-10-22
tags:
  - brush-kart
  - ros2
  - changelog
---

# Daftar Perubahan — Branch `bre/fase-0`

Dokumen ini mencatat **semua** perubahan pada branch `bre/fase-0` di repo
`ros2_gs` (ground station) dan `ros2_ur` (underwater robot), dibandingkan
`main`. Branch ini dibuat dari:

- `ros2_gs` main @ `7fbdca0`
- `ros2_ur` main @ `c124b71`

`main` di kedua repo **tidak diubah**. Perubahan baru berlaku setelah
pull request di-merge.

> ⚠️ **WAJIB BUILD ULANG DI KEDUA MESIN.** `OperatorCommand.msg` dan
> `RelayOperator.msg` berubah struktur. Ground station dan robot harus
> sama-sama memakai hasil build branch ini — message lama dan baru
> tidak bisa saling bicara.

---

## 1. Keputusan desain yang tertanam di perubahan ini

| # | Keputusan | Alasan |
|---|---|---|
| 1 | Konvensi arah dikunci: `drive > 0` = maju, `steering > 0` = belok kanan | Ditulis di `OperatorCommand.msg` + README sebagai sumber kebenaran |
| 2 | **Bug arah diperbaiki di gateway**: kode lama menafsirkan drive negatif = forward & steering positif = left, yang terhadap data jstest (stick atas/kanan terbaca negatif) membuat stick atas = mundur dan stick kanan = belok kiri | Sekarang: positif = forward (relay2), positif steering = right (relay5) |
| 3 | `/relay_operator` menjadi **heartbeat** 20 Hz dari gateway | Relay node kini bisa membedakan "operator diam" vs "pengirim mati" |
| 4 | Mode **AUTO diperlakukan sebagai OFF** | Semi-auto belum ada; robot diam lebih aman daripada bergerak tanpa kendali |
| 5 | Pilihan kamera (SC) **tidak** masuk `OperatorCommand` | Itu urusan tampilan lokal GS → topic baru `/camera_select` untuk GUI |
| 6 | Topic kamera diganti nama: `image_raw` (bukan `raw_image`) | Menyesuaikan diagram desain; `compressed` dan `camera_info` di namespace yang sama |

## 2. Asumsi yang perlu dikonfirmasi

| # | Asumsi | Di mana | Cara mengubah |
|---|---|---|---|
| A1 | Posisi SB dibaca sesuai urutan penyebutan: **atas = OFF, tengah = MANUAL, bawah = AUTO** | `joystick_interface_node._baca_mode()` | Tukar nilai kembalian di fungsi itu |
| A2 | Posisi SC: **atas = kamera mati, tengah = depan, bawah = belakang** | `joystick_interface_node._baca_kamera()` | Sama seperti di atas |
| A3 | Tabel kebenaran stick kanan → thruster memakai **pola pasangan** (lihat §4.1) karena geometri pemasangan 4 thruster belum ditentukan | `joystick_interface_node._baca_thruster()` | Cukup tulis ulang satu fungsi itu |
| A4 | GPIO thruster 1–4 = **12, 23, 24, 25** (menghindari I2C 2/3 dan UART 14/15) | Parameter `pin_*` di `relay_operator_node` | Ubah lewat launch/parameter, tanpa edit kode |
| A5 | Focal length pada CameraInfo adalah **estimasi** (= lebar frame), bukan hasil kalibrasi | `camera_node._buat_camera_info()` | Ganti nilai `f` setelah kalibrasi kamera |

---

## 3. Perubahan message (`brushkart_msgs`) — berlaku di KEDUA repo

File diubah identik di `ros2_gs` dan `ros2_ur` (kecuali `RobotState.msg`
yang memang hanya ada di `ros2_gs` dan **tidak berubah**).

### 3.1 `msg/OperatorCommand.msg` — DITULIS ULANG

| Field lama | Nasib | Field baru | Fungsi |
|---|---|---|---|
| — | ➕ baru | `std_msgs/Header header` | Timestamp perintah; fondasi deteksi perintah basi |
| `float32 drive` | ♻️ tetap | `float32 drive` | Gerak maju/mundur; **konvensi diperjelas: > 0 = maju** |
| `float32 steering` | ♻️ tetap | `float32 steering` | Belok; **> 0 = kanan** |
| `float32 thruster` | ❌ dihapus | — | Thruster analog lama tidak dipakai lagi |
| — | ➕ baru | `bool thruster_assist` | SF ditahan = thruster diizinkan menyala |
| — | ➕ baru | `bool thruster_1..4` | Perintah digital per thruster (brushed DC, satu arah) |
| `bool brush_enable` | ♻️ tetap | `bool brush_enable` | Brush on/off (SA) |
| `bool estop` | ♻️ tetap | `bool estop` | Emergency stop (SE, latching) |
| — | ➕ baru | `uint8 mode` + konstanta `MODE_OFF=0`, `MODE_MANUAL=1`, `MODE_AUTO=2` | Mode operasi dari SB |

### 3.2 `msg/RelayOperator.msg` — DITAMBAH 4 FIELD

| Field baru | Fungsi |
|---|---|
| `bool relay7_thruster1` | Relay thruster DC 1 |
| `bool relay8_thruster2` | Relay thruster DC 2 |
| `bool relay9_thruster3` | Relay thruster DC 3 |
| `bool relay10_thruster4` | Relay thruster DC 4 |

Field lama (`relay1_brush` … `relay6_light`, `estop`) tidak berubah nama
maupun urutan maknanya.

---

## 4. ros2_gs (Ground Station)

### 4.1 `brushkart_joystick/.../joystick_interface_node.py` — DITULIS ULANG

Sekarang menjadi penerjemah penuh peta kontrol Boxer (sebelumnya hanya
drive/steering/brush/estop kasar), dan menerbitkan dua topic:
`/robot_command` + `/camera_select` (baru, lokal GS).

**Fungsi-fungsi:**

| Fungsi | Tugasnya |
|---|---|
| `__init__` | Deklarasi parameter, publisher `/robot_command` & `/camera_select`, subscriber `/joy` |
| `_baca_mode(nilai_axis)` | Axis5 (SB) → konstanta `MODE_OFF/MANUAL/AUTO` |
| `_baca_kamera(nilai_axis)` | Axis6 (SC) → 0 mati / 1 depan / 2 belakang |
| `_baca_thruster(x, y)` | Stick kanan → 4 bool thruster dengan pola pasangan (A3) |
| `joy_callback(msg)` | Callback utama: validasi panjang axes/buttons, isi semua field `OperatorCommand` (termasuk `header.stamp`), publish; publish `/camera_select` hanya saat pilihan berubah |
| `main` | Bootstrap node |

**Perubahan perilaku penting:**

- Trigger brush tidak lagi memakai kesetaraan float persis
  (`axes[4] == -1` lama) → ambang `<= -0.5`.
- Log spam `"JOY RECEIVED"` di setiap pesan **dihapus**.
- Pesan `/joy` dengan jumlah axis/button tidak sesuai peta Boxer kini
  **diabaikan** dengan warning (dulu: berpotensi IndexError).
- Konstanta indeks axis/button diberi nama (`AXIS_DRIVE`, `BUTTON_ESTOP`,
  dst.) dan peta kontrol + nilai hasil tes jstest ditulis di docstring
  kepala file.

**Variabel/parameter baru:**

| Nama | Nilai bawaan | Fungsi |
|---|---|---|
| `thruster_threshold` (parameter) | 0.5 | Ambang kemiringan stick kanan untuk menyalakan thruster |

### 4.2 `brushkart_gateway/.../command_gateway_node.py` — DITULIS ULANG

Dulu: menerjemahkan perintah hanya saat callback dan langsung publish.
Sekarang: node heartbeat dengan penolakan perintah basi dan max-on-time.

**Fungsi-fungsi:**

| Fungsi | Tugasnya |
|---|---|
| `command_callback(msg)` | Menyimpan perintah terakhir + waktu terimanya (jam monotonik) |
| `_relay_dari_perintah(cmd)` | Penerjemahan murni OperatorCommand → RelayOperator: prioritas estop → mode → deadband drive/steering → brush → thruster (digerbang assist) |
| `_terapkan_max_on_time(relay, sekarang)` | Mematikan paksa output gerak yang menyala terus melewati `max_continuous_on_s`, dan menahannya mati sampai perintahnya berubah |
| `publish_relay()` | Siklus timer 20 Hz: bila perintah basi → publish semua OFF; selain itu publish hasil terjemahan; log hanya saat keadaan berubah |
| `_ringkas(relay)` | Ringkasan satu baris keadaan relay untuk log |

**Perbaikan bug:** perbandingan arah dibalik ke konvensi yang benar —
`drive > deadband` → `relay2_forward` (dulu `drive < -deadband`),
`steering > deadband` → `relay5_right` (dulu `relay4_left`).

**Variabel/parameter baru:**

| Nama | Nilai bawaan | Fungsi |
|---|---|---|
| `deadband` (parameter) | 0.30 | Zona mati stick drive/steering (nilai sama seperti konstanta lama `DEADBAND`) |
| `publish_rate_hz` (parameter) | 20.0 | Laju heartbeat `/relay_operator` |
| `command_timeout_s` (parameter) | 0.5 | Umur maksimum perintah sebelum dianggap basi |
| `max_continuous_on_s` (parameter) | 0.0 (nonaktif) | Batas menyala terus per output gerak; aktifkan setelah durasi aman aktuator diketahui |
| `last_command`, `last_rx_time` | — | Perintah terakhir + cap waktu monotoniknya |
| `_on_since`, `_blocked` | — | Pelacak durasi menyala & status blokir max-on-time |

### 4.3 `brushkart_state/.../robot_state_node.py` — DITULIS ULANG

**Perbaikan bug utama:** `msg.connected` → **`msg.connection`** (nama
field yang benar di `RobotState.msg`). Kode lama melempar
`AttributeError` pada siklus publikasi pertama dan node tidak pernah
berhasil menerbitkan `/robot_state`.

**Fungsi-fungsi:**

| Fungsi | Tugasnya |
|---|---|
| `sensor_callback` / `network_callback` | Menyimpan data terakhir **dan waktu terimanya** |
| `_segar(rx_time, sekarang, batas)` | Menilai apakah data masih dalam batas umur |
| `publish_robot_state` | Siklus 2 Hz: nilai kesehatan dengan memperhitungkan kebasian data, susun `fault_message`, publish |

**Perubahan perilaku:**

- Node kini **selalu** publish, termasuk sebelum data pertama tiba
  (`fault_message` = `MENUNGGU DATA SENSOR` / `MENUNGGU DATA JARINGAN`).
- Data basi = fault: muncul pesan `DATA SENSOR BASI` / `DATA JARINGAN
  BASI` dan flag terkait menjadi false (dulu data terakhir dianggap
  sehat selamanya).
- Log info per siklus 2 Hz **dihapus** (dulu membanjiri log).

**Variabel/parameter baru:**

| Nama | Nilai bawaan | Fungsi |
|---|---|---|
| `sensor_timeout_s` (parameter) | 1.0 | Batas umur data `/sensor_data` (terbit 10 Hz) |
| `network_timeout_s` (parameter) | 3.0 | Batas umur data `/network_status` (terbit 1 Hz) |
| `sensor_rx_time`, `network_rx_time` | — | Waktu monotonik penerimaan data terakhir |

### 4.4 `brushkart_joystick/package.xml` — DIPERBAIKI

- ➕ `<depend>std_msgs</depend>` (dipakai untuk `/camera_select`)
- ➕ `<depend>brushkart_msgs</depend>` (**sebelumnya tidak dideklarasikan**
  padahal node mengimpornya)

### 4.5 `brushkart_gs_bringup/` — PACKAGE BARU

Launch seluruh stack GS dalam satu perintah:
`ros2 launch brushkart_gs_bringup gs.launch.py`
(joy_node dengan `autorepeat_rate: 20.0` — wajib, agar `/joy` terus
mengalir saat stick ditahan diam — joystick_interface_node,
command_gateway_node, robot_state_node).

### 4.6 `README.md` — DITULIS (sebelumnya kosong)

Ringkasan package, cara menjalankan, tabel peta kontrol Boxer, dan
tabel kontrak topic.

### 4.7 File yang BELUM bisa dihapus lewat mekanisme push ini

`ros2_ws/src/brushkart_joystick/brushkart_joystick/package.xml` — fragmen
package.xml tidak valid yang terselip di folder modul. Dihapus terpisah
di branch yang sama (commit tersendiri), tercatat di riwayat PR.

---

## 5. ros2_ur (Underwater Robot)

### 5.1 `brushkart_operator/.../relay_operator_node.py` — DITULIS ULANG

**Fungsi-fungsi:**

| Fungsi | Tugasnya |
|---|---|
| `__init__` | Baca parameter pin & watchdog, siapkan GPIO, matikan semua relay, buat subscription + timer watchdog |
| `relay_write(field, state)` | Tulis satu relay menurut nama field-nya (menghormati `active_high`) |
| `all_off()` | Matikan semua relay (dipakai saat start, e-stop, watchdog, shutdown) |
| `relay_callback(msg)` | E-stop → semua mati; selain itu salin keadaan, terapkan **interlock**, tulis ke GPIO |
| `watchdog_check()` | Timer 0,1 dtk: bila `/relay_operator` berhenti > `watchdog_timeout_s` → `all_off()` + log error |
| `destroy_node` | `all_off()` + `GPIO.cleanup()` (dipertahankan dari kode lama) |

**Perubahan penting:**

- ➕ **Watchdog heartbeat** (fitur keselamatan utama branch ini).
- ➕ **Interlock**: forward+retreat atau left+right bersamaan → keduanya
  dimatikan + warning (dulu diteruskan begitu saja).
- ➕ 4 relay thruster (GPIO 12/23/24/25).
- Peta relay→pin kini satu tabel (`FIELD_RELAY` + `PIN_BAWAAN`) dan
  **semua pin menjadi parameter** `pin_<nama field>` — robot simulasi
  bisa memakai pin berbeda tanpa edit kode.
- Log `EMERGENCY STOP` kini hanya muncul saat e-stop benar-benar aktif.

**Variabel/parameter baru:**

| Nama | Nilai bawaan | Fungsi |
|---|---|---|
| `watchdog_timeout_s` (parameter) | 1.0 | Batas diam `/relay_operator` sebelum semua relay dimatikan |
| `active_high` (parameter) | True | Polaritas modul relay (dulu konstanta kelas `ACTIVE_HIGH`) |
| `pin_relay1_brush` … `pin_relay10_thruster4` (parameter) | 5, 6, 13, 19, 26, 16, 12, 23, 24, 25 | Nomor pin BCM per relay |
| `last_rx_time`, `_watchdog_aktif` | — | Waktu pesan terakhir + status watchdog |

### 5.2 `brushkart_sensor/.../sensor_node.py` — DITULIS ULANG

**Fungsi-fungsi:**

| Fungsi | Tugasnya |
|---|---|
| `_coba_driver()` | Inisialisasi BNO055/MS5803 dengan try/except; dipanggil lagi berkala bila sebelumnya gagal |
| `_kalibrasi_dari_sampel(p)` | Mengumpulkan 20 sampel tekanan pertama → menetapkan tekanan referensi permukaan ke driver |
| `publish_data()` | Siklus 10 Hz: baca tiap driver dalam try/except terpisah, isi `SensorData` **termasuk `header.stamp`**, publish; catat status kalibrasi IMU tiap ±10 detik |

**Perubahan perilaku:**

- **Isolasi error**: satu sensor gagal → flag-nya `false`, node tetap
  hidup dan sensor lain tetap terbit (dulu: satu pengecualian I2C
  membunuh node).
- `print("timer running")` 10×/detik **dihapus**.
- `header.stamp` + `frame_id='sensor_link'` kini diisi (dulu kosong).
- `imu_ok`/`pressure_ok` kini **jujur** mengikuti keberhasilan baca
  (dulu selalu `True` dari driver).

**Variabel/parameter baru:**

| Nama | Nilai bawaan | Fungsi |
|---|---|---|
| `surface_pressure_mbar` (parameter) | 0.0 = kalibrasi otomatis | Referensi tekanan permukaan untuk depth |
| `JUMLAH_SAMPEL_KALIBRASI` | 20 | Jumlah sampel untuk kalibrasi otomatis |
| `JEDA_COBA_LAGI_S` | 5.0 | Jeda percobaan ulang inisialisasi driver |

### 5.3 `brushkart_sensor/.../ms5803_driver.py` — DIUBAH KECIL

| Perubahan | Fungsi |
|---|---|
| ➕ atribut `surface_pressure_mbar` (bawaan 1013.25) | Referensi permukaan yang bisa ditimpa `sensor_node` hasil kalibrasi |
| ♻️ `depth_m = (pressure_mbar - self.surface_pressure_mbar) / 100.0` | Dulu dikunci ke konstanta 1013.25 di dalam rumus |
| ➕ docstring peringatan varian | 01BA jenuh di permukaan — terdokumentasi di tempat orang akan melihatnya |

### 5.4 `brushkart_sensor/.../bno055_driver.py` — DITAMBAH SATU METHOD

| Perubahan | Fungsi |
|---|---|
| ➕ `get_calibration_status()` | Membaca register 0x35 → dict `{sys, gyro, acc, mag}` (0–3); dipakai sensor_node untuk log berkala. Kalibrasi BNO055 hilang tiap power cycle, jadi harus terlihat |
| ➕ docstring catatan yaw | Yaw magnetometer tidak bisa dipercaya di dekat lambung baja |

### 5.5 `brushkart_camera/.../camera_node.py` — DITULIS ULANG

**Fungsi-fungsi / struktur:**

| Bagian | Tugasnya |
|---|---|
| `_open_capture()` | Buka device (path atau ID), **minta** width/height/fps, lalu **log format yang benar-benar dinegosiasikan** |
| `_capture_loop()` (thread) | Ambil frame terus-menerus ke slot "frame terbaru"; hitung gagal beruntun; reconnect otomatis setelah 10× gagal |
| `publish_image()` | Timer: terbitkan hanya frame baru; raw hanya bila `publish_raw` & ada subscriber; JPEG hanya bila ada subscriber compressed |
| `_buat_camera_info(w, h, stamp)` | Susun CameraInfo dasar (focal estimasi — lihat A5) |
| `destroy_node` | Hentikan thread dengan bersih, lepaskan kamera |

**Perubahan penting:**

- **Berhenti menangkap frame raksasa untuk dibuang**: resolusi/FPS kini
  diminta ke sumbernya (bawaan 640×480@15, bisa diubah per instance).
- FPS bawaan berubah 10 → **15**; resolusi bawaan 320×240 → **640×480**
  (stream yang dikirim hanya compressed secara bawaan, jadi ringan).
- QoS: RELIABLE depth 10 → **BEST_EFFORT depth 1** (video langsung).
- Topic: `/camera/raw_image` + `/camera/compressed` (absolut) →
  `image_raw` + `compressed` + `camera_info` (**relatif**, mengikuti
  namespace instance: `/camera/...`, `/camera_usb1/...`, dst.).
- Debug tulis `/tmp/test_ros.jpg` dan log FPS/mean tiap detik **dihapus**.
- Satu kode untuk semua kamera (multi-instance) — IMX290 & USB dibedakan
  lewat namespace + parameter dari launch file.

**Variabel/parameter baru:**

| Nama | Nilai bawaan | Fungsi |
|---|---|---|
| `device_id` (parameter) | 0 | Indeks V4L2 bila `device_path` kosong |
| `device_path` (parameter) | '' | Path device, disarankan `/dev/v4l/by-id/...` |
| `width` / `height` (parameter) | 640 / 480 | Resolusi yang diminta ke kamera |
| `fps` (parameter) | 15.0 | Laju tangkap & terbit |
| `jpeg_quality` (parameter) | 70 | Kualitas JPEG stream compressed |
| `publish_raw` (parameter) | False | Aktifkan topic `image_raw` |
| `frame_id` (parameter) | 'camera' | frame_id header |
| `JUMLAH_GAGAL_RECONNECT` | 10 | Gagal baca beruntun sebelum reconnect |

### 5.6 `brushkart_network/.../network_monitor_node.py` — DIUBAH

| Perubahan | Fungsi |
|---|---|
| ♻️ Ping `-c 4` → `-c 2` | Callback tidak lagi tertahan sampai ±4 detik saat koneksi buruk |
| ♻️ `last_rx_ms` dihitung dari **waktu sukses terakhir yang sebenarnya** | Dulu: 0 atau +1000 kasar per siklus |
| ➖ Log info per detik **dihapus** | Mengurangi banjir log |
| ♻️ IP target menjadi parameter `target_ip` (bawaan tetap `192.168.10.1`) | Dulu konstanta modul `MINI_PC_IP` |

### 5.7 `package.xml` — EMPAT FILE DIPERBAIKI

| Package | Perbaikan |
|---|---|
| `brushkart_sensor` | Typo dependensi `bruhskart_msgs` → **`brushkart_msgs`** |
| `brushkart_operator` | Dependensi hantu `brushkart_interfaces` **dibuang** |
| `brushkart_network` | Dependensi hantu `brushkart_utils` **dibuang**; ➕ `python3-psutil` (memang diimpor kodenya) |
| (GS) `brushkart_joystick` | Lihat §4.4 |

Catatan: `smbus2` dan `RPi.GPIO` tidak punya kunci rosdep standar yang
bisa diandalkan — cara instalasinya didokumentasikan di README repo ini
(bukan ditebak namanya di package.xml).

### 5.8 `brushkart_ur_bringup/` — PACKAGE BARU

`ros2 launch brushkart_ur_bringup ur.launch.py` menyalakan sensor,
network monitor, relay operator, dan kamera utama IMX290 (dibungkus
`prefix='libcamerify'`). Argumen `enable_usb_cameras:=true` +
`usb1_path`/`usb2_path` menyalakan dua instance kamera USB
(namespace `camera_usb1`/`camera_usb2`, **tanpa** libcamerify).

### 5.9 `README.md` — DITULIS ULANG (sebelumnya satu baris)

Instalasi Raspi (termasuk membuat overlay IMX290 permanen lewat
`/boot/firmware/config.txt`), cara menjalankan, tabel relay→GPIO, dan
catatan kejenuhan MS5803-01BA.

---

## 6. Yang SENGAJA tidak dikerjakan di branch ini

| Item | Status |
|---|---|
| Relokasi `command_gateway_node` ke sisi robot | Menunggu keputusan arsitektur |
| `brushkart_msgs` menjadi satu sumber (repo terpisah/submodule) | Menunggu keputusan mekanisme; untuk sekarang kedua salinan dijaga identik |
| Pembaca rotary encoder & limit switch di `sensor_node` | Fase 2 — field di `SensorData.msg` belum ditambah |
| `telemetri_gui_node` | Belum dibuat; `/robot_state` + `/camera_select` sudah siap dikonsumsi |
| Logika semi-auto | Belum — mode AUTO saat ini = robot diam (§1 #4) |
| Test otomatis (unit/integration) | Belum ada; fungsi penerjemahan gateway kini murni agar mudah diuji menyusul |

## 7. Cara memeriksa branch ini (disarankan)

1. Ikuti **Bagian B & C** pada checklist testing (clean build + smoke
   test) di kedua mesin.
2. **Bagian D** checklist: verifikasi arah fisik — stick atas harus
   menggerakkan robot **maju** (perbaikan bug arah §1 #2 terasa di sini).
3. **Bagian G** checklist (fault injection G1–G4): cabut tether / matikan
   node GS saat relay aktif — semua relay harus mati ≤ ±1 detik
   (heartbeat gateway 20 Hz + watchdog relay 1 detik).
4. Periksa log GS: tidak ada lagi banjir log per pesan.

## Terkait

- [[project_review_201026]]
- [[Brush_Kart_Audit_Devils_Advocate]]
- [[Brush_Kart_Checklist_Testing]]
- [[joystick_interface_node]]
- [[Joystick_input_test]]
