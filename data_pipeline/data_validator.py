# src/data_validator.py
import logging
import pandas as pd


logger = logging.getLogger(__name__)


def validate_dataframe(df, required_columns, numeric_columns):
    """Validate the DataFrame and return valid data.

    required_columns: a list of column names that must exist.
    numeric_columns: a list of column names whose values should be numeric.
    """
    before = len(df)
    for col in required_columns:
        if col not in df.columns:
            logger.error(f"Missing required column: {col}")
            raise ValueError(f"Missing required column: {col}")
        
    for col in numeric_columns:
        invalid_rows = []
        for i, value in df[col].items():
            if pd.notna(value):
                try:
                    float(value)
                except ValueError:
                    logger.warning(f"A non-numeric value was found in '{col}' at index {i}: {value}")
                    invalid_rows.append(i)

        df = df.drop(invalid_rows)
        #convert to a numeric data type
        df[col] = pd.to_numeric(df[col])

    rows_validated = len(df)
    rows_removed = before - rows_validated
    logger.debug(f"Validated DataFrame: {rows_validated} rows, and {rows_removed} rows removed")

    return df
