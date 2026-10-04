import json
import logging
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Setup JDK 21 and Hadoop Home
possible_jdks = [
    r"C:\Program Files\Android\Android Studio\jbr",
    r"C:\Users\nvvar\.vscode\extensions\redhat.java-1.56.0-win32-x64\jre\21.0.1",
]
for jdk_path in possible_jdks:
    if os.path.exists(os.path.join(jdk_path, "bin", "java.exe")):
        os.environ["JAVA_HOME"] = jdk_path
        os.environ["PATH"] = os.path.join(jdk_path, "bin") + os.path.pathsep + os.environ.get("PATH", "")
        break

hadoop_home = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "hadoop_home"))
if os.path.exists(os.path.join(hadoop_home, "bin", "winutils.exe")):
    os.environ["HADOOP_HOME"] = hadoop_home
    os.environ["PATH"] = os.path.join(hadoop_home, "bin") + os.path.pathsep + os.environ.get("PATH", "")

from pyspark.sql import SparkSession

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_spark_microbatch")

spark = SparkSession.builder \
    .appName("TestMicroBatch") \
    .getOrCreate()

raw_df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "localhost:9092") \
    .option("subscribe", "weather.raw") \
    .option("startingOffsets", "earliest") \
    .load()

def micro_batch_handler(batch_df, batch_id):
    logger.info("--> MICRO BATCH %s CALLED! Rows count: %d", batch_id, batch_df.count())
    rows = batch_df.collect()
    for row in rows:
        val = row.value.decode("utf-8") if isinstance(row.value, bytes) else str(row.value)
        logger.info("--> ROW VALUE: %s", val)

query = raw_df.writeStream \
    .foreachBatch(micro_batch_handler) \
    .start()

logger.info("Query started! Waiting 10 seconds for micro-batches...")
time.sleep(10)
query.stop()
spark.stop()
