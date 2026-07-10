# Protokol Pengambilan Data Squat (Panduan Perekaman)

Dokumen ini panduan langkah-demi-langkah untuk merekam video squat yang akan
diproses otomatis oleh sistem. Ikuti apa adanya — tidak perlu paham teknis di
baliknya. Tujuannya: mengukur **seberapa akurat sistem menghitung repetisi (rep)**
pada berbagai **situasi** (arah kamera, jarak, cahaya, baju, kedalaman squat).

---

## 1. Istilah singkat (baca sekali saja)

- **Rep (repetisi):** satu kali gerakan squat penuh — turun lalu naik lagi.
- **Atlet:** orang yang melakukan squat dan direkam. Kita ada 4 atlet: **A1, A2, A3, A4**.
- **Viewpoint / arah kamera:** posisi kamera terhadap badan (depan / serong / samping).
- **Diagonal (serong) 45°:** badan menghadap serong ke kamera, kira-kira setengah
  menghadap depan, setengah menyamping.
- **Baseline:** kondisi **patokan/standar**. Semua kondisi lain hanya mengubah
  **satu hal** dari baseline ini.
- **OFAT ("ubah satu saja"):** aturan penting — saat menguji satu faktor (misal
  cahaya redup), **semua faktor lain harus tetap sama seperti baseline**.
- **Take:** pengambilan/rekaman. Tiap kondisi direkam **2 kali** (take 1 & take 2).

---

## 2. Kondisi BASELINE (patokan)

Hafalkan ini — semua kondisi lain berangkat dari sini:

| Faktor | Nilai baseline |
|---|---|
| Arah kamera | **Diagonal (serong 45°)** |
| Jarak | **2 meter** (kira-kira 3 langkah besar dari kamera) |
| Cahaya | **Normal** (ruangan terang biasa) |
| Baju | **Pas badan** (kaos/legging, tidak longgar) |
| Kedalaman squat | **Penuh** (turun dalam, paha di bawah sejajar lantai) |
| Tempo | **Normal** (tidak cepat, tidak lambat) |
| Jumlah rep | **10 rep** tiap video |

### Cara setel kamera (penting, baca pelan)

- **Tinggi kamera:** setinggi pinggang–dada. Jangan di lantai, jangan terlalu tinggi.
- **Pastikan seluruh badan masuk layar** — dari kepala sampai telapak kaki, dari
  awal berdiri sampai posisi paling bawah squat. Cek dulu sebelum mulai.
- **Diagonal (baseline):** berdiri serong ~45° terhadap kamera (badan setengah
  menghadap kamera). Ini posisi TERBAIK menurut riset.
- **Front (depan):** badan menghadap lurus ke kamera.
- **Side (samping):** badan menyamping penuh 90° ke kamera. (Ini sengaja diuji
  karena diduga paling sulit untuk sistem — wajar kalau hasilnya jelek.)
- **Jarak 2 m** ≈ 3 langkah besar; **jarak 1 m** ≈ 1,5 langkah (lebih dekat).

---

## 3. Daftar 11 kondisi per atlet

Setiap atlet merekam **11 kondisi**, masing-masing **2 take** → **22 video/atlet**.

### A. Grid arah kamera × jarak (cahaya/baju/kedalaman = baseline)

| No | Kondisi | Kode nama file | Yang diatur |
|----|---------|----------------|-------------|
| 1 | Depan, 1 m | `front-1m` | kamera di **depan**, jarak **1 m** |
| 2 | Depan, 2 m | `front-2m` | kamera di **depan**, jarak **2 m** |
| 3 | Serong, 1 m | `diag-1m` | kamera **serong**, jarak **1 m** |
| 4 | **BASELINE** (serong, 2 m) | `base` | semua = baseline |
| 5 | Samping, 1 m | `side-1m` | kamera **samping**, jarak **1 m** |
| 6 | Samping, 2 m | `side-2m` | kamera **samping**, jarak **2 m** |

### B. Ubah satu faktor (OFAT) — sisanya = baseline (serong, 2 m)

