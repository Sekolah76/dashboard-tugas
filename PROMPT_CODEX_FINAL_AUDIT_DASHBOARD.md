# Prompt Codex Final: DANA Insight Command Center

Anda bertindak sebagai senior Streamlit developer, UI/UX designer, fintech
dashboard designer, data visualization engineer, data auditor, privacy
engineer, dan QA engineer.

Kerjakan project:

`C:\Users\Arsyad\Documents\dashboard-tugas`

Entry point:

`app.py`

Tujuan akhir adalah memperbaiki dashboard yang sudah ada sampai siap
dipresentasikan untuk UAS. Jangan membangun ulang secara membabi buta.
Pertahankan bagian yang sudah bekerja, khususnya loader data, filter
draft-versus-active, Apply Filter, Reset, sorting, dan sanitasi publik, lalu
perbaiki kekurangannya secara terarah.

## 1. Preflight Wajib

1. Baca seluruh instruksi repo yang tersedia.
2. `RTK.md` tidak ditemukan pada audit tanggal 13 Juni 2026. Jangan
   mengarang isinya atau membuat file tersebut tanpa instruksi pengguna.
3. Inventaris seluruh file sebelum mengedit.
4. Folder ini saat audit belum merupakan repository Git. Jangan mengklaim
   GitHub atau Streamlit Cloud sudah tersedia.
5. Jangan menjalankan `builder.py`. File tersebut adalah generator legacy
   yang menulis ulang `app.py` dan dapat menghapus hasil final.
6. Pertahankan `builder.py`, `data_logic.py`, seluruh backup, dan seluruh
   file data. Jangan menghapus file milik pengguna.
7. Sebelum mengedit, pastikan target backup belum ada, lalu salin:

   `app.py` menjadi `app_backup_before_final_data_ui_submission.py`

8. Jangan menimpa backup berikut:

   - `app_backup_before_redesign.py`
   - `app_backup_before_final_redesign.py`
   - `app_backup_before_final_codex_redesign.py`
   - `app_backup_before_final_submission_fix.py`

9. Jika target backup baru ternyata sudah ada, jangan overwrite. Gunakan
   nama dengan timestamp dan laporkan.
10. Catat hash atau minimal ukuran dan modification time file data sebelum
    dan sesudah pekerjaan untuk membuktikan data asli tidak berubah.

## 2. Inventaris Data Aktual

Sumber utama dashboard:

- `data/survey_clean.xlsx`: 50 baris, 24 kolom, sudah tanpa nama responden.
- `data/ulasan_clean.xlsx`: 330 baris, 3 kolom, sudah tanpa username.
- `data/hasil_kuesioner.csv`: 20 baris, 2 kolom, sama persis dengan hasil
  rata-rata 20 pertanyaan pada survey.

Sumber lokal terlindungi:

- `data/raw_survey_clean.xlsx`: 50 baris, 25 kolom, masih memiliki
  `Siapa nama Anda?`.
- `data/raw_ulasan_clean.xlsx`: 330 baris, 4 kolom, masih memiliki
  `username`.

File opsional berikut belum ditemukan saat audit:

- `data/hasil_analisis_dana.db`

Pengguna menyebut ada empat file data tambahan, tetapi saat audit hanya dua
file tambahan `raw_*` yang ditemukan. Pada awal pekerjaan, cari kembali semua
`*.xlsx`, `*.csv`, `*.db`, `*.sqlite`, `*.json`, dan `*.parquet` di folder
project. Jika file tambahan baru sudah tersedia, audit dan integrasikan hanya
jika aman dan relevan. Jika belum tersedia, laporkan secara jelas. Jangan
mengarang isi, skema, angka, atau grafik untuk file yang tidak ada.

## 3. Aturan Sumber Data dan Privasi

1. Sumber angka dashboard tetap:
   - `survey_clean.xlsx`
   - `ulasan_clean.xlsx`
   - `hasil_kuesioner.csv`
2. File `raw_*` hanya untuk rekonsiliasi lokal. Jangan pernah:
   - dimuat oleh dashboard publik;
   - ditampilkan dalam tabel;
   - disediakan untuk download;
   - diunggah ke GitHub;
   - dikirim ke Streamlit Cloud.
3. Perbarui `.gitignore` agar setidaknya mengabaikan:
   - `data/raw_*`
   - database lokal yang belum dinyatakan aman;
   - file ekspor atau screenshot sementara yang tidak diperlukan.
