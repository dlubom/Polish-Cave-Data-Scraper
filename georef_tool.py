#!/usr/bin/env python3
"""
Cave Plan Georeferencing Tool (Fixed Mathematics Implementation + Meridian Convergence)

This tool allows interactive georeferencing of cave plans.
Key features:
- Correct sequential affine transformation math (ensures anchor point stays fixed).
- Interactive marking of entrance, scale bar, and north direction.
- Console prompts for real-world distances and magnetic declination.
- Automatic meridian (grid) convergence computation for PL-1992 based on entrance coordinates.
- Outputs CS92 GeoTIFF and WGS84 KML.
"""

from dataclasses import dataclass
import json
import logging
import math
from pathlib import Path
import sys
from typing import Any, Optional

from affine import Affine
import click
import cv2
import numpy as np
from pyproj import Transformer
import rasterio
from rasterio.crs import CRS
import simplekml

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# --- Structures ---


@dataclass
class CaveData:
    """Cave data structure holding basic info and geolocated entrance."""

    cave_id: str
    name: str
    inventory_number: str
    latitude: float  # WGS84
    longitude: float  # WGS84
    plan_images: list[dict[str, Any]]

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "CaveData":
        """Create CaveData from a JSON dictionary line."""
        # Filter for plan images only
        plan_images = [
            img
            for img in data.get("images", [])
            if img.get("metadata", {}).get("graphics_type_name") in ["plan", "plan i przekrój"]
        ]
        return cls(
            cave_id=data["cave_id"],
            name=data["name"],
            inventory_number=data.get("inventory_number", ""),
            latitude=data.get("latitude", 0.0),
            longitude=data.get("longitude", 0.0),
            plan_images=plan_images,
        )


