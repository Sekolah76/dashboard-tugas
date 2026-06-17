# FILE HELPER
# =============================================================================
def get_file_mtime(path: Path):
    """Return file modification time or None if file doesn't exist."""
    try:
        return path.stat().st_mtime if path.exists() else None
    except Exception:
        return None


def file_status(path: Path) -> dict:
    """Return dict with exists, size, readable status."""
    info = {"exists": False, "size": 0, "readable": False, "error": ""}
    if not path.exists():
        info["error"] = "File tidak ditemukan"
        return info
    info["exists"] = True
    info["size"] = path.stat().st_size
    if info["size"] == 0:
        info["error"] = "File kosong (0 byte)"
        return info
    info["readable"] = True
    return info


# =============================================================================
# DATA LOADING — cached with mtime so cache refreshes when file changes
# =============================================================================
@st.cache_data(show_spinner=True)
def load_excel_cached(path_str: str, mtime):
    """Load Excel file — mtime param busts cache when file changes."""
    return pd.read_excel(path_str, engine="openpyxl")


@st.cache_data(show_spinner=True)
def load_csv_cached(path_str: str, mtime):
    """Load CSV file — mtime param busts cache when file changes."""
    return pd.read_csv(path_str)


def load_data():
    """
    Load all three data files using absolute pathlib paths.
    Returns dict: survey, ulasan, kuesioner, errors (list of dicts).
    """
    result = {
        "survey":    None,
        "ulasan":    None,
        "kuesioner": None,
        "errors":    {},   # key -> error message
    }

    # ---- Survey ----
    fs = file_status(SURVEY_PATH)
    if not fs["exists"]:
        result["errors"]["survey"] = f"File tidak ditemukan: {SURVEY_PATH}"
    elif fs["size"] == 0:
        result["errors"]["survey"] = f"File kosong (0 byte): {SURVEY_PATH}"
    else:
        try:
            result["survey"] = load_excel_cached(
                str(SURVEY_PATH), get_file_mtime(SURVEY_PATH)
            )
        except Exception as e:
            result["errors"]["survey"] = f"File tidak bisa dibaca: {e}"

    # ---- Ulasan ----
    fu = file_status(REVIEW_PATH)
    if not fu["exists"]:
        result["errors"]["ulasan"] = f"File tidak ditemukan: {REVIEW_PATH}"
    elif fu["size"] == 0:
        result["errors"]["ulasan"] = f"File kosong (0 byte): {REVIEW_PATH}"
    else:
        try:
            result["ulasan"] = load_excel_cached(
                str(REVIEW_PATH), get_file_mtime(REVIEW_PATH)
            )
        except Exception as e:
            result["errors"]["ulasan"] = f"File tidak bisa dibaca: {e}"

    # ---- Kuesioner CSV ----
    fk = file_status(QUESTIONNAIRE_PATH)
    if not fk["exists"]:
        result["errors"]["kuesioner"] = f"File tidak ditemukan: {QUESTIONNAIRE_PATH}"
    elif fk["size"] == 0:
        result["errors"]["kuesioner"] = "File kosong (0 byte). Rata-rata akan dihitung dari survey."
    else:
        try:
            df_k = load_csv_cached(
                str(QUESTIONNAIRE_PATH), get_file_mtime(QUESTIONNAIRE_PATH)
            )
            if df_k.empty:
                result["errors"]["kuesioner"] = "File CSV kosong. Rata-rata akan dihitung dari survey."
            else:
                result["kuesioner"] = df_k
        except Exception as e:
            result["errors"]["kuesioner"] = f"File tidak bisa dibaca: {e}"

    return result


# =============================================================================
# COLUMN DETECTION
# =============================================================================
def detect_column(df, keywords):
    """Return first column name matching any keyword (case-insensitive)."""
    if df is None:
        return None
    for kw in keywords:
        for col in df.columns:
            if kw.lower() in str(col).lower():
                return col
    return None


