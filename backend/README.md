# Backend

FastAPI backend using a local MongoDB database.

## Run

```bash
cd backend
python -m uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

## Environment

Copy `.env.example` to `.env` and set a strong `JWT_SECRET`.

Default MongoDB:

```text
mongodb://localhost:27017
```

## Endpoints

- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/me`
- `POST /api/shops`
- `GET /api/shops`
- `GET /api/shops/me`
- `GET /api/shops/{shop_id}`
- `PATCH /api/shops/{shop_id}`
- `DELETE /api/shops/{shop_id}`
- `POST /api/shops/{shop_id}/products`
- `GET /api/shops/{shop_id}/products` returns `{ "shop": {}, "products": [] }`
- `GET /api/shops/{shop_id}/products/{product_id}` returns `{ "shop": {}, "product": {} }`
- `PATCH /api/shops/{shop_id}/products/{product_id}`
- `PATCH /api/shops/{shop_id}/products/{product_id}/image`
- `DELETE /api/shops/{shop_id}/products/{product_id}`
- `POST /api/shops/{shop_id}/categories`
- `GET /api/shops/{shop_id}/categories`
- `GET /api/shops/{shop_id}/categories/{category_id}`
- `PATCH /api/shops/{shop_id}/categories/{category_id}`
- `DELETE /api/shops/{shop_id}/categories/{category_id}`
- `POST /api/shops/{shop_id}/orders`
- `GET /api/shops/{shop_id}/orders` returns `{ "shop": {}, "orders": [] }`
- `GET /api/shops/{shop_id}/orders/{order_id}` returns `{ "shop": {}, "order": {} }`
- `PATCH /api/shops/{shop_id}/orders/{order_id}`
- `DELETE /api/shops/{shop_id}/orders/{order_id}`

Protected endpoints read the JWT from the `access_token` HTTP-only cookie. They also accept a `Bearer` token for API clients.

Each owner can create multiple shops. Products, categories, and orders are scoped by shop through the `{shop_id}` path parameter.

Product image uploads use multipart form data with an `image` file field. The backend uploads the image to Supabase S3-compatible storage and saves the public URL in the product `image` field.
