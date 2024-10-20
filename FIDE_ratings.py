# Import necessary modules
from flask import Flask, render_template_string
import requests
from bs4 import BeautifulSoup
from tabulate import tabulate
import json
import os
import logging

# Initialize Flask app
app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.INFO)

# Define cache file
CACHE_FILE = 'fide_ratings_cache.json'

# Function to get cached ratings
def get_cached_ratings():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            logging.error(f"Cache file {CACHE_FILE} is corrupted or empty. Re-fetching data.")
            return None
        except IOError as e:
            logging.error(f"Failed to read cache file {CACHE_FILE}: {e}")
            return None
    return None

# Function to cache ratings
def cache_ratings(ratings):
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump(ratings, f)
        logging.info(f"Cache written successfully to {CACHE_FILE}")
    except IOError as e:
        logging.error(f"Failed to write cache to {CACHE_FILE}: {e}")

# Function to fetch player ratings from FIDE website
def get_fide_rating(fide_id):
    url = f"https://ratings.fide.com/profile/{fide_id}"
    logging.info(f"Fetching data for FIDE ID: {fide_id} from URL: {url}")
    try:
        response = requests.get(url)
        response.raise_for_status()  # This will raise an error for HTTP errors (4xx and 5xx)

        # Log response status
        logging.info(f"Received response from FIDE for {fide_id}: {response.status_code}")

        soup = BeautifulSoup(response.text, 'html.parser')

        # Check if the response contains the expected data structure
        if not soup.find('div', class_='profile-top-title'):
            logging.warning(f"Player not found for FIDE ID: {fide_id}")
            return {"name": f"Player ID {fide_id}", "fide_id": fide_id, "standard": "Unrated", "rapid": "Unrated", "blitz": "Unrated"}

        # Extract player name
        name_tag = soup.find('div', class_='profile-top-title')
        name = name_tag.text.strip() if name_tag else f"Player ID {fide_id}"

        # Extract FIDE ratings
        ratings_section = soup.find('div', class_='profile-top-rating-dataCont')
        standard_rating, rapid_rating, blitz_rating = "Unrated", "Unrated", "Unrated"

        if ratings_section:
            rating_entries = ratings_section.find_all('div', class_='profile-top-rating-data')
            for entry in rating_entries:
                rating_type = entry.find('span', class_='profile-top-rating-dataDesc').text.strip()
                rating_text = entry.text.strip().split()[-1]  # Get the last part (the number)

                try:
                    rating_value = int(rating_text)
                    if rating_value < 0:  # FIDE ratings can't be negative
                        rating_value = "Unrated"
                except ValueError:
                    rating_value = "Unrated"  # Set to "Unrated" if it's not a valid number

                if rating_type == "std":
                    standard_rating = rating_value
                elif rating_type == "rapid":
                    rapid_rating = rating_value
                elif rating_type == "blitz":
                    blitz_rating = rating_value

        logging.info(f"Fetched ratings for {fide_id}: {name}, Std: {standard_rating}, Rapid: {rapid_rating}, Blitz: {blitz_rating}")
        return {"name": name, "fide_id": fide_id, "standard": standard_rating, "rapid": rapid_rating, "blitz": blitz_rating}

    except requests.exceptions.HTTPError as http_err:
        logging.error(f"HTTP error occurred for ID {fide_id}: {http_err}")
    except requests.exceptions.RequestException as req_err:
        logging.error(f"Request exception occurred for ID {fide_id}: {req_err}")
    except Exception as err:
        logging.error(f"An unexpected error occurred for ID {fide_id}: {err}")

    return {"name": f"Player ID {fide_id}", "fide_id": fide_id, "standard": "Unrated", "rapid": "Unrated", "blitz": "Unrated"}

# Function to fetch FIDE ratings and cache results
def fetch_fide_ratings(fide_ids):
    ratings = [get_fide_rating(fide_id) for fide_id in fide_ids]
    cache_ratings(ratings)
    return ratings

# Function to read FIDE IDs from a file
def read_fide_ids_from_file(file_path):
    try:
        with open(file_path, 'r') as file:
            content = file.read().strip()
            fide_ids = content.split()  # Split by spaces, newlines, or tabs to ensure all IDs are captured
            logging.info(f"Loaded FIDE IDs from file: {fide_ids}")
            return fide_ids
    except FileNotFoundError:
        logging.error(f"The file {file_path} was not found.")
        return []
    except Exception as err:
        logging.error(f"An error occurred while reading the file: {err}")
        return []

# Route to display FIDE ratings
@app.route('/')
def show_ratings():
    file_path = 'ratings.txt'  # File containing FIDE IDs
    fide_ids = read_fide_ids_from_file(file_path)  # Read FIDE IDs from the file

    # Check for cached ratings
    players = get_cached_ratings()
    if players is None:
        players = fetch_fide_ratings(fide_ids)

    # Log the players data fetched
    logging.info(f"Players Data: {players}")

    # Fallback message if no players data is available
    if not players:
        logging.warning("No player data found or fetched.")
        table = "<p>No player data available.</p>"
    else:
        # Sort players by Standard rating, placing "Unrated" at the bottom
        sorted_players = sorted(players, key=lambda x: (x['standard'] == "Unrated", x['standard']), reverse=True)

        # Create HTML table with Tabulate
        table = tabulate(
            [[player['name'], player['fide_id'], player['standard'], player['rapid'], player['blitz']] for player in sorted_players],
            headers=["Player", "FIDE ID", "Standard", "Rapid", "Blitz"],
            tablefmt="html"
        )

    # Log generated table
    logging.info(f"Generated Table: {table}")

    # Create full HTML page
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
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))  # Run app
