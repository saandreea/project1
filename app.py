import os

from flask import Flask, session, render_template, request, redirect, session, jsonify, url_for
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import date
import requests

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# Check for environment variable
if not os.getenv("DATABASEURL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASEURL"))
db = scoped_session(sessionmaker(bind=engine))

# Home Page
@app.route("/")
def index():
    session.clear()
    return render_template("index.html")


# Register Page
@app.route("/register", methods=["GET", "POST"])
def register():
    # User reached route via GET (as by clicking a link or via redirect)
    if request.method =="GET":
        # Forget any username
        session.clear()
        return render_template("register.html")

    # User reached route via POST (as by submitting a form via POST)
    else:
        firstname = (request.form.get("firstname")).capitalize()
        lastname = (request.form.get("lastname")).capitalize()
        username = (request.form.get("username")).lower()
        password = request.form.get("password")
        password2 = request.form.get("password2")
        email = (request.form.get("email")).upper()
        city = (request.form.get("city")).upper()

        #---PASSWORD rules---

        if not request.form.get("password"):
            return render_template("register.html", error="Missing password", firstname=firstname, lastname=lastname, username=username, email=email, city=city)

        if not request.form.get("password2"):
            return render_template("register.html", error="Retype password", firstname=firstname, lastname=lastname, username=username, email=email, city=city)

        if request.form.get("password") != request.form.get("password2"):
            return render_template("register.html", error="The password must match", firstname=firstname, lastname=lastname, username=username, email=email, city=city)

        #--- Username rules---
        if not request.form.get("username"):
            return render_template("register.html", error="Please type an username", firstname=firstname, lastname=lastname, email=email, city=city,  password=password, password2=password2)

        if db.execute("SELECT * FROM users WHERE username = :username", {"username": username}).rowcount != 0:
            return render_template("register.html", error="This username isn't available. Please try another.", firstname=firstname, lastname=lastname, email=email, city=city,  password=password, password2=password2)

        #---EMAIL rules---

        if not request.form.get("email"):
            return render_template("register.html", error="Missing email address", firstname=firstname, lastname=lastname, username=username,  city=city,  password=password, password2=password2)

        # parola = request.form.get("password")
        hashed = generate_password_hash(password)

        result = db.execute("""INSERT INTO users(user_firstname, user_lastname, username, password, email, city)
                                VALUES (:firstname, :lastname, :username, :password, :email, :city)"""
                                , {"firstname": firstname, "lastname": lastname, "username": username, "password": hashed, "email": email, "city": city})
        db.commit()

        if not result:
            return render_template("login.html", error="You already have an account!")

        # Query database for username
        user = db.execute("SELECT * FROM users WHERE username = :username", {"username": username}).fetchone()

        # Remember the user id in session
        session["user_id"] = user.user_id
        session["user_username"] = user.username
        session["user_firstname"] = user.user_firstname

        # Redirect user to search page
        return redirect("/search")


# Login Page
@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""
    # Forget any username
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        username=(request.form.get("username")).lower()
        password=request.form.get("password")

        # Ensure cnp was submitted
        if not request.form.get("username"):
            return render_template("login.html", error="Please enter your username.", password=password)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return render_template("login.html", error="Please enter your password.", username=username)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username", {"username": username}).fetchone()

        # Ensure username exists and password is correct
        if rows is None or not check_password_hash(rows.password, password):
            return render_template("login.html", error="Invalid Username and/or password!")


        # Remember which user has logged in
        session["user_id"] = rows.user_id
        session["user_username"] = rows.username
        session["user_firstname"] = rows.user_firstname

        return redirect("/search")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


# Logout Page
@app.route("/logout")
def logout():
    session.clear()

    # Redirect user to homepage
    return redirect("/")


# Search Page
@app.route("/search", methods=["GET", "POST"])
def books():
    if request.method == "GET":
        if session.get('user_id') is None:
            return redirect("/login")
        else:
            books_isbn = db.execute("SELECT isbn FROM books").fetchall()
            books_title = db.execute("SELECT title FROM books").fetchall()
            books_author = db.execute("SELECT DISTINCT author FROM books").fetchall()
            lista = []
            for isbn in books_isbn:
                lista.append(isbn[0])
            for title in books_title:
                lista.append(title[0])
            for author in books_author:
                lista.append(author[0])

            if session["user_firstname"] != "":
                name =''.join(["Hello ", ', ', session["user_firstname"], "!"])
            else:
                name ="Hello!"
            return render_template("search.html", lista=lista, alerta=name)
    else:
        return redirect("/")