| No | Kondisi | Kode nama file | Yang diubah (sisanya TETAP baseline) |
|----|---------|----------------|--------------------------------------|
| 7 | Cahaya redup | `dim` | lampu diredupkan / sebagian dimatikan |
| 8 | Cahaya dari belakang | `backlit` | ada sumber cahaya terang **di belakang** atlet (mis. jendela) |
| 9 | Baju longgar | `loose` | pakai baju **longgar/kedodoran** |
| 10 | Kedalaman parallel | `parallel` | squat turun **pas sejajar** saja (paha ~sejajar lantai, tidak lebih dalam) |
| 11 | Kedalaman partial | `partial` | squat **setengah** saja (dangkal, tidak sampai sejajar) — ini sengaja, harusnya TIDAK dihitung sistem |

> **Ingat OFAT:** misal kondisi `dim` → yang berubah HANYA cahaya. Arah kamera
> tetap serong, jarak tetap 2 m, baju tetap pas, squat tetap penuh.

---

## 4. Aturan penamaan file (WAJIB tepat)

Format:
```
{atlet}_{kode}_t{take}.mp4
```
Contoh benar:
- `A1_base_t1.mp4`  → atlet A1, baseline, take 1
- `A2_side-2m_t1.mp4` → atlet A2, samping 2 m, take 1
- `A3_partial_t2.mp4` → atlet A3, kedalaman partial, take 2

Aturan:
- Gunakan **kode nama file persis** seperti di tabel (huruf kecil, ada tanda `-`).
- `t1` = take 1, `t2` = take 2.
- Nama file harus **sama persis** dengan kolom `video` di file label (lihat bagian 7).

---

## 5. Jumlah video & target waktu

- 11 kondisi × 2 take × 4 atlet = **88 video** (+ baseline ulang di akhir, lihat §6).
- Tiap video ~10 rep (~40 detik). Muat dikerjakan **1 hari**.
- Tips cepat: bagi tugas — satu orang jadi atlet, satu pegang/cek kamera, satu
  catat nama file. Gantian.

---

## 6. Urutan rekaman & kontrol kelelahan

Supaya hasil adil (tidak bias karena capek di akhir):

1. **Rekam BASELINE dulu** (`base_t1`, `base_t2`) di awal, saat masih segar.
2. Lanjut kondisi lain dengan **urutan yang diacak per atlet** (lihat tabel di bawah).
3. **Rekam BASELINE lagi di paling akhir** dengan nama `A_x_base-end_t1.mp4`.
   Ini untuk cek: kalau hasil baseline-akhir jauh beda dari baseline-awal, berarti
   atlet sudah capek (squat jadi dangkal) — kita jadi tahu.

Urutan disarankan (boleh diikuti apa adanya):

| Atlet | Urutan kondisi |
|---|---|
| A1 | base → front-2m → side-1m → dim → parallel → diag-1m → loose → front-1m → side-2m → backlit → partial → **base-end** |
| A2 | base → side-2m → dim → front-1m → partial → diag-1m → backlit → front-2m → loose → side-1m → parallel → **base-end** |
| A3 | base → dim → front-2m → parallel → side-1m → loose → diag-1m → backlit → side-2m → front-1m → partial → **base-end** |
| A4 | base → front-1m → parallel → side-2m → backlit → diag-1m → dim → loose → front-2m → side-1m → partial → **base-end** |

---

## 7. Checklist tiap rekaman (centang sebelum & sesudah)

Sebelum mulai satu video:
- [ ] Arah kamera & jarak sesuai kondisi yang sedang diuji?
- [ ] Faktor lain masih **sama seperti baseline**? (aturan OFAT)
- [ ] Seluruh badan (kepala–kaki) masuk layar dari berdiri sampai paling bawah?
- [ ] Sudah tahu nama file yang benar?

Saat merekam:
- [ ] Lakukan **tepat 10 rep** dengan tempo normal.
- [ ] Kalau meleset (mis. cuma 9 atau 11), **tidak apa-apa** — cukup catat jumlah
      aslinya di kolom `rep_asli` (lihat §9).

Setelah selesai:
- [ ] Simpan/rename file sesuai format `{atlet}_{kode}_t{take}.mp4`.
- [ ] Pindahkan ke folder `videos/` di proyek.

