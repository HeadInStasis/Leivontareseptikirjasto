from flask import Flask, render_template, request, redirect, session, flash
import sqlite3
import db
from flask_wtf.csrf import CSRFProtect, CSRFError
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "bakelist-secret-key"

csrf = CSRFProtect(app)


@app.errorhandler(CSRFError)
def handle_csrf_error(error):
    flash("Invalid or missing CSRF token. Please try again.")
    return redirect("/")



@app.route("/")
def index():
    sql = """
        SELECT recipes.id, recipes.name, users.username
        FROM recipes
        JOIN users ON recipes.user_id = users.id
        ORDER BY recipes.name ASC
    """

    recipes = db.query(sql)

    return render_template("index.html", recipes=recipes)

@app.route("/recipe/<int:recipe_id>")
def recipe(recipe_id):
    result = db.get_recipe(recipe_id)


    if not result:
        flash("Recipe not found.")
        return redirect("/")

    recipe = result[0]

    categories = db.get_recipe_categories(recipe_id)


    comments = db.query(
    """
    SELECT comments.content,
           comments.created_at,
           users.username
    FROM comments
    JOIN users ON comments.user_id = users.id
    WHERE comments.recipe_id = ?
    ORDER BY comments.created_at DESC
    """,
    [recipe_id]
    )

    return render_template(
        "recipe.html",
        recipe=recipe,
        categories=categories,
        comments=comments
    )



@app.route("/register")
def register():
    return render_template("register.html")


@app.route("/create", methods=["POST"])
def create():
    username = request.form["username"].strip()
    password1 = request.form["password1"]
    password2 = request.form["password2"]

    if not username:
        flash("Username cannot be empty.")
        return redirect("/register")

    if len(username) < 3:
        flash("Username must contain at least 3 characters.")
        return redirect("/register")

    if not password1:
        flash("Password cannot be empty.")
        return redirect("/register")

    if len(password1) < 8:
        flash("Password must contain at least 8 characters.")
        return redirect("/register")

    if password1 != password2:
        flash("Passwords do not match.")
        return redirect("/register")

    password_hash = generate_password_hash(password1)

    try:
        sql = """
            INSERT INTO users (username, password_hash)
            VALUES (?, ?)
        """
        db.execute(sql, [username, password_hash])

    except sqlite3.IntegrityError:
        flash("Username is already taken.")
        return redirect("/register")

    flash("Account created successfully. You can now log in.")
    return redirect("/")


@app.route("/login", methods=["POST"])
def login():
    username = request.form["username"].strip()
    password = request.form["password"]

    result = db.query(
        "SELECT password_hash FROM users WHERE username = ?",
        [username]
    )

    if result and check_password_hash(
        result[0]["password_hash"],
        password
    ):
        session["username"] = username
        flash("Logged in successfully.")
        return redirect("/")

    flash("Wrong username or password.")
    return redirect("/")


@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect("/")


@app.route("/account")
def account():
    if "username" not in session:
        flash("You must be logged in to view your account.")
        return redirect("/")

    user = db.query(
        "SELECT id, username FROM users WHERE username = ?",
        [session["username"]]
    )

    if not user:
        session.clear()
        flash("User account was not found.")
        return redirect("/")

    user_id = user[0]["id"]

    recipes = db.query(
        """
        SELECT *
        FROM recipes
        WHERE user_id = ?
        ORDER BY name ASC
        """,
        [user_id]
    )

    recipe_count = db.query(
        """
        SELECT COUNT(*) AS count
        FROM recipes
        WHERE user_id = ?
        """,
        [user_id]
    )[0]["count"]

    return render_template(
        "account.html",
        recipes=recipes,
        recipe_count=recipe_count
    )



@app.route("/delete-account", methods=["POST"])
def delete_account():
    if "username" not in session:
        flash("You must be logged in to delete your account.")
        return redirect("/")

    username = session["username"]

    db.execute(
        "DELETE FROM users WHERE username = ?",
        [username]
    )

    session.clear()

    flash("Account deleted successfully.")
    return redirect("/")



@app.route("/add-recipe", methods=["GET", "POST"])
def add_recipe():
    if "username" not in session:
        flash("You must be logged in to add a recipe.")
        return redirect("/")

    categories = db.get_categories()

    if request.method == "GET":
        return render_template(
            "add_recipe.html",
            categories=categories
        )

    name = request.form["name"].strip()
    ingredients = request.form["ingredients"].strip()
    instructions = request.form["instructions"].strip()

    if not name:
        flash("Recipe name cannot be empty.")
        return redirect("/add-recipe")

    if not ingredients:
        flash("Ingredients cannot be empty.")
        return redirect("/add-recipe")

    if not instructions:
        flash("Instructions cannot be empty.")
        return redirect("/add-recipe")

    user = db.query(
        "SELECT id FROM users WHERE username = ?",
        [session["username"]]
    )

    if not user:
        session.clear()
        flash("User account was not found.")
        return redirect("/")

    user_id = user[0]["id"]

    db.execute(
        """
        INSERT INTO recipes
        (user_id, name, ingredients, instructions)
        VALUES (?, ?, ?, ?)
        """,
        [user_id, name, ingredients, instructions]
    )

    recipe_id = db.last_insert_id()

    selected_categories = request.form.getlist("categories")

    for category_id in selected_categories:
        category = db.query(
            "SELECT id FROM categories WHERE id = ?",
            [category_id]
        )

        if category:
            db.execute(
                """
                INSERT INTO recipe_categories
                (recipe_id, category_id)
                VALUES (?, ?)
                """,
                [recipe_id, category_id]
            )

    flash("Recipe added successfully.")
    return redirect("/recipe/" + str(recipe_id))


