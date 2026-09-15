from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "somesecretkey123" 

books = [
    {"id": 1, "title": "The Alchemist", "author": "Paulo Coelho", "category": "Fiction", "total_copies": 3, "available_copies": 3},
    {"id": 2, "title": "Clean Code", "author": "Robert C. Martin", "category": "Programming", "total_copies": 2, "available_copies": 2},
    {"id": 3, "title": "Wings of Fire", "author": "A.P.J. Abdul Kalam", "category": "Biography", "total_copies": 4, "available_copies": 4},
    {"id": 4, "title": "Atomic Habits", "author": "James Clear", "category": "Self-Help", "total_copies": 3, "available_copies": 3},
    {"id": 5, "title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "category": "Fiction", "total_copies": 2, "available_copies": 2},
    {"id": 6, "title": "Harry Potter and the Philosopher's Stone", "author": "J.K. Rowling", "category": "Fantasy", "total_copies": 5, "available_copies": 5},
    {"id": 7, "title": "Python Crash Course", "author": "Eric Matthes", "category": "Programming", "total_copies": 3, "available_copies": 3},
    {"id": 8, "title": "The Power of Now", "author": "Eckhart Tolle", "category": "Self-Help", "total_copies": 2, "available_copies": 2}
]
members = {}
issued_records = []
next_book_id = 9
next_record_id = 1

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

FINE_PER_DAY = 5 

def find_book(book_id):
    for b in books:
        if b["id"] == book_id:
            return b
    return None

def is_logged_in():
    return "username" in session

def is_admin():
    return session.get("role") == "admin"

# ------------------HOME

@app.route("/")
def home():
    if not is_logged_in():
        return redirect(url_for("login"))
    if is_admin():
        return redirect(url_for("admin_dashboard"))
    return redirect(url_for("dashboard"))


# ------------------REGISTER

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        if username in members:
            flash("That username is already taken,try another name.")
            return redirect(url_for("register"))

        members[username] = {"name": name, "email": email, "password": password}
        flash("Registration successful! You can login now.")
        return redirect(url_for("login"))

    return render_template("register.html")


# ------------------LOGIN

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        # check admim
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["username"] = username
            session["role"] = "admin"
            flash("Welcome back, Admin!")
            return redirect(url_for("admin_dashboard"))

        # check member
        member = members.get(username)
        if member and member["password"] == password:
            session["username"] = username
            session["role"] = "member"
            flash("Login successful. Welcome " + member["name"] + "!")
            return redirect(url_for("dashboard"))

        flash("Invalid username or password.")
        return redirect(url_for("login"))

    return render_template("login.html")


# ------------------LOGOUT

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for("login"))


# ------------------CATALOG

@app.route("/catalog")
def catalog():
    if not is_logged_in():
        return redirect(url_for("login"))

    search=request.args.get("search", "")
    if search:
        results=[b for b in books if search.lower() in b["title"].lower()
                   or search.lower() in b["author"].lower()]
    else:
        results=books

    return render_template("catalog.html", books=results, search=search)


# ------------------MEMBER DASHBOARD

@app.route("/dashboard")
def dashboard():
    if not is_logged_in() or is_admin():
        return redirect(url_for("login"))

    username=session["username"]
    my_records=[r for r in issued_records if r["username"] == username and r["return_date"] is None]
    today =datetime.now().date()

    return render_template("dashboard.html", records=my_records, books=books, today=today)


# ------------------ADMIN DASHBOARD

@app.route("/admin/dashboard")
def admin_dashboard():
    if not is_logged_in() or not is_admin():
        return redirect(url_for("login"))

    total_books = len(books)
    total_members = len(members)
    currently_issued = [r for r in issued_records if r["return_date"] is None]
    today = datetime.now().date()
    overdue = [r for r in currently_issued if r["due_date"] < today]

    return render_template("admin_dashboard.html",
                            total_books=total_books,
                            total_members=total_members,
                            issued_count=len(currently_issued),
                            overdue_count=len(overdue))


# ------------------ VIEW ALL MEMBERS--ISSUED BOOKS
@app.route("/admin/members")
def admin_members():
    if not is_logged_in() or not is_admin():
        return redirect(url_for("login"))
    return render_template("admin_members.html", members=members, records=issued_records, books=books)


# ------------------ADD BOOK