def detect_questionnaire_columns(df):
    """
    Detect score columns: numeric columns with values in 1-5, excluding demographics.
    """
    if df is None:
        return []
    demo_kws = ["timestamp", "siapa nama", "jenis kelamin", "usia", "seberapa sering",
                "email", "no hp", "pekerjaan", "pendidikan"]
    q_cols = []
    for col in df.columns:
        col_l = col.lower()
        if any(kw in col_l for kw in demo_kws):
            continue
        if pd.api.types.is_numeric_dtype(df[col]):
            vals = df[col].dropna().unique()
            if len(vals) > 0 and all(v in [1, 2, 3, 4, 5] for v in vals if not np.isnan(float(v))):
                q_cols.append(col)
    # Fallback: any non-demo numeric column
    if not q_cols:
        for col in df.columns:
            if any(kw in col.lower() for kw in demo_kws):
                continue
            if pd.api.types.is_numeric_dtype(df[col]):
                q_cols.append(col)
    return q_cols


# =============================================================================
# DATA PREPARATION
# =============================================================================
def prepare_survey_data(df):
    """Return cleaned survey df + detected column dict."""
    if df is None:
        return None, {}
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    cols = {
        "nama":   detect_column(df, ["siapa nama", "nama anda", "nama"]),
        "gender": detect_column(df, ["jenis kelamin", "gender", "kelamin"]),
        "usia":   detect_column(df, ["usia", "umur", "age"]),
        "freq":   detect_column(df, ["seberapa sering", "frekuensi", "frequency"]),
        "timestamp": detect_column(df, ["timestamp", "waktu", "time"]),
    }
    cols["q_cols"] = detect_questionnaire_columns(df)

    # Hide nama column from display (privacy)
    if cols["nama"] and cols["nama"] in df.columns:
        df = df.drop(columns=[cols["nama"]])

    return df, cols


def prepare_review_data(df):
    """Return cleaned review df + detected column dict, with sentimen column."""
    if df is None:
        return None, {}
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    cols = {
        "username": detect_column(df, ["username", "user", "pengguna"]),
        "rating":   detect_column(df, ["rating", "bintang", "nilai"]),
        "tanggal":  detect_column(df, ["tanggal", "date", "waktu", "time"]),
        "ulasan":   detect_column(df, ["ulasan", "review", "komentar", "isi", "content"]),
    }

    # Sentimen from rating
    if cols["rating"] and cols["rating"] in df.columns:
        df[cols["rating"]] = pd.to_numeric(df[cols["rating"]], errors="coerce")
        def _sent(r):
            if pd.isna(r):  return "Netral"
            r = float(r)
            if r >= 4:      return "Positif"
            elif r == 3:    return "Netral"
            else:           return "Negatif"
        df["sentimen"] = df[cols["rating"]].apply(_sent)
    else:
        df["sentimen"] = "Tidak Diketahui"

    # Parse tanggal
    if cols["tanggal"] and cols["tanggal"] in df.columns:
        try:
            df[cols["tanggal"]] = pd.to_datetime(df[cols["tanggal"]], errors="coerce")
        except Exception:
            pass

    return df, cols


