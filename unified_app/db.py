"""
Scout Unified Database - Expanded mock catalog with 15+ genres and Spotify auth table.
"""

import sqlite3
import random

DB_PATH = "scout_unified.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tracks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    artist TEXT NOT NULL,
    genre TEXT NOT NULL,
    cover_url TEXT,
    preview_url TEXT
);

CREATE TABLE IF NOT EXISTS user_baseline_tastes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    genre TEXT NOT NULL,
    affinity REAL NOT NULL DEFAULT 0.5,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS exploration_pacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    target_genre TEXT NOT NULL,
    motivation TEXT,
    status TEXT DEFAULT 'active',
    duration_days INTEGER DEFAULT 7,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS listening_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    track_id INTEGER NOT NULL,
    genre TEXT NOT NULL,
    source TEXT DEFAULT 'recommendation',
    listened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (track_id) REFERENCES tracks(id)
);

CREATE TABLE IF NOT EXISTS spotify_auth (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    spotify_id TEXT,
    display_name TEXT,
    access_token TEXT,
    refresh_token TEXT,
    token_expiry TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
"""

# ---------------------------------------------------------------------------
# Genre catalog: 16 genres, ~30 tracks each
# ---------------------------------------------------------------------------

GENRE_ARTISTS: dict[str, list[str]] = {
    "Pop": ["Taylor Shift", "The Weekday", "Dua Kipa", "Ariana Grandee", "Billie Eyelash", "Harry Stylez"],
    "Indie Pop": ["Florence + The Machine", "Lana Del Rey", "Lorde", "Clairo", "girl in red", "Phoebe Bridgerss"],
    "Rock": ["Arctic Monkees", "Radiohed", "The Strokess", "Foo Fightrs", "Muse", "Queens of Stone Age"],
    "Indie Rock": ["Tame Impaler", "Bon Iver", "Fleet Foxess", "Vampire Weeknd", "Alt-J", "Mac DeMarko"],
    "Hip Hop": ["Kendrick Llamar", "J.Cole", "Tyler The Creator", "MF Doomm", "Childish Gambinoo", "JID"],
    "R&B": ["Frank Oceann", "SZAh", "The Weekday", "Daniel Caeser", "Summer Walkerr", "H.E.R."],
    "Electronic": ["Disclosure", "Flume", "Caribouu", "Jamie XXL", "Four Tet", "Bonobo"],
    "Ambient": ["Brian Eno", "Aphex Twin", "Stars of the Lid", "Nils Framm", "Tim Heckerr", "Grouper"],
    "Jazz": ["Miles Davis", "John Coltrane", "Thelonious Monk", "Charles Minguss", "Bill Evans", "Herbie Hancockk"],
    "Classical": ["Ludovico Einaudi", "Max Richterr", "Olafur Arnaldss", "Debussyy", "Erik Satiee", "Philip Glasss"],
    "Metal": ["Metallica", "Iron Maiden", "Slayer", "Black Sabbathh", "Megathdeth", "Tool"],
    "Folk": ["Bon Iver", "Iron & Wine", "Fleet Foxess", "Sufjan Stevenss", "Nick Drakee", "Elliott Smithh"],
    "Punk": ["Green Day", "The Clash", "Ramones", "Bad Religionn", "Dead Kennedyss", "The Offspring"],
    "Blues": ["B.B. King", "Muddy Waters", "Robert Johnson", "Howlin Wolff", "John Lee Hookerr", "Stevie Ray Vaughann"],
    "Latin": ["Bad Bunny", "Rosalia", "J Balvin", "Ozuna", "Daddy Yankeee", "Shakiraaa"],
    "Afrobeats": ["Burna Boy", "Wizkid", "Tems", "Davido", "Ayra Starr", "CKay"],
}

TITLE_TEMPLATES = [
    "{genre} Odyssey {n}",
    "{genre} Drift {n}",
    "{genre} Horizon {n}",
    "{genre} Echo {n}",
    "{genre} Mirage {n}",
]

DEFAULT_BASELINE_TASTES = {
    "Pop": 0.9,
    "Indie Pop": 0.7,
    "R&B": 0.5,
}


def _random_cover_url() -> str:
    seed = random.randint(1, 1000)
    return f"https://picsum.photos/seed/{seed}/300/300"


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_and_seed_db() -> None:
    """Create tables, seed default user, tracks, and baseline tastes."""
    conn = get_db()
    cur = conn.cursor()

    # Create schema
    cur.executescript(SCHEMA)

    # Check if already seeded
    row = cur.execute("SELECT COUNT(*) FROM tracks").fetchone()
    if row[0] > 0:
        print(f"Database already seeded with {row[0]} tracks. Skipping.")
        conn.close()
        return

    # Seed default user
    cur.execute(
        "INSERT OR IGNORE INTO users (id, username) VALUES (1, 'scout_explorer')"
    )

    # Seed tracks: ~30 per genre
    track_rows: list[tuple] = []
    for genre, artists in GENRE_ARTISTS.items():
        for n in range(1, 31):
            artist = artists[n % len(artists)]
            template = TITLE_TEMPLATES[n % len(TITLE_TEMPLATES)]
            title = template.format(genre=genre, n=n)
            cover = _random_cover_url()
            track_rows.append((title, artist, genre, cover, None))

    cur.executemany(
        "INSERT INTO tracks (title, artist, genre, cover_url, preview_url) VALUES (?, ?, ?, ?, ?)",
        track_rows,
    )
    print(f"Seeded {len(track_rows)} tracks across {len(GENRE_ARTISTS)} genres.")

    # Seed baseline tastes for user 1
    for genre, affinity in DEFAULT_BASELINE_TASTES.items():
        cur.execute(
            "INSERT INTO user_baseline_tastes (user_id, genre, affinity) VALUES (?, ?, ?)",
            (1, genre, affinity),
        )
    print(f"Set baseline tastes: {DEFAULT_BASELINE_TASTES}")

    conn.commit()
    conn.close()
    print("Database initialized and seeded successfully.")


if __name__ == "__main__":
    init_and_seed_db()