# Api Page
@app.route("/api/<string:isbn_number>")
def search_api(isbn_number):
    book = db.execute("SELECT * FROM books WHERE isbn = :isbn;", {"isbn": isbn_number}).fetchone()
    rev = db.execute("""SELECT COUNT(reviews.rating), AVG(reviews.rating) FROM books
                         INNER JOIN reviews ON books.book_id = reviews.book_id  WHERE books.isbn = :isbn;""",{"isbn": isbn_number}).fetchone()

    if book is None:
        return jsonify({"error": "Invalid ISBN Number!"}), 404

    if rev[0] == 0 and rev[1] == None:
        return jsonify({
        "title": book["title"],
        "author": book["author"],
        "year": book["year"],
        "isbn": book["isbn"],
        "review_count": 0,
        "average_score": 0
        })

    return jsonify({
        "title": book["title"],
        "author": book["author"],
        "year": book["year"],
        "isbn": book["isbn"],
        "review_count": rev[0],
        "average_score": str(round(rev[1],2))
        })

# Search Page -> Update Content
@app.route("/search/update", methods=["GET"])
def search_update():
    if request.method == "GET":
        if session.get('user_id') is None:
            return redirect("/login")
        else:
            box = request.args.get('book_searched')
            rezultat = db.execute("SELECT * FROM books WHERE isbn LIKE '%{0}%' OR title LIKE '%{0}%' OR author LIKE '%{0}%'".format(box)).fetchall()
            result = {}

            result['title'] = []
            result['author'] = []
            result['isbn'] = []

            for row in rezultat:
                result['title'].append(row["title"])
                result['author'].append(row["author"])
                result["isbn"].append(row["isbn"])

            # print(result)
            return jsonify(result)
    else:
        return jsonify({"error": "error"})

# Book Details Page
@app.route("/books/<string:isbn_number>")
def carte(isbn_number):
    book = db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn": isbn_number}).fetchone()
    if book is None:
        return render_template("message.html", headline="Error!", message="No such book.")
    
    reviews = db.execute("SELECT rating, text_message, username FROM reviews INNER JOIN users on reviews.user_id = users.user_id WHERE reviews.book_id = :id", {"id": book.book_id}).fetchall()
    numar_review = db.execute("SELECT COUNT(rating) FROM reviews WHERE book_id = :id", {"id": book.book_id}).fetchone()
    avg_review = db.execute("SELECT AVG(rating) FROM reviews WHERE book_id = :id ", {"id": book.book_id}).fetchone()
    if avg_review[0] is None:
        review_avg = 0
    else:
        review_avg = round(avg_review[0], 2)

    # Get average rating & no. reviews from Goodreads
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "DSyEqotpot7tSPibliSfLw", "isbns": isbn_number})
    
    if res.status_code == 404:
        raspuns_gooodreads = "No reviews for this book on Goodreads."
    else:
        rezultat_goodreads = res.json()
        no_goodreads = rezultat_goodreads['books'][0]['work_ratings_count']
        average_goodreads = rezultat_goodreads['books'][0]['average_rating']
        raspuns_gooodreads  = average_goodreads + " average based on " + str(no_goodreads) + " reviews."
        print(raspuns_gooodreads)

    return render_template("book.html", book=book, reviews=reviews, avg_review=review_avg,numar_review=numar_review[0], raspuns_gooodreads=raspuns_gooodreads)

# Book submit reviews
@app.route("/review", methods=["POST"])
def review():
    if session.get('user_id') is None:
        return render_template("message.html", headline="Error!", message="You are not logged in!")

    book_id = request.form.get('bk_id')
    user_id = session.get('user_id')

    if db.execute("SELECT review_id FROM reviews WHERE user_id = :user_id AND book_id = :book_id", {"user_id": user_id, "book_id":book_id}).rowcount == 0:
        rating = request.form.get('rating')
        if rating is None:
            return render_template("message.html", headline="Error!", message="Please select a rate!")
        text = request.form.get('text')
        data = date.today()
        result = db.execute("""INSERT INTO reviews (rating, text_message, date, book_id, user_id) VALUES 
                            (:rating, :text, :date, :book_id, :user_id)"""
                            ,{"rating": rating, "text": text, "date": data, "book_id": book_id, "user_id": user_id})
        db.commit()
        if not result:
            return render_template("message.html", headline="Error!", message="Something went wrong.")
        else:
            return render_template("message.html", headline="Success!", message="Thank you for your review!")
    else:
        return render_template("message.html", headline="Error!", message="You have already submitted a review for this book.")
    
