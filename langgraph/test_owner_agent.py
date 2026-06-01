"""Local tests for the owner LangGraph agent."""

from owner import owner_backend_client
from owner.nodes import owner_router as owner_router_module
from owner.owner_memory import owner_sessions
from owner.owner_runner import run_owner_chat


OWNER_ID = "owner-1"
SHOP = {"id": "shop-1", "name": "Beauty Shop Casa"}
PRODUCT = {"id": "product-1", "name": "Hair Oil", "price": 99, "stock": 10, "available": True}
ORDER = {"id": "123", "status": "pending", "total_price": 99, "items": []}


class BackendMock:
    def __init__(self):
        self.calls = []
        self.shops = [dict(SHOP)]
        self.products = [dict(PRODUCT)]

    def get_owner_shops(self, owner_id):
        self.calls.append(("get_owner_shops", owner_id))
        return {"shops": self.shops}

    def get_shop_products(self, shop_id):
        self.calls.append(("get_shop_products", shop_id))
        return {"products": self.products}

    def create_product(self, shop_id, product_data):
        self.calls.append(("create_product", shop_id, product_data))
        product = {**PRODUCT, **product_data, "id": f"product-{len(self.products) + 1}"}
        self.products.append(product)
        return {"message": "Product created by backend", "product": product}

    def update_product(self, shop_id, product_id, update_data):
        self.calls.append(("update_product", shop_id, product_id, update_data))
        product = self._find_product(product_id)
        product.update(update_data)
        return {"message": "Product updated by backend", "product": product}

    def update_product_stock(self, shop_id, product_id, stock_update):
        self.calls.append(("update_product_stock", shop_id, product_id, stock_update))
        product = self._find_product(product_id)
        quantity = stock_update["quantity"]
        if stock_update["operation"] == "set":
            stock = quantity
        elif stock_update["operation"] == "increase":
            stock = int(product.get("stock") or 0) + quantity
        else:
            stock = max(0, int(product.get("stock") or 0) - quantity)
        product["stock"] = stock
        product["available"] = stock > 0
        return {"message": "Stock updated by backend", "product": product}

    def update_product_price(self, shop_id, product_id, price):
        self.calls.append(("update_product_price", shop_id, product_id, price))
        product = self._find_product(product_id)
        product["price"] = price
        return {"message": "Price updated by backend", "product": product}

    def get_product(self, shop_id, product_id):
        self.calls.append(("get_product", shop_id, product_id))
        return {"product": self._find_product(product_id)}

    def delete_product(self, shop_id, product_id):
        self.calls.append(("delete_product", shop_id, product_id))
        product = self._find_product(product_id)
        self.products = [item for item in self.products if item.get("id") != product.get("id")]
        return {"message": "Product deleted by backend", "product": product}

    def get_shop_orders(self, shop_id, status=None):
        self.calls.append(("get_shop_orders", shop_id, status))
        return {"orders": [{**ORDER, "status": status or ORDER["status"]}]}

    def update_order_status(self, order_id, status):
        self.calls.append(("update_order_status", order_id, status))
        return {"message": "Order status updated by backend"}

    def _find_product(self, product_id):
        for product in self.products:
            if product.get("id") == product_id or product.get("name") == product_id:
                return product
        return self.products[0]


def install_backend_mock(mock: BackendMock):
    originals = {
        "get_owner_shops": owner_backend_client.get_owner_shops,
        "get_shop_products": owner_backend_client.get_shop_products,
        "create_product": owner_backend_client.create_product,
        "update_product": owner_backend_client.update_product,
        "update_product_stock": owner_backend_client.update_product_stock,
        "update_product_price": owner_backend_client.update_product_price,
        "get_product": owner_backend_client.get_product,
        "delete_product": owner_backend_client.delete_product,
        "get_shop_orders": owner_backend_client.get_shop_orders,
        "update_order_status": owner_backend_client.update_order_status,
        "route_with_llm": owner_router_module.route_with_llm,
    }
    owner_backend_client.get_owner_shops = mock.get_owner_shops
    owner_backend_client.get_shop_products = mock.get_shop_products
    owner_backend_client.create_product = mock.create_product
    owner_backend_client.update_product = mock.update_product
    owner_backend_client.update_product_stock = mock.update_product_stock
    owner_backend_client.update_product_price = mock.update_product_price
    owner_backend_client.get_product = mock.get_product
    owner_backend_client.delete_product = mock.delete_product
    owner_backend_client.get_shop_orders = mock.get_shop_orders
    owner_backend_client.update_order_status = mock.update_order_status
    owner_router_module.route_with_llm = lambda state, use_llm=False: None
    return originals


