#!/usr/bin/env python3
"""
Compare coordinates between scraped data and PGI shapefile data.

This script:
1. Loads scraped cave data from parquet file
2. Loads PGI shapefile data from CSV
3. Matches caves by inventory number
4. Compares coordinates and calculates differences
5. Generates a detailed comparison report
"""

import pandas as pd
import numpy as np
from pathlib import Path


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points on earth (in meters).
    Uses the Haversine formula.
    """
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])

    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    r = 6371000  # Radius of earth in meters
    return c * r


def load_scraped_data(file_path):
    """Load scraped cave data from JSONL file."""
    print(f"Loading scraped data from {file_path}...")
    df = pd.read_json(file_path, lines=True)

    # Select relevant columns
    df_clean = df[['cave_id', 'name', 'inventory_number', 'latitude', 'longitude']].copy()
    df_clean = df_clean.dropna(subset=['latitude', 'longitude'])

    print(f"  Loaded {len(df_clean)} caves with coordinates")
    return df_clean


def load_pgi_data(file_path):
    """Load PGI shapefile data from CSV."""
    print(f"Loading PGI data from {file_path}...")
    df = pd.read_csv(file_path)

    # Select relevant columns and rename for consistency
    df_clean = df[['ID', 'NAZWA', 'NR_INWENT', 'lat', 'lon']].copy()
    df_clean.columns = ['pgi_id', 'pgi_name', 'inventory_number', 'pgi_latitude', 'pgi_longitude']
    df_clean = df_clean.dropna(subset=['pgi_latitude', 'pgi_longitude'])

    print(f"  Loaded {len(df_clean)} caves with coordinates")
    return df_clean


def match_and_compare(scraped_df, pgi_df):
    """Match caves and compare coordinates."""
    print("\nMatching caves by inventory number...")

    # Merge on inventory number
    merged = scraped_df.merge(
        pgi_df,
        on='inventory_number',
        how='inner'
    )

    print(f"  Found {len(merged)} matching caves")

    # Calculate differences
    print("\nCalculating coordinate differences...")
    merged['lat_diff'] = merged['latitude'] - merged['pgi_latitude']
    merged['lon_diff'] = merged['longitude'] - merged['pgi_longitude']

    # Calculate distance in meters using Haversine formula
    merged['distance_m'] = haversine_distance(
        merged['latitude'],
        merged['longitude'],
        merged['pgi_latitude'],
        merged['pgi_longitude']
    )

    # Calculate absolute differences in decimal degrees
    merged['lat_abs_diff'] = merged['lat_diff'].abs()
    merged['lon_abs_diff'] = merged['lon_diff'].abs()

    return merged


def generate_report(comparison_df):
    """Generate detailed comparison report."""
    print("\n" + "="*80)
    print("COORDINATE COMPARISON REPORT")
    print("="*80)

    print(f"\nTotal matching caves: {len(comparison_df)}")

    # Statistics on distance differences
    print("\n--- Distance Statistics (meters) ---")
    print(f"Mean distance:   {comparison_df['distance_m'].mean():.2f} m")
    print(f"Median distance: {comparison_df['distance_m'].median():.2f} m")
    print(f"Min distance:    {comparison_df['distance_m'].min():.2f} m")
    print(f"Max distance:    {comparison_df['distance_m'].max():.2f} m")
    print(f"Std deviation:   {comparison_df['distance_m'].std():.2f} m")

    # Count caves with identical coordinates
    identical = (comparison_df['distance_m'] < 0.01).sum()  # Less than 1cm difference
    print(f"\nCaves with identical coordinates (< 1cm): {identical} ({identical/len(comparison_df)*100:.1f}%)")

    # Count caves within certain distance thresholds
    thresholds = [1, 5, 10, 50, 100, 500]
    print("\n--- Distance Distribution ---")
    for threshold in thresholds:
        count = (comparison_df['distance_m'] <= threshold).sum()
        pct = count / len(comparison_df) * 100
        print(f"Within {threshold:4d}m: {count:5d} caves ({pct:5.1f}%)")

    # Statistics on coordinate differences
    print("\n--- Coordinate Differences (decimal degrees) ---")
    print(f"Latitude  - Mean abs diff: {comparison_df['lat_abs_diff'].mean():.8f}°")
    print(f"Latitude  - Max abs diff:  {comparison_df['lat_abs_diff'].max():.8f}°")
    print(f"Longitude - Mean abs diff: {comparison_df['lon_abs_diff'].mean():.8f}°")
    print(f"Longitude - Max abs diff:  {comparison_df['lon_abs_diff'].max():.8f}°")

    # Show top 10 caves with largest differences
    print("\n--- Top 10 Caves with Largest Coordinate Differences ---")
    top_10 = comparison_df.nlargest(10, 'distance_m')[
        ['inventory_number', 'name', 'distance_m', 'latitude', 'longitude', 'pgi_latitude', 'pgi_longitude']
    ]
    print(top_10.to_string(index=False))

    # Show sample of caves with identical coordinates
    print("\n--- Sample of 10 Caves with Identical Coordinates ---")
    identical_caves = comparison_df[comparison_df['distance_m'] < 0.01]
    if len(identical_caves) > 0:
        sample = identical_caves.head(10)[
            ['inventory_number', 'name', 'latitude', 'longitude', 'distance_m']
        ]
        print(sample.to_string(index=False))
    else:
        print("No caves with identical coordinates found!")

    print("\n" + "="*80)

    # Save detailed results to CSV
    output_file = "locations/coordinate_comparison.csv"
    comparison_df.to_csv(output_file, index=False)
    print(f"\nDetailed comparison saved to: {output_file}")


def main():
    # Load data
    scraped_df = load_scraped_data("caves_transformed.jsonl")
    pgi_df = load_pgi_data("locations/jaskinie_wspolrzedne_wgs84.csv")

    # Match and compare
    comparison_df = match_and_compare(scraped_df, pgi_df)

    # Generate report
    generate_report(comparison_df)


if __name__ == "__main__":
    main()