@dataclass
class GeoreferenceParams:
    """
    Parameters collected from user interaction needed for transformation.

    north_angle_degrees:
        Angle from image TOP to the North arrow on the plan, clockwise.
        If the plan is already oriented to geographic (true) north, this is
        usually 0 when the arrow points straight up.

    magnetic_declination:
        Additional manual correction to add to the north_angle_degrees.
        For plans already corrected to geographic north (like Czarna), this
        should normally be 0.0.

    use_meridian_convergence:
        If True, the code will automatically compute the meridian (grid)
        convergence for the entrance point (for PL-1992) and add it as an
        extra rotation component so that the plan aligns with grid north.
    """

    entrance_pixel: tuple[int, int]  # (x, y) pixel coordinates of entrance on plan
    scale_pixels_per_meter: float  # Number of pixels corresponding to 1 meter
    north_angle_degrees: float  # Angle from image TOP to North (clockwise)
    magnetic_declination: float = 0.0  # Extra correction to add to north_angle
    use_meridian_convergence: bool = True  # Automatically account for grid convergence

    @staticmethod
    def _compute_meridian_convergence_deg(
        latitude_deg: float,
        longitude_deg: float,
        target_crs: str,
    ) -> float:
        """
        Approximate meridian (grid) convergence at given location, in degrees.

        Currently implemented for:
            - EPSG:2180 (PL-1992), central meridian lambda0 = 19 degrees.

        Formula (approximate, as suggested):
            convergence ≈ (lambda0 - lambda) * sin(phi)

        where:
            lambda0  - central meridian (deg),
            lambda   - geographic longitude of the point (deg),
            phi      - geographic latitude of the point (deg).

        Returned value is in degrees and is intended to be ADDED to the
        clockwise angle from image TOP.
        """
        if target_crs != "EPSG:2180":
            return 0.0

        central_meridian_deg = 19.0  # PL-1992 central meridian
        # Convert latitude to radians for sine; longitude stays in degrees.
        convergence_deg = (central_meridian_deg - longitude_deg) * math.sin(
            math.radians(latitude_deg)
        )
        return convergence_deg

    def calculate_transform(
        self,
        entrance_lat_wgs84: float,
        entrance_lon_wgs84: float,
        target_crs: str = "EPSG:2180",  # Domyślnie PL-1992
    ) -> Affine:
        """
        Calculates the affine transformation matrix using sequential steps.
        THIS IS THE CRITICAL MATHEMATICAL PART.
        """
        logger.info(f"Calculating transform based on inputs and target CRS: {target_crs}")

        # 1. Project target coordinates (WGS84 -> Target CRS, e.g., PL-1992)
        # always_xy=True ensures order is (Longitude/X, Latitude/Y)
        transformer = Transformer.from_crs("EPSG:4326", target_crs, always_xy=True)
        world_x, world_y = transformer.transform(entrance_lon_wgs84, entrance_lat_wgs84)
        logger.info(f"Entrance projected coordinates: X={world_x:.2f}, Y={world_y:.2f}")

        # 1a. Compute meridian (grid) convergence if enabled
        meridian_conv_deg = 0.0
        if self.use_meridian_convergence:
            meridian_conv_deg = self._compute_meridian_convergence_deg(
                entrance_lat_wgs84,
                entrance_lon_wgs84,
                target_crs,
            )
            logger.info(
                "Meridian convergence at entrance: %.4f degrees " "(lat=%.6f, lon=%.6f)",
                meridian_conv_deg,
                entrance_lat_wgs84,
                entrance_lon_wgs84,
            )

        # 2. Calculate scale factor (meters per pixel)
        if self.scale_pixels_per_meter <= 0:
            raise ValueError("Scale pixels per meter must be positive.")
        meters_per_pixel = 1.0 / self.scale_pixels_per_meter

        # 3. Calculate total rotation angle
        # Input is angle from image TOP clockwise.
        # Affine rotation expects degrees counter-clockwise.
        total_angle_clockwise = (
            self.north_angle_degrees + self.magnetic_declination + meridian_conv_deg
        )

        rotation_angle_ccw = -total_angle_clockwise

        logger.info(
            "Total rotation (clockwise from image top): %.4f deg "
            "(north_angle=%.4f, declination=%.4f, meridian_conv=%.4f)",
            total_angle_clockwise,
            self.north_angle_degrees,
            self.magnetic_declination,
            meridian_conv_deg,
        )

        # --- Build transformation sequentially (read from bottom to top) ---

        # Step 4 (T2): Translate the (0,0) point to the final map coordinates.
        T_world_pos = Affine.translation(world_x, world_y)  # noqa: N806

        # Step 3 (R): Rotate around the (0,0) point.
        R_rotate = Affine.rotation(rotation_angle_ccw)  # noqa: N806

        # Step 2 (S): Scale pixels to meters and invert Y axis.
        # CRITICAL: Image Y goes DOWN, Map Y goes UP. We must apply negative Y scale.
        S_scale = Affine.scale(meters_per_pixel, -meters_per_pixel)  # noqa: N806

        # Step 1 (T1): Translate image so the entrance pixel is at (0,0).
        T_origin_offset = Affine.translation(  # noqa: N806
            -self.entrance_pixel[0], -self.entrance_pixel[1]
        )

        # Combine transformations by multiplying matrices
        final_transform = T_world_pos * R_rotate * S_scale * T_origin_offset

        return final_transform


