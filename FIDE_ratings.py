from flask import Flask, render_template_string
import requests
from bs4 import BeautifulSoup
from tabulate import tabulate

app = Flask(__name__)

# Function to fetch player ratings from FIDE website
def get_fide_rating(fide_id):
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
                rating_text = entry.text.strip().split()[-1]  # Get the last part (the number)

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

        return {"name": name, "fide_id": fide_id, "standard": standard_rating, "rapid": rapid_rating, "blitz": blitz_rating}

    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred for ID {fide_id}: {http_err}")
    except Exception as err:
        print(f"An error occurred for ID {fide_id}: {err}")

    return {"name": f"Player ID {fide_id}", "fide_id": fide_id, "standard": 0, "rapid": 0, "blitz": 0}

# Function to read FIDE IDs from file
def read_fide_ids_from_file(file_path):
    try:
        with open(file_path, 'r') as file:
            content = file.read().strip()
            fide_ids = content.split()  # Split by spaces, newlines, or tabs to ensure all IDs are captured
            return fide_ids
    except FileNotFoundError:
        print(f"The file {file_path} was not found.")
        return []
    except Exception as err:
        print(f"An error occurred while reading the file: {err}")
        return []

# Flask route to display the ratings
@app.route('/')
def show_ratings():
    # Replace with your actual file path
    file_path = 'C:\\Users\\rmcra\\OneDrive\\Ambiente de Trabalho\\ratings.txt'
    fide_ids = read_fide_ids_from_file(file_path)

    players = [get_fide_rating(fide_id) for fide_id in fide_ids]

    # Sort players by Standard rating, defaulting to 0-rated at the bottom
    sorted_players = sorted(players, key=lambda x: x['standard'], reverse=True)

    # Create HTML table with Tabulate
    table = tabulate(
        [[player['name'], player['fide_id'], player['standard'], player['rapid'], player['blitz']] for player in sorted_players],
        headers=["Player", "FIDE ID", "Standard", "Rapid", "Blitz"],
        tablefmt="html"
    )

    # Render the table to HTML using Flask
    return render_template_string(f"<html><body>{table}</body></html>")

if __name__ == '__main__':
    app.run(debug=True)