def restore_backend(originals):
    for name, value in originals.items():
        if name == "route_with_llm":
            owner_router_module.route_with_llm = value
        else:
            setattr(owner_backend_client, name, value)


def reset_owner_memory():
    owner_sessions.pop(OWNER_ID, None)


def assert_call(mock: BackendMock, name: str):
    assert any(call[0] == name for call in mock.calls), mock.calls


def product_named(mock: BackendMock, name: str) -> dict:
    matches = [product for product in mock.products if product.get("name") == name]
    assert matches, mock.products
    return matches[-1]


def run_tests():
    mock = BackendMock()
    originals = install_backend_mock(mock)
    try:
        reset_owner_memory()
        result = run_owner_chat(OWNER_ID, "show my shops")
        assert result["intent"] == "list_shops", result
        assert "Beauty Shop Casa" in result["response"], result

        result = run_owner_chat(OWNER_ID, "select Beauty Shop Casa")
        assert result["intent"] == "select_shop", result
        assert result["selected_shop_id"] == "shop-1", result
        assert result["current_shop_id"] == "shop-1", result

        reset_owner_memory()
        run_owner_chat(OWNER_ID, "show my shops")
        result = run_owner_chat(OWNER_ID, "Your shops: 1. Beauty Shop Casa")
        assert result["intent"] == "select_shop", result
        assert result["selected_shop_id"] == "shop-1", result

        reset_owner_memory()
        result = run_owner_chat(OWNER_ID, "show products")
        assert result["intent"] == "list_products", result
        assert result["current_shop_id"] == "shop-1", result
        assert "Hair Oil" in result["response"], result

        run_owner_chat(OWNER_ID, "select Beauty Shop Casa")
        result = run_owner_chat(OWNER_ID, "show products")
        assert result["intent"] == "list_products", result
        assert result["current_shop_id"] == "shop-1", result
        assert "Hair Oil" in result["response"], result
        assert_call(mock, "get_shop_products")

        result = run_owner_chat(OWNER_ID, "add product Hair Oil price 99 stock 10 category Hair Care")
        assert result["intent"] == "create_product", result
        assert "I added Hair Oil" in result["response"], result
        create_call = [call for call in mock.calls if call[0] == "create_product"][-1]
        assert create_call[1] == "shop-1", create_call
        assert create_call[2]["name"] == "Hair Oil", create_call
        assert create_call[2]["price"] == 99, create_call
        assert create_call[2]["stock"] == 10, create_call
        assert create_call[2]["category"] == "Hair Care", create_call

        result = run_owner_chat(OWNER_ID, "add product Hair Oil stock 10 category Hair Care")
        assert result["intent"] == "create_product", result
        assert result["response"] == "What price should I set for Hair Oil?", result
        mock.products = [dict(PRODUCT)]

        result = run_owner_chat(OWNER_ID, "set Hair Oil stock to 20")
        assert result["intent"] == "update_stock", result
        assert result["response"] == "Done. Hair Oil stock is now 20.", result
        stock_call = [call for call in mock.calls if call[0] == "update_product_stock"][-1]
        assert stock_call[1] == "shop-1", stock_call
        assert stock_call[2] == "product-1", stock_call
        assert stock_call[3]["operation"] == "set", stock_call
        assert stock_call[3]["quantity"] == 20, stock_call

        result = run_owner_chat(OWNER_ID, "change Hair Oil price to 120")
        assert result["intent"] == "update_price", result
        assert result["response"] == "Done. The Hair Oil price is now 120 DH.", result
        price_call = [call for call in mock.calls if call[0] == "update_product_price"][-1]
        assert price_call[1:] == ("shop-1", "product-1", 120.0), price_call

        price_calls_before = len([call for call in mock.calls if call[0] == "update_product_price"])
        result = run_owner_chat(OWNER_ID, "change Hair Oil price to 10")
        assert result["intent"] == "update_price", result
        assert "Please confirm" in result["response"], result
        price_calls_after = len([call for call in mock.calls if call[0] == "update_product_price"])
        assert price_calls_after == price_calls_before, mock.calls

        mock.products = [PRODUCT, {"id": "product-2", "name": "Hair Oil Plus", "price": 149, "stock": 3, "available": True}]
        result = run_owner_chat(OWNER_ID, "update stock of Hair to 5")
        assert result["intent"] == "update_stock", result
        assert "multiple matching products" in result["response"], result
        mock.products = [PRODUCT]

        result = run_owner_chat(OWNER_ID, "show pending orders")
        assert result["intent"] == "list_orders", result
        orders_call = [call for call in mock.calls if call[0] == "get_shop_orders"][-1]
        assert orders_call == ("get_shop_orders", "shop-1", "pending"), orders_call

        result = run_owner_chat(OWNER_ID, "mark order 123 as delivered")
        assert result["intent"] == "update_order_status", result
        assert result["response"] == "Order status updated by backend", result
        status_call = [call for call in mock.calls if call[0] == "update_order_status"][-1]
        assert status_call == ("update_order_status", "123", "delivered"), status_call

        result = run_owner_chat(OWNER_ID, "add 3 units to Hair Oil")
        assert result["intent"] == "update_stock", result
        stock_call = [call for call in mock.calls if call[0] == "update_product_stock"][-1]
        assert stock_call[3]["operation"] == "increase", stock_call
        assert stock_call[3]["quantity"] == 3, stock_call

        result = run_owner_chat(OWNER_ID, "make Hair Oil unavailable")
        assert result["intent"] == "mark_unavailable", result
        update_call = [call for call in mock.calls if call[0] == "update_product"][-1]
        assert update_call[3]["available"] is False, update_call

        result = run_owner_chat(OWNER_ID, "delete Hair Oil")
        assert result["intent"] == "delete_product", result
        assert "Please confirm" in result["response"], result
        assert not any(call[0] == "delete_product" for call in mock.calls), mock.calls

        result = run_owner_chat(OWNER_ID, "confirm")
        assert result["intent"] == "delete_product", result
        assert "Deleted Hair Oil" in result["response"], result
        assert_call(mock, "delete_product")

        result = run_owner_chat(OWNER_ID, "make the dashboard magical")
        assert result["intent"] == "unknown", result
        assert result["response"], result
    finally:
        restore_backend(originals)
        reset_owner_memory()


