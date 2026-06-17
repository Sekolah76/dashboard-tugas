# DESIGN.md — DANA Insight Command Center

> **Status:** Panduan desain aktif — gunakan dokumen ini sebagai satu-satunya acuan
> implementasi UI/UX. Jangan mengubah file data atau angka validasi.
> Dokumen ini hanya membahas tampilan; implementasi dilakukan pada sesi terpisah.

---

## 1. Design Objective

Dashboard **DANA Insight Command Center** harus menjadi sebuah *fintech analytics
dashboard* bergaya DANA yang modern, bersih, responsif, dan layak untuk presentasi
akademik tingkat universitas. Tujuan utamanya adalah memudahkan pembaca — baik dosen,
penguji, maupun mahasiswa — untuk memahami data survei kepuasan dan ulasan pengguna
aplikasi DANA **tanpa perlu mengubah atau menginterpretasikan ulang data asli**.

Prinsip desain yang harus dijaga:

| Prinsip | Keterangan |
|---|---|
| **Data-first** | Visual melayani data, bukan sebaliknya. |
| **Brand coherence** | Warna, ikon, dan aset mengacu pada identitas visual DANA. |
| **Academic clarity** | Semua angka harus bisa ditelusuri ke sumber data asli. |
| **Responsive** | Tampilan berfungsi baik di desktop, tablet, dan ponsel. |
| **Accessible** | Kontras, ukuran font, dan label memenuhi standar keterbacaan. |
| **Privacy-safe** | Tidak ada identitas pengguna yang pernah ditampilkan. |

---

## 2. Non-Negotiable Data Rules

> ⚠️ **ATURAN INI TIDAK BOLEH DILANGGAR DALAM IMPLEMENTASI APA PUN.**

1. **File data tidak boleh diubah.** Tiga file berikut harus dibiarkan persis seperti
   adanya:
   - `data/survey_clean.xlsx`
   - `data/ulasan_clean.xlsx`
   - `data/hasil_kuesioner.csv`

2. **Semua perhitungan harus berasal dari file data.** Tidak ada angka yang boleh
   di-*hardcode* di dalam kode tampilan (kecuali angka validasi *baseline* yang sudah
   didefinisikan di `EXPECTED_BASELINE`).

3. **Gambar referensi / mockup tidak boleh dipakai sebagai sumber angka.** Mockup hanya
   acuan layout, warna, dan UI/UX.

4. **Data pribadi tidak boleh tampil.** Kolom berikut wajib disembunyikan di Data
   Explorer dan download CSV publik:
   - Nama lengkap / nama responden
   - Username / User ID
   - Email / Alamat email
   - Nomor HP / telepon
   - Kolom lain yang mengandung identitas unik individu

5. **Database `hasil_analisis_dana.db` hanya sebagai validasi tambahan.** Jika
   digunakan, wajib menerapkan `drop_duplicates()` sebelum setiap operasi agregat.
   Database ini **tidak boleh** menjadi sumber utama KPI yang ditampilkan di dashboard.

6. **Filter survey tidak memengaruhi analisis ulasan, dan sebaliknya.** Kedua sumber
   data bersifat independen dan harus tetap terpisah secara logis.

---

## 3. Visual Reference Summary

Berdasarkan analisis gambar referensi yang diberikan, UI target memiliki karakteristik
berikut:

### Layout Utama
- **Sidebar biru** di sisi kiri layar — permanen di desktop, *drawer* di tablet/mobile.
- **Topbar putih** *sticky* di bagian atas — logo kiri, aksi kanan.
- **Hero banner** lebar dengan gambar aset DANA di sisi kanan dan teks di kiri.
- **KPI cards** besar dan bersih di bawah hero.
- **Tabs horizontal** dengan pill container di bawah KPI.
- **Card putih** dengan *shadow* lembut untuk setiap blok konten.

### Chart & Data
- Chart responsif, latar transparan/putih.
- Tabel modern dengan tinggi stabil dan *horizontal scroll*.
- Tooltip bersih dengan format angka presisi 1 desimal.

### Keseluruhan Feel
- Desain konsisten dari desktop hingga mobile.
- Visual DANA terasa kuat namun tidak mengganggu keterbacaan data.
- Nuansa *fintech profesional* — bukan *akademik kaku*.

---

## 4. Brand & Color System

### Token Warna

```css
/* Primary Brand */
--dana-primary:        #108EE9;   /* DANA Blue utama */
--dana-deep:           #004AAD;   /* Deep Blue untuk sidebar & header */
--dana-electric:       #2563EB;   /* Aksen biru elektrik */
--dana-sky:            #38BDF8;   /* Biru langit untuk gradien */

/* Backgrounds */
--dana-bg:             #EAF6FF;   /* Soft Blue Background halaman */
--dana-panel:          #F3F8FF;   /* Panel / section background */
--dana-card:           #FFFFFF;   /* Card putih */
--dana-sidebar-from:   #004AAD;   /* Gradien sidebar atas */
--dana-sidebar-to:     #108EE9;   /* Gradien sidebar bawah */

/* Text */
--dana-text:           #071633;   /* Navy text — heading utama */
--dana-muted:          #64748B;   /* Teks pendukung / caption */
--dana-sidebar-text:   #FFFFFF;   /* Teks di atas sidebar biru */

/* Borders */
--dana-border:         #DCEBFA;   /* Border card lembut */
--dana-border-strong:  #BFDBFE;   /* Border sedikit lebih tegas */

/* Semantic Colors */
--dana-positive:       #16B978;   /* Hijau — positif / kuat / baik */
--dana-negative:       #FF4D5E;   /* Merah — negatif / perlu perhatian */
--dana-warning:        #F9B233;   /* Kuning — cukup / netral */
--dana-neutral:        #94A3B8;   /* Abu — teks minor */

/* Accent */
--dana-purple:         #6D5DFB;   /* Ungu — rating / variabel M */
--dana-cyan:           #12C6D7;   /* Cyan — accent dekoratif */

/* Soft Backgrounds (untuk card semantik) */
--dana-soft-green:     #ECFDF5;
--dana-soft-red:       #FEF2F2;
--dana-soft-amber:     #FFFBEB;
--dana-soft-blue:      #EFF6FF;
--dana-soft-purple:    #EDE9FE;
```

### Panduan Penggunaan Warna

