# DANA Insight Command Center

Dashboard penelitian berbasis Streamlit untuk menganalisis pengalaman pengguna
aplikasi DANA dari data survei dan ulasan hasil web scraping.

**Role:** Dashboard Developer  
**Developer:** Muhammad Arsyad Arroyan  
**Status:** Siap dijalankan dan diuji lokal untuk presentasi UAS

## Tujuan Penelitian

Dashboard menyatukan profil responden, hasil 20 indikator kuesioner, analisis
variabel penelitian, rating dan sentimen ulasan, filter interaktif, insight
utama, data explorer yang aman, serta kesimpulan deskriptif.

Dashboard tidak menyatakan hubungan kausal. Sentimen diturunkan dari rating:

- Rating 4-5: Positif
- Rating 3: Netral
- Rating 1-2: Negatif

## Sumber Data

Sumber utama runtime:

| File | Peran | Baseline |
|---|---|---:|
| `data/survey_clean.xlsx` | Survey anonim | 50 responden |
| `data/ulasan_clean.xlsx` | Ulasan anonim | 330 ulasan |
| `data/hasil_kuesioner.csv` | Ringkasan indikator | 20 indikator |

Sumber lokal terlindungi:

- `data/raw_survey_clean.xlsx` masih memuat nama responden.
- `data/raw_ulasan_clean.xlsx` masih memuat username.

File `raw_*` hanya digunakan untuk rekonsiliasi lokal, tidak pernah dimuat oleh
dashboard publik, dan sudah diabaikan oleh `.gitignore`.

`data/hasil_analisis_dana.db` tersedia sebagai sumber validasi lokal dan
diabaikan oleh Git. Isi mentahnya memiliki duplikasi 2x: 660 ulasan,
40 indikator, dan 18 baris demografi. Audit menggunakan deduplikasi sehingga
hasil validasinya menjadi 330 ulasan, 20 indikator, dan 9 kategori demografi.
Database tidak pernah menjadi sumber KPI dashboard.

## Baseline Terverifikasi

- Responden: 50
- Perempuan: 39 atau 78.0%
- Laki-laki: 11 atau 22.0%
- Usia 18-22 tahun: 36
- Frekuensi Jarang: 21
- Skor kuesioner: 4.002 atau 4.00
- Ulasan: 330
- Rating rata-rata: 3.8909 atau 3.89
- Positif: 232 atau 70.3%
- Netral: 13 atau 3.9%
- Negatif: 85 atau 25.8%
- 9 Juni 2026: 248 ulasan
- 10 Juni 2026: 82 ulasan

Angka dihitung dari file runtime. Nilai baseline di source digunakan sebagai
assertion validasi, bukan untuk menggantikan perhitungan data.

## Analisis Variabel

Dashboard menghitung:

- X1 - Fleksibilitas
- X2 - Praktis
- M - Kepercayaan
- Y - Keseluruhan

Mapping berada pada konstanta `VARIABLE_GROUPS` di `app.py` agar mudah
disesuaikan. Mapping saat ini masih mengikuti arahan project. Y memakai seluruh
Q1-Q20 sehingga overlap dengan X1, X2, dan M. Sesuaikan mapping jika instrumen
penelitian resmi memiliki pembagian indikator lain.

## Fitur Dashboard

- Landing presentasi tampil pertama, dengan tombol masuk dan module routing ke lima halaman
- Sticky header dengan tombol Buka/Tutup Filter
- Pencarian cepat indikator dan ulasan yang tidak mengubah KPI atau filter statistik
- Filter rail biru pada desktop dan panel berurutan pada layar kecil
- Status validasi data, live clock WIB, data update, dan cache refresh
- Hero total data yang tidak berubah saat filter aktif
- KPI responden, ulasan, skor, rating, dan sentimen positif
- Lima tab: Overview, Analisis Survei, Analisis Ulasan, Data Explorer, dan Lampiran Presentasi
- Plotly chart interaktif dengan modebar minimal saat hover dan fullscreen custom pada header card
- Pagination, pencarian, sorting, limit baris, serta ekspor CSV publik pada tabel
- Responsif desain untuk berbagai perangkat
- Analisis X1/X2/M/Y
- Tren ulasan per tanggal dan distribusi jam sebagai analisis tambahan
- Keyword serta istilah keluhan negatif berbasis data
- Audit sumber data dan invariant baseline
- Pencarian dan sorting lokal pada tabel Data Explorer
- Empty state visual ketika filter atau pencarian tidak menghasilkan data
- Download CSV publik yang disanitasi
- Mode presentasi, insight otomatis, animasi, sorting, dan limit tabel
- Aset PNG dan SVG lokal tanpa download internet

## Filter Interaktif