def run_owner_message_example_tests():
    mock = BackendMock()
    originals = install_backend_mock(mock)
    try:
        reset_owner_memory()
        mock.products = [
            {"id": "shoes-1", "name": "Nike shoes", "price": 500, "stock": 12, "available": True},
            {"id": "dress-1", "name": "red dress", "price": 350, "stock": 2, "available": True},
            {"id": "jacket-1", "name": "blue jacket", "price": 450, "stock": 4, "available": True},
            {"id": "shirt-1", "name": "white t-shirt", "price": 120, "stock": 7, "available": True},
            {"id": "cap-1", "name": "black cap", "price": 80, "stock": 0, "available": False},
        ]

        run_owner_chat(OWNER_ID, "select Beauty Shop Casa")
        result = run_owner_chat(OWNER_ID, "Add a black hoodie for 299 DH, sizes M L XL, stock 10")
        assert result["intent"] == "create_product", result
        created = product_named(mock, "black hoodie")
        assert created["price"] == 299, created
        assert created["stock"] == 10, created
        assert created["variants"] == ["M", "L", "XL", "black"], created

        result = run_owner_chat(OWNER_ID, "Change the price of the black hoodie to 249 DH")
        assert result["intent"] == "update_price", result
        assert product_named(mock, "black hoodie")["price"] == 249, mock.products

        result = run_owner_chat(OWNER_ID, "Update stock of Nike shoes to 5")
        assert result["intent"] == "update_stock", result
        assert product_named(mock, "Nike shoes")["stock"] == 5, mock.products

        delete_calls_before = len([call for call in mock.calls if call[0] == "delete_product"])
        result = run_owner_chat(OWNER_ID, "Delete the red dress")
        assert result["intent"] == "delete_product", result
        assert "Please confirm" in result["response"], result
        delete_calls_after = len([call for call in mock.calls if call[0] == "delete_product"])
        assert delete_calls_before == delete_calls_after, mock.calls

        result = run_owner_chat(OWNER_ID, "confirm")
        assert result["intent"] == "delete_product", result
        assert not [product for product in mock.products if product.get("name") == "red dress"], mock.products

        result = run_owner_chat(OWNER_ID, "Make the blue jacket unavailable")
        assert result["intent"] == "mark_unavailable", result
        assert product_named(mock, "blue jacket")["available"] is False, mock.products

        result = run_owner_chat(OWNER_ID, "Add 3 units to the white t-shirt")
        assert result["intent"] == "update_stock", result
        assert product_named(mock, "white t-shirt")["stock"] == 10, mock.products

        result = run_owner_chat(OWNER_ID, "Rename black hoodie to oversized black hoodie")
        assert result["intent"] == "update_product", result
        assert product_named(mock, "oversized black hoodie"), mock.products

        result = run_owner_chat(OWNER_ID, "Show me all products")
        assert result["intent"] == "list_products", result
        assert "oversized black hoodie" in result["response"].lower(), result

        result = run_owner_chat(OWNER_ID, "Which products are out of stock?")
        assert result["intent"] == "list_products", result
        assert "black cap" in result["response"].lower(), result
        assert "nike shoes" not in result["response"].lower(), result
    finally:
        restore_backend(originals)
        reset_owner_memory()