---

## 8. Cara memproses video (jalankan sistem)

Setelah **semua** video ada di folder `videos/`:

1. Buka terminal di folder proyek.
2. Jalankan:
   ```
   python scripts/batch.py --workers 4
   ```
3. Tunggu sampai selesai. Hasilnya muncul sebagai file **`dataset.csv`**.
   Tiap baris = satu video, berisi hasil hitung sistem (kolom penting:
   `video`, `total_reps`, `full_reps`, `partial_reps`, `status`, `min_depth_angle`).

> `status` artinya:
> - `ok` = video diproses normal.
> - `uncalibrated` = sistem gagal mengukur posisi berdiri (sering terjadi di
>   sudut sulit) → jangan dipakai untuk hitung akurasi.
> - `no_pose` = tidak terdeteksi orang.
> - `error` = video rusak/gagal dibuka.

---

## 9. Cara isi label & hitung hasil (Sheet A / B / C)

Kita pakai 3 tabel (boleh di Google Sheets/Excel):

- **Sheet A (label):** gunakan file `docs/experiment/label_template.csv` yang sudah
  disiapkan. Isinya sudah lengkap 88 baris. Yang perlu kalian lakukan hanya:
  - Pastikan kolom `video` cocok dengan nama file kalian.
  - Kalau rep yang dilakukan **bukan 10**, ubah angka di kolom `rep_asli`.
- **Sheet B (hasil sistem):** salin isi `dataset.csv` ke sini (atau buka langsung).
- **Sheet C (analisis):** gabungkan A dan B berdasarkan kolom **`video`**
  (pakai `VLOOKUP`/`XLOOKUP` di Excel/Sheets), lalu hitung:
  - **Selisih** = `total_reps` (Sheet B) − `rep_asli` (Sheet A).
  - **Error** = nilai mutlak selisih (`ABS(...)`).
  - **Benar?** = 1 kalau `total_reps` == `rep_asli`, selain itu 0.

Contoh baris Sheet C:
```
video            arah_kamera  rep_asli  total_reps  error  benar
A1_base_t1       serong       10        10          0      1
A2_side-2m_t1    samping      10        6           4      0
```

---

## 10. Yang dilaporkan (analisis akhir)

Sebelum menghitung akurasi, **buang baris yang `status` ≠ `ok`** (catat berapa
banyak yang dibuang per kondisi — ini juga temuan).

Lalu bandingkan rata-rata **error** dan **persen benar** untuk tiap faktor:

1. **Arah kamera:** depan vs serong vs **samping**. Dugaan: **samping paling jelek**
   (sesuai riset — kaki depan menutupi kaki belakang). Serong paling bagus.
2. **Jarak:** 1 m vs 2 m.
3. **Cahaya:** normal vs redup vs backlit. (Belum banyak diteliti orang → nilai plus.)
4. **Baju:** pas vs longgar. (Juga jarang diteliti → nilai plus.)
5. **Kedalaman:** penuh vs parallel vs partial.
   - `partial` **seharusnya tidak dihitung** → cek apakah `total_reps` turun.
   - `parallel` harus terhitung, tapi `full_reps` kecil.
   - `full` → `full_reps` besar.
6. **Kelelahan:** bandingkan baseline-awal vs `base-end` (apakah squat jadi dangkal).

Sajikan sebagai tabel/grafik sederhana: "Faktor → rata-rata error → persen benar".

---

## 11. Ringkasan super singkat (tempel di dinding)

1. Baseline = **serong, 2 m, terang, baju pas, squat penuh, 10 rep**.
2. Tiap kondisi **ubah 1 hal saja** dari baseline.
3. Tiap kondisi **2 take**. Baseline direkam **awal & akhir**.
4. Nama file: `A1_base_t1.mp4` (atlet_kode_take).
5. Seluruh badan **masuk layar**. Lakukan **10 rep**.
6. Semua video → folder `videos/` → jalankan `python scripts/batch.py --workers 4`.
7. Isi `rep_asli` di Sheet A hanya kalau rep bukan 10. Gabung by `video` → hitung error.
