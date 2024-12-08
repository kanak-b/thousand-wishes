from pyspark.sql import SparkSession
from pyspark.sql.functions import col

# Start Spark session with MinIO configs
spark = SparkSession.builder \
    .appName("ParquetReader") \
    .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000") \
    .config("spark.hadoop.fs.s3a.access.key", "minioadmin") \
    .config("spark.hadoop.fs.s3a.secret.key", "minioadmin") \
    .config("spark.hadoop.fs.s3a.path.style.access", "true") \
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

# Load parquet files from MinIO
df_clicks = spark.read.parquet("s3a://clickstream/data/").alias("clicks")
df_users = spark.read.parquet("s3a://users/data/").alias("users")
df_txns = spark.read.parquet("s3a://transactions/data/").alias("txns")

# Join clicks with users
clicks_users = df_clicks.join(
    df_users,
    col("clicks.user_id") == col("users.user_id"),
    how="left"
).drop(df_users["user_id"])


full_df = clicks_users.join(
    df_txns,
    col("clicks.session_id") == col("txns.session_id"),
    how="left"
).drop(df_txns["session_id"])

# Print schema and count
print("Total Records:", full_df.count())
full_df.printSchema()

full_df.select(
    col("clicks.user_id").alias("user_id"),
    col("clicks.session_id").alias("session_id"),
    col("clicks.page"),
    col("txns.transaction_amount"),
    col("users.email")
).show(10, truncate=False)