def run_current_product_followup_tests():
    mock = BackendMock()
    originals = install_backend_mock(mock)
    try:
        reset_owner_memory()
        mock.products = [
            {"id": "hoodie-1", "name": "black hoodie", "price": 299, "stock": 10, "available": True},
            {"id": "shoes-1", "name": "Nike shoes", "price": 500, "stock": 12, "available": True},
            {"id": "dress-1", "name": "red dress", "price": 350, "stock": 2, "available": True},
        ]

        result = run_owner_chat(OWNER_ID, "what is current product?")
        assert result["intent"] == "list_products", result
        assert "black hoodie" in result["response"].lower(), result

        result = run_owner_chat(OWNER_ID, "change price of first product to 249 DH")
        assert result["intent"] == "update_price", result
        assert product_named(mock, "black hoodie")["price"] == 249, mock.products
        assert product_named(mock, "Nike shoes")["price"] == 500, mock.products

        price_call = [call for call in mock.calls if call[0] == "update_product_price"][-1]
        assert price_call == ("update_product_price", "shop-1", "hoodie-1", 249.0), price_call

        result = run_owner_chat(OWNER_ID, "show products")
        assert "black hoodie" in result["response"].lower(), result
        assert "249" in result["response"], result
    finally:
        restore_backend(originals)
        reset_owner_memory()


