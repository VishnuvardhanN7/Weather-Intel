import os
import sys

# Find existing JDK
possible_jdks = [
    r"C:\Program Files\Android\Android Studio\jbr",
    r"C:\Users\nvvar\.vscode\extensions\redhat.java-1.56.0-win32-x64\jre\21.0.1",
]

for jdk_path in possible_jdks:
    if os.path.exists(os.path.join(jdk_path, "bin", "java.exe")):
        os.environ["JAVA_HOME"] = jdk_path
        os.environ["PATH"] = os.path.join(jdk_path, "bin") + os.path.pathsep + os.environ.get("PATH", "")
        print("Set JAVA_HOME to:", jdk_path)
        break

from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .appName("KafkaFormatTest") \
    .getOrCreate()

print("SUCCESS: SparkSession created cleanly!")
print("Spark Version:", spark.version)

df = spark.read.format("kafka") \
    .option("kafka.bootstrap.servers", "localhost:9092") \
    .option("subscribe", "weather.raw") \
    .option("startingOffsets", "earliest") \
    .load()

print("SUCCESS: PySpark Kafka source created!")
print("Schema fields:", [field.name for field in df.schema.fields])
spark.stop()
