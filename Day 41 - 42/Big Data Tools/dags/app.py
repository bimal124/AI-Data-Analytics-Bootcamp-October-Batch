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
    "Referer": 'https://www.amazon.com/',
    "Sec-Ch-Ua": "Not_A Brand",
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": "macOS",
    'User-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36'
}

# ==============================
# 3. Function to Fetch Amazon Book Data
# ==============================
def get_amazon_data_books(num_books, ti):
    # Base URL for fetching books from Amazon
    base_url = "https://www.amazon.com/s?k=data+engineering+books"
    books = []  # List to hold book data
    seen_titles = set()  # To avoid duplicates based on title
    page = 1  # Starting page for pagination

    # Loop until we fetch the required number of books
    while len(books) < num_books:
        url = f"{base_url}&page={page}"
        response = requests.get(url, headers=headers)

        # Check if the response is successful
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "html.parser")
            book_containers = soup.find_all("div", {"class": "s-result-item"})

            # Extract relevant book information from each container
            for book in book_containers:
                title_tag = book.find("span", {"class": "a-text-normal"})
                author_tag = book.find("a", {"class": "a-size-base"})
                price_tag = book.find("span", {"class": "a-price-whole"})
                rating_tag = book.find("span", {"class": "a-icon-alt"})

                if title_tag and price_tag:
                    book_title = title_tag.text.strip()
                    if book_title not in seen_titles:
                        seen_titles.add(book_title)  # Add to set to avoid duplicates
                        author = author_tag.text.strip() if author_tag else "Unknown"
                        price = price_tag.text.strip()
                        rating = rating_tag.text.strip() if rating_tag else "No Rating"

                        # Append book data to list
                        books.append({
                            "Title": book_title,
                            "Author": author,
                            "Price": price,
                            "Rating": rating,
                        })

            page += 1  # Increment page for pagination
        else:
            print(f"Failed to fetch page {page}. Status code: {response.status_code}")
            break

    # Limit the number of books to the specified amount and remove duplicates
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
    postgres_hook = PostgresHook(postgres_conn_id='books_connection')
    insert_query = """
    INSERT INTO books (title, authors, price, rating)
    VALUES (%s, %s, %s, %s)
    """
    # Insert each book into the Postgres database
    for book in book_data:
        postgres_hook.run(insert_query, parameters=(book['Title'], book['Author'], book['Price'], book['Rating']))

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
    'fetch_and_store_amazon_books',
    default_args=default_args,
    description='A DAG to fetch book data from Amazon and store it in Postgres',
    schedule_interval=timedelta(days=1),  # The DAG will run once every day
) as dag:

    # ==============================
    # 7. Task to Fetch Book Data
    # ==============================
    fetch_book_data_task = PythonOperator(
        task_id='fetch_book_data',
        python_callable=get_amazon_data_books,
        op_args=[50],  # Number of books to fetch
    )

    # ==============================
    # 8. Task to Create the Postgres Table
    # ==============================
    create_table_task = PostgresOperator(
        task_id='create_table',
        postgres_conn_id='books_connection',
        sql=""" 
        CREATE TABLE IF NOT EXISTS books (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            authors TEXT,
            price TEXT,
            rating TEXT
        );
        """,  # SQL to create the table if it does not exist
    )

    # ==============================
    # 9. Task to Insert Book Data into the Table
    # ==============================
    insert_book_data_task = PythonOperator(
        task_id='insert_book_data',
        python_callable=insert_book_data_into_postgres,
    )

    # ==============================
    # 10. Define Task Dependencies
    # ==============================
    fetch_book_data_task >> create_table_task >> insert_book_data_task  # Task execution order