4. Jangan menghapus file raw dari komputer pengguna.
5. Database opsional hanya menjadi validation source. Dashboard tidak boleh
   gagal jika database tidak ada.
6. Jika database ada, inspeksi tabel dan deduplicate sebelum validasi:
   - ulasan unik harus 330;
   - indikator kuesioner unik harus 20;
   - kategori demografi unik yang diharapkan harus 9.
7. Jangan menggunakan DB mentah sebagai sumber KPI jika masih berisi
   duplikasi.
8. Perbaiki `sanitize_public_df()` agar mendeteksi secara aman:
   - username;
   - nama, nama lengkap, nama responden, name;
   - email dan variasinya;
   - phone, telepon, handphone;
   - nomor dan kontak;
   - responden;
   - id pengguna dan user id;
   - `Siapa nama Anda?`.
9. Gunakan normalisasi token atau regex berbatas kata. Jangan menggunakan
   pencarian substring `name` yang salah menganggap `Unnamed: 0` sebagai
   kolom identitas.
10. Terapkan sanitasi pada seluruh dataframe UI dan seluruh download publik,
    walaupun file clean saat ini sudah anonim.

## 4. Audit Data yang Harus Dibuat

Buat fungsi terpusat `audit_data_sources()` yang mengembalikan struktur data
atau dataframe audit, bukan sekadar teks statis. Audit minimal berisi:

- nama dan peran file;
- ditemukan atau tidak;
- ukuran;
- jumlah sheet atau tabel;
- jumlah baris dan kolom;
- nama kolom;
- jumlah null;
- exact duplicate rows;
- indikasi kolom identitas;
- status rekonsiliasi;
- status valid atau warning.

Audit publik tidak boleh menampilkan nilai identitas. Untuk file raw, cukup
metadata dan nama kolom sensitif. Tampilkan ringkasan audit yang aman pada tab
`Output & Presentasi`, dan gunakan hasilnya untuk status `Data Loaded`.

Tambahkan validasi invariants. Jika angka tidak sesuai, tampilkan error yang
jelas di aplikasi/log dan perbaiki logika. Jangan mengubah data agar cocok.

## 5. Baseline Data Terverifikasi

Semua angka total berikut sudah diverifikasi langsung dari file.

Survey:

- responden: 50;
- Perempuan: 39 atau 78.0%;
- Laki-laki: 11 atau 22.0%;
- usia `< 18 Tahun`: 9;
- usia `18 - 22 Tahun`: 36;
- usia `23 - 27 Tahun`: 3;
- usia `> 27 Tahun`: 2;
- Jarang: 21 atau 42.0%;
- Beberapa kali seminggu: 19 atau 38.0%;
- Setiap hari: 10 atau 20.0%;
- rentang timestamp survey: 16 April 2026 sampai 19 April 2026;
- indikator: 20;
- mean seluruh skor: 4.002, tampilkan 4.00;
- kategori indikator: 13 Kuat/Baik, 7 Cukup, 0 Perlu Perhatian.

Top 5:

1. DANA membuat transaksi lebih praktis: 4.26.
2. Transaksi dapat diselesaikan dengan mudah: 4.26.
3. Tampilan DANA memudahkan pengoperasian: 4.26.
4. Fitur dapat digunakan sesuai kebutuhan: 4.24.
5. Mudah beradaptasi dengan fitur baru: 4.22.

Bottom 5:

1. Sudah mencoba hampir seluruh fitur: 3.30.
2. Lag atau error jarang terjadi: 3.44.
3. DANA lebih menguntungkan dibanding e-wallet lain: 3.68.
4. Kegagalan penggunaan jarang terjadi: 3.76.
5. Nyaman mengandalkan DANA sehari-hari: 3.78.

Ulasan:

- total: 330;
- rating 1: 73;
- rating 2: 12;
- rating 3: 13;
- rating 4: 12;
- rating 5: 220;
- mean rating: 3.890909, tampilkan 3.89;
- Positif, rating 4-5: 232 atau 70.3%;
- Netral, rating 3: 13 atau 3.9%;
- Negatif, rating 1-2: 85 atau 25.8%;
- 9 Juni 2026: 248 atau 75.2%;
- 10 Juni 2026: 82 atau 24.8%;
- tidak ada null, exact duplicate row, atau duplicate review text.