def run_more_owner_intent_tests():
    mock = BackendMock()
    originals = install_backend_mock(mock)
    try:
        reset_owner_memory()
        mock.products = [
            {"id": "hoodie-1", "name": "black hoodie", "price": 300, "stock": 10, "available": True},
            {"id": "sneaker-1", "name": "white sneakers", "price": 600, "stock": 8, "available": True},
            {"id": "bag-1", "name": "leather bag", "price": 450, "stock": 3, "available": True},
            {"id": "hat-1", "name": "green hat", "price": 90, "stock": 0, "available": False},
        ]

        run_owner_chat(OWNER_ID, "select Beauty Shop Casa")
        result = run_owner_chat(OWNER_ID, "add red dress 350 DH stock 4 sizes S M category dresses")
        assert result["intent"] == "create_product", result
        created = product_named(mock, "red dress")
        assert created["price"] == 350, created
        assert created["stock"] == 4, created
        assert created["category"] == "dresses", created
        assert created["variants"] == ["S", "M", "red"], created

        result = run_owner_chat(OWNER_ID, "add product blue jeans stock 6")
        assert result["intent"] == "create_product", result
        assert result["response"] == "What price should I set for blue jeans?", result
        assert not [product for product in mock.products if product.get("name") == "blue jeans"], mock.products

        result = run_owner_chat(OWNER_ID, "show black hoodie")
        assert result["intent"] == "get_product", result
        assert "black hoodie" in result["response"].lower(), result
        assert "300" in result["response"], result

        mock.products.append(
            {
                "id": "samba-1",
                "name": "Adidas Samba OG0",
                "price": 1000,
                "stock": 4,
                "available": True,
                "variants": ["White 40", "White 41", "Black 42"],
            }
        )
        result = run_owner_chat(OWNER_ID, "what is the price of - Adidas Samba OG0")
        assert result["intent"] == "get_product", result
        assert result["response"] == "The price of Adidas Samba OG0 is 1000 DH.", result
        assert "size" not in result["response"].lower(), result
        assert "color" not in result["response"].lower(), result

        result = run_owner_chat(OWNER_ID, "rename white sneakers to white running sneakers")
        assert result["intent"] == "update_product", result
        assert product_named(mock, "white running sneakers")["id"] == "sneaker-1", mock.products

        result = run_owner_chat(OWNER_ID, "change price of white running sneakers to 650 DH")
        assert result["intent"] == "update_price", result
        assert product_named(mock, "white running sneakers")["price"] == 650, mock.products

        result = run_owner_chat(OWNER_ID, "update stock of leather bag to 9")
        assert result["intent"] == "update_stock", result
        assert product_named(mock, "leather bag")["stock"] == 9, mock.products

        result = run_owner_chat(OWNER_ID, "add 2 units to leather bag")
        assert result["intent"] == "update_stock", result
        assert product_named(mock, "leather bag")["stock"] == 11, mock.products

        result = run_owner_chat(OWNER_ID, "decrease leather bag stock by 4")
        assert result["intent"] == "update_stock", result
        assert product_named(mock, "leather bag")["stock"] == 7, mock.products

        stock_calls_before = len([call for call in mock.calls if call[0] == "update_product_stock"])
        result = run_owner_chat(OWNER_ID, "set leather bag stock to 0")
        assert result["intent"] == "update_stock", result
        assert "Please confirm" in result["response"], result
        stock_calls_after = len([call for call in mock.calls if call[0] == "update_product_stock"])
        assert stock_calls_after == stock_calls_before, mock.calls

        result = run_owner_chat(OWNER_ID, "confirm")
        assert result["intent"] == "update_stock", result
        assert product_named(mock, "leather bag")["stock"] == 0, mock.products
        assert product_named(mock, "leather bag")["available"] is False, mock.products

        result = run_owner_chat(OWNER_ID, "make black hoodie unavailable")
        assert result["intent"] == "mark_unavailable", result
        assert product_named(mock, "black hoodie")["available"] is False, mock.products

        result = run_owner_chat(OWNER_ID, "show products")
        assert result["intent"] == "list_products", result
        assert "black hoodie" in result["response"].lower(), result

        result = run_owner_chat(OWNER_ID, "which products are out of stock?")
        assert result["intent"] == "list_products", result
        assert "leather bag" in result["response"].lower(), result
        assert "green hat" in result["response"].lower(), result
        assert "white running sneakers" not in result["response"].lower(), result

        result = run_owner_chat(OWNER_ID, "show green hat")
        assert result["intent"] == "get_product", result
        assert "green hat" in result["response"].lower(), result

        delete_calls_before = len([call for call in mock.calls if call[0] == "delete_product"])
        result = run_owner_chat(OWNER_ID, "delete it")
        assert result["intent"] == "delete_product", result
        assert "Please confirm" in result["response"], result
        assert len([call for call in mock.calls if call[0] == "delete_product"]) == delete_calls_before, mock.calls

        result = run_owner_chat(OWNER_ID, "confirm")
        assert result["intent"] == "delete_product", result
        assert not [product for product in mock.products if product.get("name") == "green hat"], mock.products

        mock.products.append({"id": "hoodie-2", "name": "black hoodie premium", "price": 500, "stock": 5, "available": True})
        price_calls_before = len([call for call in mock.calls if call[0] == "update_product_price"])
        result = run_owner_chat(OWNER_ID, "change hoodie price to 250")
        assert result["intent"] == "update_price", result
        assert "multiple matching products" in result["response"], result
        assert len([call for call in mock.calls if call[0] == "update_product_price"]) == price_calls_before, mock.calls

        result = run_owner_chat(OWNER_ID, "please optimize my whole store")
        assert result["intent"] == "unknown", result
        assert result["response"], result
    finally:
        restore_backend(originals)
        reset_owner_memory()


