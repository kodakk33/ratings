from flask import Flask, render_template_string
import requests
from bs4 import BeautifulSoup
import logging
from tabulate import tabulate

app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.INFO)

def read_fide_ids_from_file(file_path):
    """Read FIDE IDs from a text file, supporting space-separated values."""
    with open(file_path, 'r') as file:
        # Read the first line and split by spaces
        line = file.readline().strip()
        return line.split()  # Split the line into separate IDs

def fetch_fide_ratings(fide_ids):
    """Fetch ratings for multiple FIDE IDs."""
    players = []
    for fide_id in fide_ids:
        player_data = get_fide_rating(fide_id)
        if player_data:
            players.append(player_data)
    return players

def get_fide_rating(fide_id):
    """Fetch player ratings from the FIDE website."""
    url = f"https://ratings.fide.com/profile/{fide_id}"
    logging.info(f"Fetching data for FIDE ID: {fide_id} from URL: {url}")
    
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for HTTP errors
        logging.info(f"Received response for {fide_id}: {response.status_code}")

        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract player name
        name_tag = soup.find('div', class_='profile-top-title')
        name = name_tag.text.strip() if name_tag else f"Player ID {fide_id}"

        # Extract FIDE ratings
        ratings_section = soup.find('div', class_='profile-top-rating-dataCont')
        logging.info(f"Ratings section found for {fide_id}: {ratings_section}")  # Debugging line
        standard_rating, rapid_rating, blitz_rating = 0, 0, 0  # Set default values to 0

        if ratings_section:
            rating_entries = ratings_section.find_all('div', class_='profile-top-rating-data')
            for entry in rating_entries:
                rating_type = entry.find('span', class_='profile-top-rating-dataDesc').text.strip()
                rating_text = entry.text.strip().split()[-1]  # Get the last part (the text)

                # Debugging line to see what is being processed
                logging.info(f"Processing {rating_type} rating for {fide_id}: {rating_text}")

                # Adjust this condition to handle "Not rated"
                if "Not rated" in rating_text or "rated" in rating_text:  
                    rating_value = 0  # Set unrated players' ratings to 0
                else:
                    try:
                        rating_value = int(rating_text)
                        if rating_value < 0:  # FIDE ratings can't be negative
                            rating_value = 0  # Set negative ratings to 0
                    except ValueError:
                        rating_value = 0  # Set to 0 if it's not a valid number

                # Assign ratings based on the type
                if "std" in rating_type:  # Adjusted condition
                    standard_rating = rating_value
                elif "rapid" in rating_type:  # Adjusted condition
                    rapid_rating = rating_value
                elif "blitz" in rating_type:  # Adjusted condition
                    blitz_rating = rating_value

        logging.info(f"Fetched ratings for {fide_id}: {name}, Std: {standard_rating}, Rapid: {rapid_rating}, Blitz: {blitz_rating}")
        return {"name": name, "fide_id": fide_id, "standard": standard_rating, "rapid": rapid_rating, "blitz": blitz_rating}

    except requests.exceptions.HTTPError as http_err:
        logging.error(f"HTTP error occurred for ID {fide_id}: {http_err}")
    except Exception as err:
        logging.error(f"An unexpected error occurred for ID {fide_id}: {err}")

    return {"name": f"Player ID {fide_id}", "fide_id": fide_id, "standard": 0, "rapid": 0, "blitz": 0}  # Return 0 for unrated

@app.route('/')
def show_ratings():
    """Flask route to display the ratings."""
    file_path = 'ratings.txt'
    fide_ids = read_fide_ids_from_file(file_path)  # Read FIDE IDs from the file

    logging.info(f"Loaded FIDE IDs from file: {fide_ids}")

    players = fetch_fide_ratings(fide_ids)  # Fetch new ratings

    # Check if players data was fetched
    if not players or all(player.get('standard') == 0 for player in players):
        logging.warning("No player data found or fetched.")
        return "<p>No player data available.</p>"

    # Sort players by Standard rating
    sorted_players = sorted(players, key=lambda x: (x['standard'] == 0, x['standard']), reverse=True)

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
            img {{ display: block; margin: 20px auto; max-width: 80%; height: auto; }}  /* Responsive image styling */
        </style>
    </head>
    <body>
        <h1>FIDE Ratings</h1>
        {table}
        <img src="https://tse1.mm.bing.net/th?id=OIP.M-tpqp1vhciWWHzgooe-NQAAAA&pid=Api&P=0&h=220" alt="Descriptive Alt Text">
    </body>
    </html>
    """

    return render_template_string(html_content)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)  # Use a fixed port for testing
