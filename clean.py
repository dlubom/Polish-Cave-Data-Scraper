import os

os.environ["SPARK_VERSION"] = "3.5"

from pyspark.sql import SparkSession
import pyspark.sql.functions as F
import pyspark.sql.types as T
from pyspark.sql.types import *
from pydeequ.checks import *
from pydeequ.verification import *
from pydeequ.analyzers import *
import pydeequ
import re

# Create a Spark session
spark = (
    SparkSession.builder.appName("Caves Data Processing")
    .config("spark.jars.packages", pydeequ.deequ_maven_coord)
    .config("spark.jars.excludes", pydeequ.f2j_maven_coord)
    .config("spark.some.config.option", "some-value")
    .getOrCreate()
)

# Verify Spark session creation
print("Spark Session created:", spark.version)

# 1. Define the schema
cave_schema = T.StructType(
    [
        T.StructField("Nazwa", T.StringType(), False),
        T.StructField("Inne nazwy", T.StringType(), True),
        T.StructField("Nr inwentarzowy", T.StringType(), True),
        T.StructField("Region", T.StringType(), True),
        T.StructField("Współrzędne WGS84", T.StringType(), True),
        T.StructField("Gmina", T.StringType(), True),
        T.StructField("Powiat", T.StringType(), True),
        T.StructField("Województwo", T.StringType(), True),
        T.StructField("Właściciel terenu", T.StringType(), True),
        T.StructField("Podstawa ochrony", T.StringType(), True),
        T.StructField("Ekspozycja otworu", T.StringType(), True),
        T.StructField("Pozostałe otwory", T.StringType(), True),
        T.StructField("Wysokość bezwzględna [m n.p.m.]", T.StringType(), True),
        T.StructField("Wysokość względna [m]", T.StringType(), True),
        T.StructField("Głębokość [m]", T.StringType(), True),
        T.StructField("Przewyższenie [m]", T.StringType(), True),
        T.StructField("Deniwelacja [m]", T.StringType(), True),
        T.StructField("Długość [m]", T.StringType(), True),
        T.StructField("w tym szacowane [m]", T.StringType(), True),
        T.StructField("Rozciągłość horyzontalna [m]", T.StringType(), True),
        T.StructField("Położenie geograficzne", T.StringType(), True),
        T.StructField("Opis drogi dojścia do otworu", T.StringType(), True),
        T.StructField("Opis jaskini", T.StringType(), True),
        T.StructField("Historia badań", T.StringType(), True),
        T.StructField("Historia eksploracji", T.StringType(), True),
        T.StructField("Historia dokumentacji", T.StringType(), True),
        T.StructField("Zniszczona, niedostępna lub nieodnaleziona", T.StringType(), True),
        T.StructField("Literatura", T.StringType(), True),
        T.StructField("Materialy archiwalne", T.StringType(), True),
        T.StructField("Autorzy opracowania", T.StringType(), True),
        T.StructField("Redakcja", T.StringType(), True),
        T.StructField("Stan na rok", T.StringType(), True),
        T.StructField("Grafika, zdjęcia", T.StringType(), True),
        T.StructField("Obiekt w serwisie Geostanowiska", T.StringType(), True),
        T.StructField(
            "images",
            T.ArrayType(
                T.StructType(
                    [
                        T.StructField(
                            "metadata",
                            T.StructType(
                                [
                                    T.StructField("grafika_id", T.LongType(), True),
                                    T.StructField("mime", T.StringType(), True),
                                    T.StructField("grafika", T.ArrayType(T.StringType()), True),
                                    T.StructField("data_wykonania", T.StringType(), True),
                                    T.StructField("dataWykonaniaString", T.StringType(), True),
                                    T.StructField("grafika_nazwa", T.StringType(), True),
                                    T.StructField("wielkosc", T.LongType(), True),
                                    T.StructField("autor_nazwa", T.StringType(), True),
                                    T.StructField("jaskinia_id", T.LongType(), True),
                                    T.StructField("jaskinia_nazwa", T.StringType(), True),
                                    T.StructField("typ_grafiki_id", T.LongType(), True),
                                    T.StructField("typ_grafiki_nazwa", T.StringType(), True),
                                    T.StructField("nr_inwent", T.StringType(), True),
                                    T.StructField("region", T.StringType(), True),
                                    T.StructField("maxWidth", T.LongType(), True),
                                    T.StructField("maxHeight", T.LongType(), True),
                                    T.StructField("fileUpload", T.StringType(), True),
                                    T.StructField("Authors", T.StringType(), True),
                                    T.StructField("GraphicsTypes", T.StringType(), True),
                                ]
                            ),
                            True,
                        ),
                        T.StructField("image_path", T.StringType(), True),
                        T.StructField("description", T.StringType(), True),
                    ]
                )
            ),
            True,
        ),
        T.StructField("cave_id", T.StringType(), False),
    ]
)

# 2. Load the data
df = spark.read.json("caves.jsonl", schema=cave_schema)

