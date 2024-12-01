import os
import time
import json
import random
import string
import requests
from faker import Faker
from datetime import datetime, timedelta
from confluent_kafka import Producer
from concurrent.futures import ThreadPoolExecutor

# START_TIME = datetime.strptime("2025-01-01 10:00:00", "%Y-%m-%d %H:%M:%S")
# END_TIME = datetime.strptime("2025-04-01 18:00:00", "%Y-%m-%d %H:%M:%S")

END_TIME = datetime.now()
START_TIME = END_TIME - timedelta(minutes=30)
TIME_STEP = timedelta(seconds=10)  


fake = Faker()
SESSION_DURATION = 10  # max delay between clicks
CONCURRENT_USERS = 100  # how many user journeys at once

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")

TOPICS = {
    "user": "users",
    "click": "clickstream",
    "transaction": "transactions"
}

producer = Producer({'bootstrap.servers': KAFKA_BROKER})

def delivery_report(err, msg):
    if err is not None:
        print(f"❌ Delivery failed: {err}")
    else:
        print(f"✅ Delivered to {msg.topic()} [{msg.partition()}]")

def get_random_user(timestamp):
    try:
        response = requests.get("https://randomuser.me/api/?nat=in", timeout=3)
        user_data = response.json()['results'][0]
        return {
            "user_id": user_data['login']['uuid'],
            "name": f"{user_data['name']['first']} {user_data['name']['last']}",
            "email": user_data['email'],
            "location": f"{user_data['location']['city']}, {user_data['location']['state']}",
            "registered_at": timestamp.strftime("%Y-%m-%d %H:%M:%S")
        }
    except:
        return {
            "user_id": ''.join(random.choices(string.ascii_letters + string.digits, k=12)),
            "name": fake.name(),
            "email": fake.email(),
            "location": fake.city(),
            "registered_at": timestamp.strftime("%Y-%m-%d %H:%M:%S")
        }

def generate_click_event(user_id, session_id,timestamp):
    return {
        "user_id": user_id,
        "session_id": session_id,
        "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        "page": random.choices(
            ["/home", "/products", "/cart", "/checkout", "/offers"],
            weights=[0.4, 0.2, 0.15, 0.1, 0.15],  
            k=1
        )[0],
        "device": random.choice(["Android", "iOS", "Chrome", "Safari"]),
        "action": random.choice(["click", "scroll", "hover", "navigate"]),
    }

def generate_transaction_event(user_id, session_id,timestamp):
    categories = {
        "Electronics": (500, 5000),
        "Clothing": (300, 1500),
        "Home & Kitchen": (200, 2000),
        "Books": (100, 500),
        "Toys": (150, 800),
        "Beauty": (100, 1000),
        "Sports": (300, 2500)
    }

    num_products = random.randint(1, 3)
    products = []

    for _ in range(num_products):
        category = random.choice(list(categories.keys()))
        price_range = categories[category]
        unit_price = round(random.uniform(*price_range), 2)
        
        products.append({
            "product_id": "PROD" + ''.join(random.choices(string.digits, k=5)),
            "product_category": category,
            "quantity": random.randint(1, 4),
            "unit_price": unit_price
        })

    total_amount = round(
        sum(p["quantity"] * p["unit_price"] for p in products), 2
    )

    return {
        "user_id": user_id,
        "session_id": session_id,
        "transaction_id": "TXN" + ''.join(random.choices(string.digits, k=12)),
        "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        "transaction_amount": total_amount,
        "payment_method": random.choice(["UPI", "credit_card", "paypal","debit_card"]),
        "payment_status": random.choice(["successful", "failed"]),
        "products": products
    }

def send_to_kafka(topic, data):
    producer.produce(topic, value=json.dumps(data), callback=delivery_report)

def simulate_user_journey(timestamp):
    user = get_random_user(timestamp)
    session_id = "SESS" + ''.join(random.choices(string.digits, k=10))

    send_to_kafka(TOPICS['user'], user)
    print(f"\n👤 Sent user: {user['name']} | {user['user_id']}")

    for _ in range(random.randint(3, 6)):
        click = generate_click_event(user['user_id'], session_id,timestamp)
        send_to_kafka(TOPICS['click'], click)
        print(f"🖱️  Click: {click['page']} @ {click['timestamp']}")
        time.sleep(random.uniform(0.5, 2.0))  # smaller delay

    if random.random() < 0.7:
        txn = generate_transaction_event(user['user_id'], session_id,timestamp)
        send_to_kafka(TOPICS['transaction'], txn)
        print(f"💰 Transaction: ₹{txn['transaction_amount']} ({txn['payment_status']})")

if __name__ == "__main__":
    try:
        with ThreadPoolExecutor(max_workers=CONCURRENT_USERS) as executor:
            timestamp = START_TIME
            while timestamp <= END_TIME:
                futures = [executor.submit(simulate_user_journey, timestamp) for _ in range(CONCURRENT_USERS)]
                for f in futures:
                    f.result()
                producer.flush()
                timestamp += TIME_STEP  # advance simulated time
                print("-" * 50)
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        producer.flush()
