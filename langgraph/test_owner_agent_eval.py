"""Owner-agent behavior evals for conversational product-management flows.

This file is intentionally separate from test_owner_agent.py. It is an eval
report: passing cases show current coverage, known gaps document desired
behavior that is not implemented yet.
"""

from dataclasses import dataclass
from typing import Callable

from test_owner_agent import BackendMock, OWNER_ID, install_backend_mock, product_named, restore_backend
from owner.owner_memory import owner_sessions
from owner.owner_runner import run_owner_chat


Check = Callable[[BackendMock, dict], None]


@dataclass
class EvalCase:
    number: int
    message: str
    check: Check
    known_gap: bool = False
    note: str = ""


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def response_contains(text: str) -> Check:
    return lambda _mock, result: _assert(text.lower() in result["response"].lower(), result["response"])


def intent_is(intent: str) -> Check:
    return lambda _mock, result: _assert(result["intent"] == intent, str(result))


def and_checks(*checks: Check) -> Check:
    def check(mock: BackendMock, result: dict) -> None:
        for item in checks:
            item(mock, result)

    return check


def product_has(name: str, **fields) -> Check:
    def check(mock: BackendMock, _result: dict) -> None:
        product = product_named(mock, name)
        for key, value in fields.items():
            _assert(product.get(key) == value, f"{name}.{key} expected {value!r}, got {product.get(key)!r}")

    return check


def last_call_is(name: str) -> Check:
    def check(mock: BackendMock, _result: dict) -> None:
        _assert(any(call[0] == name for call in mock.calls), f"missing backend call {name}: {mock.calls}")

    return check


def no_delete_call(mock: BackendMock, _result: dict) -> None:
    _assert(not any(call[0] == "delete_product" for call in mock.calls), f"delete happened too early: {mock.calls}")


def has_pending_confirmation(_mock: BackendMock, result: dict) -> None:
    _assert("confirm" in result["response"].lower(), result["response"])


def shop_selected(name: str) -> Check:
    return lambda _mock, result: _assert(result.get("selected_shop_name") == name, str(result))


