import logging
import sqlite3
import pandas as pd
from .database import get_connection, initialize_database

logger = logging.getLogger(__name__)
MOVIE_COLUMNS = ["title", "release_year", "rating", "genre"]

class MovieStorage:
    def __init__(self, db_path="data/movies.db"):
        self.db_path = db_path
        initialize_database(self.db_path)

    def save(self, df):
        """Replace all movie rows in one transaction."""
        df_clean = df.astype(object)
        df_clean = df_clean.where(pd.notna(df_clean), None)
        rows = []
        for index, row in df_clean.iterrows():
            values = (row["title"], row["release_year"], row["rating"], row["genre"])
            rows.append(values)
        connection = get_connection(self.db_path)
        try:
            connection.execute("DELETE FROM movies")
            sql_statement = """
            INSERT INTO movies (title, release_year, rating, genre) 
            VALUES (?, ?, ?, ?)
            """
            connection.executemany(sql_statement, rows)
            connection.commit()
        except sqlite3.Error:
            connection.rollback()
            raise
        finally:
            connection.close()

        no_of_rows = len(rows)
        logger.debug(f"Saved {no_of_rows} rows in movies to SQLite.")

    def get(self):
        """Return the four movie columns as a DataFrame, ordered by id."""
        # TODO: SELECT the four fields, fetch rows, and create the DataFrame.
        # Return a DataFrame with columns=MOVIE_COLUMNS,
        # so the column names are preserved even when the query returns no rows.
        connection = get_connection(self.db_path)
        try:
            sql_statement = """
            SELECT title, release_year, rating, genre
            FROM movies
            ORDER BY id
            """
            rows = connection.execute(sql_statement).fetchall()
        finally:
            connection.close()

        records = []
        for row in rows:
            records.append(dict(row))
        df = pd.DataFrame(records, columns=MOVIE_COLUMNS)

        no_of_rows = len(df)
        logger.debug(f"Retrieved {no_of_rows} rows from movies in SQLite.")
        return df

    def select_columns(self, columns, limit=5):
        """Return id plus the requested movie columns, ordered by id."""
        if not columns:
            logger.error("Select at least one column")
            raise ValueError("Select at least one column")

        for column in columns:
            if column not in MOVIE_COLUMNS:
                logger.error(f"Unsupported column: {column}")
                raise ValueError(f"Unsupported column: {column}")

        selected_columns = ", ".join(["id"] + columns)
        connection = get_connection(self.db_path)
        try:
            sql_statement = f"SELECT {selected_columns} FROM movies ORDER BY id LIMIT ?"
            rows = connection.execute(sql_statement, (limit,)).fetchall()
            records = []
            for row in rows:
                records.append(dict(row))
            no_of_rows = len(records)
            logger.debug(f"Selected {no_of_rows} rows with columns: {columns}")
            return records
        finally:
            connection.close()

    def count_movies(self):
        """Return the number of stored movies using SQL COUNT(*)."""
        connection = get_connection(self.db_path)
        try:
            sql_statement = "SELECT COUNT(*) AS total FROM movies"
            row = connection.execute(sql_statement).fetchone()
            total = row["total"]
            logger.debug(f"Counted movies: total = {total}")
            return total
        finally:
            connection.close()

    def query_movies(self, columns, min_rating, limit):
        """Return selected fields from matching movies using SQL."""
        # TODO: validate columns as in select_columns().
        # SELECT id plus those columns and filter by minimum rating.
        # Sort by rating DESC then id ASC, and apply limit.
        # Return dictionaries and log the selected columns and row count at DEBUG.
        if not columns:
            logger.error("Select at least one column")
            raise ValueError("Select at least one column")
        for column in columns:
            if column not in MOVIE_COLUMNS:
                logger.error(f"Unsupported column: {column}")
                raise ValueError(f"Unsupported column: {column}")

        selected_columns = ", ".join(["id"] + columns)
        connection = get_connection(self.db_path)
        try:
            sql_statement = f"""
            SELECT {selected_columns} 
            FROM movies 
            WHERE rating >= ? 
            ORDER BY rating DESC, id ASC 
            LIMIT ?
            """
            rows = connection.execute(sql_statement, (min_rating, limit)).fetchall()
            records = []
            for row in rows:
                records.append(dict(row))
            no_of_rows = len(records)
            logger.debug(f"Queried movies: rows: {no_of_rows} columns: {columns}")
            return records
        finally:
            connection.close()