| Konteks | Warna |
|---|---|
| Brand, navigasi, KPI utama, tombol primer | `#108EE9` (Primary Blue) |
| Sidebar, header gelap | Gradien `#004AAD → #108EE9` |
| Positif / Kuat / Baik | `#16B978` (Positive Green) |
| Negatif / Perlu perhatian | `#FF4D5E` (Negative Red) |
| Cukup / Netral | `#F9B233` (Warning Yellow) |
| Variabel M / Rating / Ungu | `#6D5DFB` (Purple Accent) |
| Teks pendukung / caption | `#94A3B8` (Neutral Gray) |
| Chart donut — Positif | `#16B978` |
| Chart donut — Netral | `#F9B233` |
| Chart donut — Negatif | `#FF4D5E` |

---

## 5. Typography System

### Font Stack

```css
font-family: "Inter", "Segoe UI", system-ui, -apple-system, BlinkMacSystemFont,
             "Helvetica Neue", Arial, sans-serif;
```

Prioritaskan `Inter` dari Google Fonts (CDN lokal jika perlu) atau biarkan sistem
memilih fallback. Jangan memakai font serif di dalam dashboard.

### Skala Tipografi

| Role | Ukuran (desktop) | Ukuran (mobile) | Weight | Keterangan |
|---|---|---|---|---|
| Hero Title | 40–48 px | 28–34 px | 800–900 | Judul utama hero section |
| Page Heading | 28–32 px | 22–26 px | 700–800 | Judul section (h2) |
| Section Kicker | 11–12 px | 11 px | 700 | Uppercase, letter-spacing 0.08em |
| Card Title / Label | 13–15 px | 12–14 px | 700–800 | Uppercase label KPI |
| KPI Value | 30–42 px | 24–32 px | 800–900 | Angka besar KPI card |
| Body Text | 14–16 px | 14–15 px | 400–500 | Paragraf dan isi card |
| Caption | 12–13 px | 12 px | 400 | Catatan bawah chart/tabel |
| Button | 14–15 px | 13–14 px | 600–700 | Label tombol |

### Panduan Penulisan

- Gunakan bahasa **akademik, ringkas, dan profesional** — tidak casual.
- Hindari singkatan ambigu.
- Semua label angka harus menyertakan konteks (unit, dari total, persentase).
- Kalimat kesimpulan tidak boleh mengklaim hubungan kausal tanpa uji statistik.

---

## 6. Layout System

### Grid Utama

```
┌─────────────┬──────────────────────────────────────────────────┐
│  Sidebar    │                  Main Content                     │
│   260px     │        fluid, max-width: 1440–1520px             │
│  (desktop)  │                                                   │
└─────────────┴──────────────────────────────────────────────────┘
```

| Property | Nilai |
|---|---|
| Sidebar width | 260 px (desktop), *drawer* (tablet/mobile) |
| Main max-width | 1440–1520 px |
| Content padding | 24–32 px kiri-kanan |
| Gap antar card/kolom | 20–24 px |
| Card border-radius | 20–24 px |
| Card padding | 20–28 px |
| Card shadow | `0 6px 22px rgba(15,23,42,.045)` |
| Card border | `1px solid #DCEBFA` |
| Transition default | `0.25s ease` untuk hover dan shadow |

### Breakpoints

```
Desktop     ≥ 1200px  → sidebar permanen, KPI 5 kolom, chart 2–4 kolom
Tablet      768–1199px → sidebar sebagai drawer, KPI 2–3 kolom, chart 2 kolom
Mobile      ≤ 767px   → sidebar drawer, KPI 1–2 kolom, chart 1 kolom
Small       ≤ 480px   → KPI 1 kolom, hero compact, tabs scroll
```

### Responsive Behavior Detail

| Komponen | Desktop | Tablet | Mobile |
|---|---|---|---|
| Sidebar | Permanen kiri | Drawer (toggle) | Drawer (toggle) |
| KPI Cards | 5 kolom | 2–3 kolom | 1 kolom |
| Overview charts | 2 kolom | 2 kolom | 1 kolom |
| Analisis Survei chart | Full width | Full width | Full width |
| Analisis Ulasan charts | 2 kolom | 2 kolom | 1 kolom |
| Tabs | Horizontal pill | Horizontal pill | Horizontal scroll |
| Tabel | Fixed height, full width | Full width | Horizontal scroll |
| Hero | Gambar kanan, teks kiri | Gambar kanan kecil | Tanpa gambar |
| Topbar | Full row | Full row | Compact |

---

## 7. Page Architecture

Struktur halaman lengkap yang harus diimplementasikan:

```
DANA Insight Command Center
│
├── [Opsional] Lobby / Landing Page
│    └── Tombol "Masuk ke Dashboard" → Dashboard Shell
│
└── Dashboard Shell
     ├── Sidebar Filter & Kontrol (260px, biru, sticky desktop)
     └── Main Area
          ├── Topbar (sticky, putih)
          ├── Hero Banner (gambar + stats)
          ├── KPI Cards (5 kartu)
          ├── Filter Status Banner
          ├── Tabs
          │    ├── Tab 0: Overview
          │    ├── Tab 1: Analisis Survei
          │    ├── Tab 2: Analisis Ulasan
          │    ├── Tab 3: Data Explorer
          │    └── Tab 4: Lampiran Presentasi
          └── Kesimpulan Utama (di bawah tabs, selalu tampil)
```

---

## 8. Lobby / Landing Page Design

Landing page bersifat **opsional** — dapat dilewati dengan *query param* atau toggle sesi.

### Spesifikasi Visual

| Elemen | Spesifikasi |
|---|---|
| Visual kanan | `assets/dana_hero_full_1600x900.png` |
| Logo kiri atas | `assets/dana_logo_wordmark_header_480x120.png` |
| Background | Gradien `#EAF6FF → #FFFFFF` atau `#004AAD → #108EE9` (dark mode) |
| Layout | Split 50/50 — teks kiri, gambar kanan |

### Konten Wajib

**Bagian kiri:**
```
[Logo DANA]
[Eyebrow: Fintech Experience Analytics · 2026]

DANA Insight
Command Center

Dashboard interaktif untuk memahami pengalaman pengguna DANA
berdasarkan data survei dan ulasan pengguna.

[Tombol Utama: Masuk ke Dashboard →]
[Tombol Sekunder: Lihat Ringkasan ↓]
```

**KPI Mini Row** (di bawah tombol):
```
50           |  330        |  20         |  4.00       |  70.3%
Responden    |  Ulasan     |  Indikator  |  Skor       |  Sentimen +
```