def run_missing_create_fields_followup_tests():
    mock = BackendMock()
    originals = install_backend_mock(mock)
    try:
        reset_owner_memory()
        mock.products = []

        result = run_owner_chat(OWNER_ID, "i need add some product")
        assert result["intent"] == "create_product", result
        assert result["response"].startswith("Please select a shop first."), result
        assert not mock.products, mock.products

        result = run_owner_chat(OWNER_ID, "Beauty Shop Casa.")
        assert result["intent"] == "create_product", result
        assert result["selected_shop_id"] == "shop-1", result
        assert result["response"] == "Selected shop: Beauty Shop Casa.\n\nWhat is the product name?", result

        create_calls_before = len([call for call in mock.calls if call[0] == "create_product"])
        result = run_owner_chat(OWNER_ID, "add red dress")
        assert result["intent"] == "create_product", result
        assert result["response"] == "What price should I set for red dress?", result
        assert len([call for call in mock.calls if call[0] == "create_product"]) == create_calls_before, mock.calls

        result = run_owner_chat(OWNER_ID, "350 DH stock 4 sizes S M")
        assert result["intent"] == "create_product", result
        assert "i added red dress" in result["response"].lower(), result
        created = product_named(mock, "red dress")
        assert created["price"] == 350, created
        assert created["stock"] == 4, created
        assert set(created["variants"]) == {"red", "S", "M"}, created

        result = run_owner_chat(OWNER_ID, "show products")
        assert result["intent"] == "list_products", result
        assert "red dress" in result["response"].lower(), result

        result = run_owner_chat(OWNER_ID, "add product blue jeans stock 6")
        assert result["intent"] == "create_product", result
        assert result["response"] == "What price should I set for blue jeans?", result
        assert not [product for product in mock.products if product.get("name") == "blue jeans"], mock.products

        result = run_owner_chat(OWNER_ID, "price 220 DH category jeans")
        assert result["intent"] == "create_product", result
        created = product_named(mock, "blue jeans")
        assert created["price"] == 220, created
        assert created["stock"] == 6, created
        assert created["category"] == "jeans", created

        mock.products = []
        reset_owner_memory()
        run_owner_chat(OWNER_ID, "select Beauty Shop Casa")
        result = run_owner_chat(OWNER_ID, "i need add some product")
        assert result["intent"] == "create_product", result
        assert result["response"] == "What is the product name?", result
        assert not mock.products, mock.products

        result = run_owner_chat(OWNER_ID, "name of product is Tshirt and price is 20$")
        assert result["intent"] == "create_product", result
        assert "i added Tshirt".lower() in result["response"].lower(), result
        created = product_named(mock, "Tshirt")
        assert created["price"] == 20, created

        result = run_owner_chat(OWNER_ID, "create new product called description price 20")
        assert result["intent"] == "create_product", result
        assert result["response"] == "Done. I added description for 20 DH.", result
        created = product_named(mock, "description")
        assert created["price"] == 20, created

        mock.products = []
        reset_owner_memory()
        run_owner_chat(OWNER_ID, "select Beauty Shop Casa")
        create_calls_before = len([call for call in mock.calls if call[0] == "create_product"])
        result = run_owner_chat(OWNER_ID, "add black hoodie")
        assert result["intent"] == "create_product", result
        assert result["response"] == "What price should I set for black hoodie?", result
        assert len([call for call in mock.calls if call[0] == "create_product"]) == create_calls_before, mock.calls

        result = run_owner_chat(OWNER_ID, "250 MAD")
        assert result["intent"] == "create_product", result
        assert result["response"] == "Done. I added black hoodie for 250 MAD.", result
        created = product_named(mock, "black hoodie")
        assert created["price"] == 250, created

        mock.products = []
        reset_owner_memory()
        run_owner_chat(OWNER_ID, "select Beauty Shop Casa")
        result = run_owner_chat(OWNER_ID, "i need add new products here")
        assert result["intent"] == "create_product", result
        assert result["response"] == "What is the product name?", result

        result = run_owner_chat(OWNER_ID, "Tshirt K4")
        assert result["intent"] == "create_product", result
        assert result["response"] == "What price should I set for Tshirt K4?", result
        assert not [product for product in mock.products if product.get("name") == "Tshirt K4"], mock.products

        result = run_owner_chat(OWNER_ID, "250 MAD")
        assert result["intent"] == "create_product", result
        assert result["response"] == "Done. I added Tshirt K4 for 250 MAD.", result
        created = product_named(mock, "Tshirt K4")
        assert created["price"] == 250, created

        result = run_owner_chat(OWNER_ID, "i need also add description")
        assert result["intent"] == "update_product", result
        assert result["response"] == "Sure. Send me the description for Tshirt K4.", result
        assert result["pending_field"]["field"] == "description", result
        assert result["pending_field"]["target"]["id"] == created["id"], result

        description = "this is summer Tshirt for kids available in white and blue color"
        result = run_owner_chat(OWNER_ID, description)
        assert result["intent"] == "update_product", result
        assert result["response"] == "Done. I updated the description for Tshirt K4.", result
        assert result["pending_field"] is None, result
        assert product_named(mock, "Tshirt K4")["description"] == description, mock.products

        result = run_owner_chat(OWNER_ID, "add description luxury watch for men")
        assert result["intent"] == "update_product", result
        assert result["response"] == "Done. I updated the description for Tshirt K4.", result
        assert product_named(mock, "Tshirt K4")["description"] == "luxury watch for men", mock.products

        result = run_owner_chat(OWNER_ID, "also i need add a description")
        assert result["intent"] == "update_product", result
        assert result["response"] == "Sure. Send me the description for Tshirt K4.", result

        original_llm_router = owner_router_module.route_with_llm
        try:
            mock.products = [{"id": "old-1", "name": "old shirt", "price": 100, "stock": 2, "available": True}]
            reset_owner_memory()
            run_owner_chat(OWNER_ID, "select Beauty Shop Casa")
            result = run_owner_chat(OWNER_ID, "i need add new products")
            assert result["response"] == "What is the product name?", result

            def fake_update_router(state, use_llm=False):
                if state["message"] == "Tshirst U90":
                    return {
                        "intent": "update_product",
                        "product_reference": "Tshirst U90",
                        "action": "update_product",
                        "fields": {"name": "Tshirst U90"},
                        "stock_operation": {"type": None, "quantity": None},
                        "language": "english",
                        "confidence": 0.91,
                        "requires_confirmation": False,
                        "missing_fields": [],
                        "notes": None,
                    }
                return None

            owner_router_module.route_with_llm = fake_update_router
            result = run_owner_chat(OWNER_ID, "Tshirst U90")
            assert result["intent"] == "create_product", result
            assert result["response"] == "What price should I set for Tshirst U90?", result
            assert not [product for product in mock.products if product.get("name") == "Tshirst U90"], mock.products

            reset_owner_memory()
            run_owner_chat(OWNER_ID, "select Beauty Shop Casa")
            result = run_owner_chat(OWNER_ID, "i need add new products")
            assert result["response"] == "What is the product name?", result

            def fake_select_shop_router(state, use_llm=False):
                if state["message"] == "TshirtG4":
                    return {
                        "intent": "select_shop",
                        "product_reference": None,
                        "action": None,
                        "fields": {"shop_query": "TshirtG4"},
                        "stock_operation": {"type": None, "quantity": None},
                        "language": "english",
                        "confidence": 0.91,
                        "requires_confirmation": False,
                        "missing_fields": [],
                        "notes": None,
                    }
                return None

            owner_router_module.route_with_llm = fake_select_shop_router
            result = run_owner_chat(OWNER_ID, "TshirtG4")
            assert result["intent"] == "create_product", result
            assert result["response"] == "What price should I set for TshirtG4?", result
        finally:
            owner_router_module.route_with_llm = original_llm_router

        mock.products = [{"id": "hoodie-1", "name": "black hoodie", "price": 200, "stock": 5, "available": True}]
        reset_owner_memory()
        run_owner_chat(OWNER_ID, "select Beauty Shop Casa")
        result = run_owner_chat(OWNER_ID, "add red dress")
        assert result["intent"] == "create_product", result
        assert result["response"] == "What price should I set for red dress?", result

        result = run_owner_chat(OWNER_ID, "show products")
        assert result["intent"] == "list_products", result
        assert "black hoodie" in result["response"].lower(), result
        assert "red dress" not in result["response"].lower(), result
        assert any("Cancelled pending create due to new intent: list_products" in step for step in result["steps"]), result
    finally:
        restore_backend(originals)
        reset_owner_memory()