# 3. Rename columns to lower case, in English, with underscores
col_name_mapping = {
    "Nazwa": "name",
    "Inne nazwy": "other_names",
    "Nr inwentarzowy": "inventory_number",
    "Region": "region",
    "Współrzędne WGS84": "coordinates_wgs84",
    "Gmina": "commune",
    "Powiat": "district",
    "Województwo": "province",
    "Właściciel terenu": "land_owner",
    "Podstawa ochrony": "protection_basis",
    "Ekspozycja otworu": "entrance_exposition",
    "Pozostałe otwory": "other_entrances",
    "Wysokość bezwzględna [m n.p.m.]": "absolute_height_masl",
    "Wysokość względna [m]": "relative_height_m",
    "Głębokość [m]": "depth_m",
    "Przewyższenie [m]": "elevation_difference_m",
    "Deniwelacja [m]": "denivelation_m",
    "Długość [m]": "length_m",
    "w tym szacowane [m]": "estimated_length_m",
    "Rozciągłość horyzontalna [m]": "horizontal_extent_m",
    "Położenie geograficzne": "geographical_location",
    "Opis drogi dojścia do otworu": "entrance_access_description",
    "Opis jaskini": "cave_description",
    "Historia badań": "research_history",
    "Historia eksploracji": "exploration_history",
    "Historia dokumentacji": "documentation_history",
    "Zniszczona, niedostępna lub nieodnaleziona": "destroyed_unavailable_or_unfound",
    "Literatura": "literature",
    "Materialy archiwalne": "archival_materials",
    "Autorzy opracowania": "authors_of_study",
    "Redakcja": "editorial",
    "Stan na rok": "state_in_year",
    "Grafika, zdjęcia": "graphics_photos",
    "Obiekt w serwisie Geostanowiska": "object_in_geostanowiska_service",
    "images": "images",
    "cave_id": "cave_id",
}

for old_col, new_col in col_name_mapping.items():
    df = df.withColumnRenamed(old_col, new_col)

# 4. Convert numeric columns from strings to numbers
numeric_cols = [
    "absolute_height_masl",
    "relative_height_m",
    "depth_m",
    "elevation_difference_m",
    "denivelation_m",
    "length_m",
    "estimated_length_m",
    "horizontal_extent_m",
]

# Replace commas with dots and cast to float for numeric columns
for col in numeric_cols:
    df = df.withColumn(
        col, F.when(F.trim(F.col(col)) != "", F.regexp_replace(F.col(col), ",", ".").cast("float")).otherwise(None)
    )

# 5. Extract geographic coordinates from 'coordinates_wgs84'
# Extract DMS strings
lon_pattern = r"λ:\s*([\d°′″,\.\s]+)"
lat_pattern = r"φ:\s*([\d°′″,\.\s]+)"

df = df.withColumn("lon_dms", F.regexp_extract(F.col("coordinates_wgs84"), lon_pattern, 1))
df = df.withColumn("lat_dms", F.regexp_extract(F.col("coordinates_wgs84"), lat_pattern, 1))

# Replace commas with dots
df = df.withColumn("lon_dms", F.regexp_replace("lon_dms", ",", "."))
df = df.withColumn("lat_dms", F.regexp_replace("lat_dms", ",", "."))

# Extract degrees, minutes, seconds
dms_pattern = r"(\d+)°\s*(\d+)′\s*([\d\.]+)″"

df = df.withColumn("lon_deg", F.regexp_extract("lon_dms", dms_pattern, 1).cast("float"))
df = df.withColumn("lon_min", F.regexp_extract("lon_dms", dms_pattern, 2).cast("float"))
df = df.withColumn("lon_sec", F.regexp_extract("lon_dms", dms_pattern, 3).cast("float"))

df = df.withColumn("lat_deg", F.regexp_extract("lat_dms", dms_pattern, 1).cast("float"))
df = df.withColumn("lat_min", F.regexp_extract("lat_dms", dms_pattern, 2).cast("float"))
df = df.withColumn("lat_sec", F.regexp_extract("lat_dms", dms_pattern, 3).cast("float"))

# Calculate decimal degrees
df = df.withColumn("latitude", F.col("lat_deg") + F.col("lat_min") / 60 + F.col("lat_sec") / 3600)
df = df.withColumn("longitude", F.col("lon_deg") + F.col("lon_min") / 60 + F.col("lon_sec") / 3600)

# Drop intermediate columns
df = df.drop("lon_dms", "lat_dms", "lon_deg", "lon_min", "lon_sec", "lat_deg", "lat_min", "lat_sec")

# 6. Data validation using pydeequ
check = Check(spark, CheckLevel.Warning, "Data Validation")

checkResult = (
    VerificationSuite(spark)
    .onData(df)
    .addCheck(
        check.isComplete("cave_id")
        .isUnique("cave_id")
        .isComplete("name")
        .isComplete("latitude")
        .isComplete("longitude")
    )
    .run()
)

# Get the results
verificationResult = VerificationResult.checkResultsAsDataFrame(spark, checkResult)

print(verificationResult.toPandas())
verificationResult.toPandas().to_json("logs/verification_result.jsonl", orient="records", lines=True)

# 7. Write the transformed data to a file
df.toPandas().to_json("caves_transformed.jsonl", orient="records", lines=True, force_ascii=False)

df.repartition(1).write.mode("overwrite").parquet("caves_transformed.parquet")
