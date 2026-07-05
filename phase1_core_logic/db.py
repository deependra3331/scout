import sqlite3
import random
import os

DB_PATH = "scout.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_and_seed_db():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    
    conn = get_db_connection()
    c = conn.cursor()

    # --- Create Tables ---
    c.executescript('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL
        );

        CREATE TABLE tracks (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            artist TEXT NOT NULL,
            genre TEXT NOT NULL,
            cover_image_url TEXT
        );

        CREATE TABLE user_baseline_tastes (
            user_id INTEGER,
            genre TEXT,
            affinity_score REAL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );

        CREATE TABLE exploration_pacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            raw_conversation_log TEXT,
            target_genre_or_artist TEXT,
            breadth TEXT,
            intensity TEXT,
            user_motivation TEXT,
            start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            window_days INTEGER,
            target_share REAL,
            status TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        
        CREATE TABLE listening_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            track_id INTEGER,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(track_id) REFERENCES tracks(id)
        );
    ''')

    # --- Insert Mock User ---
    c.execute("INSERT INTO users (id, username) VALUES (1, 'TestScoutUser')")
    
    # --- Insert Baseline Tastes ---
    # User is heavily into mainstream Pop and Indie Pop
    c.execute("INSERT INTO user_baseline_tastes (user_id, genre, affinity_score) VALUES (1, 'Pop', 0.8)")
    c.execute("INSERT INTO user_baseline_tastes (user_id, genre, affinity_score) VALUES (1, 'Indie Pop', 0.6)")

    # --- Insert Mock Tracks ---
    genres = {
        'Pop': ["Taylor Shift", "The Weekday", "Dua Kipa", "Ariana Grandee", "Billie Eyelash", "Harry Stylez"],
        'Indie Pop': ["Florence + The Machine", "Lana Del Rey", "Lorde", "Clairo", "girl in red", "Phoebe Bridgerss"],
        'J-pop': ["Arashi", "AKB48", "LiSA", "Hikaru Utada", "Yoasobi", "Official Hige Dandism"],
        'K-pop': ["BTS", "Blackpink", "Twice", "EXO", "Red Velvet", "Stray Kids"],
        'Rock': ["Arctic Monkees", "Radiohed", "The Strokess", "Foo Fightrs", "Muse", "Queens of Stone Age"],
        'Indie Rock': ["Tame Impaler", "Bon Iver", "Fleet Foxess", "Vampire Weeknd", "Alt-J", "Mac DeMarko"],
        'Hip Hop': ["Kendrick Llamar", "J.Cole", "Tyler The Creator", "MF Doomm", "Childish Gambinoo", "JID"],
        'R&B': ["Frank Oceann", "SZAh", "The Weekday", "Daniel Caeser", "Summer Walkerr", "H.E.R."],
        'Electronic': ["Disclosure", "Flume", "Caribouu", "Jamie XXL", "Four Tet", "Bonobo"],
        'Ambient': ["Brian Eno", "Aphex Twin", "Stars of the Lid", "Nils Framm", "Tim Heckerr", "Grouper"],
        'Jazz': ["Miles Davis", "John Coltrane", "Thelonious Monk", "Charles Minguss", "Bill Evans", "Herbie Hancockk"],
        'Classical': ["Ludovico Einaudi", "Max Richterr", "Olafur Arnaldss", "Debussyy", "Erik Satiee", "Philip Glasss"],
        'Metal': ["Metallica", "Iron Maiden", "Slayer", "Black Sabbathh", "Megathdeth", "Tool"],
        'Folk': ["Bon Iver", "Iron & Wine", "Fleet Foxess", "Sufjan Stevenss", "Nick Drakee", "Elliott Smithh"],
        'Punk': ["Green Day", "The Clash", "Ramones", "Bad Religionn", "Dead Kennedyss", "The Offspring"],
        'Blues': ["B.B. King", "Muddy Waters", "Robert Johnson", "Howlin Wolff", "John Lee Hookerr", "Stevie Ray Vaughann"],
        'Latin': ["Bad Bunny", "Rosalia", "J Balvin", "Ozuna", "Daddy Yankeee", "Shakiraaa"],
        'Afrobeats': ["Burna Boy", "Wizkid", "Tems", "Davido", "Ayra Starr", "CKay"]
    }

    track_id_counter = 1
    for genre, artists in genres.items():
        # Generate 50 tracks per genre to simulate a catalog
        for i in range(1, 51):
            title = f"{genre} Track {i}"
            artist = random.choice(artists)
            cover_url = f"https://picsum.photos/seed/{genre.replace(' ', '')}{i}/200/200"
            c.execute(
                "INSERT INTO tracks (id, title, artist, genre, cover_image_url) VALUES (?, ?, ?, ?, ?)",
                (track_id_counter, title, artist, genre, cover_url)
            )
            track_id_counter += 1

    conn.commit()
    conn.close()
    print("Phase 1 DB initialized and seeded.")

if __name__ == "__main__":
    init_and_seed_db()
