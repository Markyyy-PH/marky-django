from django.shortcuts import render, redirect, get_object_or_404
from store.models import Product, Variation
from .models import Cart, CartItem
from django.core.exceptions import ObjectDoesNotExist
from django.contrib import messages  # Import messages for user notifications

def _cart_id(request):
    cart = request.session.session_key
    if not cart:
        cart = request.session.create()
    return cart


def add_cart(request, product_id):
    product = Product.objects.get(id=product_id)
    product_variation = []

    if request.method == "POST":
        for key, value in request.POST.items():
            if value:  # Ensure empty selections are ignored
                try:
                    variation = Variation.objects.get(
                        product=product, variation_category__iexact=key, variation_value__iexact=value
                    )
                    product_variation.append(variation)
                except Variation.DoesNotExist:
                    pass  # Skip if variation does not exist

    # Check if size is required but missing
    required_variations = Variation.objects.filter(product=product).values_list('variation_category', flat=True).distinct()
    selected_variation_categories = {var.variation_category.lower() for var in product_variation}

    if "size" in [cat.lower() for cat in required_variations] and "size" not in selected_variation_categories:
        messages.error(request, "Please select a size before adding to cart.")  # Show error message
        return redirect(request.META.get("HTTP_REFERER", "store"))  # Stay on the same page

    # Proceed to add to cart if all required variations are selected
    cart, created = Cart.objects.get_or_create(cart_id=_cart_id(request))

    is_cart_item_exists = CartItem.objects.filter(product=product, cart=cart).exists()
    if is_cart_item_exists:
        cart_items = CartItem.objects.filter(product=product, cart=cart)
        
        ex_var_list = []
        id_list = []
        for item in cart_items:
            existing_variation = list(item.variations.all())
            ex_var_list.append(existing_variation)
            id_list.append(item.id)

        if product_variation in ex_var_list:
            index = ex_var_list.index(product_variation)
            item_id = id_list[index]
            item = CartItem.objects.get(id=item_id)
            item.quantity += 1
            item.save()
        else:
            item = CartItem.objects.create(product=product, quantity=1, cart=cart)
            if product_variation:
                item.variations.set(product_variation)
            item.save()
    else:
        cart_item = CartItem.objects.create(product=product, quantity=1, cart=cart)
        if product_variation:
            cart_item.variations.set(product_variation)
        cart_item.save()
    
    return redirect('cart')


def remove_cart(request, product_id):
    cart = Cart.objects.get(cart_id=_cart_id(request))
    product = get_object_or_404(Product, id=product_id)

    product_variation = []
    if request.method == "POST":
        for key, value in request.POST.items():
            try:
                variation = Variation.objects.get(
                    product=product, variation_category__iexact=key, variation_value__iexact=value
                )
                product_variation.append(variation)
            except:
                pass

    cart_items = CartItem.objects.filter(product=product, cart=cart)

    # Fix: Ensure we match the right item
    for cart_item in cart_items:
        existing_variations = list(cart_item.variations.all())
        if existing_variations == product_variation or not product_variation:
            if cart_item.quantity > 1:
                cart_item.quantity -= 1
                cart_item.save()
            else:
                cart_item.delete()
            break  

    return redirect('cart')


def remove_cart_item(request, product_id):
    cart = Cart.objects.get(cart_id=_cart_id(request))
    product = get_object_or_404(Product, id=product_id)

    product_variation = []
    if request.method == "POST":
        for key, value in request.POST.items():
            try:
                variation = Variation.objects.get(
                    product=product, variation_category__iexact=key, variation_value__iexact=value
                )
                product_variation.append(variation)
            except:
                pass

    cart_items = CartItem.objects.filter(product=product, cart=cart)

    # Ensure the exact matching item is removed
    for cart_item in cart_items:
        existing_variations = list(cart_item.variations.all())

        if existing_variations == product_variation:
            cart_item.delete()
            return redirect('cart')  # Ensure only the matching item is deleted

    return redirect('cart')


def cart(request, total=0, quantity=0, cart_items=None):
    try:
        cart = Cart.objects.get(cart_id=_cart_id(request))
        cart_items = CartItem.objects.filter(cart=cart, is_active=True)
        for cart_item in cart_items:
            total += cart_item.product.price * cart_item.quantity
            quantity += cart_item.quantity

        shipping = (20 * total) / 100
        grand_total = total + shipping
    except ObjectDoesNotExist:
        cart_items = []
        shipping = 0
        grand_total = 0

    context = {
        'total': total,
        'quantity': quantity,
        'cart_items': cart_items,
        'shipping': shipping,
        'grand_total': grand_total,
    }
    return render(request, 'store/cart.html', context)
