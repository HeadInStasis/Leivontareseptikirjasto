CREATE TABLE users(
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE,
    password_hash TEXT
);

CREATE TABLE recipes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL
    name TEXT NOT NULL
    ingredients TEXT NO NULL,
    instructions TEXT NOT NULL,
    image TEXT
    FOREGNT KEY (user_id) REFERENCES users(id)
    	

);