def prepare_questionnaire_data(survey_df, survey_cols, kuesioner_df):
    """
    Build DataFrame[pertanyaan, rata_rata, label].
    Priority: hasil_kuesioner.csv → compute from survey.
    Handles the actual CSV format: unnamed first col = pertanyaan, second col = nilai.
    """
    # ---- From CSV (actual format: Unnamed:0 = pertanyaan, '0' = nilai) ----
    if kuesioner_df is not None:
        df = kuesioner_df.copy()
        # Drop trailing empty rows
        df = df.dropna(how="all")

        # Detect columns flexibly
        cols = list(df.columns)
        # Check if it's the raw export format: first col = pertanyaan text, second = score
        # Column names might be 'Unnamed: 0' and '0'
        str_cols  = [c for c in cols if df[c].dtype == object or str(c).startswith("Unnamed")]
        num_cols  = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])]

        # Also try renamed approach
        rename_map = {}
        for c in cols:
            cs = str(c).lower().strip()
            if any(k in cs for k in ["pertanyaan", "question", "indikator", "unnamed"]):
                rename_map[c] = "pertanyaan"
            elif any(k in cs for k in ["rata", "mean", "avg", "skor", "score", "nilai"]):
                rename_map[c] = "rata_rata"
            # Handle numeric column name like '0'
            elif cs.isdigit():
                rename_map[c] = "rata_rata"
        df = df.rename(columns=rename_map)

        # If first column was Unnamed, it likely holds question text
        if "pertanyaan" not in df.columns and len(df.columns) >= 2:
            df.columns = ["pertanyaan", "rata_rata"] + list(df.columns[2:])

        if "pertanyaan" in df.columns and "rata_rata" in df.columns:
            df["rata_rata"] = pd.to_numeric(df["rata_rata"], errors="coerce")
            df = df.dropna(subset=["rata_rata"])
            df["pertanyaan"] = df["pertanyaan"].astype(str).str.strip()
            df = df[df["pertanyaan"].str.len() > 3]  # Remove empty/junk rows
            df = df.reset_index(drop=True)
            df["label"] = [f"Q{i+1}" for i in range(len(df))]
            return df[["pertanyaan", "rata_rata", "label"]]

    # ---- Compute from survey ----
    if survey_df is not None and survey_cols.get("q_cols"):
        q_cols = survey_cols["q_cols"]
        means  = survey_df[q_cols].mean()
        df = pd.DataFrame({
            "pertanyaan": q_cols,
            "rata_rata":  means.values,
            "label":      [f"Q{i+1}" for i in range(len(q_cols))]
        })
        return df

    return None


# =============================================================================
# FILTER FUNCTIONS
# =============================================================================
def apply_survey_filters(df, cols, f_gender, f_usia, f_freq):
    if df is None or df.empty:
        return df
    fdf = df.copy()
    if cols.get("gender") and f_gender and "Semua" not in f_gender and cols["gender"] in fdf.columns:
        fdf = fdf[fdf[cols["gender"]].isin(f_gender)]
    if cols.get("usia") and f_usia and cols["usia"] in fdf.columns:
        lo, hi = f_usia
        fdf = fdf[pd.to_numeric(fdf[cols["usia"]], errors="coerce").between(lo, hi)]
    if cols.get("freq") and f_freq and "Semua" not in f_freq and cols["freq"] in fdf.columns:
        fdf = fdf[fdf[cols["freq"]].isin(f_freq)]
    return fdf


def apply_review_filters(df, cols, f_rating, f_sentiment, f_date_range, f_search):
    if df is None or df.empty:
        return df
    fdf = df.copy()
    if cols.get("rating") and f_rating and cols["rating"] in fdf.columns:
        fdf = fdf[pd.to_numeric(fdf[cols["rating"]], errors="coerce").isin(f_rating)]
    if f_sentiment and "Semua" not in f_sentiment:
        fdf = fdf[fdf["sentimen"].isin(f_sentiment)]
    if cols.get("tanggal") and f_date_range and len(f_date_range) == 2 and cols["tanggal"] in fdf.columns:
        try:
            tgl = fdf[cols["tanggal"]]
            if pd.api.types.is_datetime64_any_dtype(tgl):
                s = pd.to_datetime(f_date_range[0])
                e = pd.to_datetime(f_date_range[1])
                fdf = fdf[tgl.between(s, e)]
        except Exception:
            pass
    if f_search and cols.get("ulasan") and cols["ulasan"] in fdf.columns:
        fdf = fdf[fdf[cols["ulasan"]].astype(str).str.lower()
                  .str.contains(f_search.lower(), na=False)]
    return fdf


# =============================================================================
# CHART CONFIG