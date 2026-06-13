import re
import pandas as pd

PII_COLUMNS = {
    "email",
    "phone",
}

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"\+?\d[\d\s().-]{7,}\d")


def mask_dataframe_pii(df: pd.DataFrame) -> pd.DataFrame:
    safe_df = df.copy()

    for col in safe_df.columns:
        if col.lower() in PII_COLUMNS:
            safe_df[col] = f"[{col.upper()}_REDACTED]"

    for col in safe_df.select_dtypes(include="object").columns:
        safe_df[col] = (
            safe_df[col]
            .astype(str)
            .str.replace(EMAIL_RE, "[EMAIL_REDACTED]", regex=True)
            .str.replace(PHONE_RE, "[PHONE_REDACTED]", regex=True)
        )

    return safe_df


def mask_text_pii(text: str) -> str:
    text = EMAIL_RE.sub("[EMAIL_REDACTED]", text)
    text = PHONE_RE.sub("[PHONE_REDACTED]", text)
    return text