def run_pending_shop_action_tests():
    mock = BackendMock()
    originals = install_backend_mock(mock)
    try:
        mock.shops = [
            {"id": "urban-fit", "name": "Urban Fit"},
            {"id": "shoes-shop", "name": "Shoes"},
        ]
        mock.products = [
            {"id": "hoodie-1", "name": "black hoodie", "price": 200, "stock": 5, "available": True},
            {"id": "samba-1", "name": "Adidas Samba OG0", "price": 900, "stock": 4, "available": True},
        ]

        reset_owner_memory()
        result = run_owner_chat(OWNER_ID, "what are my products")
        assert result["intent"] == "list_products", result
        assert result["pending_action"]["intent"] == "list_products", result
        assert "Which shop would you like to manage?" in result["response"], result
        assert "Urban Fit" in result["response"], result

        result = run_owner_chat(OWNER_ID, "Urban Fit")
        assert result["intent"] == "list_products", result
        assert result["selected_shop_name"] == "Urban Fit", result
        assert result["pending_action"] is None, result
        assert result["response"].startswith("Selected shop: Urban Fit.\n\n"), result
        assert "black hoodie" in result["response"].lower(), result

        reset_owner_memory()
        run_owner_chat(OWNER_ID, "show my shops")
        result = run_owner_chat(OWNER_ID, "Urban Fit")
        assert result["intent"] == "select_shop", result
        assert result["response"] == "Selected shop: Urban Fit.", result

        reset_owner_memory()
        create_calls_before = len([call for call in mock.calls if call[0] == "create_product"])
        result = run_owner_chat(OWNER_ID, "add black hoodie price 200")
        assert result["intent"] == "create_product", result
        assert result["pending_action"]["intent"] == "create_product", result
        assert len([call for call in mock.calls if call[0] == "create_product"]) == create_calls_before, mock.calls

        result = run_owner_chat(OWNER_ID, "Urban Fit")
        assert result["intent"] == "create_product", result
        assert result["pending_action"] is None, result
        assert result["response"].startswith("Selected shop: Urban Fit.\n\nDone. I added black hoodie"), result
        assert product_named(mock, "black hoodie")["price"] == 200, mock.products

        reset_owner_memory()
        mock.products = [
            {"id": "hoodie-1", "name": "black hoodie", "price": 200, "stock": 5, "available": True},
            {"id": "samba-1", "name": "Adidas Samba OG0", "price": 900, "stock": 4, "available": True},
        ]
        price_calls_before = len([call for call in mock.calls if call[0] == "update_product_price"])
        result = run_owner_chat(OWNER_ID, "set price of black hoodie to 250")
        assert result["intent"] == "update_price", result
        assert result["pending_action"]["intent"] == "update_price", result
        pending_payload = result["pending_action"]["router_output"]
        assert pending_payload["product_reference"] == "black hoodie", result
        assert pending_payload["fields"]["price"] == 250.0, result
        assert len([call for call in mock.calls if call[0] == "update_product_price"]) == price_calls_before, mock.calls

        result = run_owner_chat(OWNER_ID, "Urban Fit")
        assert result["intent"] == "update_price", result
        assert result["pending_action"] is None, result
        assert result["response"].startswith("Selected shop: Urban Fit.\n\nDone. The black hoodie price is now 250 DH."), result
        assert product_named(mock, "black hoodie")["price"] == 250, mock.products
    finally:
        restore_backend(originals)
        reset_owner_memory()


