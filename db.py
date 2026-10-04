import sqlite3
from flask import g

def get_connection():
    con = sqlite3.connect("database.db")
    con.execute("PRAGMA foreign_keys = ON")
    con.row_factory = sqlite3.Row
    return con

def execute(sql, params=()):
    con = get_connection()
    result = con.execute(sql, params)
    con.commit()
    g.last_insert_id = result.lastrowid
    con.close()

def last_insert_id():
    return g.last_insert_id

def query(sql, params=()):
    con = get_connection()
    result = con.execute(sql, params).fetchall()
    con.close()
    return result

def get_recipe(recipe_id):
    return query(
        """
        SELECT recipes.*, users.username
        FROM recipes
        JOIN users ON recipes.user_id = users.id
        WHERE recipes.id = ?
        """,
        [recipe_id]
    )


def get_categories():
    return query(
        "SELECT id, name FROM categories ORDER BY name"
    )


def get_recipe_categories(recipe_id):
    return query(
        """
        SELECT categories.name
        FROM categories
        JOIN recipe_categories
            ON categories.id = recipe_categories.category_id
        WHERE recipe_categories.recipe_id = ?
        ORDER BY categories.name
        """,
        [recipe_id]
    )

def get_comments(recipe_id):
    return query(
        """
        SELECT comments.id,
               comments.content,
               comments.created_at,
               users.username
        FROM comments
        JOIN users ON comments.user_id = users.id
        WHERE comments.recipe_id = ?
        ORDER BY comments.created_at DESC
        """,
        [recipe_id]
    )