Istilah keluhan yang benar-benar muncul pada 85 ulasan negatif antara lain:

- akun: 13;
- saldo: 13;
- hilang: 12;
- transaksi: 10;
- lag: 8;
- premium: 5;
- kecewa: 5;
- upgrade: 2;
- biaya: 1;
- gagal: 1.

Hitung ulang dari data saat runtime. Angka di atas adalah assertion, bukan
sumber hardcode untuk menggantikan perhitungan.

## 6. Analisis Variabel Penelitian

Tambahkan section `Analisis Variabel Penelitian` di tab `Analisis Survei`.
Definisikan mapping pada satu tempat:

```python
VARIABLE_GROUPS = {
    "X1 - Fleksibilitas": [
        "Penggunaan DANA membuat aktivitas keuangan menjadi lebih fleksibel."
    ],
    "X2 - Praktis": [
        "Saya merasa aplikasi DANA membuat transaksi menjadi lebih praktis."
    ],
    "M - Kepercayaan": [
        "Dibandingkan dengan aplikasi e-wallet lainnya, saya merasa DANA memberikan keuntungan lebih dalam bertransaksi.",
        "Saya yakin DANA dapat membantu saya dalam berbagai situasi pembayaran.",
        "Saya merasa nyaman mengandalkan DANA untuk transaksi sehari-hari.",
    ],
    "Y - Keseluruhan": "ALL_QUESTION_COLUMNS",
}
```

Nilai hasil audit untuk mapping tersebut:

- X1: 4.00, 1 indikator;
- X2: 4.26, 1 indikator;
- M: 3.82, 3 indikator;
- Y: 4.002, 20 indikator.

Jangan hardcode nilai. Hitung dari `survey_clean.xlsx` atau survey hasil
filter aktif. Jika kolom mapping tidak ditemukan, tampilkan warning dan daftar
kolom yang hilang.

Catatan akademik wajib: mapping di atas masih mapping sementara dari arahan
pengguna. `Y - Keseluruhan` memakai seluruh pertanyaan sehingga overlap dengan
X1, X2, dan M. Jangan menyebutnya model kausal atau validitas konstruk. Beri
catatan singkat bahwa mapping perlu disesuaikan dengan operasionalisasi
variabel pada instrumen penelitian jika dosen/kelompok memiliki pembagian Q1
sampai Q20 yang resmi.

Interpretasi:

- skor >= 4.00: Kuat/Baik;
- 3.00 sampai 3.99: Cukup;
- skor < 3.00: Perlu Perhatian.

Chart variabel wajib menampilkan nama, skor, interpretasi, jumlah indikator,
dan scope total atau filter aktif.

## 7. Bug UI dan Interaksi yang Harus Diperbaiki

### Ikon berubah menjadi teks acak

Source tidak mengandung string `double_arrow_right`, tetapi CSS saat ini
memberi `font-family` pada selector luas `[class*="st-"]`. Ini berisiko
menimpa font ligature Material Symbols milik kontrol bawaan Streamlit.

Perbaiki dengan:

- hapus selector font global yang menyasar semua class Streamlit;
- scope font hanya ke body dan elemen teks dashboard;
- jangan memakai Material Symbols untuk icon custom;
- sembunyikan kontrol sidebar native jika custom filter drawer sudah aktif;
- gunakan SVG inline/file SVG atau Unicode sederhana;
- pastikan tidak ada `double_arrow_right`,
  `keyboard_double_arrow_right`, atau `_arrow_right` yang terlihat.

### Hamburger tidak jelas dan tidak mengontrol panel

Saat ini tidak ada custom hamburger pada header. Garis tiga di kiri atas
adalah kontrol sidebar native Streamlit, sedangkan header custom hanya punya
tombol refresh.

Implementasikan:

```python
if "show_filter_panel" not in st.session_state:
    st.session_state.show_filter_panel = True
```

- tombol header berlabel eksplisit `Buka Filter` atau `Tutup Filter`;
- tombol mengubah `show_filter_panel`;
- panel benar-benar muncul atau hilang;
- saat panel hilang, content tetap layout wide;
- beri help `Buka/Tutup Filter`;
- jangan membuat tombol yang hanya rerun tanpa perubahan visual.