**Card Modul** (6 card di bawah KPI mini):
```
[Overview]  [Analisis Survei]  [Analisis Ulasan]
[Data Explorer]  [Lampiran Presentasi]  [Kesimpulan]
```

**Privacy Banner** (paling bawah landing):
```
🔒 Seluruh identitas pribadi pengguna disamarkan.
   Data yang ditampilkan bersifat agregat dan anonim.
```

---

## 9. Dashboard Shell Design

Dashboard utama mengikuti struktur referensi dengan elemen berikut:

```
┌──────────────────────────────────────────────────────────────────┐
│  TOPBAR — logo | title | search | refresh | avatar              │ sticky
├──────────────┬───────────────────────────────────────────────────┤
│              │  HERO BANNER                                      │
│   SIDEBAR    │  KPI CARDS  [5 kolom]                            │
│              │  FILTER STATUS BANNER                             │
│  (Filter &   │  ┌─────────────────────────────────────────────┐ │
│  Kontrol)    │  │ TABS: Overview | Survei | Ulasan | Explorer  │ │
│              │  │        | Lampiran                            │ │
│   260px      │  │  ....content berdasarkan tab aktif....       │ │
│   biru       │  └─────────────────────────────────────────────┘ │
│   sticky     │  KESIMPULAN UTAMA                                 │
│              │  FOOTER                                           │
└──────────────┴───────────────────────────────────────────────────┘
```

---

## 10. Sidebar Filter & Kontrol

### Visual

```css
background: linear-gradient(180deg, #004AAD 0%, #108EE9 100%);
width: 260px;
position: sticky;   /* desktop */
position: fixed;    /* tablet/mobile — di belakang overlay */
top: 0;
height: 100vh;
overflow-y: auto;
```

### Struktur Konten (dari atas ke bawah)

```
[Logo DANA — assets/dana_mark.svg + wordmark]

─────── FILTER & KONTROL ───────

Periode Data
  └── [Tanggal mulai] – [Tanggal akhir]

─── Filter Survey ───
  Gender         [Multiselect: Semua / Perempuan / Laki-laki]
  Kelompok Usia  [Multiselect: Semua / < 18 / 18-22 / 23-27 / > 27]
  Frekuensi      [Multiselect: Semua / Jarang / Beberapa kali seminggu / Setiap hari]
  Tanggal Survei [Date range — jika kolom Timestamp tersedia]

─── Filter Ulasan ───
  Sentimen       [Multiselect: Semua / Positif / Netral / Negatif]
  Rating         [Multiselect: Semua / 1 / 2 / 3 / 4 / 5]
  Tanggal Ulasan [Date range]
  Cari kata      [Text input]
  Urutkan        [Selectbox: Terbaru / Terlama / Rating ↑ / Rating ↓]

─── Tampilan ───
  Indikator View [Selectbox: Semua / Top 5 / Bottom 5 / X1/X2/M/Y]
  Kategori Skor  [Multiselect: Kuat/Baik / Cukup / Perlu Perhatian]
  Baris tabel    [Selectbox: 10 / 25 / 50 / 100 / Semua]
  Insight otomatis [Toggle ON/OFF]
  Animasi        [Toggle ON/OFF]
  Mode Presentasi [Toggle ON/OFF]

[  Terapkan Filter  ]     ← tombol putih besar
[  Reset Filter     ]     ← tombol outline

─────────────────────────────
Data updated: DD MMM YYYY HH:MM WIB
```

### Aturan Logika Filter

> **PENTING:** Kedua sumber data bersifat independen.

| Filter | Memengaruhi |
|---|---|
| Gender, Usia, Frekuensi, Tanggal Survei | Responden survei, skor kuesioner, variabel X1/X2/M/Y |
| Sentimen, Rating, Tanggal Ulasan, Kata kunci | Ulasan, distribusi sentimen, rating, keyword, tabel ulasan |
| Insight/Animasi/Mode | Tampilan visual saja, tidak memengaruhi data |

- Jika user memilih **semua opsi** pada satu filter → filter tersebut dianggap tidak aktif.
- Chip filter aktif **tidak boleh muncul** jika semua opsi dipilih.
- Filter gender **tidak pernah** memengaruhi data ulasan.

---

## 11. Topbar Design

### Visual

```css
background: #FFFFFF;
border-bottom: 1px solid #DCEBFA;
box-shadow: 0 2px 8px rgba(15,23,42,.04);
position: sticky;
top: 0;
z-index: 1000;
height: 56–64px;
padding: 0 24px;
```

### Elemen (kiri ke kanan)

```
[☰ Toggle Sidebar]  [Logo kecil DANA]  [DANA Insight Command Center]
                    ────────────── spacer ──────────────
[🔍 Search/Filter Input]  [↻ Refresh]  [⬤ Data Loaded]  [👤 Admin]
```

- **Toggle Sidebar:** Muncul di tablet/mobile untuk membuka/menutup *drawer*.
- **Logo kecil:** `assets/dana_mark.svg` — 32×32 px.
- **Title:** "DANA Insight Command Center" — font-weight 800.
- **Refresh button:** Bersihkan cache data, beri feedback loading sementara.
- **Status badge:** Hijau jika data berhasil dimuat; merah jika ada error.
- Topbar tidak boleh terlalu tinggi — maksimal 64 px.

---

## 12. Hero Banner Design

### Visual

```css
height: 220–260px;             /* desktop */
height: 160–200px;             /* tablet */
height: auto; min-height: 140px; /* mobile */
background-image: url('assets/dana_hero_banner_1920x520.png');
background-size: cover;
background-position: center right;
border-radius: 20–24px;
overflow: hidden;
```

### Overlay

Tambahkan overlay putih transparan di **sisi kiri** agar teks selalu terbaca:

```css
/* Pseudo-element overlay */
background: linear-gradient(90deg,
  rgba(0, 74, 173, 0.88) 0%,
  rgba(16, 142, 233, 0.65) 55%,
  transparent 100%);
```

### Konten Teks (di atas overlay, kiri)

```
[Eyebrow badge: Total Data · Fintech Experience Analytics]

DANA Insight
Command Center

Dashboard interaktif untuk memahami pola penggunaan,
skor pengalaman, rating, dan sentimen pengguna aplikasi DANA.

[50 Responden]  [330 Ulasan]  [Plotly Interaktif]  [Data Anonim]
─────────────────────────────────────────────────────
50          |  330       |  4.00       |  3.89 / 5  |  70.3%
Responden   |  Ulasan    |  Skor Rata  |  Rating    |  Sentimen+
```

### Gambar Kanan