@app.route("/edit-recipe/<int:recipe_id>", methods=["GET", "POST"])
def edit_recipe(recipe_id):
    if "username" not in session:
        flash("You must be logged in to edit a recipe.")
        return redirect("/")

    user = db.query(
        "SELECT id FROM users WHERE username = ?",
        [session["username"]]
    )

    if not user:
        session.clear()
        flash("User account was not found.")
        return redirect("/")

    user_id = user[0]["id"]

    recipe_result = db.query(
        "SELECT * FROM recipes WHERE id = ?",
        [recipe_id]
    )

    if not recipe_result:
        flash("Recipe not found.")
        return redirect("/")

    recipe = recipe_result[0]

    if recipe["user_id"] != user_id:
        flash("You do not have permission to edit this recipe.")
        return redirect("/recipe/" + str(recipe_id))

    categories = db.get_categories()

    if request.method == "GET":
        selected_categories = db.query(
            """
            SELECT category_id
            FROM recipe_categories
            WHERE recipe_id = ?
            """,
            [recipe_id]
        )

        selected_category_ids = [
            category["category_id"]
            for category in selected_categories
        ]

        return render_template(
            "edit_recipe.html",
            recipe=recipe,
            categories=categories,
            selected_category_ids=selected_category_ids
        )

    name = request.form["name"].strip()
    ingredients = request.form["ingredients"].strip()
    instructions = request.form["instructions"].strip()

    if not name or not ingredients or not instructions:
        flash("All fields are required.")
        return redirect("/edit-recipe/" + str(recipe_id))

    selected_categories = request.form.getlist("categories")

    db.execute(
        """
        UPDATE recipes
        SET name = ?, ingredients = ?, instructions = ?
        WHERE id = ?
        """,
        [name, ingredients, instructions, recipe_id]
    )

    db.execute(
        "DELETE FROM recipe_categories WHERE recipe_id = ?",
        [recipe_id]
    )

    for category_id in selected_categories:
        category = db.query(
            "SELECT id FROM categories WHERE id = ?",
            [category_id]
        )

        if category:
            db.execute(
                """
                INSERT INTO recipe_categories
                (recipe_id, category_id)
                VALUES (?, ?)
                """,
                [recipe_id, category_id]
            )

    flash("Recipe updated successfully.")
    return redirect("/recipe/" + str(recipe_id))



@app.route("/delete-recipe/<int:recipe_id>", methods=["POST"])
def delete_recipe(recipe_id):
    if "username" not in session:
        flash("You must be logged in to delete a recipe.")
        return redirect("/")

    user = db.query(
        "SELECT id FROM users WHERE username = ?",
        [session["username"]]
    )

    if not user:
        session.clear()
        flash("User account was not found.")
        return redirect("/")

    user_id = user[0]["id"]

    recipe = db.query(
        "SELECT user_id FROM recipes WHERE id = ?",
        [recipe_id]
    )

    if not recipe:
        flash("Recipe not found.")
        return redirect("/my-recipes")

    if recipe[0]["user_id"] != user_id:
        flash("You do not have permission to delete this recipe.")
        return redirect("/my-recipes")

    db.execute(
        "DELETE FROM recipes WHERE id = ?",
        [recipe_id]
    )

    flash("Recipe deleted successfully.")
    return redirect("/my-recipes")


@app.route("/search")
def search():
    query = request.args.get("query", "").strip()

    if not query:
        flash("Enter a recipe name to search.")
        return redirect("/")

    sql = """
        SELECT recipes.id, recipes.name, users.username
        FROM recipes
        JOIN users ON recipes.user_id = users.id
        WHERE recipes.name LIKE ?
        ORDER BY recipes.name ASC
    """

    recipes = db.query(sql, ["%" + query + "%"])

    return render_template(
        "search_results.html",
        recipes=recipes,
        query=query
    )


@app.route("/my-recipes")
def my_recipes():
    if "username" not in session:
        flash("You must be logged in to view your recipes.")
        return redirect("/")

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


@app.route("/add-comment/<int:recipe_id>", methods=["POST"])
def add_comment(recipe_id):
    if "username" not in session:
        flash("You must be logged in to add a comment.")
        return redirect("/recipe/" + str(recipe_id))

    content = request.form["content"].strip()

    if not content:
        flash("Comment cannot be empty.")
        return redirect("/recipe/" + str(recipe_id))

    user = db.query(
        "SELECT id FROM users WHERE username = ?",
        [session["username"]]
    )

    if not user:
        session.clear()
        flash("User account was not found.")
        return redirect("/")

    recipe = db.query(
        "SELECT id FROM recipes WHERE id = ?",
        [recipe_id]
    )

    if not recipe:
        flash("Recipe not found.")
        return redirect("/")

    user_id = user[0]["id"]

    db.execute(
        """
        INSERT INTO comments (recipe_id, user_id, content)
        VALUES (?, ?, ?)
        """,
        [recipe_id, user_id, content]
    )

    flash("Comment added successfully.")
    return redirect("/recipe/" + str(recipe_id))
