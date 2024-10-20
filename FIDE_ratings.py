from flask import Flask, render_template_string
import requests
from bs4 import BeautifulSoup
from tabulate import tabulate
import json
import os
import logging

app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.DEBUG)

CACHE_FILE = 'fide_ratings_cache.json'  # Define the cache file name

def get_cached_ratings():
    """Check if the cache file exists and read the ratings from it."""
    if os.path.exists(CACHE_FILE):  # Check if the cache file exists
        with open(CACHE_FILE, 'r') as f:  # Open the cache file for reading
            return json.load(f)  # Load and return the JSON data from the file
    return None  # Return None if the cache file does not exist

def cache_ratings(ratings):
    """Write the ratings data to the cache file."""
    with open(CACHE_FILE, 'w') as f:  # Open the cache file for writing
        json.dump(ratings, f)  # Convert the ratings list to JSON and write it to the file

def fetch_fide_ratings(fide_ids):
    """Fetch FIDE ratings for a list of FIDE IDs and cache the results."""
    ratings = [get_fide_rating(fide_id) for fide_id in fide_ids]  # Get ratings for each FIDE ID
    cache_ratings(ratings)  # Cache the fetched ratings
    return ratings  # Return the fetched ratings

def get_fide_rating(fide_id):
    """Fetch player ratings from the FIDE website."""
    url = f"https://ratings.fide.com/profile/{fide_id}"
    logging.info(f"Fetching data for FIDE ID: {fide_id} from URL: {url}")
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for HTTP errors
        logging.info(f"Received response for {fide_id}: {response.status_code}")

        # Log the response text for debugging
        logging.debug(f"Response content for {fide_id}: {response.text}")

        soup = BeautifulSoup(response.text, 'html.parser')

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

                # If it says "Unrated", we handle it properly
                if "Unrated" in rating_text:
                    rating_value = "Unrated"
                else:
                    try:
                        rating_value = int(rating_text)  # Convert to integer
                        if rating_value < 0:  # FIDE ratings can't be negative
                            rating_value = "Unrated"
                    except ValueError:
                        rating_value = "Unrated"  # Set to "Unrated" if it's not a valid number

                # Assign ratings based on the type
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
    except Exception as err:
        logging.error(f"An unexpected error occurred for ID {fide_id}: {err}")

    return {"name": f"Player ID {fide_id}", "fide_id": fide_id, "standard": "Unrated", "rapid": "Unrated", "blitz": "Unrated"}

def read_fide_ids_from_file(file_path):
    """Read FIDE IDs from a file."""
    try:
        with open(file_path, 'r') as file:
            content = file.read().strip()
            fide_ids = content.split()  # Split by spaces, newlines, or tabs to ensure all IDs are captured
            return fide_ids
    except FileNotFoundError:
        logging.error(f"The file {file_path} was not found.")
        return []
    except Exception as err:
        logging.error(f"An error occurred while reading the file: {err}")
        return []

@app.route('/')
def show_ratings():
    """Flask route to display the ratings."""
    file_path = 'ratings.txt'
    fide_ids = read_fide_ids_from_file(file_path)  # Read FIDE IDs from the file

    # Log the loaded FIDE IDs
    logging.info(f"Loaded FIDE IDs from file: {fide_ids}")

    # Try to get ratings from the cache first
    players = get_cached_ratings()  # Attempt to retrieve cached ratings
    if players is None:  # If no cached ratings are found
        players = fetch_fide_ratings(fide_ids)  # Fetch new ratings and cache them

    # Check if players data was fetched
    if not players or all(player.get('standard') == "Unrated" for player in players):
        logging.warning("No player data found or fetched.")
        return "<p>No player data available.</p>"

    # Sort players by Standard rating
    sorted_players = sorted(players, key=lambda x: (x['standard'] == "Unrated", x['standard']), reverse=True)

    # Create HTML table with Tabulate
    table = tabulate(
        [[player['name'], player['fide_id'], player['standard'], player['rapid'], player['blitz']] for player in sorted_players],
        headers=["Player", "FIDE ID", "Standard", "Rapid", "Blitz"],
        tablefmt="html"
    )

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
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))  # Set debug