- Gunakan `assets/dana_wallet_cluster_720x720.png` atau `assets/dana_mobile_mockup_720x960.png` sebagai ilustrasi kanan.
- Ukuran: `max-width: 220px` di desktop, sembunyikan di mobile (max-width 480px).
- Tambahkan `filter: drop-shadow(...)` untuk kesan mengambang.
- **Jangan biarkan gambar menutupi teks.** Gunakan `pointer-events: none` dan pastikan gambar berada di layer belakang teks via z-index.

---

## 13. KPI Card Design

### Lima KPI Wajib

| # | Label | Nilai | Warna | Progress |
|---|---|---|---|---|
| 1 | Responden Survei | **50** | `#108EE9` | Tidak ada |
| 2 | Ulasan Pengguna | **330** | `#2563EB` | Tidak ada |
| 3 | Rata-rata Skor | **4.00 / 5** | `#108EE9` | 80% (4/5) |
| 4 | Rata-rata Rating | **3.89 / 5** | `#F9B233` | 77.8% |
| 5 | Sentimen Positif | **70.3%** | `#16B978` | 70.3% |

### Struktur Satu Card

```
┌──────────────────────────────────┐
│  [Icon]                  [Label] │  ← row atas
│                                  │
│  42                              │  ← angka besar (animasi)
│  caption kecil                   │
│  ████████░░░░░░░░░░░░░░░░░░░░░  │  ← progress bar (jika ada)
└──────────────────────────────────┘
```

### CSS

```css
.kpi-card {
  min-height: 156px;
  padding: 20px;
  border: 1px solid var(--dana-border);
  border-radius: 20px;
  background: var(--dana-card);
  box-shadow: 0 6px 22px rgba(15,23,42,.045);
  transition: transform .25s ease, box-shadow .25s ease;
}

.kpi-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 16px 34px rgba(16,142,233,.11);
}

.kpi-value {
  font-size: clamp(28px, 3.5vw, 42px);
  font-weight: 850;
  letter-spacing: -0.04em;
  color: var(--dana-text);
}

.progress-bar {
  height: 6px;
  border-radius: 999px;
  background: var(--kpi-color);
  animation: grow-bar 0.9s cubic-bezier(.16,1,.3,1) both;
}
```

### Aturan

- **Nilai wajib dari data aktual** — tidak boleh *hardcode* di tampilan.
- Animasi *count-up* saat pertama kali dimuat (jika animasi aktif).
- Jika filter aktif, caption berubah menjadi "berdasarkan filter aktif".
- Jangan menampilkan data palsu jika data belum dimuat.

---

## 14. Filter Status Banner

### Aturan Tampilan

```
Kondisi 1 — Tidak ada filter aktif:
┌───────────────────────────────────────────────────────┐
│  Menampilkan seluruh data. Tidak ada filter yang       │
│  mempersempit dataset.                                 │
└───────────────────────────────────────────────────────┘
  (background: #F8FAFC, border: #E2E8F0, teks: #64748B)

Kondisi 2 — Ada filter aktif:
┌────────────────────────────────────────────────────────┐
│  Filter aktif                                          │
│  [Gender: Perempuan]  [Usia: 18-22 Tahun]  [... ]     │
└────────────────────────────────────────────────────────┘
  (background: #EFF6FF, border: #BFDBFE, teks: #1E40AF)
```

### Aturan Chip

- Chip hanya muncul jika **sebagian** opsi dipilih (bukan semua).
- Jika semua gender dipilih → **tidak muncul** chip gender.
- Jika semua rating (1,2,3,4,5) dipilih → **tidak muncul** chip rating.
- Jika semua sentimen dipilih → **tidak muncul** chip sentimen.
- Chip yang tampil harus mencerminkan kondisi filter yang benar-benar aktif.

---

## 15. Tabs Design

### Lima Tab Wajib

```
[ Overview ]  [ Analisis Survei ]  [ Analisis Ulasan ]  [ Data Explorer ]  [ Lampiran Presentasi ]
```

### Visual

```css
/* Tab container */
.tab-list {
  display: flex;
  gap: 4px;
  padding: 5px;
  background: #EDF5FF;
  border: 1px solid var(--dana-border);
  border-radius: 999px;
  overflow-x: auto;             /* horizontal scroll di mobile */
  scrollbar-width: none;        /* sembunyikan scrollbar */
}

/* Tab item */
.tab-item {
  min-height: 38px;
  padding: 6px 16px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 700;
  color: var(--dana-muted);
  white-space: nowrap;
  cursor: pointer;
  transition: all 0.2s ease;
}

/* Tab aktif */
.tab-item.active {
  color: var(--dana-deep);
  background: white;
  box-shadow: 0 5px 14px rgba(16,142,233,.13);
}
```

- Setiap tab boleh memiliki ikon kecil (SVG 14–16 px) di sebelah kiri label.
- Di mobile, tabs harus bisa di-*scroll* horizontal tanpa scrollbar terlihat.
- Animasi transisi tab: *fade-in* ringan (opacity 0 → 1, 0.3s).

---

## 16. Overview Content

### Summary Cards (4 card di atas chart)

```
[Mayoritas Responden]  [Frekuensi Terbanyak]  [Rating Rata-rata]  [Sentimen Dominan]
 Perempuan (78%)        Jarang                  3.89 / 5            Positif (70.3%)
```

### Charts (2×2 grid)

| Posisi | Chart | Data |
|---|---|---|
| Kiri atas | Distribusi Gender Responden (Donut) | Perempuan 78%, Laki-laki 22% |
| Kanan atas | Frekuensi Penggunaan DANA (Bar) | Jarang 42%, dll. |
| Kiri bawah | Distribusi Kelompok Usia (Bar) | 18-22 Th 72%, dll. |
| Kanan bawah | Volume Ulasan per Tanggal (Bar) | 09 Jun: 248, 10 Jun: 82 |

### Data yang Harus Muncul (dari data aktual)

```
Mayoritas responden: Perempuan = 39/50 = 78%
Frekuensi dominan:   Jarang = 21/50 = 42%
Rating rata-rata:    3.89 / 5
Sentimen dominan:    Positif = 232/330 = 70.3%
Volume ulasan:       9 Jun: 248 | 10 Jun: 82
```

---

## 17. Analisis Survei Content

### Health Cards (3 card kualitas indikator)

```
[Indikator Kuat/Baik]  [Indikator Cukup]  [Perlu Perhatian]
       13                     7                   0
    Skor ≥ 4.00           Skor 3–3.99          Skor < 3.00
```

