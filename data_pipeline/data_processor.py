import logging
import pandas as pd

logger = logging.getLogger(__name__)


def remove_duplicates(df):
    """Remove duplicate rows."""
    before = len(df)
    df = df.drop_duplicates()
    after = len(df)
    logger.debug(f"Removed duplicates: {before} rows to {after} rows")
    return df


def handle_missing(df, axis="rows"):
    """Drop rows or columns containing missing values."""
    if axis == "rows":
        before = len(df)
        df = df.dropna(axis=0)
        after = len(df)
        logger.debug(f"Removed missing rows: {before} rows to {after} rows")
    elif axis == "columns":
        before = len(df.columns)
        df = df.dropna(axis=1)
        after = len(df.columns)
        logger.debug(f"Removed missing columns: {before} columns to {after} columns")
    else:
        logger.error(f"Unsupported axis: {axis}")
        raise ValueError(f"Unsupported axis: {axis}")
    return df


def remove_outliers(df, columns, method, threshold):
    """Remove outliers from the specified numeric columns."""
    if method != "iqr" and method != "zscore":
        logger.error(f"Unsupported outlier method: {method}")
        raise ValueError(f"Unsupported outlier method: {method}")
    for column in columns:
        if column not in df.columns:
            logger.warning(f"Column not found: {column}")
            continue

        column_type = df[column].dtype
        if column_type !="int64" and column_type != "float64":
            logger.warning(f"Column is not numeric: {column}")
            continue
        
        before = len(df)

        if method == "iqr":
            Q1 = df[column].quantile(0.25)
            Q3 = df[column].quantile(0.75)
            IQR = Q3 - Q1
            lower = Q1 - threshold * IQR
            upper = Q3 + threshold * IQR
            df = df[(df[column] >= lower) & (df[column] <= upper)]
            after = len(df)
            rows_removed = before - after
            logger.debug(
                f"{column}: method={method}, threshold={threshold}, "
                f"lower={lower}, upper={upper}, removed={rows_removed}"
            )
        else:
            mean = df[column].mean()
            std = df[column].std()
            if std == 0:
                logger.debug(f"{column}: has same values, hence no outliers removed")
                continue

            z_scores = (df[column] - mean) / std
            df = df[z_scores.abs() <= threshold]
            rows_removed = before - len(df)
            logger.debug(
                f"{column}: method={method}, threshold={threshold}, "
                f"removed={rows_removed}"
            )

    return df


def process_data(df, config):
    """Apply the processing steps enabled in the configuration."""
    settings = config["processing"]

    if settings.get("remove_duplicates", False):
        df = remove_duplicates(df)

    missing_settings = settings["missing"]
    if missing_settings["enabled"]:
        axis = missing_settings["axis"]
        df = handle_missing(df, axis)

    outliers_settings = settings["outliers"]
    if outliers_settings["enabled"]:
        columns = outliers_settings["columns"]
        method = outliers_settings["method"]
        threshold = outliers_settings["threshold"]
        df = remove_outliers(df, columns, method, threshold)

    return df


def create_cleaning_report(df_before, df_after):
    """Return a dictionary summarizing the cleaning results."""
    return {
        "rows_before": len(df_before),
        "rows_after": len(df_after),
        "rows_removed": len(df_before) - len(df_after),
        "columns_before": len(df_before.columns),
        "columns_after": len(df_after.columns),
        "columns_removed": len(df_before.columns) - len(df_after.columns),
    }