def run_eval() -> list[tuple[EvalCase, str, str]]:
    owner_sessions.pop(OWNER_ID, None)
    mock = BackendMock()
    mock.shops = [{"id": "urban-fit", "name": "Urban Fit"}, {"id": "shoes-shop", "name": "Shoes"}]
    mock.products = []
    originals = install_backend_mock(mock)

    cases = [
        EvalCase(1, "i need add a new product", and_checks(intent_is("create_product"), response_contains("select a shop"))),
        EvalCase(2, "shoes", and_checks(intent_is("create_product"), shop_selected("Shoes"), response_contains("product name"))),
        EvalCase(3, "Rolexj", and_checks(intent_is("create_product"), response_contains("price"))),
        EvalCase(4, "3000 dh", and_checks(intent_is("create_product"), product_has("Rolexj", price=3000.0))),
        EvalCase(5, "what are my products", and_checks(intent_is("list_products"), response_contains("Rolexj"))),
        EvalCase(6, "i need set 10 in stock in Rolexj product", product_has("Rolexj", stock=10), known_gap=True, note="stock phrasing parser is incomplete"),
        EvalCase(7, "also i need add a description", and_checks(intent_is("update_product"), response_contains("description"), response_contains("Rolexj"))),
        EvalCase(8, "luxury watch for men", and_checks(intent_is("update_product"), product_has("Rolexj", description="luxury watch for men"))),
        EvalCase(9, "add description: premium black watch with metal strap", product_has("Rolexj", description="premium black watch with metal strap")),
        EvalCase(10, "change the price", response_contains("price"), known_gap=True, note="pending price field lifecycle is not implemented"),
        EvalCase(11, "set price to 3500 dh", product_has("Rolexj", price=3500.0), known_gap=True, note="active-product price update without explicit product is incomplete"),
        EvalCase(12, "update stock", response_contains("stock"), known_gap=True, note="pending stock field lifecycle is not implemented"),
        EvalCase(13, "set stock to 20", product_has("Rolexj", stock=20), known_gap=True, note="active-product stock update without explicit product is incomplete"),
        EvalCase(14, "make Rolexj unavailable", product_has("Rolexj", available=False)),
        EvalCase(15, "make Rolexj available again", product_has("Rolexj", available=True), known_gap=True, note="available=true path is not implemented"),
        EvalCase(16, "change category to watches", product_has("Rolexj", category="watches"), known_gap=True, note="active product category update is incomplete"),
        EvalCase(17, "set brand to Rolex", product_has("Rolexj", brand="Rolex"), known_gap=True, note="active product brand update is incomplete"),
        EvalCase(18, "delivery time is 2 days", product_has("Rolexj", delivery_time="2 days"), known_gap=True, note="delivery-time field update is incomplete"),
        EvalCase(19, "add colors black and silver", lambda m, _r: _assert({"black", "silver"}.issubset(set(product_named(m, "Rolexj").get("variants", []))), "missing colors"), known_gap=True, note="color/variant update is incomplete"),
        EvalCase(20, "delete Rolexj", and_checks(intent_is("delete_product"), has_pending_confirmation, no_delete_call)),
        EvalCase(21, "delete all products", has_pending_confirmation, known_gap=True, note="bulk destructive delete is not implemented"),
        EvalCase(22, "remove the shop Shoes", has_pending_confirmation, known_gap=True, note="shop deletion intent is not implemented"),
        EvalCase(23, "set Rolexj stock to -5", response_contains("stock cannot be negative"), known_gap=True, note="negative stock validation is not implemented"),
        EvalCase(24, "set Rolexj price to -100", response_contains("price cannot be negative"), known_gap=True, note="negative price validation is not implemented"),
        EvalCase(25, "create product", and_checks(intent_is("create_product"), response_contains("product name"))),
        EvalCase(26, "create product black hoodie", and_checks(intent_is("create_product"), response_contains("price"))),
        EvalCase(27, "250", and_checks(intent_is("create_product"), product_has("black hoodie", price=250.0))),
        EvalCase(28, "create new product description price 20", and_checks(intent_is("create_product"), product_has("description", price=20.0))),
        EvalCase(29, "add a description", response_contains("which product"), known_gap=True, note="no-active-product description clarify path is incomplete"),
        EvalCase(30, "also change it to 4000", product_has("Rolexj", price=4000.0), known_gap=True, note="last_discussed_field price is not tracked"),
        EvalCase(31, "also change it to 15", product_has("Rolexj", stock=15), known_gap=True, note="last_discussed_field stock is not tracked"),
        EvalCase(32, "update Rolexj", lambda _m, result: _assert(any(word in result["response"].lower() for word in ["specify", "clarify"]), result["response"])),
        EvalCase(33, "change Rolexj description", response_contains("description")),
        EvalCase(34, "change description for Rolexj to waterproof luxury watch", product_has("Rolexj", description="waterproof luxury watch"), known_gap=True, note="explicit product description update parser is incomplete"),
        EvalCase(35, "TshirtG4", response_contains("price"), known_gap=True, note="requires pending create context; standalone case follows prior update context"),
        EvalCase(36, "set stock of TshirtG4 to 30", product_has("TshirtG4", stock=30), known_gap=True, note="TshirtG4 product does not exist in this linear eval unless case 35 creates it"),
        EvalCase(37, "what shops do I have", intent_is("list_shops")),
        EvalCase(38, "show me shop summary", intent_is("shop_summary")),
        EvalCase(39, "switch to Urban Fit", and_checks(intent_is("select_shop"), shop_selected("Urban Fit"))),
        EvalCase(40, "add new product to Urban Fit called blue tshirt price 99", product_has("blue tshirt", price=99.0), known_gap=True, note="explicit target shop in create command is incomplete"),
    ]

    results: list[tuple[EvalCase, str, str]] = []
    try:
        for case in cases:
            before_calls = len(mock.calls)
            result = run_owner_chat(OWNER_ID, case.message)
            try:
                case.check(mock, result)
                status = "PASS"
                detail = result["response"]
            except Exception as exc:
                status = "KNOWN_GAP" if case.known_gap else "FAIL"
                detail = f"{exc} | response={result.get('response')!r} | new_calls={mock.calls[before_calls:]}"
            results.append((case, status, detail))
    finally:
        restore_backend(originals)
        owner_sessions.pop(OWNER_ID, None)

    return results


def main() -> None:
    results = run_eval()
    unexpected_failures = [item for item in results if item[1] == "FAIL"]
    for case, status, detail in results:
        note = f" ({case.note})" if case.note else ""
        print(f"{status:9} {case.number:02d}. {case.message}{note}")
        if status != "PASS":
            print(f"          {detail}")
    print()
    print(f"Summary: {sum(1 for _, status, _ in results if status == 'PASS')} pass, "
          f"{sum(1 for _, status, _ in results if status == 'KNOWN_GAP')} known gaps, "
          f"{len(unexpected_failures)} unexpected failures")
    if unexpected_failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