### Variabel Penelitian (4 card atau 1 chart bar)

```
X1 - Fleksibilitas   : [skor dihitung dari indikator terkait]
X2 - Praktis         : [skor dihitung dari indikator terkait]
M  - Kepercayaan     : [skor dihitung dari indikator terkait]
Y  - Keseluruhan     : [rata-rata seluruh Q1-Q20]
```

> Angka skor **wajib dihitung dari data aktual**, bukan di-*hardcode*.

### Chart Horizontal Bar (Q1–Q20)

- Sumbu Y: label Q1, Q2, ... Q20 (dengan pertanyaan singkat di tooltip).
- Sumbu X: rata-rata skor 0–5.
- Warna: hijau ≥ 4.00, kuning 3.00–3.99, merah < 3.00.
- Garis vertikal putus-putus di x=3 (batas cukup) dan x=4 (batas kuat).
- Label angka di kanan bar.
- Urutkan dari terendah (atas) ke tertinggi (bawah).

### Top & Bottom 5

```
Top 5:                          Bottom 5:
1. Q__ — [pertanyaan] — x.xx   1. Q__ — [pertanyaan] — x.xx
...                             ...
```

### Insight Otomatis Survei

```
Rata-rata keseluruhan: 4.00/5
Indikator tertinggi: Q__ (x.xx) — [pertanyaan]
Indikator terendah: Q__ (x.xx) — [pertanyaan]
Area terendah layak menjadi prioritas evaluasi.
```

> **Catatan Metodologi:** Nilai variabel M (Kepercayaan) yang tercatat sebesar 3.82
> adalah rata-rata indikator M. Jika ada indikator individual di bawah itu, boleh
> disebut "indikator M terendah" — tetapi jangan menyebut angka indikator sebagai
> "nilai variabel M".

---

## 18. Analisis Ulasan Content

### Summary Cards (5 card)

```
[Total Ulasan]  [Positif]  [Netral]  [Negatif]  [Rating Rata-rata]
    330           232        13         85            3.89
                70.3%       3.9%      25.8%         dari 5
```

### Keyword Chips (umum, dari semua ulasan)

```
[kata1 (n)]  [kata2 (n)]  [kata3 (n)]  ...
```

- Diambil dari frekuensi kata dalam teks ulasan (bukan asumsi manual).
- Stopwords Indonesia disaring.
- Tampilkan 15 keyword teratas.

### Charts

| Chart | Tipe | Data |
|---|---|---|
| Distribusi Sentimen | Donut | Positif 70.3%, Netral 3.9%, Negatif 25.8% |
| Distribusi Rating | Bar (warna) | 1–5 bintang |
| Volume Ulasan per Tanggal | Bar | 9 Jun: 248, 10 Jun: 82 |

### Keluhan Negatif Utama

```
[keyword1 (n)]  [keyword2 (n)]  ...
```

- **Wajib diambil hanya dari ulasan berstatus Negatif** (sentimen = "Negatif").
- Bukan dari asumsi atau daftar manual.
- Tampilkan 5–10 keyword terbanyak.
- Cantumkan caption: "Kata dalam ulasan negatif; satu ulasan bisa mengandung lebih dari satu istilah."

### Tabel Ulasan Aman

```
No | Rating | Tanggal          | Ulasan                    | Sentimen
 1 |   5    | 09-06-2026 ...   | "Aplikasi sangat..."      | Positif
 2 |   1    | 09-06-2026 ...   | "Saldo hilang..."         | Negatif
...
```

- Kolom username **tidak boleh tampil**.
- Height stabil (mis. 520 px), bisa horizontal scroll.
- Download CSV aman (tanpa username/nama).

---

## 19. Data Explorer Content

### Struktur

```
[Privacy Note Banner]

#### Data Survey
[Tabel survey — tanpa kolom identitas]
[Download survey hasil filter (CSV aman)]

────────────────────────

#### Data Ulasan
[Tabel ulasan — tanpa username/nama]
[Download ulasan hasil filter (CSV aman)]

────────────────────────

#### Data Hasil Kuesioner
[Tabel: No | Kode | Pertanyaan | Rata-rata]
[Download hasil kuesioner publik (CSV aman)]
```

### Privacy Note Banner

```
🔒 Privacy note. Nama responden, username, email, nomor telepon, dan kolom
identitas serupa tidak ditampilkan. File download publik juga tidak memuat
identitas pengguna.
```

### Aturan Tabel

- `hide_index = True`
- Height stabil (390–440 px untuk survey/ulasan, auto untuk kuesioner)
- Horizontal scroll otomatis
- Tidak menampilkan kolom bertipe identitas (nama, email, username, nomor)

---

## 20. Lampiran Presentasi Content

### Struktur

```
[Audit Sumber Data — tabel metadata file]
[Status validasi baseline]

#### Deliverables (grid 3 kolom)
[Dashboard Streamlit]  [Source Code]  [GitHub Repository]
[Streamlit Cloud]      [Screenshot]   [Ringkasan Fitur]

#### Tautan Publik
GitHub URL     : [kolom input — isi setelah repository dibuat]
Streamlit URL  : [kolom input — isi setelah deployment]
Catatan: isi ini hanya catatan sesi, tidak otomatis terhubung.

#### Daftar Screenshot Presentasi
No | Nama Screenshot           | Status
 1 | 01_Hero_KPI               | Perlu diambil setelah QA visual
 2 | 02_Control_Panel          | ...
 3 | 03_Overview               | ...
 4 | 04_Analisis_Survei        | ...
 5 | 05_Analisis_Ulasan        | ...
 6 | 06_Data_Explorer          | ...
 7 | 07_Kesimpulan             | ...

#### Ringkasan Fitur Dashboard
[Deskripsi fitur utama — 1 paragraf]

#### Checklist Output
[ ] app.py dapat di-compile
[ ] Data 50 survey, 330 ulasan, 20 indikator
[ ] KPI sesuai baseline
[ ] Tooltip rapi
[ ] Tidak ada identitas pribadi tampil
[ ] Semua tab berfungsi
[ ] Mobile responsif
[ ] Download CSV aman
```

### Aturan

- Jangan membuat link palsu atau URL yang tidak aktif.
- Placeholder boleh ditampilkan sebagai input teks kosong.
- Tab ini adalah **lampiran akademik**, bukan bagian inti analisis.

---

## 21. Chart Design Rules

### Library

