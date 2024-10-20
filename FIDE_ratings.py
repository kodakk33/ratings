from flask import Flask, render_template_string
import requests
from bs4 import BeautifulSoup
from tabulate import tabulate
import json
import os
import logging

app = Flask(__name__)

# Set up logging for better error handling
logging.basicConfig(level=logging.INFO)

CACHE_FILE = 'fide_ratings_cache.json'  # Define the cache file name

def get_cached_ratings():
    """
    Check if the cache file exists and read the ratings from it.
    Returns:
        list: Cached ratings data if it exists, None otherwise.
    """
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                data = json.load(f)
                logging.info("Cache found and loaded.")
                return data
        except json.JSONDecodeError:
            logging.error("Cache file is corrupted or empty.")
    return None  # Return None if no cache file exists or it's corrupted

def cache_ratings(ratings):
    """
    Write the ratings data to the cache file.
    Args:
        ratings (list): List of ratings data to cache.
    """
    with open(CACHE_FILE, 'w') as f:
        json.dump(ratings, f)
    logging.info("Ratings cached successfully.")

def fetch_fide_ratings(fide_ids):
    """
    Fetch FIDE ratings for a list of FIDE IDs and cache the results.
    Args:
        fide_ids (list): List of FIDE IDs to fetch ratings for.
    Returns:
        list: List of ratings data.
    """
    ratings = [get_fide_rating(fide_id) for fide_id in fide_ids]
    cache_ratings(ratings)
    return ratings

def get_fide_rating(fide_id):
    """
    Fetch the FIDE rating for a specific player by ID.
    Args:
        fide_id (str): The FIDE ID of the player.
    Returns:
        dict: Player's ratings.
    """
    url = f"https://ratings.fide.com/profile/{fide_id}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract player name
        name_tag = soup.find('div', class_='profile-top-title')
        name = name_tag.text.strip() if name_tag else f"Player ID {fide_id}"

        # Extract FIDE ratings
        ratings_section = soup.find('div', class_='profile-top-rating-dataCont')
        standard_rating, rapid_rating, blitz_rating = 0, 0, 0

        if ratings_section:
            rating_entries = ratings_section.find_all('div', class_='profile-top-rating-data')
            for entry in rating_entries:
                rating_type = entry.find('span', class_='profile-top-rating-dataDesc').text.strip()
                rating_text = entry.text.strip().split()[-1]

                try:
                    rating_value = int(rating_text)
                except ValueError:
                    rating_value = 0  # Default to 0 if it's not a valid number

                if rating_type == "std":
                    standard_rating = rating_value
                elif rating_type == "rapid":
                    rapid_rating = rating_value
                elif rating_type == "blitz":
                    blitz_rating = rating_value

        logging.info(f"Fetched rating for FIDE ID {fide_id}: {name}, Std: {standard_rating}, Rapid: {rapid_rating}, Blitz: {blitz_rating}")
        return {"name": name, "fide_id": fide_id, "standard": standard_rating, "rapid": rapid_rating, "blitz": blitz_rating}

    except requests.exceptions.HTTPError as http_err:
        logging.error(f"HTTP error occurred for ID {fide_id}: {http_err}")
    except Exception as err:
        logging.error(f"An error occurred for ID {fide_id}: {err}")

    return {"name": f"Player ID {fide_id}", "fide_id": fide_id, "standard": 0, "rapid": 0, "blitz": 0}

def read_fide_ids_from_file(file_path):
    """
    Read FIDE IDs from the specified file.
    Args:
        file_path (str): Path to the file containing FIDE IDs.
    Returns:
        list: List of FIDE IDs.
    """
    try:
        with open(file_path, 'r') as file:
            content = file.read().strip()
            fide_ids = content.split()  # Splitting by spaces, newlines, or tabs
            logging.info(f"Loaded FIDE IDs from file: {fide_ids}")
            return fide_ids
    except FileNotFoundError:
        logging.error(f"The file {file_path} was not found.")
        return []
    except Exception as err:
        logging.error(f"An error occurred while reading the file: {err}")
        return []

@app.route('/')
def show_ratings():
    file_path = 'ratings.txt'
    fide_ids = read_fide_ids_from_file(file_path)

    # Try to get ratings from the cache first
    players = get_cached_ratings()  # Attempt to retrieve cached ratings
    if players is None:
        players = fetch_fide_ratings(fide_ids)  # Fetch new ratings and cache them

    logging.info(f"Fetched Players Data: {players}")  # Log the fetched players data

    # Sort players by Standard rating
    sorted_players = sorted(players, key=lambda x: x['standard'], reverse=True)

    # Create HTML table with Tabulate
    table = tabulate(
        [[player['name'], player['fide_id'], player['standard'], player['rapid'], player['blitz']] for player in sorted_players],
        headers=["Player", "FIDE ID", "Standard", "Rapid", "Blitz"],
        tablefmt="html"
    )

    # Log the table content to debug
    logging.info(f"Generated Table: {table}")

    # Create the full HTML page
    html_content = f"""
    <html>
    <head>
        <title>FIDE Ratings</title>
        <style>
            body {{ font-family: Arial, sans-serif; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #dddddd; text-align: left; padding: 8px; }}
            th {{ background-color: #f2f2f2; }}
        </style>
    </head>
    <body>
        <h1>FIDE Ratings</h1>
        {table}
    </body>
    </html>
    """

    return render_template_string(html_content)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
