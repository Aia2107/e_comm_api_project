from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from sqlalchemy import Column, Integer, String, Float, ForeignKey, Table
from sqlalchemy.orm import relationship

# --- Flask Setup ---
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = ("mysql+mysqlconnector://root:Code1234@localhost/ecommerce_db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# --- Initialize Extensions ---
db = SQLAlchemy(app)
ma = Marshmallow(app)

# --- Association Table (Many-to-Many: orders <-> products) ---
order_product = Table(
    "order_product",
    db.metadata,
    Column("order_id", Integer, ForeignKey("orders.id")),
    Column("product_id", Integer, ForeignKey("products.id")),
)

# --- Models ---


class User(db.Model):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(120), unique=True, nullable=False)

    # One-to-many relationship with orders
    orders = relationship("Order", back_populates="user")


class Product(db.Model):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    price = Column(Float, nullable=False)

    # Reverse relationship defined via secondary table in Order
    orders = relationship("Order", secondary=order_product, back_populates="products")


class Order(db.Model):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Many-to-one: each order belongs to one user
    user = relationship("User", back_populates="orders")

    # Many-to-many: each order can have many products
    products = relationship("Product", secondary=order_product, back_populates="orders")


# --- Schemas ---


class ProductSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Product
        load_instance = True


class OrderSchema(ma.SQLAlchemyAutoSchema):
    products = ma.Nested(ProductSchema, many=True)

    class Meta:
        model = Order
        include_fk = True
        load_instance = True


class UserSchema(ma.SQLAlchemyAutoSchema):
    orders = ma.Nested(OrderSchema, many=True)

    class Meta:
        model = User
        load_instance = True


product_schema = ProductSchema()
products_schema = ProductSchema(many=True)
order_schema = OrderSchema()
orders_schema = OrderSchema(many=True)
user_schema = UserSchema()
users_schema = UserSchema(many=True)

# --- Routes ---


@app.route("/api/users", methods=["POST"])
def create_user():
    data = request.get_json()
    new_user = User(name=data["name"], email=data["email"])
    db.session.add(new_user)
    db.session.commit()
    return user_schema.jsonify(new_user), 201


@app.route("/api/users", methods=["GET"])
def get_users():
    return users_schema.jsonify(User.query.all())


@app.route("/api/products", methods=["POST"])
def create_product():
    data = request.get_json()
    new_product = Product(name=data["name"], price=data["price"])
    db.session.add(new_product)
    db.session.commit()
    return product_schema.jsonify(new_product), 201


@app.route("/api/products", methods=["GET"])
def get_products():
    return products_schema.jsonify(Product.query.all())


@app.route("/api/orders", methods=["POST"])
def create_order():
    data = request.get_json()
    user_id = data["user_id"]
    product_ids = data.get("product_ids", [])
    products = Product.query.filter(Product.id.in_(product_ids)).all()
    new_order = Order(user_id=user_id, products=products)
    db.session.add(new_order)
    db.session.commit()
    return order_schema.jsonify(new_order), 201


@app.route("/api/orders", methods=["GET"])
def get_orders():
    return orders_schema.jsonify(Order.query.all())


# @app.before_first_request
# def create_tables():
#     db.create_all()


if __name__ == "__main__":
    
    with app.app_context(): 
        db.create_all()
    app.run(debug=True)
