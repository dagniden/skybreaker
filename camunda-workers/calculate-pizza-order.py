import asyncio
import os

from pyzeebe import ZeebeWorker, create_insecure_channel


ZEEBE_ADDRESS = os.getenv("ZEEBE_ADDRESS", "localhost:26500")


def calculate_pizza_order(customer: dict, order: dict):
    items = order.get("items", [])

    total_quantity = sum(item.get("quantity", 0) for item in items)
    total_price = sum(
        item.get("quantity", 0) * item.get("price", 0)
        for item in items
    )

    is_vip = customer.get("vip", False)
    discount_percent = 10 if is_vip else 0
    final_price = round(total_price * (100 - discount_percent) / 100, 2)

    distance_km = order.get("distanceKm", 0)
    delivery_allowed = not order.get("delivery", False) or distance_km <= 10

    return {
        "totalQuantity": total_quantity,
        "totalPrice": total_price,
        "discountPercent": discount_percent,
        "finalPrice": final_price,
        "needsApproval": total_quantity > 5 or final_price > 5000,
        "deliveryAllowed": delivery_allowed,
    }


async def main():
    channel = create_insecure_channel(ZEEBE_ADDRESS)
    worker = ZeebeWorker(channel)

    worker.task(
        task_type="calculate-pizza-order",
        variables_to_fetch=["customer", "order"],
    )(calculate_pizza_order)

    print(f"Listening for calculate-pizza-order jobs on {ZEEBE_ADDRESS}")
    await worker.work()


if __name__ == "__main__":
    asyncio.run(main())