class InteractiveGeoreferencer:
    """Handles the interactive GUI operations using OpenCV."""

    def __init__(self, window_name: str = "Georeferencing Tool"):
        self.window_name = window_name
        self.base_image: Optional[np.ndarray] = None
        self.display_image: Optional[np.ndarray] = None
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)

    def set_image(self, image: np.ndarray):
        self.base_image = image.copy()
        self.reset_display()

    def reset_display(self):
        if self.base_image is not None:
            self.display_image = self.base_image.copy()
            self.show()

    def show(self):
        if self.display_image is not None:
            cv2.imshow(self.window_name, self.display_image)

    def mark_point(self, prompt: str) -> tuple[int, int]:
        """Interactively mark a single point."""
        print(f"\n--- {prompt} ---")
        print("Click on the image to mark the point. Press SPACE or ENTER to confirm.")

        point: list[tuple[int, int]] = []

        def mouse_callback(event, x, y, flags, param):
            if event == cv2.EVENT_LBUTTONDOWN:
                point.clear()
                point.append((x, y))
                self.reset_display()
                # Draw marker
                cv2.circle(self.display_image, (x, y), 5, (0, 0, 255), -1)  # Red dot
                cv2.circle(self.display_image, (x, y), 15, (0, 0, 255), 2)  # Red circle
                self.show()

        cv2.setMouseCallback(self.window_name, mouse_callback)
        self.show()

        while True:
            key = cv2.waitKey(1) & 0xFF
            if key in [32, 13]:  # Space or Enter
                if point:
                    cv2.setMouseCallback(self.window_name, lambda *args: None)  # Clear callback
                    return point[0]
                else:
                    print("Please mark a point first.")
            elif key == 27:  # ESC
                raise SystemExit("Operation cancelled by user.")

    def mark_line_and_get_scale(self) -> float:
        """Interactively mark two points for scale and ask for real distance."""
        print("\n--- MARK SCALE BAR ---")
        print("Click Start point, then click End point of the scale bar.")

        points: list[tuple[int, int]] = []

        def mouse_callback(event, x, y, flags, param):
            if event == cv2.EVENT_LBUTTONDOWN and len(points) < 2:
                points.append((x, y))
                self.reset_display()

                # Draw first point
                if len(points) >= 1:
                    cv2.circle(self.display_image, points[0], 5, (0, 255, 0), -1)

                # Draw line and second point
                if len(points) == 2:
                    cv2.circle(self.display_image, points[1], 5, (0, 255, 0), -1)
                    cv2.line(self.display_image, points[0], points[1], (0, 255, 0), 2)

                self.show()

        cv2.setMouseCallback(self.window_name, mouse_callback)
        self.show()

        # Wait for 2 points
        while len(points) < 2:
            key = cv2.waitKey(100) & 0xFF
            if key == 27:
                raise SystemExit("Cancelled.")

        cv2.setMouseCallback(self.window_name, lambda *args: None)

        # Calculate pixel distance
        p1, p2 = points
        pixel_dist = np.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)
        logger.info(f"Scale bar length in pixels: {pixel_dist:.2f}")

        if pixel_dist == 0:
            raise ValueError("Scale points cannot be the same.")

        # Ask for real world distance
        while True:
            try:
                meters_str = input(
                    f"Enter the real-world length of this line in METERS [pixels={pixel_dist:.1f}]: "
                )
                meters = float(meters_str)
                if meters <= 0:
                    print("Distance must be positive.")
                    continue
                break
            except ValueError:
                print("Invalid input. Please enter a number.")

        pixels_per_meter = float(pixel_dist / meters)
        logger.info(f"Calculated scale: {pixels_per_meter:.4f} pixels/meter")
        return pixels_per_meter

    def mark_north_arrow(self) -> float:
        """
        Interactively mark North direction or skip.
        Returns angle in degrees from image TOP, clockwise.
        """
        print("\n--- MARK NORTH DIRECTION ---")
        print("Option 1: Click base of arrow, then tip of arrow pointing North.")
        print("Option 2: Press 'S' if North is straight UP on the image.")

        points: list[tuple[int, int]] = []
        angle_from_top = 0.0

        def mouse_callback(event, x, y, flags, param):
            if event == cv2.EVENT_LBUTTONDOWN and len(points) < 2:
                points.append((x, y))
                self.reset_display()

                if len(points) >= 1:
                    cv2.circle(self.display_image, points[0], 5, (255, 0, 0), -1)  # Blue base

                if len(points) == 2:
                    # Draw arrow
                    cv2.arrowedLine(
                        self.display_image, points[0], points[1], (255, 0, 0), 3, tipLength=0.2
                    )

                self.show()

        cv2.setMouseCallback(self.window_name, mouse_callback)
        self.show()

        processed = False
        while not processed:
            key = cv2.waitKey(100) & 0xFF
            if key == 27:
                raise SystemExit("Cancelled.")

            # Option 2: Skip
            if key == ord("s") or key == ord("S"):
                logger.info("North marking skipped. Defaulting to North = UP (0 degrees).")
                angle_from_top = 0.0
                processed = True

            # Option 1: Two points clicked
            if len(points) == 2 and not processed:
                # Calculate vector dx, dy (image coordinates, y grows down)
                dx = points[1][0] - points[0][0]
                dy = points[1][1] - points[0][1]

                # Calculate angle relative to straight up (negative Y axis in image)
                # atan2(x, y) gives angle from positive Y axis (down), clockwise.
                # We want angle from negative Y axis (up), clockwise.
                # Using atan2(dx, -dy) achieves this.
                angle_rad = np.arctan2(dx, -dy)
                angle_from_top = np.degrees(angle_rad)
                logger.info(f"Calculated North angle from top: {angle_from_top:.2f} degrees")
                processed = True

        cv2.setMouseCallback(self.window_name, lambda *args: None)
        return angle_from_top

    def close(self):
        cv2.destroyAllWindows()


