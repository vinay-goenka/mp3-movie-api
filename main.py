import io
import logging
from pathlib import Path
import pandas as pd
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from src import (
    HealthResponse,
    setup_logging,
    ProcessConfig,
    log_requests,
    MovieStorage,
    MovieUploadInfo,
    MovieDataResponse,
    MovieProcessingReport,
    MovieCache
)
from data_pipeline import create_cleaning_report, process_data, validate_dataframe
from src.storage import MOVIE_COLUMNS

setup_logging(verbose=True)
logger = logging.getLogger(__name__)

app = FastAPI(title="Data Processing API", version="1.0.0")
app.middleware("http")(log_requests)
storage = MovieStorage()
cache = MovieCache()

@app.get("/health", response_model=HealthResponse)
def health_check():
    """Return the application status and version."""
    response = HealthResponse(status="ok", version="1.0.0")
    return response

@app.post("/upload", response_model=MovieUploadInfo)
async def upload_movies(file: UploadFile = File(...)):
    filename = file.filename or ""
    extension = Path(filename).suffix.lower()
    if extension != ".csv":
        logger.warning(f"Unsupported file extension: {extension}")
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file extension: {extension}. Only .csv files are allowed.",
        )
    
    contents = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(contents))
    except pd.errors.EmptyDataError:
        logger.warning(f"Uploaded file is empty: {filename}")
        raise HTTPException(
            status_code=400, 
            detail="The uploaded CSV is empty"
            )
    except pd.errors.ParserError:
        logger.warning(f"CSV file could not be parsed: {filename}")
        raise HTTPException(
            status_code=400, 
            detail="File couldn't be read as a CSV."
            )
    except UnicodeDecodeError:
        logger.warning(f"Could not decode file: {filename}")
        raise HTTPException(
            status_code=400, 
            detail="The uploaded file could not be decoded"
            )

    uploaded_columns = sorted(df.columns)
    expected_columns = sorted(MOVIE_COLUMNS)
    if uploaded_columns != expected_columns:
        logger.warning(f"Incorrect columns in upload: {list(df.columns)}")
        raise HTTPException(
            status_code=400,
            detail=f"Uploaded CSV must have exactly these columns: {MOVIE_COLUMNS}"
        )

    if df.empty:
        logger.warning(f"Uploaded CSV is empty (no rows): {filename}")
        raise HTTPException(
            status_code=400,
            detail="The uploaded CSV is empty (no rows)"
        )
    df = df[MOVIE_COLUMNS] 
    storage.save(df)
    cache.invalidate()
    no_of_rows = len(df)
    logger.info(f"Uploaded file: {filename}, saved rows: {no_of_rows}")
    response = MovieUploadInfo(
        filename=filename,
        rows=no_of_rows,
        columns=len(df.columns),
        column_names=list(df.columns),
    )
    return response

@app.get("/movies", response_model=MovieDataResponse)
def get_movies(limit: int = Query(default=100, ge=1)):
    cached_response = cache.get(limit)
    if cached_response is not None:
        logger.info(f"Cache hit for movies: limit={limit}")
        return cached_response
    records = storage.select_columns(MOVIE_COLUMNS, limit)
    total_rows = storage.count_movies()

    response = {}
    response["data"] = records
    response["total_rows"] = total_rows
    cache.set(limit, response)
    returned_rows = len(records)
    logger.info(f"Retrieved movies: returned_rows={returned_rows}")
    return response

@app.get("/movies/search", response_model=list[dict])
def query_movies(
    columns: list[str] = Query(default=["title"]),
    min_rating: float = Query(default=0, ge=0, le=10),
    limit: int = Query(default=100, ge=1)
):
    try:
        results = storage.query_movies(columns, min_rating, limit)
    except ValueError as e:
        logger.warning(f"Search failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    returned_rows = len(results)
    logger.info(
        f"Queried movies: columns={columns}, min_rating={min_rating}, "
        f"returned_rows={returned_rows}"
    )
    return results

@app.post("/movies/process", response_model=MovieProcessingReport)
def process_movies(config: ProcessConfig):
    df = storage.get()
    if df.empty:
        logger.warning("No data available for processing.")
        raise HTTPException(
            status_code=400,
            detail="No data available for processing. Upload a CSV file first."
        )
    config_dict = config.model_dump()
    required_columns = config_dict["validation"]["required_columns"]
    numeric_columns = config_dict["validation"]["numeric_columns"]
    for col in numeric_columns:
        if col not in df.columns:
            logger.warning(f"Numeric column '{col}' not found in data.")
            raise HTTPException(
                status_code=400,
                detail=f"Numeric column '{col}' not found in data."
            )
    try:
        rows_before_val = len(df)
        df_valid = validate_dataframe(df, required_columns, numeric_columns)
        rows_after_val = len(df_valid)
        validation_rows_removed = rows_before_val - rows_after_val
        df_before = df_valid.copy()
        df_clean = process_data(df_valid, config_dict)
    except ValueError as e:
        logger.warning(f"Processing failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    report = create_cleaning_report(df_before, df_clean)
    for col in MOVIE_COLUMNS:
        if col not in df_clean.columns:
            df_clean[col] = None
    storage.save(df_clean)
    cache.invalidate()
    logger.info(
        f"Processed movies: validation_rows_removed={validation_rows_removed}, "
        f"rows_before={report['rows_before']}, rows_after={report['rows_after']}"
    )
    response = {
        "validation_rows_removed": validation_rows_removed,
        "cleaning_report": report
    }
    return response
    