Survey:

- Jenis kelamin
- Kelompok usia
- Frekuensi penggunaan
- Rentang tanggal survey

Ulasan:

- Sentimen
- Rating
- Rentang tanggal
- Pencarian literal
- Sorting

Kuesioner dan tampilan:

- Kategori Kuat/Baik, Cukup, atau Perlu Perhatian
- Semua indikator, Top 5, Bottom 5, atau Variabel X1/X2/M/Y
- Limit tabel
- Insight otomatis
- Animasi
- Mode presentasi

Gunakan `Apply Filter` untuk menerapkan draft filter. `Reset Semua`
mengembalikan seluruh data dan `Refresh Data` membersihkan cache. Note: Filter chip hanya muncul saat opsi yang dipilih benar-benar mempersempit data (bukan 'semua' yang dipilih).

## Privasi

Fungsi `sanitize_public_df()` membuang kolom identitas berdasarkan token dan
frasa berbatas kata, termasuk nama, username, email, nomor, kontak, responden,
serta user ID. `Unnamed: 0` tidak salah dianggap sebagai kolom `name`.

Sanitasi diterapkan kembali pada tabel dan file download walaupun file runtime
sudah anonim.

## Struktur Project

```text
dashboard-tugas/
|-- app.py
|-- test_dashboard.py
|-- Ringkasan_Fitur_Dashboard.txt
|-- requirements.txt
|-- README.md
|-- assets/
|   |-- dana_hero_banner_1920x520.png
|   |-- dana_hero_full_1600x900.png
|   |-- dana_logo_wordmark_header_480x120.png
|   |-- dana_mobile_mockup_360x480.png
|   |-- dana_wallet_cluster_480x480.png
|   |-- dana_mark.svg
|   |-- wallet_illustration.svg
|   |-- review_illustration.svg
|   |-- filter_illustration.svg
|   |-- survey_illustration.svg
|   |-- variable_illustration.svg
|   |-- phone_dashboard_illustration.svg
|   |-- shield_privacy.svg
|   `-- empty_state.svg
|-- data/
|   |-- survey_clean.xlsx
|   |-- ulasan_clean.xlsx
|   |-- hasil_kuesioner.csv
|   `-- hasil_analisis_dana.db (lokal, di-ignore)
`-- .streamlit/config.toml
```

`builder.py` dan `data_logic.py` adalah file legacy. Jangan menjalankan
`builder.py` karena file tersebut dapat menulis ulang `app.py`.

## Menjalankan Lokal

```powershell
python -m pip install -r requirements.txt
python -m streamlit cache clear
python -m streamlit run app.py
```

Buka `http://localhost:8501`.

## Testing

```powershell
python -m py_compile app.py
python -m unittest -v test_dashboard.py
```

Test mencakup invariant data, privasi, skor variabel, volume per tanggal,
deduplikasi database, active filter chips, konfigurasi Plotly, tooltip,
aset lokal, pencarian literal, landing sebagai halaman pertama, navigasi
custom lima halaman, fullscreen custom, pagination, Apply Filter, dan Reset
Semua.

## GitHub

Folder belum menjadi repository Git pada saat dokumentasi ini dibuat.

```powershell
git init
git status --short
git add .
git status --short
git commit -m "Finalize DANA Insight Command Center"
git branch -M main
git remote add origin https://github.com/USERNAME/dashboard-tugas.git
git push -u origin main
```

Sebelum commit, pastikan `data/raw_*`, database lokal, secret, dan file
sementara tidak muncul pada `git status`.

## Streamlit Community Cloud

1. Push repository aman ke GitHub.
2. Buka `https://share.streamlit.io/`.
3. Pilih repository, branch `main`, dan main file `app.py`.
4. Deploy.
5. Uji kembali filter, tabel, download, dan tampilan mobile.
6. Isi URL publik pada tab Lampiran Presentasi.

Repository GitHub dan URL Streamlit Cloud belum dibuat otomatis karena
memerlukan akun dan autentikasi pengguna.

## Output untuk Dosen

- Dashboard Streamlit
- Source code `app.py`
- Repository GitHub
- URL Streamlit Cloud
- Screenshot dashboard
- Ringkasan fitur
- Insight dan kesimpulan penelitian

Daftar screenshot yang disarankan tersedia pada tab Lampiran Presentasi:
Lobby, Hero KPI, Control Panel, Overview, Analisis Survei, Analisis Ulasan,
Data Explorer, Kesimpulan, Lampiran Presentasi, dan Mobile View.

Screenshot dari build sebelum finalisasi bukan bukti QA visual build terbaru.
Ambil ulang seluruh screenshot setelah pemeriksaan desktop, tablet, dan mobile.
