from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Table, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime

# --- App Setup ---
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = (
    "mysql+mysqlconnector://root:Code1234@localhost/ecommerce_db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# --- Initialize Extensions ---
db = SQLAlchemy(app)
ma = Marshmallow(app)

# --- Association Table with UniqueConstraint ---
order_product = Table(
    "order_product",
    db.metadata,
    Column("order_id", Integer, ForeignKey("orders.id"), primary_key=True),
    Column("product_id", Integer, ForeignKey("products.id"), primary_key=True),
    UniqueConstraint(
        "order_id", "product_id", name="unique_order_product"
    ),  # Prevent duplicate products in an order
)


# --- User Model ---
class User(db.Model):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    address = Column(String(200), nullable=True)
    email = Column(String(120), unique=True, nullable=False)

    orders = relationship("Order", back_populates="user")


# --- Product Model ---
class Product(db.Model):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    product_name = Column(String(100), nullable=False)
    price = Column(Float, nullable=False)

    orders = relationship("Order", secondary=order_product, back_populates="products")


# --- Order Model ---
class Order(db.Model):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    order_date = Column(DateTime, default=datetime.utcnow)  # Default to current time
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    user = relationship("User", back_populates="orders")
    products = relationship("Product", secondary=order_product, back_populates="orders")


# --- Marshmallow Schemas ---
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


# --- Schema Instances ---
product_schema = ProductSchema()
products_schema = ProductSchema(many=True)
order_schema = OrderSchema()
orders_schema = OrderSchema(many=True)
user_schema = UserSchema()
users_schema = UserSchema(many=True)

# --- API Routes ---


# Create user
@app.route("/api/users", methods=["POST"])
def create_user():
    data = request.get_json()
    new_user = User(name=data["name"], address=data.get("address"), email=data["email"])
    db.session.add(new_user)
    db.session.commit()
    return user_schema.jsonify(new_user), 201


# Get all users
@app.route("/api/users", methods=["GET"])
def get_users():
    return users_schema.jsonify(User.query.all())


# Create product
@app.route("/api/products", methods=["POST"])
def create_product():
    data = request.get_json()
    new_product = Product(product_name=data["product_name"], price=data["price"])
    db.session.add(new_product)
    db.session.commit()
    return product_schema.jsonify(new_product), 201


# Get all products
@app.route("/api/products", methods=["GET"])
def get_products():
    return products_schema.jsonify(Product.query.all())


# Create order
@app.route("/api/orders", methods=["POST"])
def create_order():
    data = request.get_json()
    user_id = data["user_id"]
    product_ids = data.get("product_ids", [])

    # Fetch products and ensure no duplicates
    unique_ids = list(set(product_ids))
    products = Product.query.filter(Product.id.in_(unique_ids)).all()

    new_order = Order(user_id=user_id, products=products)
    db.session.add(new_order)
    db.session.commit()
    return order_schema.jsonify(new_order), 201


# Get all orders
@app.route("/api/orders", methods=["GET"])
def get_orders():
    return orders_schema.jsonify(Order.query.all())


# --- Update User ---
@app.route("/api/users/<int:user_id>", methods=["PUT"])
def update_user(user_id):
    user = User.query.get_or_404(user_id)
    data = request.get_json()
    user.name = data.get("name", user.name)
    user.address = data.get("address", user.address)
    user.email = data.get("email", user.email)
    db.session.commit()
    return user_schema.jsonify(user)


# --- Update Product ---
@app.route("/api/products/<int:product_id>", methods=["PUT"])
def update_product(product_id):
    product = Product.query.get_or_404(product_id)
    data = request.get_json()
    product.product_name = data.get("product_name", product.product_name)
    product.price = data.get("price", product.price)
    db.session.commit()
    return product_schema.jsonify(product)


# --- Update Order (e.g. change product list) ---
@app.route("/api/orders/<int:order_id>", methods=["PUT"])
def update_order(order_id):
    order = Order.query.get_or_404(order_id)
    data = request.get_json()

    # Update user ID if provided
    if "user_id" in data:
        order.user_id = data["user_id"]

    # Replace product list
    if "product_ids" in data:
        product_ids = list(set(data["product_ids"]))
        order.products = Product.query.filter(Product.id.in_(product_ids)).all()

    db.session.commit()
    return order_schema.jsonify(order)


# --- Delete User ---
@app.route("/api/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return jsonify({"message": "User deleted"})


# --- Delete Product ---
@app.route("/api/products/<int:product_id>", methods=["DELETE"])
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    return jsonify({"message": "Product deleted"})


# --- Delete Order ---
@app.route("/api/orders/<int:order_id>", methods=["DELETE"])
def delete_order(order_id):
    order = Order.query.get_or_404(order_id)
    db.session.delete(order)
    db.session.commit()
    return jsonify({"message": "Order deleted"})


# --- Run App ---
if __name__ == "__main__":
    
    with app.app_context():
        db.create_all()
app.run(debug=True)
