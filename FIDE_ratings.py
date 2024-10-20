from flask import Flask, render_template_string
import requests
from bs4 import BeautifulSoup
import logging

app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.INFO)

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
        standard_rating, rapid_rating, blitz_rating = "Unrated", "Unrated", "Unrated"

        if ratings_section:
            rating_entries = ratings_section.find_all('div', class_='profile-top-rating-data')
            for entry in rating_entries:
                rating_type = entry.find('span', class_='profile-top-rating-dataDesc').text.strip()
                rating_text = entry.text.strip().split()[-1]  # Get the last part (the number)

                if "Unrated" in rating_text:
                    rating_value = "Unrated"
                else:
                    try:
                        rating_value = int(rating_text)
                        if rating_value < 0:
                            rating_value = "Unrated"
                    except ValueError:
                        rating_value = "Unrated"

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

@app.route('/')
def show_ratings():
    """Flask route to display the ratings."""
    fide_ids = ['1940376', '1984349', '1984357']  # Temporary FIDE IDs for testing
    players = [get_fide_rating(fide_id) for fide_id in fide_ids]

    # Check if players data was fetched
    if not players or all(player.get('standard') == "Unrated" for player in players):
        logging.warning("No player data found or fetched.")
        return "<p>No player data available.</p>"

    # Create HTML table
    table_rows = "".join(
        f"<tr><td>{player['name']}</td><td>{player['fide_id']}</td><td>{player['standard']}</td><td>{player['rapid']}</td><td>{player['blitz']}</td></tr>"
        for player in players
    )

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
        <table>
            <tr>
                <th>Player</th>
                <th>FIDE ID</th>
                <th>Standard</th>
                <th>Rapid</th>
                <th>Blitz</th>
            </tr>
            {table_rows}
        </table>
    </body>
    </html>
    """

    return render_template_string(html_content)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)  # Use a fixed port for testing