class CavePlanGeoreferencerApp:
    """Main application logic coordinating data loading, interaction, and saving."""

    def __init__(self, caves_file: str, image_dir: str, output_dir: str):
        self.caves_file = Path(caves_file)
        self.image_dir = Path(image_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.gui = InteractiveGeoreferencer()

    def load_cave_data(self, cave_id: str) -> Optional[CaveData]:
        """Search for cave data in the JSONL file."""
        logger.info(f"Searching for cave ID: {cave_id}...")
        try:
            with open(self.caves_file, encoding="utf-8") as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        if data.get("cave_id") == cave_id:
                            return CaveData.from_json(data)
                    except json.JSONDecodeError:
                        continue
        except FileNotFoundError:
            logger.error(f"Caves file not found: {self.caves_file}")
        return None

    def load_image(self, cave_data: CaveData, plan_index: int = 0) -> Optional[np.ndarray]:
        """Load the specified plan image for the cave."""
        if not cave_data.plan_images:
            logger.error("No plan images found for this cave.")
            return None

        # Assume image path in JSON is relative or needs adjustment based on image_dir structure
        # Adjust this logic if your JSON paths are absolute or different.
        img_filename = Path(cave_data.plan_images[plan_index]["image_path"]).name
        # Try creating path assuming image_dir/cave_id/filename structure
        image_path = self.image_dir / cave_data.cave_id / img_filename

        if not image_path.exists():
            # Fallback: try just image_dir/filename
            image_path = self.image_dir / img_filename
            if not image_path.exists():
                logger.error(f"Image file not found at {image_path}")
                return None

        logger.info(f"Loading image: {image_path}")
        # Load in color, opencv loads as BGR
        image_bgr: Optional[np.ndarray] = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if image_bgr is None:
            logger.error("Failed to decode image via OpenCV.")
            return None
        return image_bgr

    def save_geotiff(
        self,
        image_rgb: np.ndarray,
        transform: Affine,
        output_path: Path,
        crs_wkt: str,
    ):
        """Write the georeferenced image to a GeoTIFF."""
        height, width, bands = image_rgb.shape

        # Rasterio expects channels first (bands, height, width) for multichannel array
        # or we can write band by band. Writing band by band is safer here.

        try:
            with rasterio.open(
                output_path,
                "w",
                driver="GTiff",
                height=height,
                width=width,
                count=bands,  # usually 3 for RGB
                dtype=image_rgb.dtype,
                crs=crs_wkt,
                transform=transform,
                compress="lzw",  # Good lossless compression for plans
            ) as dst:
                for i in range(bands):
                    dst.write(image_rgb[:, :, i], i + 1)

            logger.info(f"Successfully saved GeoTIFF: {output_path}")
        except Exception as e:
            logger.error(f"Failed to save GeoTIFF: {e}")
            raise

    def save_kml(self, cave_data: CaveData, geotiff_path: Path, kml_path: Path):
        """Generate KML ground overlay from the GeoTIFF bounding box."""
        # 1. Read GeoTIFF bounds and CRS
        with rasterio.open(geotiff_path) as src:
            bounds_proj = src.bounds
            crs_proj = src.crs

        # 2. Transform bounds to WGS84 for KML
        transformer = Transformer.from_crs(crs_proj, "EPSG:4326", always_xy=True)

        # Transform corners to get bounding box in lat/lon
        lon_min, lat_min = transformer.transform(bounds_proj.left, bounds_proj.bottom)
        lon_max, lat_max = transformer.transform(bounds_proj.right, bounds_proj.top)

        # 3. Create KML
        kml = simplekml.Kml()
        ground = kml.newgroundoverlay(name=f"{cave_data.name} Plan")
        # KML expects relative path to the image if they are in same dir
        ground.icon.href = geotiff_path.name
        ground.latlonbox.north = max(lat_min, lat_max)
        ground.latlonbox.south = min(lat_min, lat_max)
        ground.latlonbox.east = max(lon_min, lon_max)
        ground.latlonbox.west = min(lon_min, lon_max)

        kml.save(str(kml_path))
        logger.info(f"Successfully saved KML: {kml_path}")

    def run(self, cave_id: str):
        """Main execution flow."""
        try:
            # 1. Load Data
            cave = self.load_cave_data(cave_id)
            if not cave:
                raise ValueError(f"Cave {cave_id} not found.")

            if cave.latitude == 0.0 and cave.longitude == 0.0:
                logger.warning(
                    "Cave has no valid coordinates (0,0). Georeferencing will place it at null island."
                )

            logger.info(f"Found cave: {cave.name} (Lon: {cave.longitude}, Lat: {cave.latitude})")

            # 2. Load Image
            image_bgr = self.load_image(cave)
            if image_bgr is None:
                raise ValueError("Could not load image.")

            self.gui.set_image(image_bgr)
            logger.info("Image loaded. Starting interaction sequence...")
            print("\n" + "=" * 40)
            print("INTERACTIVE GEOREFERENCING SEQUENCE")
            print("Follow instructions in terminal and image window.")
            print("Press ESC at any time to cancel.")
            print("=" * 40)

            # 3. Interaction Sequence
            # A) Entrance
            entrance_px = self.gui.mark_point("STEP 1: MARK CAVE ENTRANCE")
            logger.info(f"Entrance marked at: {entrance_px}")

            # B) Scale
            scale_ppm = self.gui.mark_line_and_get_scale()

            # C) North
            north_angle = self.gui.mark_north_arrow()

            # D) Magnetic Declination (Console only)
            print("\n--- MAGNETIC / MANUAL DECLINATION CORRECTION ---")
            declination_str = input(
                "Enter additional declination correction in degrees "
                "(usually 0 for plans already in geographic north; "
                "positive if the arrow is still magnetic): "
            ).strip()
            try:
                declination = float(declination_str) if declination_str else 0.0
            except ValueError:
                logger.warning(
                    f"Invalid declination input: '{declination_str}'. Defaulting to 0.0."
                )
                declination = 0.0
            logger.info(f"Additional (manual) declination used: {declination}")

            self.gui.close()

            # 4. Calculations
            params = GeoreferenceParams(
                entrance_pixel=entrance_px,
                scale_pixels_per_meter=scale_ppm,
                north_angle_degrees=north_angle,
                magnetic_declination=declination,
                # use_meridian_convergence left as default=True
            )

            # Target CRS: EPSG:2180 (PL-1992) - Good for Poland metric calculations
            target_crs_str = "EPSG:2180"
            transform_matrix = params.calculate_transform(
                cave.latitude, cave.longitude, target_crs=target_crs_str
            )
            logger.info(f"Final Affine Transform Matrix:\n{transform_matrix}")

            # 5. Export
            base_filename = f"{cave.cave_id}_{cave.inventory_number.replace(' ', '_')}"
            geotiff_path = self.output_dir / f"{base_filename}.tif"
            kml_path = self.output_dir / f"{base_filename}.kml"

            # Convert BGR to RGB for saving
            image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)

            # Get CRS WKT for Rasterio
            crs_wkt = CRS.from_string(target_crs_str).wkt

            self.save_geotiff(image_rgb, transform_matrix, geotiff_path, crs_wkt)
            self.save_kml(cave, geotiff_path, kml_path)

            print("\n" + "=" * 40)
            print("✅ DONE! Output files generated in:")
            print(f"-> {self.output_dir}")
            print("=" * 40)

        except Exception as e:
            self.gui.close()
            logger.error(f"An error occurred: {e}")
            sys.exit(1)


# --- CLI Entry Point ---


@click.command()
@click.option("--cave-id", required=True, help="ID of the cave to georeference.")
@click.option(
    "--caves-file",
    default="caves_transformed.jsonl",
    help="Path to JSONL data file.",
    show_default=True,
)
@click.option(
    "--image-dir",
    default="caves_upscaled",
    help="Directory containing cave images.",
    show_default=True,
)
@click.option(
    "--output-dir",
    default="georeferenced_output",
    help="Directory for output files.",
    show_default=True,
)
def main(cave_id, caves_file, image_dir, output_dir):
    """Interactive tool to georeference cave plans."""
    app = CavePlanGeoreferencerApp(caves_file, image_dir, output_dir)
    app.run(cave_id)


if __name__ == "__main__":
    main()