Untuk stabilitas, panel boleh berupa in-page filter drawer berbasis
`st.container` yang dirender kondisional, bukan sidebar native. Jangan
memaksakan CSS drawer palsu yang rapuh. Pertahankan form, draft state, Apply
Filter, Reset Semua, dan Refresh Data yang saat ini sudah bekerja.

### Tren ulasan salah memakai jam

Hapus auto-switch ke per jam dari chart utama. Chart utama selalu:

`Tren Ulasan per Tanggal`

Gunakan:

```python
dates = pd.to_datetime(df[date_col], errors="coerce")
daily = dates.dt.normalize().value_counts().sort_index()
```

atau `.dt.date`. X-axis wajib tanggal tanpa jam. Hover:

- tanggal;
- jumlah ulasan;
- denominator data yang tampil;
- persentase.

Chart jam boleh menjadi chart opsional terpisah bernama
`Distribusi Ulasan per Jam`, tidak menggantikan chart tanggal.

### Klaim AI yang tidak benar

Sentimen saat ini berasal dari rule rating, bukan AI. Ganti badge
`AI Sentiment` menjadi `Rating-based Sentiment` atau `Sentimen dari Rating`.

### Logo saat ini tidak layak

`dana_logo.png` berukuran 1024 x 1024, sebenarnya file JPEG dengan ekstensi
PNG, tidak memiliki alpha, dan memiliki checkerboard yang tertanam. Jangan
gunakan file tersebut pada UI final. Jangan menghapusnya tanpa izin.

## 8. Struktur Dashboard Final

Gunakan lima tab:

1. `Overview`
2. `Analisis Survei`
3. `Analisis Ulasan`
4. `Data Explorer`
5. `Output & Presentasi`

Header:

- tombol Buka/Tutup Filter;
- custom DANA-inspired SVG mark;
- judul dan subtitle;
- status data;
- live clock WIB;
- waktu file data terakhir berubah;
- waktu cache terakhir direfresh;
- tombol Refresh Data.

Jangan menyebut waktu session dibuat sebagai `data last refreshed`. Bedakan:

- `Data updated`: max modification time sumber utama;
- `Cache refreshed`: waktu tombol refresh digunakan.

Hero:

- compact;
- label `Total Data`;
- selalu memakai total asli 50, 330, 4.00, 3.89, 70.3%;
- tidak berubah karena filter;
- menggunakan SVG wallet.

KPI:

- Responden;
- Ulasan;
- Skor Kuesioner;
- Rating;
- Sentimen Positif;
- mengikuti filter aktif;
- caption menjelaskan total atau filter aktif;
- progress dan animasi hanya jika stabil.

Tambahkan teks eksplisit:

- `Menampilkan X dari 50 responden berdasarkan filter aktif.`
- `Menampilkan X dari 330 ulasan berdasarkan filter aktif.`
- atau `Menampilkan seluruh data.`

Overview:

- executive summary;
- gender;
- usia;
- frekuensi;
- trend ulasan per tanggal;
- insight ringkas.

Analisis Survei:

- skor rata-rata;
- 20 indikator;
- kategori skor;
- chart X1/X2/M/Y;
- Top 5;
- Bottom 5;
- expander Q1-Q20;
- filter kategori dan mode tampilan indikator;
- insight otomatis.

Analisis Ulasan:

- total asli dan hasil filter;
- sentimen tiga kategori;
- rating 1-5;
- trend tanggal;
- optional distribusi jam;
- keyword chips;
- keluhan negatif berbasis data;
- contoh ulasan;
- tabel dan download aman.

Data Explorer:

- survey publik;
- ulasan publik;
- hasil kuesioner;
- audit DB jika tersedia dan aman;
- kolom `No`;
- `hide_index=True`;
- download publik;
- catatan privasi.

Output & Presentasi:

- tabel audit sumber data;
- checklist deliverable dosen;
- ringkasan fitur;
- placeholder/input GitHub URL dan Streamlit URL;
- daftar screenshot:
  - `01_Hero_KPI`
  - `02_Control_Panel`
  - `03_Overview`
  - `04_Analisis_Survei`
  - `05_Analisis_Ulasan`
  - `06_Data_Explorer`
  - `07_Kesimpulan`
- jangan mengklaim link sudah aktif jika belum dibuat.

Kesimpulan:

- otomatis dari scope yang jelas;
- tampilkan skor 4.00, rating 3.89, positif 70.3% untuk total;
- jika memakai filter, beri label filter aktif;
- indikator tertinggi dan terendah;
- keluhan negatif yang benar-benar ditemukan;
- jangan menyimpulkan kausalitas.

Footer:

- DANA Insight Command Center;
- Developer: Muhammad Arsyad Arroyan;
- Built with Streamlit & Plotly;
- Siap presentasi UAS.

## 9. Filter Wajib

Pertahankan filter yang sudah bekerja:

- gender;
- kelompok usia;
- frekuensi;
- tanggal survey;
- rating;
- sentimen;
- tanggal ulasan;
- pencarian literal, `regex=False`;
- sorting;
- limit tabel;
- mode presentasi;
- insight;
- animasi;
- Apply;
- Reset;
- Refresh.

Tambahkan filter kuesioner:

- Kuat/Baik;
- Cukup;
- Perlu Perhatian;
- Semua indikator;
- Top 5;
- Bottom 5;
- Variabel X1/X2/M/Y.

Default harus tetap seluruh data. Active chips hanya menampilkan filter yang
benar-benar mempersempit data. Sorting dan limit tabel bukan filter statistik,
jadi jangan mengubah KPI.

## 10. Plotly dan Interaktivitas

Semua chart utama dibuat dari dataframe, bukan PNG.

Chart wajib:

- donut gender;
- bar usia;
- bar frekuensi;
- bar X1/X2/M/Y;
- horizontal bar Q1-Q20;
- donut sentimen;
- bar rating;
- trend ulasan per tanggal.

Setiap hover wajib memuat:

- nama kategori;
- jumlah atau skor;
- denominator;
- persentase jika berupa distribusi;
- scope total/filter aktif.

Contoh:

- `Perempuan: 39 dari 50 (78.0%)`;
- `Rating 5: 220 dari 330 (66.7%)`;
- `Positif: 232 dari 330 (70.3%)`;
- `9 Juni 2026: 248 dari 330 (75.2%)`.

Gunakan `customdata` untuk denominator dan persentase. Jangan hanya menulis
`Jumlah: 39` tanpa konteks. Legend dapat diklik ketika chart memiliki
kategori/trace yang relevan.

Native Plotly selection boleh ditambahkan hanya jika stabil pada versi
Streamlit yang terpasang dan lolos QA. Jangan menambah dependency berat.
Hover/tap detail lebih penting daripada click-to-filter yang rapuh.

Jika membuat chart biner dari arahan teman, gunakan:

- `Positif vs Non-positif`: 232 vs 98 dari seluruh 330;

atau jika mengecualikan Netral, tulis denominator 317 dengan sangat jelas.
Jangan menyebut `Positif vs Negatif` sambil diam-diam menghapus 13 data Netral.

## 11. Visual, Assets, dan UI

Buat folder `assets/` dan SVG ringan:

- `assets/dana_mark.svg`
- `assets/wallet_illustration.svg`
- `assets/review_illustration.svg`
- `assets/filter_illustration.svg`
- `assets/survey_illustration.svg`
- `assets/variable_illustration.svg`

Kriteria:

- custom DANA-inspired, bukan logo resmi hasil download;
- tidak memakai internet;
- ringan dan responsif;
- alt text atau dekoratif dengan benar;
- dipakai nyata pada hero dan section, bukan sekadar dibuat.

Jika gambar referensi teman tersedia, simpan pada `assets/reference/` dan
tampilkan hanya dalam expander `Referensi Grafik Awal`. Grafik utama tetap
Plotly.

Gunakan design tokens yang sudah ada. Jangan menghapus modern fintech style
yang sudah cukup baik. Rapikan:

- whitespace;
- alignment;
- panjang judul;
- responsivitas mobile;
- kontras;
- focus state keyboard;
- reduced motion;
- loading, empty, warning, dan error state.

Sembunyikan elemen Streamlit default secara selector spesifik dan aman:

- `#MainMenu`;
- footer native;
- toolbar/deploy;
- sidebar native control setelah custom control tersedia.

Jangan memakai selector generik yang merusak icon font atau komponen.

## 12. README, Ringkasan, dan Repository Safety

Perbarui `README.md`:

