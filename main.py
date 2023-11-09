from flask import *
import sqlite3


def find_by_name(name):
    connection = sqlite3.connect("shop_data.db")
    cursor = connection.cursor()
    data = cursor.execute("SELECT * FROM Goods WHERE NAME='{}' ".format(name)).fetchone()
    connection.commit()
    connection.close()
    return data


def in_shopping_cart():
    connection = sqlite3.connect("shop_data.db")
    cursor = connection.cursor()
    shopping_cart = cursor.execute("""SELECT * FROM Cart""").fetchall()
    connection.commit()
    connection.close()
    return shopping_cart


def total_price(cart):
    total = 0
    for row in cart:
        connection = sqlite3.connect("shop_data.db")
        cursor = connection.cursor()
        item = cursor.execute("""SELECT * FROM Goods WHERE NAME='{}'""".format(row[0])).fetchone()
        connection.commit()
        connection.close()
        item_price = item[2] * row[1]
        try:
            total += int(item_price)
        except ValueError:
            total += 0
    return total

app = Flask(__name__)
TOTAL = 0
ERROR = None


@app.route("/cart", methods=["POST", "GET"])
def in_cart():
    global TOTAL
    payment = None

    shopping_cart = in_shopping_cart()

    if shopping_cart:
        TOTAL = total_price(shopping_cart)

    # --------------payment methode-----------------
    if "account_pay" in request.form:
        payment = "account"

    if "card_pay" in request.form:
        payment = "card"

    if "Submit" in request.form:
        for item in shopping_cart:
            # ---------------UPDATING number of pieces in Goods table
            connection = sqlite3.connect("shop_data.db")
            cursor = connection.cursor()
            data = cursor.execute("""SELECT * FROM Goods where NAME='{}' """.format(item[0])).fetchone()
            old_pieces = int(data[3])
            connection.commit()
            connection.close()

            current_pieces = old_pieces - item[1]

            connection = sqlite3.connect("shop_data.db")
            cursor = connection.cursor()
            cursor.execute("""UPDATE Goods SET PIECES=? where NAME='{}' """.format(item[0]), ([current_pieces]))
            connection.commit()
            connection.close()

        connection = sqlite3.connect("shop_data.db")
        cursor = connection.cursor()
        cursor.execute("""DELETE FROM Cart""")
        connection.commit()
        connection.close()
        TOTAL = 0

    # --------------changing number of pieces-----------------
    if "new_pieces" in request.form:
        pieces = request.form.get("num_pieces")
        name = request.form.get("item_name")
        connection = sqlite3.connect("shop_data.db")
        cursor = connection.cursor()
        cursor.execute("""UPDATE Cart SET QUANTITY=? where NAME='{}' """.format(name),
                       ([pieces])
                       )
        connection.commit()
        connection.close()
        return redirect(url_for("in_cart"))

    if "delete" in request.form:
        name = request.form.get("item_delete")
        connection = sqlite3.connect("shop_data.db")
        cursor = connection.cursor()
        cursor.execute("""DELETE FROM Cart WHERE NAME='{}' """.format(name))
        connection.commit()
        connection.close()
        return redirect(url_for("in_cart"))

    return render_template("cart.html", total=TOTAL, cart=shopping_cart, pay_methode=payment)


