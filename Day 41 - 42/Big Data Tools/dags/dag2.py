# ==============================
# 1. Importing Libraries
# ==============================
from datetime import datetime, timedelta
from airflow import DAG
import requests
import pandas as pd
from bs4 import BeautifulSoup

from airflow.operators.python import PythonOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook

# ==============================
# 2. Headers for Simulating Browser Behavior
# ==============================
headers = {
    "Referer": 'https://www.google.com/',
    "Sec-Ch-Ua": "Not_A Brand",
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": "macOS",
    'User-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36'
}

# ==============================
# 3. Function to Fetch Google Books Data
# ==============================
def get_google_books_data(num_books, ti):
    base_url = "https://www.googleapis.com/books/v1/volumes"
    books = []  # List to hold book data
    seen_titles = set()  # To avoid duplicates based on title
    start_index = 0  # Start index for pagination

    while len(books) < num_books:
        url = f"{base_url}?q=data+engineering&startIndex={start_index}&maxResults=10"
        response = requests.get(url, headers=headers)

        # Check if the response is successful
        if response.status_code == 200:
            data = response.json()
            items = data.get('items', [])

            for item in items:
                book_info = item.get('volumeInfo', {})
                title = book_info.get('title', 'No Title')
                authors = ', '.join(book_info.get('authors', ['Unknown Author']))
                price = "Not Available"  # Google Books API doesn't provide price in the response
                rating = book_info.get('averageRating', 'No Rating')
                link = book_info.get('infoLink', 'No Link')

                if title not in seen_titles:
                    seen_titles.add(title)  # Add to set to avoid duplicates
                    
                    books.append({
                        "Title": title,
                        "Author": authors,
                        "Price": price,
                        "Rating": rating,
                        "Link": link
                    })

            start_index += 10  # Increment index for pagination
        else:
            print(f"Failed to fetch data. Status code: {response.status_code}")
            break

    # Limit the number of books to the specified amount
    books = books[:num_books]
    df = pd.DataFrame(books)
    df.drop_duplicates(subset="Title", inplace=True)

    # Push the book data to XCom for further use
    ti.xcom_push(key='book_data', value=df.to_dict('records'))

# ==============================
# 4. Function to Insert Book Data into Postgres
# ==============================
def insert_book_data_into_postgres(ti):
    # Pull the book data from XCom (task instance storage)
    book_data = ti.xcom_pull(key='book_data', task_ids='fetch_book_data')

    # Check if no data was fetched
    if not book_data:
        raise ValueError("No book data found")

    # Set up the PostgresHook to interact with PostgreSQL
    postgres_hook = PostgresHook(postgres_conn_id='books_connection2')
    insert_query = """
    INSERT INTO google_books (title, authors, price, rating, link)
    VALUES (%s, %s, %s, %s, %s)
    """
    # Insert each book into the Postgres database
    for book in book_data:
        postgres_hook.run(insert_query, parameters=(book['Title'], book['Author'], book['Price'], book['Rating'], book['Link']))

# ==============================
# 5. Default Arguments for the DAG
# ==============================
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 6, 20),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# ==============================
# 6. Define the DAG
# ==============================
with DAG(
    'fetch_and_store_google_books',
    default_args=default_args,
    description='A DAG to fetch book data from Google Books and store it in Postgres',
    schedule_interval=timedelta(days=1),  # The DAG will run once every day
) as dag:

    # ==============================
    # 7. Task to Fetch Google Books Data
    # ==============================
    fetch_book_data_task = PythonOperator(
        task_id='fetch_book_data',
        python_callable=get_google_books_data,
        op_args=[50],  # Number of books to fetch
    )

    # ==============================
    # 8. Task to Create the Postgres Table for Google Books
    # ==============================
    create_table_task = PostgresOperator(
        task_id='create_table',
        postgres_conn_id='books_connection2',
        sql=""" 
        CREATE TABLE IF NOT EXISTS google_books (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            authors TEXT,
            price TEXT,
            rating TEXT,
            link TEXT
        );
        """,  # SQL to create the table if it does not exist
    )

    # ==============================
    # 9. Task to Insert Book Data into the Google Books Table
    # ==============================
    insert_book_data_task = PythonOperator(
        task_id='insert_book_data',
        python_callable=insert_book_data_into_postgres,
    )

    # ==============================
    # 10. Define Task Dependencies
    # ==============================
    fetch_book_data_task >> create_table_task >> insert_book_data_task  # Task execution order
