import os
from flask import (
    Flask, flash, render_template,
    redirect, request, session, url_for)
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from flask_uploads import UploadSet, IMAGES, configure_uploads
from werkzeug.security import generate_password_hash, check_password_hash
if os.path.exists("env.py"):
    import env


app = Flask(__name__)

app.config["MONGO_DBNAME"] = os.environ.get("MONGO_DBNAME")
app.config["MONGO_URI"] = os.environ.get("MONGO_URI")
app.secret_key = os.environ.get("SECRET_KEY")
app.config['UPLOADED_PHOTOS_DEST'] = 'static/uploads'

mongo = PyMongo(app)
photos = UploadSet('photos', IMAGES)
configure_uploads(app, (photos))


@app.route("/")
def index():
    posts = list(mongo.db.posts.find().sort("date_posted", -1).limit(3))
    return render_template("index.html", page_title="Home", posts=posts)


@app.route("/get_posts")
def get_posts():
    posts = list(mongo.db.posts.find())
    return render_template("posts.html", posts=posts, page_title="Ads")


@app.route("/search", methods=["GET", "POST"])
def search():
    query = request.form.get("query")
    posts = list(mongo.db.posts.find({"$text": {"$search": query}}))
    return render_template("posts.html", posts=posts)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # check if username already exists in db
        existing_user = mongo.db.users.find_one(
            {"username": request.form.get("username").lower()})

        if existing_user:
            flash("Username already exists")
            return redirect(url_for("register"))

        register = {
            "username": request.form.get("username").lower(),
            "password": generate_password_hash(request.form.get("password")),
            "wishlist": []
        }
        mongo.db.users.insert_one(register)

        # put the new user into 'session' cookie
        session["user"] = request.form.get("username").lower()
        flash("Registration Successful!")
        return redirect(url_for("profile", username=session["user"]))

    return render_template("register.html")


@app.route("/add_to_wishlist/<post_id>")
def add_to_wishlist(post_id):
    post = mongo.db.posts.find_one({"_id": ObjectId(post_id)})
    mongo.db.users.update(
        {"username": session["user"]},
        {
            "$push": {"wishlist": post}
        }
    )
    return redirect(url_for('get_posts'))


@app.route("/clear_wishlist/<post_id>", methods=['GET', 'POST'])
def clear_wishlist(post_id):
    post = mongo.db.posts.find_one({"_id": ObjectId(post_id)})
    mongo.db.users.update(
        {"username": session["user"]},
        {
            "$pull": {"wishlist": post}
        }
    )
    return redirect(url_for('profile'))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # check if username exists in db
        existing_user = mongo.db.users.find_one(
            {"username": request.form.get("username").lower()})

        if existing_user:
            # ensure hashed password matches user input
            if check_password_hash(
                    existing_user["password"], request.form.get("password")):
                session["user"] = request.form.get("username").lower()
                flash("Welcome, {}".format(
                    request.form.get("username")))
                return redirect(url_for(
                            "profile", username=session["user"]))
            else:
                # invalid password match
                flash("Incorrect Username and/or Password")
                return redirect(url_for("login"))

        else:
            # username doesn't exist
            flash("Incorrect Username and/or Password")
            return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/profile/<username>", methods=["GET", "POST"])
def profile(username):
    username = mongo.db.users.find_one(
        {"username": session["user"]})["username"]
    wishlist = mongo.db.users.find_one(
        {"username": session["user"]})["wishlist"]
    if session["user"]:
        return render_template(
            "profile.html", username=username, wishlist=wishlist)
    return redirect(url_for("login"))


@app.route("/logout")
def logout():
    flash("You've been logged out")
    session.pop("user")
    return redirect(url_for("login"))


@app.route("/add_post", methods=["GET", "POST"])
def add_post():
    if request.method == "POST":
        filename = photos.save(request.files['image'])
        post = {
            "category_name": request.form.get("category_name"),
            "model": request.form.get("model"),
            "year": request.form.get("year"),
            "description": request.form.get("description"),
            "image": filename,
            "mileage": request.form.get("mileage"),
            "price": request.form.get("price"),
            "seller": request.form.get("seller"),
            "contact_number": request.form.get("contact_number"),
            "date_posted": request.form.get("date_posted"),
            "created_by": session["user"]
        }
        mongo.db.posts.insert_one(post)
        flash("Advert Succesfully Created")
        return redirect(url_for("get_posts"))
    categories = mongo.db.categories.find().sort("category_name", 1)
    return render_template("add_post.html", categories=categories)


@app.route("/edit_post/<post_id>", methods=["GET", "POST"])
def edit_post(post_id):
    post = mongo.db.posts.find_one({"_id": ObjectId(post_id)})
    if request.method == "POST":
        if 'image' in request.files:
            filename = photos.save(request.files['image'])
        else:
            filename = post['image']
        submit = {
            "category_name": request.form.get("category_name"),
            "model": request.form.get("model"),
            "year": request.form.get("year"),
            "description": request.form.get("description"),
            "image": filename,
            "mileage": request.form.get("mileage"),
            "price": request.form.get("price"),
            "seller": request.form.get("seller"),
            "contact_number": request.form.get("contact_number"),
            "date_posted": request.form.get("date_posted"),
            "created_by": session["user"]
        }
        mongo.db.posts.update({"_id": ObjectId(post_id)}, submit)
        flash("Advert Succesfully Updated")

    categories = mongo.db.categories.find().sort("category_name", 1)
    return render_template("edit_post.html", post=post, categories=categories)


@app.route("/delete_post/<post_id>")
def delete_post(post_id):
    mongo.db.posts.remove({"_id": ObjectId(post_id)})
    flash("Advert Succesfully Deleted")
    return redirect(url_for("get_posts"))


@app.route("/get_categories")
def get_categories():
    categories = list(mongo.db.categories.find().sort("category_name, 1"))
    return render_template("categories.html", categories=categories)


@app.route("/add_category", methods=["GET", "POST"])
def add_category():
    if request.method == "POST":
        category = {
            "category_name": request.form.get("category_name")
        }
        mongo.db.categories.insert_one(category)
        flash("New Category Added")
        return redirect(url_for("get_categories"))

    return render_template("add_category.html")


@app.route("/edit_category/<category_id>", methods=["GET", "POST"])
def edit_category(category_id):
    if request.method == "POST":
        submit = {
            "category_name": request.form.get("category_name")
        }
        mongo.db.categories.update({"_id": ObjectId(category_id)}, submit)
        flash("Category Succesfully Updated")
        return redirect(url_for("get_categories"))

    category = mongo.db.categories.find_one({"_id": ObjectId(category_id)})
    return render_template("edit_category.html", category=category)


@app.route("/delete_category/<category_id>")
def delete_category(category_id):
    mongo.db.categories.remove({"_id": ObjectId(category_id)})
    flash("Category Successfully Deleted")
    return redirect(url_for("get_categories"))


if __name__ == "__main__":
    app.run(host=os.environ.get("IP"),
            port=int(os.environ.get("PORT")),
            debug=True)