@app.route("/", methods=["POST", "GET"])
def home():
    # -----------------SHOPPING PRICE------------------
    global TOTAL
    global ERROR

    shopping_cart = in_shopping_cart()
    if shopping_cart:
        TOTAL = total_price(shopping_cart)

    if "item" in request.form:
        pieces_add = int(request.form.get('pieces'))
        item_name = request.form['ItemName']

        connection = sqlite3.connect("shop_data.db")
        cursor = connection.cursor()
        data = cursor.execute("""SELECT * FROM Goods where NAME='{}' """.format(item_name)).fetchone()
        connection.commit()
        connection.close()
        if pieces_add > data[3]:
            ERROR = "Not enough pieces"
            return redirect(url_for("home"))

        add_cart = {
                   "NAME": item_name,
                   "QUANTITY": pieces_add
                   }
        connection = sqlite3.connect("shop_data.db")
        cursor = connection.cursor()
        try:
            cursor.execute("""INSERT INTO Cart VALUES (:NAME, :QUANTITY)""", add_cart)
            connection.commit()
            connection.close()
            ERROR = None
            return redirect(url_for("home"))

        except sqlite3.IntegrityError:

            cursor.execute("""UPDATE Cart SET QUANTITY=? where NAME='{}' """.format(item_name),
                           ([pieces_add])
                           )
            connection.commit()
            connection.close()
            ERROR = None
            return redirect(url_for("home"))

    # ------------------FILTER-------------------------------------
    connection = sqlite3.connect("shop_data.db")
    cursor = connection.cursor()
    filter_param = request.args.get("filter")

    if filter_param:
        if filter_param == "ascending":
            query = "SELECT * FROM Goods ORDER BY PRICE ASC NULLS LAST"
            cursor.execute(query)
            results = cursor.fetchall()
            return render_template("index.html", images=results, total=TOTAL, error=ERROR)

        elif filter_param == "descending":
            query = "SELECT * FROM Goods ORDER BY PRICE DESC NULLS LAST"
            cursor.execute(query)
            results = cursor.fetchall()
            return render_template("index.html", images=results, total=TOTAL, error=ERROR)

    if not filter_param:
        query = "SELECT * FROM Goods"
        cursor.execute(query)
        results = cursor.fetchall()
        return render_template("index.html", images=results, total=TOTAL, error=ERROR)

# ----------------just for admin-------------------


@app.route("/admin", methods=["POST", "GET"])
def new_item():
    error = None

    if request.method == "POST":
        if "new_item" in request.form:
            uploaded_image = request.files["product_img"]
            if uploaded_image:
                file_path = "static/goods/" + uploaded_image.filename
                uploaded_image.save(file_path)
                name = request.form["name"]
                pieces = request.form["pieces"]
                price = request.form["price"]
                info = request.form["info"]
                new_goods = {
                             "NAME": name,
                             "IMAGE_PATH": file_path,
                             "PRICE": price,
                             "PIECES": pieces,
                             "INFO": info
                             }
                connection = sqlite3.connect("shop_data.db")
                cursor = connection.cursor()
                cursor.execute("""INSERT INTO Goods VALUES (:NAME, :IMAGE_PATH, :PRICE, :PIECES, :INFO)""", new_goods)
                connection.commit()
                connection.close()

        elif "delete_item" in request.form:
            name = request.form["name"]
            connection = sqlite3.connect("shop_data.db")
            cursor = connection.cursor()
            cursor.execute("""delete from Goods WHERE NAME='{}' """.format(name))
            connection.commit()
            connection.close()

        elif "update_item" in request.form:
            old_name = request.form["old_name"]
            data = find_by_name(old_name)

            if data:
                file_path = data[1]
            else:
                error = "Product is not listed."
                return error

            new_name = request.form["new_name"]
            if new_name == "":
                new_name = old_name

            new_price = request.form["new_price"]
            if new_price == "":
                new_price = find_by_name(old_name)[2]

            new_pieces = request.form["new_pieces"]
            if new_pieces == "":
                new_pieces = find_by_name(old_name)[3]

            new_info = request.form["new_info"]
            if new_info == "":
                new_info = find_by_name(old_name)[4]

            # change image and path
            uploaded_image = request.files["product_img"]
            if uploaded_image:
                file_path = "static/goods/" + uploaded_image.filename
                uploaded_image.save(file_path)
                return file_path

            connection = sqlite3.connect("shop_data.db")
            cursor = connection.cursor()
            cursor.execute("""UPDATE Goods SET NAME=?, IMAGE_PATH=?, PRICE=?, PIECES=?, INFO=?
                           where NAME='{}' """.format(old_name),
                           (new_name, file_path, new_price, new_pieces, new_info)
                           )
            connection.commit()
            connection.close()

    return render_template("new_item.html", message=error)


if __name__ == "__main__":
    app.run(debug=True)