Gunakan **Plotly** (`plotly.graph_objects`). Tidak ada library chart lain yang dibutuhkan.

### Konfigurasi Global Wajib

```python
PLOTLY_CONFIG = {
    "displayModeBar": False,   # ← WAJIB False — hilangkan modebar bawaan
    "displaylogo": False,
    "responsive": True,
    "scrollZoom": False,
}
```

> ⚠️ **Jangan gunakan fullscreen Plotly bawaan.** Fullscreen Plotly menyebabkan glitch
> pada layout Streamlit karena konflik z-index dan event listener. Sebagai gantinya,
> gunakan **`st.expander` besar** atau **custom "Lihat Detail"** untuk chart penting
> yang ingin ditampilkan lebih besar.

### Layout Default Chart

```python
def base_layout(title, height=330, **overrides):
    return {
        "title": {
            "text": f"<b>{title}</b>",
            "x": 0.02, "y": 0.96,
            "font": {"size": 14, "color": "#071633"},
        },
        "template": "plotly_white",
        "height": height,
        "margin": {"t": 55, "b": 32, "l": 28, "r": 24},
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "font": {"family": "Inter, Segoe UI, sans-serif", "color": "#64748B"},
        "hoverlabel": {"bgcolor": "#071633", "font_color": "white", "bordercolor": "#108EE9"},
        "transition": {"duration": 500, "easing": "cubic-in-out"},
        **overrides
    }
```

### Chart Heights yang Direkomendasikan

| Chart | Height |
|---|---|
| Donut (distribusi) | 320–360 px |
| Bar horizontal (Q1–Q20) | max(500, n×29+100) px |
| Bar vertikal (variabel, rating) | 340–380 px |
| Bar tanggal / trend | 300–340 px |
| Bar distribusi jam | 300 px |

### Rendering

```python
st.plotly_chart(
    figure,
    use_container_width=True,   # ← gunakan ini untuk responsivitas
    theme=None,
    config=PLOTLY_CONFIG,
    key="unique_key",
)
```

---

## 22. Tooltip Rules

Semua tooltip Plotly **wajib menggunakan format presisi tetap**. Jangan biarkan angka
*floating point* panjang seperti `70.3030303030303` muncul di tooltip.

### Contoh Tooltip Wajib

**Gender (Donut):**
```html
<b>Perempuan</b><br>
39 dari 50 responden<br>
78.0% dari total data<extra></extra>
```

**Sentimen (Donut):**
```html
<b>Positif</b><br>
232 dari 330 ulasan<br>
70.3% dari total data<extra></extra>
```

**Rating (Bar):**
```html
<b>Rating 5</b><br>
220 dari 330 ulasan<br>
66.7% dari total data<extra></extra>
```

**Volume Ulasan per Tanggal (Bar):**
```html
<b>2026-06-09</b><br>
248 dari 330 ulasan<br>
75.2% dari total data<extra></extra>
```

**Skor Indikator (Bar Horizontal):**
```html
<b>Q2</b><br>
Pertanyaan: Saya merasa aplikasi DANA...<br>
Skor rata-rata: <b>4.26</b><br>
Interpretasi: Kuat/Baik<br>
Berdasarkan 50 responden (Total data)<extra></extra>
```

**Variabel (Bar Vertikal):**
```html
<b>X2 - Praktis</b><br>
Skor rata-rata: <b>4.26</b><br>
Interpretasi: Kuat/Baik<br>
Berdasarkan 1 indikator<br>
Dari Total data<extra></extra>
```

### Implementasi Teknis

Untuk mencegah angka panjang, gunakan pendekatan berikut:

```python
# ✅ BENAR — format persentase sebelum masuk customdata
customdata = [
    [total, f"{pct:.1f}", scope_label]
    for pct in percentages
]
# hovertemplate: "%{customdata[1]}% dari ..."

# ❌ SALAH — biarkan Plotly format sendiri
customdata = [[total, pct, scope_label] for pct in percentages]
# hovertemplate: "%{customdata[1]:.1f}% dari ..."
# ← bisa tetap akurat, tapi string pre-format lebih aman
```

- Jangan ada teks seperti `Scope: -` atau `Data tampil: Total data` yang terasa seperti debug output.
- Semua teks dalam tooltip harus natural dalam bahasa Indonesia.

---

## 23. Table Design Rules

### Kolom Ulasan yang Disarankan

```
No | Rating | Tanggal          | Ulasan (teks)              | Sentimen
```

- Kolom **username, nama, email, telepon** wajib dihapus sebelum ditampilkan.
- Fungsi `sanitize_public_df()` harus aktif sebelum semua `st.dataframe()`.

### Konfigurasi Streamlit DataFrame

```python
st.dataframe(
    frame,
    use_container_width=True,   # responsif
    height=520,                 # tinggi stabil, bisa scroll vertikal
    hide_index=True,
    column_config={
        "No": st.column_config.NumberColumn("No", width="small"),
        "rating": st.column_config.NumberColumn("Rating", format="%d", width="small"),
        "tanggal": st.column_config.DatetimeColumn("Tanggal", format="DD-MM-YYYY HH:mm"),
        "ulasan": st.column_config.TextColumn("Ulasan", width="large"),
        "sentimen": st.column_config.TextColumn("Sentimen", width="small"),
    }
)
```

### Aturan Tambahan

- Jangan pernah gunakan `st.write(dataframe)` — selalu `st.dataframe()`.
- Tidak menggunakan fullscreen bawaan Streamlit/Plotly yang bisa menyebabkan glitch.
- Download button CSV menggunakan `utf-8-sig` encoding agar Excel Indonesia terbaca.
- Tabel kuesioner tidak perlu `hide_index=True` jika sudah ada kolom "No".

---

## 24. Animation & Microinteraction

### Yang Harus Ada

| Animasi | Deskripsi |
|---|---|
| **Fade-in page** | Konten utama muncul dengan opacity 0→1, 0.55s |
| **Fade-up card** | Card muncul dari bawah 14px, 0.62s |
| **KPI count-up** | Angka KPI beranimasi naik dari 0 ke nilai asli (950ms) |
| **Card hover lift** | `translateY(-4px)`, shadow meningkat, 0.25s |
| **Progress bar grow** | Bar tumbuh dari kiri, `scaleX(0→1)`, 0.9s |
| **Tab underline** | Slide smooth saat berganti tab |
| **Button hover** | Background lebih gelap / terang, 0.2s |
| **Sidebar hover** | Item hover warna sedikit lebih terang |
| **Hero asset float** | Animasi naik-turun lembut (keyframe float), 4s infinite |

