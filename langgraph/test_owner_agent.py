"""Local tests for the owner LangGraph agent."""

from owner import owner_backend_client
from owner.owner_memory import owner_sessions
from owner.owner_runner import run_owner_chat


OWNER_ID = "owner-1"
SHOP = {"id": "shop-1", "name": "Beauty Shop Casa"}
PRODUCT = {"id": "product-1", "name": "Hair Oil", "price": 99, "stock": 10, "available": True}
ORDER = {"id": "123", "status": "pending", "total_price": 99, "items": []}


class BackendMock:
    def __init__(self):
        self.calls = []

    def get_owner_shops(self, owner_id):
        self.calls.append(("get_owner_shops", owner_id))
        return {"shops": [SHOP]}

    def get_shop_products(self, shop_id):
        self.calls.append(("get_shop_products", shop_id))
        return {"products": [PRODUCT]}

    def create_product(self, shop_id, product_data):
        self.calls.append(("create_product", shop_id, product_data))
        return {"message": "Product created by backend"}

    def update_product(self, shop_id, product_id, update_data):
        self.calls.append(("update_product", shop_id, product_id, update_data))
        return {"message": "Product updated by backend"}

    def update_product_stock(self, shop_id, product_id, stock_update):
        self.calls.append(("update_product_stock", shop_id, product_id, stock_update))
        return {"message": "Stock updated by backend"}

    def update_product_price(self, shop_id, product_id, price):
        self.calls.append(("update_product_price", shop_id, product_id, price))
        return {"message": "Price updated by backend"}

    def get_shop_orders(self, shop_id, status=None):
        self.calls.append(("get_shop_orders", shop_id, status))
        return {"orders": [{**ORDER, "status": status or ORDER["status"]}]}

    def update_order_status(self, order_id, status):
        self.calls.append(("update_order_status", order_id, status))
        return {"message": "Order status updated by backend"}


def install_backend_mock(mock: BackendMock):
    originals = {
        "get_owner_shops": owner_backend_client.get_owner_shops,
        "get_shop_products": owner_backend_client.get_shop_products,
        "create_product": owner_backend_client.create_product,
        "update_product": owner_backend_client.update_product,
        "update_product_stock": owner_backend_client.update_product_stock,
        "update_product_price": owner_backend_client.update_product_price,
        "get_shop_orders": owner_backend_client.get_shop_orders,
        "update_order_status": owner_backend_client.update_order_status,
    }
    owner_backend_client.get_owner_shops = mock.get_owner_shops
    owner_backend_client.get_shop_products = mock.get_shop_products
    owner_backend_client.create_product = mock.create_product
    owner_backend_client.update_product = mock.update_product
    owner_backend_client.update_product_stock = mock.update_product_stock
    owner_backend_client.update_product_price = mock.update_product_price
    owner_backend_client.get_shop_orders = mock.get_shop_orders
    owner_backend_client.update_order_status = mock.update_order_status
    return originals


def restore_backend(originals):
    for name, value in originals.items():
        setattr(owner_backend_client, name, value)


def reset_owner_memory():
    owner_sessions.pop(OWNER_ID, None)


def assert_call(mock: BackendMock, name: str):
    assert any(call[0] == name for call in mock.calls), mock.calls


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
        result = run_owner_chat(OWNER_ID, "show products")
        assert result["intent"] == "list_products", result
        assert "Which shop would you like to manage?" in result["response"], result

        run_owner_chat(OWNER_ID, "select Beauty Shop Casa")
        result = run_owner_chat(OWNER_ID, "show products")
        assert result["intent"] == "list_products", result
        assert result["current_shop_id"] == "shop-1", result
        assert "Hair Oil" in result["response"], result
        assert_call(mock, "get_shop_products")

        result = run_owner_chat(OWNER_ID, "add product Hair Oil price 99 stock 10 category Hair Care")
        assert result["intent"] == "add_product", result
        assert result["response"] == "Product created by backend", result
        create_call = [call for call in mock.calls if call[0] == "create_product"][-1]
        assert create_call[1] == "shop-1", create_call
        assert create_call[2]["name"] == "Hair Oil", create_call
        assert create_call[2]["price"] == 99, create_call
        assert create_call[2]["stock"] == 10, create_call
        assert create_call[2]["category"] == "Hair Care", create_call

        result = run_owner_chat(OWNER_ID, "add product Hair Oil stock 10 category Hair Care")
        assert result["intent"] == "add_product", result
        assert result["response"] == "Please send price.", result

        result = run_owner_chat(OWNER_ID, "set Hair Oil stock to 20")
        assert result["intent"] == "update_stock", result
        assert result["response"] == "Stock updated by backend", result
        stock_call = [call for call in mock.calls if call[0] == "update_product_stock"][-1]
        assert stock_call[1] == "shop-1", stock_call
        assert stock_call[2] == "Hair Oil", stock_call
        assert stock_call[3]["operation"] == "set", stock_call
        assert stock_call[3]["quantity"] == 20, stock_call

        result = run_owner_chat(OWNER_ID, "change Hair Oil price to 120")
        assert result["intent"] == "update_price", result
        assert result["response"] == "Price updated by backend", result
        price_call = [call for call in mock.calls if call[0] == "update_product_price"][-1]
        assert price_call[1:] == ("shop-1", "Hair Oil", 120.0), price_call

        result = run_owner_chat(OWNER_ID, "show pending orders")
        assert result["intent"] == "list_orders", result
        orders_call = [call for call in mock.calls if call[0] == "get_shop_orders"][-1]
        assert orders_call == ("get_shop_orders", "shop-1", "pending"), orders_call

        result = run_owner_chat(OWNER_ID, "mark order 123 as delivered")
        assert result["intent"] == "update_order_status", result
        assert result["response"] == "Order status updated by backend", result
        status_call = [call for call in mock.calls if call[0] == "update_order_status"][-1]
        assert status_call == ("update_order_status", "123", "delivered"), status_call

        result = run_owner_chat(OWNER_ID, "make the dashboard magical")
        assert result["intent"] == "unknown", result
        assert "clarify" in result["response"].lower(), result
    finally:
        restore_backend(originals)
        reset_owner_memory()


if __name__ == "__main__":
    run_tests()
    print("owner agent tests passed")
