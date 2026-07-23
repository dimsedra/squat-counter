# Blueprint Presentasi QCC (Atomic Single-Topic Slides)

**Prinsip Desain Utama**:
1. **One Idea Per Slide**: Setiap slide HANYA membahas SATU ide/pesan utama agar fokus audiens terjaga dan *cognitive load* minim.
2. **Palet Warna Netral & Elegan**: Menggunakan warna netral gelap modern (*Proposal 3 Dark Graphite* `#121619`, kartu `#181e22`, teks `#f0f6fc`, abu-abu sekunder `#94a3b8`, dan aksen *Muted Sage Teal* `#2dd4bf`).
3. **Whitespace yang Lapang**: Spacing longgar, hirarki tipografi besar, tanpa penumpukan elemen (*un-crowded*).
4. **Alur Presentasi QCC (17 Atomic Slides - Total 15 Menit)**.

---

## Slide 1: Cover & Perkenalan Proyek
- **Konsep**: Judul Proyek & Tim Presenter
- **Judul**: Real-Time Bodyweight Squat Repetition Counter

---

## Slide 2: Latar Belakang — Tren Pemantauan Mandiri
- **Konsep**: Meningkatnya Kebutuhan Pemantauan Olahraga Mandiri di Rumah

---

## Slide 3: Rumusan Masalah — Keterbatasan Alat Konvensional
- **Konsep**: Mengapa Memilih Visi Komputer Dibandingkan Sensor Fisik?

---

## Slide 4: Kondisi Saat Ini — Kegagalan Single Threshold
- **Konsep**: Kegagalan Algoritma Visi Komputer Konvensional (Signal Chatter)

---

## Slide 5: Penetapan Target QCC — Kriteria Keberhasilan
- **Konsep**: Target Perbaikan Sistem (SMART KPIs)

---

## Slide 6: Analisis Akar Masalah — Overview Fishbone
- **Konsep**: Diagram Fishbone Presisi (4 Kategori QCC - Vector SVG)

---

## Slide 7: Akar Masalah Utama — Geometri & Pakaian
- **Konsep**: Dua Akar Penyebab Eror Terbesar (Kamera Depan 0° & Pakaian Baggy)

---

## Slide 8: Rencana Solusi — 3 Pilar Utama Penanggulangan
- **Konsep**: 3 Pilar Inovasi Solusi QCC (Sudut 2D Invariant, Auto-Kalibrasi, 2-Threshold Hysteresis)

---

## Slide 9: Implementasi — Arsitektur Sistem 5-Layer
- **Konsep**: Arsitektur Pemrosesan Data 5-Layer Pipeline

---

## Slide 10: Jalur Eksekusi — Live Web & Batch Mode
- **Konsep**: Fleksibilitas Eksekusi Dual Mode Deployment (+ Demo Video Live Interface)

---

## Slide 11: Hasil Evaluasi — Akurasi Keseluruhan Sistem
- **Konsep**: Pencapaian Akurasi Keseluruhan Sistem (83.57% Akurasi, 64.29% Exact Match)

---

## Slide 12: Hasil Evaluasi — Keunggulan Kamera Samping
- **Konsep**: Keunggulan Presisi Kamera Samping (MAE 0.250 + Dual Video Comparison)

---

## Slide 13: Hasil Evaluasi — Penolakan Squat Dangkal (Partial Rep)
- **Konsep**: Keberhasilan Gating Partial Squat oleh Hysteresis FSM (MAE 5.750)

---

## Slide 14: Hasil Evaluasi — Jarak Kamera & Pencahayaan Lingkungan
- **Konsep**: Analisis Jarak Kamera (1.0m vs 2.0m) & Ketahanan Filter EMA (&alpha; = 0.4) Terhadap Pencahayaan Indoor
- **Poin Utama**:
  1. Jarak 1.0 m memicu *clipping* mata kaki pada atlet tinggi saat squat dalam; Jarak **2.0 m terpantau utuh 100%** dari hip hingga ankle.
  2. Filter EMA (&alpha; = 0.4) meredam *jitter* pada lampu redup (*Dim*), sementara threshold visibilitas (&tau;<sub>vis</sub> &ge; 0.5) menghentikan siluet palsu (*Backlit*).

---

## Slide 15: Standarisasi Operasional (SOP Penggunaan)
- **Konsep**: 4 Aturan Standar Pengoperasian Sistem

---

## Slide 16: Rencana Tindak Lanjut (Roadmap Masa Depan)
- **Konsep**: Roadmap Pengembangan Masa Depan (Form Feedback, Multi-Person, Mobile Native)

---

## Slide 17: Kesimpulan & Penutup (Q&A)
- **Konsep**: Terima Kasih & Sesi Diskusi Tanya Jawab