### Yang Harus Dihindari

- Animasi berat (particle, WebGL, 3D transform kompleks).
- Animasi berulang-ulang yang mengganggu pembacaan data.
- Animasi yang tidak bisa dimatikan (pengguna harus bisa menonaktifkan via toggle).

### Respek Prefers-Reduced-Motion

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

## 25. Accessibility & Readability

### Kontras Warna

| Elemen | Minimum Kontras |
|---|---|
| Teks body di atas putih | 4.5:1 (WCAG AA) |
| Heading di atas putih | 3:1 (WCAG AA) |
| Teks di atas sidebar biru | 4.5:1 |
| Angka KPI | 4.5:1 |

### Aturan Keterbacaan

- Font minimum: 12 px untuk caption; 14 px untuk body.
- Jangan bergantung **hanya** pada warna untuk menyampaikan informasi — selalu sertakan label teks.
- Semua chart harus memiliki label nilai di atas/samping bar, tidak hanya di tooltip.
- Tombol harus memiliki label teks yang jelas — tidak hanya ikon.
- Tabel harus memiliki header kolom yang deskriptif.
- Input filter harus memiliki label yang jelas.

### Atribut HTML Tambahan

```html
<img src="..." alt="Logo DANA" />              <!-- jangan alt="" untuk gambar bermakna -->
<button aria-label="Buka filter panel">...</button>
<section aria-labelledby="section-title-id">  <!-- beri landmark -->
```

---

## 26. Implementation Notes for Streamlit

### Konfigurasi Dasar

```python
st.set_page_config(
    page_title="DANA Insight Command Center",
    page_icon="D",           # atau path ke favicon
    layout="wide",
    initial_sidebar_state="collapsed",
)
```

### CSS Global

- Letakkan semua CSS kustom dalam satu fungsi `inject_custom_css()` yang dipanggil di awal `main()`.
- Gunakan CSS Variables (`--dana-*`) agar perubahan warna mudah dilakukan terpusat.
- Jangan menyebarkan CSS inline ke seluruh fungsi render.

### Helper Asset

```python
def asset_svg(filename: str, fallback: str = "") -> str:
    """Baca SVG lokal dari folder assets/."""
    path = ASSETS_DIR / filename
    return path.read_text(encoding="utf-8") if path.exists() else fallback

def asset_img_b64(filename: str) -> str:
    """Encode PNG/JPG ke base64 untuk dipakai di <img src='data:...'>."""
    path = ASSETS_DIR / filename
    if not path.exists():
        return ""
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    mime = "image/png" if filename.endswith(".png") else "image/jpeg"
    return f"data:{mime};base64,{data}"
```

- Helper harus mampu membaca **PNG** dan **SVG** lokal.
- Jangan me-*request* URL internet untuk aset — semua lokal dari `assets/`.

### Chart Helper

```python
def plot_chart(figure: go.Figure, key: str) -> None:
    st.plotly_chart(
        figure,
        use_container_width=True,
        theme=None,
        config=PLOTLY_CONFIG,
        key=key,
    )
```

- Semua chart memanggil `plot_chart()` yang sama agar konfigurasi konsisten.
- Key harus **unik** per chart per halaman.

### Versi Streamlit

- Gunakan `use_container_width=True` (standar saat ini).
- Jika versi Streamlit mendukung `width="stretch"`, boleh dipakai sebagai alternatif — tetapi pastikan tidak error di deployment.
- Jangan memakai `st.legacy_caching` atau API yang sudah *deprecated*.

### Dependency

Jaga agar `requirements.txt` tetap minimal:
```
streamlit>=1.35
plotly>=5.20
pandas>=2.1
numpy>=1.26
openpyxl>=3.1
```

Jangan menambah library berat (PyTorch, Transformers, dll.) hanya untuk fitur kecil.

### Pipeline Data

- **Jangan ubah** `load_all_data()`, `prepare_survey_data()`, `prepare_review_data()`.
- Semua filter harus bekerja di layer *presentation*, bukan mengubah data sumber.
- `compute_questionnaire_from_survey()` dan `compute_variable_scores()` harus tetap *pure* — tidak menulis ke disk.

---

## 27. QA Checklist

Sebelum dianggap siap presentasi, verifikasi semua item berikut:

### Data & Validasi

- [ ] `python -m py_compile app.py` sukses tanpa error
- [ ] `python -m streamlit run app.py` jalan tanpa crash
- [ ] Survey terbaca: **50 baris**
- [ ] Ulasan terbaca: **330 baris**
- [ ] Indikator kuesioner: **20 baris**
- [ ] KPI "Responden Survei" menampilkan **50**
- [ ] KPI "Ulasan Pengguna" menampilkan **330**
- [ ] KPI "Rata-rata Skor" menampilkan **4.00**
- [ ] KPI "Rata-rata Rating" menampilkan **3.89**
- [ ] KPI "Sentimen Positif" menampilkan **70.3%**

### Tampilan

- [ ] Tooltip hanya menampilkan angka presisi 1 desimal (tidak ada `70.303030...`)
- [ ] Modebar Plotly tidak muncul (displayModeBar: False aktif)
- [ ] Fullscreen Plotly tidak dipakai (tidak ada glitch layout)
- [ ] Custom "Lihat Detail" / expander chart berfungsi tanpa glitch
- [ ] Sidebar desktop rapi (260px, warna gradien biru)
- [ ] Drawer tablet/mobile terbuka dan tertutup dengan benar
- [ ] Hero banner: gambar tidak menutupi teks
- [ ] Teks di atas hero terbaca dengan baik

### Filter

- [ ] Chip filter aktif **tidak muncul** jika semua opsi dipilih
- [ ] Filter gender tidak memengaruhi data ulasan
- [ ] Filter sentimen tidak memengaruhi data survey
- [ ] Reset Filter mengembalikan semua ke default

### Privasi

- [ ] Kolom nama responden tidak tampil di Data Explorer
- [ ] Kolom username tidak tampil di tabel ulasan
- [ ] Download CSV survey tidak menyertakan nama/email
- [ ] Download CSV ulasan tidak menyertakan username

### Responsivitas

- [ ] Desktop (≥1200px): sidebar permanen, KPI 5 kolom, chart 2+ kolom
- [ ] Tablet (768–1199px): sidebar drawer, KPI 2–3 kolom, chart 2 kolom
- [ ] Mobile (≤767px): KPI 1 kolom, chart 1 kolom, tabs horizontal scroll
- [ ] Small mobile (≤480px): KPI 1 kolom, hero compact, semua konten terbaca
- [ ] Tabel bisa horizontal scroll di mobile