def run_llm_first_router_order_test():
    original_route_with_llm = owner_router_module.route_with_llm
    try:
        state = {
            "owner_id": OWNER_ID,
            "message": "show my shops",
            "selected_shop_id": None,
            "selected_shop_name": None,
            "current_shop_id": None,
            "current_shop_name": None,
            "last_shops": [],
            "intent": None,
            "response": None,
            "steps": [],
            "extracted_data": {},
            "router_output": {},
            "pending_confirmation": {},
            "pending_product_create": {},
            "pending_action": None,
            "pending_field": None,
            "response_prefix": None,
            "last_product": {},
            "last_products": [],
            "confidence": 0.0,
            "needs_clarification": False,
        }

        def fake_llm_router(_state, use_llm=False):
            return {
                "intent": "help",
                "product_reference": None,
                "action": None,
                "fields": {},
                "stock_operation": {"type": None, "quantity": None},
                "language": "english",
                "confidence": 0.91,
                "requires_confirmation": False,
                "missing_fields": [],
                "notes": None,
            }

        owner_router_module.route_with_llm = fake_llm_router
        result = owner_router_module.owner_router(state)
        assert result["intent"] == "help", result
        assert "Owner router used local LLM" in result["steps"], result
    finally:
        owner_router_module.route_with_llm = original_route_with_llm


if __name__ == "__main__":
    run_tests()
    run_owner_message_example_tests()
    run_current_product_followup_tests()
    run_more_owner_intent_tests()
    run_missing_create_fields_followup_tests()
    run_pending_shop_action_tests()
    run_llm_first_router_order_test()
    print("owner agent tests passed")