@app.route("/admin/books/add", methods=["GET", "POST"])
def add_book():
    global next_book_id
    if not is_logged_in() or not is_admin():
        return redirect(url_for("login"))

    if request.method == "POST":
        title=request.form["title"]
        author = request.form["author"]
        category = request.form["category"]
        copies = int(request.form["copies"])

        new_book = {
            "id": next_book_id,
            "title": title,
            "author": author,
            "category": category,
            "total_copies": copies,
            "available_copies": copies
        }
        books.append(new_book)
        next_book_id += 1

        flash("Book added successfully!")
        return redirect(url_for("catalog"))

    return render_template("add_book.html")


# ------------------EDIT BOOK

@app.route("/admin/books/edit/<int:book_id>", methods=["GET", "POST"])
def edit_book(book_id):
    if not is_logged_in() or not is_admin():
        return redirect(url_for("login"))

    book = find_book(book_id)
    if not book:
        flash("Book not found.")
        return redirect(url_for("catalog"))

    if request.method == "POST":
        book["title"] = request.form["title"]
        book["author"] = request.form["author"]
        book["category"] = request.form["category"]
        new_total = int(request.form["copies"])

        issued_out = book["total_copies"] - book["available_copies"]
        book["total_copies"] = new_total
        book["available_copies"] = max(new_total - issued_out, 0)

        flash("Book updated successfully!")
        return redirect(url_for("catalog"))

    return render_template("edit_book.html", book=book)


# ------------------DELETE BOOK

@app.route("/admin/books/delete/<int:book_id>")
def delete_book(book_id):
    if not is_logged_in() or not is_admin():
        return redirect(url_for("login"))

    book = find_book(book_id)
    if book:
        books.remove(book)
        flash("Book removed from catalog.")

    return redirect(url_for("catalog"))


# ------------------ISSUE BOOK

@app.route("/admin/issue", methods=["GET", "POST"])
def issue_book():
    global next_record_id
    if not is_logged_in() or not is_admin():
        return redirect(url_for("login"))

    if request.method == "POST":
        username = request.form["username"]
        book_id = int(request.form["book_id"])
        book = find_book(book_id)

        if not book or book["available_copies"] <= 0:
            flash("This book is not available right now.")
            return redirect(url_for("issue_book"))

        if username not in members:
            flash("That member does not exist.")
            return redirect(url_for("issue_book"))

        issue_date = datetime.now().date()
        due_date = issue_date + timedelta(days=14)

        record = {
            "record_id": next_record_id,
            "book_id": book_id,
            "username": username,
            "issue_date": issue_date,
            "due_date": due_date,
            "return_date": None,
            "fine": 0
        }
        issued_records.append(record)
        next_record_id += 1

        book["available_copies"] -= 1

        flash("Book issued to " + username + ". Due date: " + str(due_date))
        return redirect(url_for("admin_dashboard"))

    return render_template("issue_book.html", books=books, members=members)


# ------------------RETURN BOOK

@app.route("/admin/return/<int:record_id>")
def return_book(record_id):
    if not is_logged_in() or not is_admin():
        return redirect(url_for("login"))

    record = None
    for r in issued_records:
        if r["record_id"] == record_id:
            record = r
            break

    if not record:
        flash("Record not found.")
        return redirect(url_for("admin_members"))

    return_date = datetime.now().date()
    record["return_date"] = return_date

    # fine
    if return_date > record["due_date"]:
        days_late = (return_date - record["due_date"]).days
        record["fine"] = days_late * FINE_PER_DAY
        flash("Book returned. It was " + str(days_late) + " day(s) late. Fine: Rs. " + str(record["fine"]))
    else:
        record["fine"] = 0
        flash("Book returned on time. No fine.")

    book = find_book(record["book_id"])
    if book:
        book["available_copies"] += 1

    return redirect(url_for("admin_members"))


# ------------------ PROFILE

@app.route("/profile", methods=["GET", "POST"])
def profile():
    if not is_logged_in() or is_admin():
        return redirect(url_for("login"))

    username = session["username"]
    member = members[username]

    if request.method == "POST":
        member["name"] = request.form["name"]
        member["email"] = request.form["email"]
        flash("Profile updated.")
        return redirect(url_for("dashboard"))

    return render_template("profile.html", member=member)


if __name__ == "__main__":
    app.run(debug=True)