### Kesimpulan Utama

- [ ] Profil responden: Perempuan = 39/50 = 78%
- [ ] Usia dominan: 18–22 Tahun = 36/50 = 72%
- [ ] Frekuensi dominan: Jarang = 21/50 = 42%
- [ ] Skor kuesioner rata-rata: 4.00/5
- [ ] Rating rata-rata: 3.89/5
- [ ] Sentimen positif: 232/330 = 70.3%
- [ ] Sentimen negatif: 85/330 = 25.8%
- [ ] Sentimen netral: 13/330 = 3.9%
- [ ] Variabel tertinggi dan terendah berdasarkan data (bukan hardcode)
- [ ] Keyword keluhan hanya dari ulasan berstatus Negatif

---

## 28. Final Acceptance Criteria

Dashboard dianggap **selesai dan siap presentasi** jika semua kondisi berikut terpenuhi:

| Kriteria | Keterangan |
|---|---|
| ✅ Visual mendekati referensi | Layout sidebar+main, hero, KPI, tabs, card sudah sesuai |
| ✅ Aset DANA lokal tampil | Logo, hero, ilustrasi dari folder `assets/` tampil jelas |
| ✅ Data tidak berubah | File survey, ulasan, kuesioner identik dengan aslinya |
| ✅ Filter survey dan ulasan terpisah | Tidak ada cross-contamination antar filter |
| ✅ Chart tidak glitch | Tidak ada fullscreen glitch, tooltip bersih, modebar hilang |
| ✅ Tabel aman dan rapi | Tanpa identitas pribadi, bisa scroll, download aman |
| ✅ Responsive berjalan | Desktop, tablet, mobile tampil dengan baik |
| ✅ Kesimpulan dinamis dan benar | Semua angka dalam Kesimpulan Utama dari data aktual |
| ✅ Siap presentasi dosen | Tampilan profesional, akademik, tidak ada placeholder test |

---

## 29. Asset Inventory

Daftar lengkap aset visual yang tersedia di folder `assets/` dan cara penggunaannya:

| Nama File | Ukuran / Format | Digunakan Di |
|---|---|---|
| `dana_logo_wordmark_header_480x120.png` | 480×120 px, PNG | Topbar, Lobby (logo atas) |
| `dana_logo_wordmark_1200x300.png` | 1200×300 px, PNG | Lobby (logo besar), Print |
| `dana_hero_banner_1920x520.png` | 1920×520 px, PNG | Hero Banner background |
| `dana_hero_full_1600x900.png` | 1600×900 px, PNG | Lobby (visual kanan split) |
| `dana_wallet_cluster_720x720.png` | 720×720 px, PNG | Hero (ilustrasi kanan) |
| `dana_mobile_mockup_720x960.png` | 720×960 px, PNG | Hero (alternatif ilustrasi) |
| `dana_mark.svg` | SVG vektor | Topbar (logo kecil), Brand mark |
| `filter_illustration.svg` | SVG vektor | Section heading Filter/Lampiran |
| `survey_illustration.svg` | SVG vektor | Section heading Survei/Explorer |
| `review_illustration.svg` | SVG vektor | Section heading Ulasan |
| `shield_privacy.svg` | SVG vektor | Privacy banner, Data Explorer |
| `variable_illustration.svg` | SVG vektor | Section heading Variabel/Kesimpulan |
| `wallet_illustration.svg` | SVG vektor | Hero (SVG fallback jika PNG gagal) |
| `empty_state.svg` | SVG vektor | State kosong jika data tidak ada |

### Aturan Penggunaan Aset

1. **Selalu coba aset lokal terlebih dahulu.** Jika file tidak ada, tampilkan fallback
   SVG inline atau `empty_state.svg`.
2. **Jangan mengunduh aset dari internet.** Semua aset harus sudah ada di `assets/`.
3. **PNG besar** (hero banner, hero full) hanya dipakai sebagai `background-image` CSS
   atau di-*encode* base64 — tidak pernah di-upload ke CDN atau URL eksternal.
4. **SVG** lebih disukai untuk ikon dan ilustrasi karena *scalable* dan tidak perlu
   base64 jika dipakai langsung di dalam HTML.

---

## 30. References Used

Panduan desain ini mengacu pada prinsip dan dokumentasi berikut:

- **Nielsen Norman Group — Dashboard Design Best Practices:**
  Dashboard harus menyampaikan informasi penting secara cepat, mudah dipahami, dan
  tidak memaksa pengguna berpikir keras untuk membaca data. Prioritaskan informasi
  kritis di area F-pattern (kiri atas, baris pertama).

- **Streamlit Official Documentation — `st.plotly_chart`:**
  Parameter `use_container_width=True` memastikan chart mengikuti lebar container
  induknya. Parameter `config` dapat digunakan untuk menonaktifkan modebar dan kontrol
  zoom. Key unik wajib diberikan untuk mencegah konflik state antar render.

- **Plotly Python — Configuration Reference:**
  `config={"displayModeBar": False, "displaylogo": False, "responsive": True,
  "scrollZoom": False}` adalah konfigurasi minimal untuk chart yang bersih di dalam
  Streamlit. `responsive: True` memungkinkan chart menyesuaikan ukuran saat jendela
  di-*resize*.

- **Material Design / MUI — Drawer Pattern:**
  Sidebar permanen di desktop (`persistent drawer`) dan sidebar yang muncul di atas
  konten saat dipanggil (`temporary drawer`) pada layar kecil adalah pola yang sudah
  teruji secara UX untuk navigasi dan filter kompleks.

- **WCAG 2.1 — Web Content Accessibility Guidelines:**
  Level AA mensyaratkan kontras minimum 4.5:1 untuk teks normal dan 3:1 untuk teks
  besar. Jangan bergantung hanya pada warna sebagai satu-satunya cara menyampaikan
  informasi.

- **Google Fonts — Inter:**
  Inter adalah typeface yang dirancang untuk keterbacaan tinggi di layar digital,
  cocok untuk dashboard analitik yang harus menampilkan banyak angka dan teks dengan
  kejelasan maksimal.

---

*Dokumen ini terakhir diperbarui: 14 Juni 2026.*
*Penyusun: Muhammad Arsyad Arroyan.*
*Jangan mengubah file data atau angka validasi saat mengimplementasikan panduan ini.*
