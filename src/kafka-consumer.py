from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, to_json, to_timestamp, explode, expr
from pyspark.sql.types import StructType, StringType, DoubleType, ArrayType, IntegerType


import logging
from datetime import datetime
import os

# Setup logging
os.makedirs("logs", exist_ok=True)
log_file = f"logs/consumer_{datetime.now().strftime('%Y-%m-%d_%H')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(log_file, mode='w'),
        logging.StreamHandler()
    ]
)

def log_step(message):
    logging.info(message)

# Schemas
user_schema = StructType() \
    .add("user_id", StringType()) \
    .add("name", StringType()) \
    .add("email", StringType()) \
    .add("location", StringType()) \
    .add("registered_at", StringType())

click_schema = StructType() \
    .add("user_id", StringType()) \
    .add("session_id", StringType()) \
    .add("timestamp", StringType()) \
    .add("page", StringType()) \
    .add("device", StringType()) \
    .add("action", StringType())

transaction_schema = StructType() \
    .add("user_id", StringType()) \
    .add("session_id", StringType()) \
    .add("transaction_id", StringType()) \
    .add("timestamp", StringType()) \
    .add("transaction_amount", DoubleType()) \
    .add("payment_method", StringType()) \
    .add("payment_status", StringType()) \
    .add("order_status", StringType()) \
    .add("products", ArrayType(
        StructType()
            .add("product_id", StringType())
            .add("quantity", IntegerType())
            .add("unit_price", DoubleType())
            .add("product_category", StringType())
    ))

timestamp_columns = {
    "users": "registered_at",
    "clickstream": "timestamp",
    "transactions": "timestamp"
}

# Initialize Spark
spark = SparkSession.builder \
    .appName("KafkaToMinIOAndPostgres") \
    .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000") \
    .config("spark.hadoop.fs.s3a.access.key", "minioadmin") \
    .config("spark.hadoop.fs.s3a.secret.key", "minioadmin") \
    .config("spark.hadoop.fs.s3a.path.style.access", "true") \
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

# Main topic processor
def process_topic(topic, schema, s3_path, checkpoint_path, postgres_table):
    log_step(f"🔄 Subscribing to Kafka topic: '{topic}'")
    
    raw_df = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", "kafka:9092") \
        .option("subscribe", topic) \
        .option("startingOffsets", "latest") \
        .load()

    parsed_df = raw_df.selectExpr("CAST(value AS STRING) as json_string") \
        .select(from_json(col("json_string"), schema).alias("data")) \
        .select("data.*")

    if topic in timestamp_columns:
        ts_col = timestamp_columns[topic]
        parsed_df = parsed_df.withColumn(ts_col, to_timestamp(col(ts_col), "yyyy-MM-dd HH:mm:ss"))

    log_step(f"💾 Writing '{topic}' stream to MinIO: {s3_path}")
    minio_query = parsed_df.writeStream \
        .format("parquet") \
        .option("path", s3_path) \
        .option("checkpointLocation", checkpoint_path) \
        .outputMode("append") \
        .start()

    def write_to_postgres(df, epoch_id):
        log_step(f"📥 Writing '{topic}' batch {epoch_id} to PostgreSQL table: {postgres_table}")
        df.write \
            .format("jdbc") \
            .option("url", "jdbc:postgresql://postgres:5432/streaming_analytics") \
            .option("dbtable", postgres_table) \
            .option("user", "postgres") \
            .option("password", "postgres") \
            .option("driver", "org.postgresql.Driver") \
            .mode("append") \
            .save()

    if topic == "transactions":
        log_step(f"📤 Starting PostgreSQL write for topic: 'transactions'")
        parsed_df.withColumn("products", to_json(col("products"))).writeStream \
            .foreachBatch(write_to_postgres) \
            .outputMode("update") \
            .start()


        log_step(f"🔍 Exploding 'products' for transaction_items table")

        items_df = parsed_df \
            .withColumn("product", explode("products")) \
            .select(
                col("transaction_id"),
                col("product.product_id").alias("product_id"),
                col("product.product_category").alias("product_category"),
                col("product.quantity").alias("quantity"),
                col("product.unit_price").alias("unit_price"),
                expr("product.quantity * product.unit_price").alias("product_spend"),
                col("timestamp")
            )

        items_df.writeStream \
            .foreachBatch(lambda df, epoch_id: (
                log_step(f"📥 Writing batch {epoch_id} to 'transaction_items' table"),
                df.write \
                    .format("jdbc") \
                    .option("url", "jdbc:postgresql://postgres:5432/streaming_analytics") \
                    .option("dbtable", "transaction_items") \
                    .option("user", "postgres") \
                    .option("password", "postgres") \
                    .option("driver", "org.postgresql.Driver") \
                    .mode("append") \
                    .save()
            )) \
            .outputMode("update") \
            .start()

    else:
        log_step(f"📤 Starting PostgreSQL write for topic: '{topic}'")
        parsed_df.writeStream \
            .foreachBatch(write_to_postgres) \
            .outputMode("update") \
            .start()

    return minio_query

# Start queries for each topic
query_users = process_topic(
    "users", user_schema,
    "s3a://users/data/", "/tmp/users_checkpoint",
    postgres_table="users"
)

query_clicks = process_topic(
    "clickstream", click_schema,
    "s3a://clickstream/data/", "/tmp/clickstream_checkpoint",
    postgres_table="clickstream"
)

query_txns = process_topic(
    "transactions", transaction_schema,
    "s3a://transactions/data/", "/tmp/transactions_checkpoint",
    postgres_table="transactions"
)

spark.streams.awaitAnyTermination()
