from google.appengine.ext.db import BadValueError

from flask import render_template, request, abort
from flask_login import login_required, current_user

from appfactory.auth import ensure_user_admin, ensure_user_pos

from ndbextensions.ndbjson import jsonify
from ndbextensions.models import PosProduct, PosSale, Product
from ndbextensions.paginator import Paginator
from ndbextensions.utility import get_or_none

from tantalus import bp_pos as router


@router.route('/', defaults=dict(page=0))
@router.route('/page/<int:page>')
@login_required
@ensure_user_admin
def index(page):
    if page < 0:
        page = 0

    pagination = Paginator(PosProduct.query(), page, 20)
    return render_template('tantalus_posproducts.html', pagination=pagination)


@router.route('.json')
@login_required
@ensure_user_pos
def indexjson():
    return jsonify(PosProduct.query().fetch())


@router.route('/add', methods=["GET", "POST"])
@login_required
@ensure_user_admin
def addposproduct():
    form = request.json

    if request.method == "POST":
        try:
            pos = PosProduct(
                scan_id=form.get("scan_id", ""),
                keycode=form.get("keycode", "")
            )

            if 'product' in form:
                prd = get_or_none(form['product'], Product)
                if prd is None:
                    raise BadValueError("Product does not exist.")
                pos.product = prd.key
                pos.name = prd.contenttype
                pos.price = prd.value
            elif 'name' in form:
                if len(form['name']) < 1:
                    raise BadValueError("Name too short!")
                pos.price = form['price']
                pos.name = form['name']
            else:
                raise BadValueError("Need to specify either product or name!")
            pos.put()
        except (BadValueError, KeyError) as e:
            return jsonify({"messages": [e.message]}, 400)
        return jsonify(pos)

    return render_template('tantalus_posproduct.html',
                           products=Product.query(Product.hidden == False).order(Product.contenttype).fetch())


@router.route('/edit/<posproduct_id>', methods=["GET", "POST"])
@login_required
@ensure_user_admin
def editposproduct(posproduct_id):
    form = request.json

    pos = get_or_none(posproduct_id, PosProduct)

    if pos is None:
        return abort(404)

    if request.method == "POST":
        try:
            if "product" in form:
                prd = get_or_none(form["product"], Product)
                if prd is None:
                    raise BadValueError("Product does not exist.")
                pos.product = prd.key
                pos.name = prd.contenttype
                pos.price = prd.value
            elif 'name' in form:
                if len(form['name']) < 1:
                    raise BadValueError("Name too short!")
                pos.name = form['name']
                pos.product = None
                pos.price = form.get('price', pos.price)
            pos.scan_id = form.get('scan_id', pos.scan_id)
            pos.keycode = form.get('keycode', pos.keycode)
            pos.put()
        except BadValueError as e:
            return jsonify({"messages": [e.message]}, 400)
        return jsonify(pos)

    return render_template('tantalus_posproduct.html', posproduct=pos,
                           products=Product.query(Product.hidden == False).order(Product.contenttype).fetch())


@router.route('/sales', defaults=dict(page=0))
@router.route('/sales/<int:page>')
@login_required
@ensure_user_pos
def sales(page):
    if page < 0:
        page = 0

    pagination = Paginator(PosSale.query().order(-PosSale.time), page, 20)
    return render_template('tantalus_possales.html', pagination=pagination)


@router.route('/sales.json')
@login_required
@ensure_user_pos
def salesjson():
    return jsonify(PosSale.query().order(-PosSale.time))


@router.route("/sell.json", methods=["POST"])
@login_required
@ensure_user_pos
def sell():
    sale = request.json
    if not sale:
        return jsonify({"messages": ["No JSON supplied."]}, 400)

    try:
        prd = get_or_none(sale["product"], PosProduct)
        if prd.get() is None:
            raise BadValueError("Product does not exist")

        possale = PosSale(
            user=current_user.key,
            product=prd,
            amount=sale.get('amount', 1)
        )
        possale.put()
    except (BadValueError, KeyError) as e:
        return jsonify({"messages": [e.message]}, 400)
    return jsonify(possale)
