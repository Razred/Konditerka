from datetime import datetime

from flask import Blueprint, render_template, flash, url_for, request, session
from flask_login import current_user, logout_user, login_required, login_user, login_manager
from werkzeug.utils import redirect

from app import bcrypt, db
from app.models import User, Product, Order
from .forms import RegistrationForm, LoginForm


users = Blueprint('users', __name__)



@users.route('/register', methods=['POST', 'GET'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('users.account'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(email=form.email.data, name=form.name.data, password=hashed_password )
        db.session.add(user)
        db.session.commit()

        flash('Ваш аккаунт был создан. Вы можете войти')
        return redirect(url_for('users.login'))
    return render_template('register.html', form=form, title='Регистрация', legends='Регистрация')


@users.route('/login', methods=['POST', 'GET'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('users.account'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            flash(f'Добро пожаловать {current_user.name}')
            return redirect(next_page) if next_page else redirect(url_for('users.account'))
        else:
            flash(f'Войти не удалось. Пожалуйста проверьте почту или пароль', 'danger')
    return render_template('login.html', form=form, title='Авторизация', legend='Войти')


@users.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    return render_template('account.html')

@users.route('/account/update', methods=['GET', 'POST'])
@login_required
def account_update():
    user = User.query.get(current_user.id)
    if request.method == "POST":
        user.address = request.form['address']
        user.phone_number = request.form['phone_number']

        try:
            db.session.commit()
            return redirect(url_for('users.account'))
        except:
            return "Изменения невозможны"

    else:
        return render_template('account_update.html', user=user)


@users.route('/add/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    try:
        _quantity = int(request.form['quantity'])
        _id = int(request.form['id'])

        if _quantity and _id and request.method == 'POST':
            item = Product.query.get(_id)
            _item_id = str(item.id)

            itemArray = {_item_id : {'name' : item.name, 'quantity' : _quantity, 'price' : item.price, 'image' : item.image_url, 'total_price' : _quantity * item.price}}

            all_total_price = 0
            all_total_quantity = 0

            session.modified = True
            if 'cart_item' in session:
                if _item_id in session['cart_item']:
                    for key, value in session['cart_item'].items():
                        if _item_id == key:
                            old_quantity = session['cart_item'][key]['quantity']
                            total_quantity = old_quantity + _quantity
                            session['cart_item'][key]['quantity'] = total_quantity
                            session['cart_item'][key]['total_price'] = total_quantity * item.price
                            break
                else:
                    session['cart_item'] = array_merge(session['cart_item'], itemArray)

                for key, value in session['cart_item'].items():
                    individual_quantity = int(session['cart_item'][key]['quantity'])
                    individual_price = float(session['cart_item'][key]['total_price'])
                    all_total_quantity = all_total_quantity + individual_quantity
                    all_total_price = all_total_price + individual_price
            else:
                session['cart_item'] = itemArray
                all_total_quantity = all_total_quantity + _quantity
                all_total_price = all_total_price + _quantity * item.price


            session['all_total_quantity'] = all_total_quantity
            session['all_total_price'] = all_total_price

            return redirect(url_for('main.catalog'))
        else:
            return 'Error while adding item to cart'
    except Exception as e:
        print(e)

@users.route('/empty')
def empty_cart():
    try:
        session_clear()
        return redirect(url_for('main.catalog'))
    except Exception as e:
        print(e)

@users.route('/delete/<string:id>')
def delete_product(id):
    all_total_price = 0
    all_total_quantity = 0
    session.modified = True
    for key, value in session['cart_item'].items():
        if key == id:
            session['cart_item'].pop(key, None)
            if 'cart_item' in session:
                for key, value in session['cart_item'].items():
                    individual_quantity = int(session['cart_item'][key]['quantity'])
                    individual_price = float(session['cart_item'][key]['total_price'])
                    all_total_quantity = all_total_quantity + individual_quantity
                    all_total_price = all_total_price + individual_price
            break

    if all_total_quantity == 0:
        session_clear()
    else:
        session['all_total_quantity'] = all_total_quantity
        session['all_total_price'] = all_total_price

    return redirect(url_for('users.view_cart'))


def session_clear():
    session['cart_item'].clear()
    session['all_total_quantity'] = 0
    session['all_total_price'] = 0
def array_merge(first_array, second_array):
    if isinstance(first_array, list) and isinstance(second_array, list):
        return first_array + second_array
    elif isinstance(first_array, dict) and isinstance(second_array, dict):
        return dict( list(first_array.items()) + list(second_array.items()))
    elif isinstance( first_array, set) and isinstance(second_array, set):
        return first_array.union(second_array)
    return False


@users.route('/cart')
@login_required
def view_cart():
    cart = {}
    total_quantity = 0
    total_price = 0
    if 'cart_item' in session:
        cart = session['cart_item'].items()
        total_quantity = session['all_total_quantity']
        total_price = session['all_total_price']
    return render_template('cart.html', cart=cart, quantity=total_quantity, price=total_price)

@users.route('/order', methods=['GET', 'POST'])
@login_required
def order():
    try:
        if not 'cart_item' in session:
            return redirect('main.catalog')
        if request.method == "POST":
            order = Order(user_id=current_user.id, user_name=request.form['name'], address=request.form['address'],
                          total_price=session['all_total_price'], comments=request.form['comments'])
            db.session.add(order)
            db.session.commit()
            flash('Ваш заказ был успешно создан')
            return redirect(url_for('users.empty_cart'))
        else:
            return render_template('order.html', user=current_user, cart=session['cart_item'], total_price=session['all_total_price'])
    except Exception as e:
        print(e)

@users.route('/logout')
def logout():
    current_user.last_seen = datetime.now()
    db.session.commit()
    logout_user()
    return redirect(url_for('main.home'))