- judul dan tujuan penelitian;
- role Dashboard Developer;
- sumber data utama;
- sumber raw lokal yang tidak boleh dipublikasi;
- data tambahan yang benar-benar ditemukan;
- fitur dan filter;
- visualisasi;
- analisis variabel beserta caveat mapping;
- insight;
- privasi;
- menjalankan lokal;
- testing;
- GitHub;
- Streamlit Cloud;
- daftar output dosen;
- peringatan jangan menjalankan `builder.py`.

Buat:

`Ringkasan_Fitur_Dashboard.txt`

Isi ringkas:

- dashboard;
- data;
- profil responden;
- kuesioner;
- variabel;
- scraping ulasan;
- filter;
- insight;
- kesimpulan;
- placeholder GitHub;
- placeholder Streamlit Cloud;
- screenshot;
- source code.

Jangan memasukkan file raw ke Git. Sebelum memberi instruksi `git add .`,
jalankan `git status --short` dan pastikan file protected di-ignore.

## 13. Testing dan QA

Tambahkan test invariants ringan menggunakan standard library `unittest` atau
script validasi yang tidak menjadi dependency runtime berat.

Jalankan:

```powershell
python -m py_compile app.py
python -m streamlit cache clear
python -m streamlit run app.py
```

Jalankan AppTest atau pengujian setara:

- tidak ada exception;
- lima tab muncul;
- tombol Buka/Tutup Filter mengubah panel;
- default 50 dan 330;
- Apply Filter bekerja;
- Reset kembali ke default;
- filter `Perempuan + Rating 1` memberi 39 survey dan 73 ulasan;
- skor 4.00;
- rating 3.89;
- positif 70.3%;
- trend berjudul `Tren Ulasan per Tanggal`;
- tanggal 9 Juni 248 dan 10 Juni 82;
- X1 4.00, X2 4.26, M 3.82, Y 4.002;
- chart hover memiliki denominator dan persen;
- tidak ada teks icon mentah;
- tidak ada kolom identitas pada UI/download;
- `Unnamed: 0` pada CSV tidak salah dianggap identitas;
- file data tidak berubah.

Setelah server aktif, gunakan browser untuk QA visual desktop dan mobile:

- header tidak overlap;
- filter drawer nyata;
- tidak ada error merah;
- tidak ada HTML mentah;
- logo tidak memiliki checkerboard;
- chart tidak terpotong;
- tab dapat dinavigasi;
- screenshot presentasi dapat diambil.

Jika browser/screenshot tool tidak tersedia, laporkan keterbatasan. Jangan
mengklaim screenshot sudah diverifikasi.

Hentikan proses server background setelah QA jika tidak lagi diperlukan.

## 14. Batasan dan Keputusan Implementasi

- Jangan mengubah isi file data.
- Jangan menghapus file yang diberikan.
- Jangan menjalankan atau memperbarui `builder.py` sehingga menimpa app final.
- Jangan hardcode angka untuk menutupi error pembacaan data.
- Jangan mengubah sentimen rating-based menjadi model AI.
- Jangan menambah library berat tanpa kebutuhan nyata.
- Jangan membuat GitHub repo, push, atau deploy tanpa autentikasi dan izin
  pengguna.
- Jangan mengklaim empat file tambahan sudah terintegrasi jika file tidak ada.
- Jangan menampilkan data raw beridentitas pada web publik.
- Prioritaskan data benar, privasi, fungsi filter, lalu UI/animasi.

## 15. Laporan Akhir

Berikan laporan:

1. backup yang dibuat;
2. file yang diubah dan ditambah;
3. inventaris data aktual, termasuk file tambahan yang ditemukan/tidak;
4. bukti file data tidak berubah;
5. bug yang diperbaiki;
6. angka valid yang tampil;
7. analisis X1/X2/M/Y dan caveat mapping;
8. filter dan chart interaktif;
9. privasi dan `.gitignore`;
10. hasil compile, AppTest, browser QA, dan screenshot;
11. checklist kesiapan presentasi;
12. perintah menjalankan dashboard;
13. status GitHub/Streamlit Cloud yang sebenarnya;
14. langkah yang masih memerlukan tindakan atau akun pengguna.

Prioritas:

1. Data benar dan dapat diaudit.
2. File asli tetap utuh.
3. Data beridentitas tidak dipublikasi.
4. Dashboard memenuhi arahan dosen.
5. Filter dan visualisasi bekerja.
6. Analisis variabel tidak menyesatkan.
7. UI modern, efisien, dan siap presentasi.
