import os

os.environ["SPARK_VERSION"] = "3.5"

from typing import Dict, List
from dataclasses import dataclass

import pyspark.sql.functions as F
import pyspark.sql.types as T
from pyspark.sql import SparkSession
import re
import html


@dataclass
class SparkConfig:
    app_name: str = "Caves Data Processing"
    config_options: Dict[str, str] = None

    def get_default_configs(self) -> Dict[str, str]:
        return {
            "spark.some.config.option": "some-value",
        }


def create_spark_session(config: SparkConfig) -> SparkSession:
    """Create and configure Spark session"""
    builder = SparkSession.builder.appName(config.app_name)

    # Apply default configurations
    for key, value in config.get_default_configs().items():
        builder = builder.config(key, value)

    # Apply custom configurations if provided
    if config.config_options:
        for key, value in config.config_options.items():
            builder = builder.config(key, value)

    spark = builder.getOrCreate()
    print(f"Spark Session created: {spark.version}")
    return spark


def create_cave_schema() -> T.StructType:
    """Define schema for cave data including images structure"""
    # Define image metadata schema
    image_metadata_schema = T.StructType(
        [
            T.StructField("grafika_id", T.LongType(), True),
            T.StructField("mime", T.StringType(), True),
            # Commented out: 'grafika' field (graphics)
            # T.StructField("grafika", T.ArrayType(T.StringType()), True),
            # Commented out: 'data_wykonania' field (creation_date)
            # T.StructField("data_wykonania", T.StringType(), True),
            T.StructField("dataWykonaniaString", T.StringType(), True),
            T.StructField("grafika_nazwa", T.StringType(), True),
            # Commented out: 'wielkosc' field (size)
            # T.StructField("wielkosc", T.LongType(), True),
            T.StructField("autor_nazwa", T.StringType(), True),
            # Commented out: 'jaskinia_id' field (image_cave_id)
            # T.StructField("jaskinia_id", T.LongType(), True),
            # Commented out: 'jaskinia_nazwa' field (image_cave_name)
            # T.StructField("jaskinia_nazwa", T.StringType(), True),
            T.StructField("typ_grafiki_id", T.LongType(), True),
            T.StructField("typ_grafiki_nazwa", T.StringType(), True),
            T.StructField("nr_inwent", T.StringType(), True),
            # Commented out: 'region' field (image_region)
            # T.StructField("region", T.StringType(), True),
            T.StructField("maxWidth", T.LongType(), True),
            T.StructField("maxHeight", T.LongType(), True),
            # Commented out: 'fileUpload' field (file_upload)
            # T.StructField("fileUpload", T.StringType(), True),
            # Commented out: 'Authors' field (image_authors)
            # T.StructField("Authors", T.StringType(), True),
            # Commented out: 'GraphicsTypes' field (graphics_types)
            # T.StructField("GraphicsTypes", T.StringType(), True),
        ]
    )

    # Define image schema
    image_schema = T.StructType(
        [
            T.StructField("metadata", image_metadata_schema, True),
            T.StructField("image_path", T.StringType(), True),
            T.StructField("description", T.StringType(), True),
        ]
    )

    # Define main schema
    return T.StructType(
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
            T.StructField("images", T.ArrayType(image_schema), True),
            T.StructField("cave_id", T.StringType(), False),
        ]
    )


def get_column_mappings() -> Dict[str, str]:
    """Define column name mappings for both main cave data and image metadata"""
    return {
        # Main cave data mappings
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
        # Image metadata mappings
        "grafika_id": "graphics_id",
        "mime": "mime_type",
        "dataWykonaniaString": "creation_date_string",
        "grafika_nazwa": "graphics_name",
        "autor_nazwa": "author_name",
        "typ_grafiki_id": "graphics_type_id",
        "typ_grafiki_nazwa": "graphics_type_name",
        "nr_inwent": "inventory_number",
        # Commented out mappings for removed columns, all are empty or not useful
        # "grafika": "graphics",
        # "wielkosc": "size",
        # "jaskinia_id": "cave_id",
        # "jaskinia_nazwa": "cave_name",
        # "region": "region",
        # "fileUpload": "file_upload",
        # "Authors": "authors",
        # "GraphicsTypes": "graphics_types",
        # "data_wykonania": "creation_date",
    }


def rename_image_metadata_columns(df, col_mappings: Dict[str, str]):
    """Rename columns in the nested image metadata structure"""
    # Get the field names of the metadata struct
    metadata_fields = df.schema["images"].dataType.elementType["metadata"].dataType.fieldNames()

    # Build the transformation
    df = df.withColumn(
        "images",
        F.transform(
            "images",
            lambda x: F.struct(
                F.struct(
                    *[x.metadata[old_name].alias(col_mappings.get(old_name, old_name)) for old_name in metadata_fields]
                ).alias("metadata"),
                x.image_path.alias("image_path"),
                x.description.alias("description"),
            ),
        ),
    )

    return df


def process_numeric_columns(df, numeric_cols: List[str]):
    """Convert string columns to numeric values"""
    for col in numeric_cols:
        df = df.withColumn(
            col,
            F.when(
                F.trim(F.col(col)) != "",
                F.regexp_replace(F.col(col), ",", ".").cast("float"),
            ).otherwise(None),
        )
    return df


