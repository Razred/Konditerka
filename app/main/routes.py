from flask import Blueprint, render_template

from app.models import Product

main = Blueprint('main', __name__)

@main.route('/')
def home():
    return render_template('index.html', title='Главная')

@main.route('/catalog')
def catalog():
    products = Product.query.filter(Product.quantity > 0).order_by(Product.name).all()
    return render_template('catalog.html', products=products)

@main.route('/catalog/<int:id>')
def product_detail(id):
    item = Product.query.get(id)
    return render_template("product-detail.html", item=item)



