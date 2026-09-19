from flask import Flask, render_template, request, redirect, session
import db 
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash 

app = Flask(__name__)
app.secret_key = "bakelist-secret-key"


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/recipes/<letter>")
def rbl(letter):
    letter = letter.upper()

    sql = """
        SELECT recipes.id, recipes.name, users.username
        FROM recipes
        JOIN users ON recipes.user_id = users.id
        WHERE recipes.name LIKE ?
        ORDER BY recipes.name ASC
    """

    recipes = db.query(sql, [letter + "%"])
    return render_template("rbl.html", recipes=recipes, letter=letter)


@app.route("/recipe/<int:recipe_id>")
def recipe(recipe_id):
    sql = """
        SELECT recipes.*, users.username
        FROM recipes
        JOIN users ON recipes.user_id = users.id
        WHERE recipes.id = ?
    """

    result = db.query(sql, [recipe_id])
    return render_template("recipe.html", recipe=result[0])


@app.route("/register")
def register():
    return render_template("register.html")


@app.route("/create", methods=["POST"])
def create():
    username = request.form["username"]
    password1 = request.form["password1"]
    password2 = request.form["password2"]

    if password1 != password2:
        return "Passwords do not match"
    password_hash = generate_password_hash(password1)

    try:
        sql = "INSERT INTO users (username, password_hash) VALUES (?, ?)"
        db.execute(sql, [username, password_hash])
    except sqlite3.IntegrityError:
        return "Username is taken"

    return redirect("/")


@app.route("/login", methods=["POST"])
def login():
    username = request.form["username"]
    password = request.form["password"]

    sql = "SELECT password_hash FROM users WHERE username = ?"
    result = db.query(sql, [username])
    
    if result and check_password_hash(result[0]["password_hash"], password):
        session["username"] = username
        return redirect("/")
    return render_template("index.html", error="Wrong username or password")


@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect("/")


@app.route("/account")
def account():
    username = session["username"]

    sql = """
        SELECT recipes.*
        FROM recipes
        JOIN users ON recipes.user_id = users.id
        WHERE users.username = ?
        ORDER BY recipes.name ASC
    """

    recipes = db.query(sql, [username])

    return render_template("account.html", recipes=recipes)


@app.route("/my-recipes")
def my_recipes():
    username = session["username"]

    sql = """
        SELECT recipes.*
        FROM recipes
        JOIN users ON recipes.user_id = users.id
        WHERE users.username = ?
        ORDER BY recipes.name ASC
    """

    recipes = db.query(sql, [username])
    return render_template("my_recipes.html", recipes=recipes)


@app.route("/delete-account", methods=["POST"])
def delete_account():
    username = session["username"]

    sql = "DELETE FROM users WHERE username = ?"
    db.execute(sql, [username])

    session.pop("username", None)
    return redirect("/")


@app.route("/add-recipe", methods=["GET", "POST"])
def add_recipe():
    if "username" not in session:
        return redirect("/")
    if request.method == "GET":
        return render_template("add_recipe.html")

    name = request.form["name"]
    ingredients = request.form["ingredients"]
    instructions = request.form["instructions"]

    sql = "SELECT id FROM users WHERE username = ?"
    user = db.query(sql, [session["username"]])

    user_id = user[0]["id"]
    sql = """
        INSERT INTO recipes  (user_id, name, ingredients, instructions)
        VALUES (?, ?, ?, ?)
    """

    db.execute(sql, [user_id, name, ingredients, instructions])

    return redirect("/")


@app.route("/edit-recipe/<int:recipe_id>", methods=["GET", "POST"])
def edit_recipe(recipe_id):
    if request.method == "GET":
        sql = """
            SELECT *
            FROM recipes
            WHERE id = ?
        """

        result = db.query(sql, [recipe_id])
        recipe = result[0]
        return render_template("edit_recipe.html", recipe=recipe)

    name = request.form["name"]
    ingredients = request.form["ingredients"]
    instructions = request.form["instructions"]

    sql = """
        UPDATE recipes
        SET name = ?, ingredients = ?, instructions = ?
        WHERE id = ?
    """

    db.execute(sql, [name, ingredients, instructions, recipe_id])
    return redirect("/recipe/" + str(recipe_id))


@app.route("/delete-recipe/<int:recipe_id>", methods=["POST"])
def delete_recipe(recipe_id):
    sql = """
        DELETE FROM recipes
        WHERE id = ?
    """

    db.execute(sql, [recipe_id])
    return redirect("/my-recipes")