def process_string_columns(df, string_cols: List[str]):
    """Trim and replace empty strings with None"""
    for col in string_cols:
        df = df.withColumn(col, F.when(F.trim(F.col(col)) == "", None).otherwise(F.trim(F.col(col))))
    return df


def clean_text_fields(df, text_cols: List[str]):
    """Clean text fields by removing HTML tags, fixing spaces, and decoding entities"""

    # Define a UDF to clean text
    def clean_text(text):
        if text is None:
            return None
        # Remove HTML tags
        text = re.sub(r"<[^>]+>", "", text)
        # Decode HTML entities
        text = html.unescape(text)
        # Replace multiple spaces with single space
        text = re.sub(r"\s+", " ", text)
        return text

    clean_text_udf = F.udf(clean_text, T.StringType())

    for col in text_cols:
        df = df.withColumn(col, clean_text_udf(F.col(col)))
    return df


def extract_coordinates(df):
    """Extract and convert coordinates from DMS to decimal degrees"""
    # Extract DMS strings
    lon_pattern = r"λ:\s*([\d°′″,\.\s]+)"
    lat_pattern = r"φ:\s*([\d°′″,\.\s]+)"
    dms_pattern = r"(\d+)°\s*(\d+)′\s*([\d\.]+)″"

    # Extract DMS components
    df = df.withColumn("lon_dms", F.regexp_extract(F.col("coordinates_wgs84"), lon_pattern, 1))
    df = df.withColumn("lat_dms", F.regexp_extract(F.col("coordinates_wgs84"), lat_pattern, 1))

    # Replace commas with dots
    df = df.withColumn("lon_dms", F.regexp_replace("lon_dms", ",", "."))
    df = df.withColumn("lat_dms", F.regexp_replace("lat_dms", ",", "."))

    # Extract components
    for coord in ["lon", "lat"]:
        df = df.withColumn(f"{coord}_deg", F.regexp_extract(f"{coord}_dms", dms_pattern, 1).cast("float"))
        df = df.withColumn(f"{coord}_min", F.regexp_extract(f"{coord}_dms", dms_pattern, 2).cast("float"))
        df = df.withColumn(f"{coord}_sec", F.regexp_extract(f"{coord}_dms", dms_pattern, 3).cast("float"))

    # Calculate decimal degrees
    df = df.withColumn(
        "latitude",
        F.col("lat_deg") + F.col("lat_min") / 60 + F.col("lat_sec") / 3600,
    )
    df = df.withColumn(
        "longitude",
        F.col("lon_deg") + F.col("lon_min") / 60 + F.col("lon_sec") / 3600,
    )

    # Drop intermediate columns
    intermediate_cols = [
        "lon_dms",
        "lat_dms",
        "lon_deg",
        "lon_min",
        "lon_sec",
        "lat_deg",
        "lat_min",
        "lat_sec",
        "coordinates_wgs84",
    ]
    return df.drop(*intermediate_cols)


def save_data(df, output_prefix: str = "caves_transformed"):
    """Save processed data in multiple formats"""
    import shutil
    import glob
    import os

    # JSONL
    temp_dir_json = f"{output_prefix}_jsonl_temp"
    df.coalesce(1).write.mode("overwrite").json(temp_dir_json)
    temp_file_json = glob.glob(os.path.join(temp_dir_json, "part-*"))[0]
    shutil.move(temp_file_json, f"{output_prefix}.jsonl")
    shutil.rmtree(temp_dir_json)

    # Parquet
    temp_dir_parquet = f"{output_prefix}_parquet_temp"
    df.coalesce(1).write.mode("overwrite").parquet(temp_dir_parquet)
    temp_file_parquet = glob.glob(os.path.join(temp_dir_parquet, "part-*"))[0]
    shutil.move(temp_file_parquet, f"{output_prefix}.parquet")
    shutil.rmtree(temp_dir_parquet)


def main():
    # Initialize Spark
    spark_config = SparkConfig()
    spark = create_spark_session(spark_config)

    # Define schema and load data
    schema = create_cave_schema()
    df = spark.read.json("caves.jsonl", schema=schema)

    # Get column mappings
    col_mappings = get_column_mappings()

    # Rename main columns
    for old_col, new_col in col_mappings.items():
        if old_col in df.columns:  # Only rename if column exists in main structure
            df = df.withColumnRenamed(old_col, new_col)

    # Rename nested image metadata columns
    df = rename_image_metadata_columns(df, col_mappings)

    # Process numeric columns
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
    df = process_numeric_columns(df, numeric_cols)

    # Process coordinates
    df = extract_coordinates(df)

    # Get all string columns
    string_cols = [field.name for field in df.schema.fields if isinstance(field.dataType, T.StringType)]
    df = process_string_columns(df, string_cols)

    # Clean text fields
    df = clean_text_fields(df, string_cols)

    # Filter out test data
    df = df.filter(~F.col("cave_id").isin(["010569", "011054"]))

    df = df.cache()

    # Save results
    save_data(df)


if __name__ == "__main__":
    main()
