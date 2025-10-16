"""
Google Earth Engine Helper Module
Handles satellite imagery retrieval and processing using GEE API
"""

import ee
import geemap
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import json
import streamlit as st

class GEEHelper:
    """Helper class for Google Earth Engine operations"""
    
    def __init__(self):
        """Initialize GEE with authentication"""
        try:
            # Check if service account credentials are available
            if os.environ.get('GEE_SERVICE_ACCOUNT'):
                credentials_json = os.environ.get('GEE_SERVICE_ACCOUNT')
                credentials_dict = json.loads(credentials_json)
                
                # Write temporary credentials file
                credentials_path = '/tmp/gee_credentials.json'
                with open(credentials_path, 'w') as f:
                    json.dump(credentials_dict, f)
                
                # Authenticate with service account
                credentials = ee.ServiceAccountCredentials(
                    credentials_dict['client_email'],
                    credentials_path
                )
                ee.Initialize(credentials)
                self.authenticated = True
                print("✅ GEE authenticated with service account")
            else:
                # Try default authentication
                ee.Initialize()
                self.authenticated = True
                print("✅ GEE authenticated with default credentials")
                
        except Exception as e:
            print(f"⚠️ GEE Authentication failed: {str(e)}")
            print("   Real satellite data will not be available")
            self.authenticated = False
    
    def get_imagery(self, lat, lon, start_date, end_date, satellite="Sentinel-2", max_cloud=20):
        """
        Retrieve satellite imagery for specified location and date range
        CACHED: Results cached for 1 hour to improve performance
        
        Args:
            lat (float): Latitude of center point
            lon (float): Longitude of center point
            start_date (datetime): Start date for imagery search
            end_date (datetime): End date for imagery search
            satellite (str): Satellite platform ('Sentinel-2', 'Landsat 8/9', 'MODIS')
            max_cloud (int): Maximum cloud coverage percentage
        
        Returns:
            dict: Dictionary containing imagery data and metadata
        """
        
        if not self.authenticated:
            print("⚠️ GEE not authenticated - cannot retrieve real satellite imagery")
            return None
        
        try:
            # Define area of interest
            point = ee.Geometry.Point([lon, lat])
            aoi = point.buffer(1000)  # 1km radius
            
            # Select appropriate collection based on satellite
            if satellite == "Sentinel-2":
                collection = ee.ImageCollection('COPERNICUS/S2_SR') \
                    .filterBounds(aoi) \
                    .filterDate(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')) \
                    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', max_cloud))
                
            elif satellite == "Landsat 8/9":
                collection = ee.ImageCollection('LANDSAT/LC08/C02/T1_L2') \
                    .merge(ee.ImageCollection('LANDSAT/LC09/C02/T1_L2')) \
                    .filterBounds(aoi) \
                    .filterDate(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')) \
                    .filter(ee.Filter.lt('CLOUD_COVER', max_cloud))
                
            elif satellite == "MODIS":
                collection = ee.ImageCollection('MODIS/061/MOD09GA') \
                    .filterBounds(aoi) \
                    .filterDate(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
            
            # Get the most recent image
            image = collection.sort('system:time_start', False).first()
            
            if image is None:
                return None
            
            # Extract band data
            imagery_data = self._extract_band_data(image, aoi, satellite)
            
            return imagery_data
            
        except Exception as e:
            print(f"❌ Error retrieving GEE imagery: {str(e)}")
            return None
    
    def _extract_band_data(self, image, aoi, satellite):
        """Extract band data from GEE image"""
        
        try:
            # Define band names based on satellite
            if satellite == "Sentinel-2":
                bands = ['B2', 'B3', 'B4', 'B8', 'B11', 'B12']  # Blue, Green, Red, NIR, SWIR1, SWIR2
                scale = 10
            elif satellite in ["Landsat 8/9"]:
                bands = ['SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B6', 'SR_B7']  # Blue, Green, Red, NIR, SWIR1, SWIR2
                scale = 30
            else:  # MODIS
                bands = ['sur_refl_b03', 'sur_refl_b04', 'sur_refl_b01', 'sur_refl_b02']  # Blue, Green, Red, NIR
                scale = 250
            
            # Get pixel values
            pixel_data = image.select(bands).reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=aoi,
                scale=scale,
                maxPixels=1e9
            ).getInfo()
            
            # Get image metadata
            properties = image.getInfo()['properties']
            
            return {
                'bands': pixel_data,
                'metadata': {
                    'satellite': satellite,
                    'date': properties.get('system:time_start'),
                    'cloud_cover': properties.get('CLOUDY_PIXEL_PERCENTAGE', properties.get('CLOUD_COVER', 0)),
                    'scale': scale
                },
                'geometry': aoi.getInfo()
            }
            
        except Exception as e:
            print(f"Error extracting band data: {str(e)}")
            return None
    
    def get_time_series(self, lat, lon, start_date, end_date, satellite="Sentinel-2"):
        """Get time series of imagery for temporal analysis"""
        
        if not self.authenticated:
            print("⚠️ GEE not authenticated - cannot retrieve time series data")
            return None
        
        try:
            point = ee.Geometry.Point([lon, lat])
            aoi = point.buffer(1000)
            
            # Get collection
            if satellite == "Sentinel-2":
                collection = ee.ImageCollection('COPERNICUS/S2_SR') \
                    .filterBounds(aoi) \
                    .filterDate(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')) \
                    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30))
            
            # Extract time series data
            time_series = []
            images = collection.limit(20).getInfo()  # Limit to 20 most recent images
            
            for img_info in images['features']:
                img = ee.Image(img_info['id'])
                data = self._extract_band_data(img, aoi, satellite)
                if data:
                    time_series.append(data)
            
            return time_series
            
        except Exception as e:
            print(f"❌ Error retrieving time series: {str(e)}")
            return None
    
    def get_historical_blooms(self, lat, lon, years_back=5, satellite="Sentinel-2"):
        """
        Detect historical algae blooms from satellite imagery
        CACHED: Results cached for 24 hours to improve performance
        
        Args:
            lat: Latitude
            lon: Longitude
            years_back: Number of years to analyze (default 5)
            satellite: Satellite to use
            
        Returns:
            List of detected bloom events with dates and severity
        """
        
        if not self.authenticated:
            print("⚠️ GEE not authenticated - cannot retrieve historical blooms")
            return []
        
        try:
            from utils.spectral_indices import SpectralIndicesCalculator
            
            point = ee.Geometry.Point([lon, lat])
            aoi = point.buffer(1000)
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365 * years_back)
            
            # Get collection
            if satellite == "Sentinel-2":
                collection = ee.ImageCollection('COPERNICUS/S2_SR') \
                    .filterBounds(aoi) \
                    .filterDate(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')) \
                    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 40))
                scale = 10
                bands = ['B2', 'B3', 'B4', 'B8', 'B11', 'B12']
            elif satellite == "Landsat 8/9":
                collection = ee.ImageCollection('LANDSAT/LC08/C02/T1_L2') \
                    .merge(ee.ImageCollection('LANDSAT/LC09/C02/T1_L2')) \
                    .filterBounds(aoi) \
                    .filterDate(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')) \
                    .filter(ee.Filter.lt('CLOUD_COVER', 40))
                scale = 30
                bands = ['SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B6', 'SR_B7']
            else:
                print(f"Satellite {satellite} not supported for historical analysis")
                return []
            
            # Get monthly composite images to reduce data volume
            detected_blooms = []
            spectral_calc = SpectralIndicesCalculator()
            
            # Process images monthly
            current_date = start_date
            while current_date < end_date:
                month_end = current_date + timedelta(days=30)
                
                # Get monthly median composite
                monthly_collection = collection.filterDate(
                    current_date.strftime('%Y-%m-%d'),
                    month_end.strftime('%Y-%m-%d')
                )
                
                image = monthly_collection.median()
                
                try:
                    # Extract band data
                    pixel_data = image.select(bands).reduceRegion(
                        reducer=ee.Reducer.mean(),
                        geometry=aoi,
                        scale=scale,
                        maxPixels=1e9
                    ).getInfo()
                    
                    # Check if we got valid data
                    if pixel_data and any(pixel_data.values()):
                        imagery_data = {
                            'bands': pixel_data,
                            'metadata': {
                                'satellite': satellite,
                                'date': int(current_date.timestamp() * 1000),
                                'scale': scale
                            }
                        }
                        
                        # Calculate spectral indices
                        indices = spectral_calc.calculate_all_indices(imagery_data)
                        
                        # Get chlorophyll-a and other indices (handle both dict and float formats)
                        chl_a_val = indices.get('Chlorophyll-a', 0)
                        chl_a = chl_a_val.get('mean', 0) if isinstance(chl_a_val, dict) else chl_a_val
                        
                        ndvi_val = indices.get('NDVI', 0)
                        ndvi = ndvi_val.get('mean', 0) if isinstance(ndvi_val, dict) else ndvi_val
                        
                        fai_val = indices.get('FAI (Floating Algae Index)', 0)
                        fai = fai_val.get('mean', 0) if isinstance(fai_val, dict) else fai_val
                        
                        # Detect if bloom occurred based on thresholds
                        bloom_detected = self._detect_bloom_from_indices(indices)
                        
                        # IMPORTANT: Return ALL data points, not just blooms
                        # The ML model needs complete time series to calculate growth trends
                        detected_blooms.append({
                            'date': current_date.strftime('%Y-%m-%d'),
                            'year': current_date.year,
                            'month': current_date.month,
                            'severity': bloom_detected['severity'] if bloom_detected else 'None',
                            'chlorophyll_a': chl_a,
                            'ndvi': ndvi,
                            'fai': fai,
                            'coverage_estimate': bloom_detected['coverage'] if bloom_detected else 0
                        })
                
                except Exception as e:
                    # Skip months with no data or errors
                    print(f"⚠️ Error processing month {current_date.strftime('%Y-%m')}: {str(e)}")
                    pass
                
                current_date = month_end
            
            # Count actual bloom events vs total data points
            bloom_count = sum(1 for b in detected_blooms if b['severity'] != 'None')
            print(f"✅ Retrieved {len(detected_blooms)} monthly data points ({bloom_count} blooms detected) from satellite data")
            return detected_blooms
            
        except Exception as e:
            print(f"Error retrieving historical blooms: {str(e)}")
            return []
    
    def _detect_bloom_from_indices(self, indices):
        """
        Determine if a bloom occurred based on spectral indices
        
        Uses scientific thresholds:
        - Chlorophyll-a > 10 μg/L indicates potential bloom
        - Chlorophyll-a > 20 μg/L indicates moderate bloom
        - Chlorophyll-a > 40 μg/L indicates severe bloom
        """
        
        chl_a = indices.get('Chlorophyll-a', {}).get('mean', 0)
        ndvi = indices.get('NDVI', {}).get('mean', 0)
        fai = indices.get('FAI (Floating Algae Index)', {}).get('mean', 0)
        
        # Bloom detection criteria
        bloom_threshold = chl_a > 10 or (ndvi > 0.3 and fai > 0.1)
        
        if not bloom_threshold:
            return None
        
        # Determine severity based on chlorophyll-a levels
        if chl_a > 40:
            severity = "Severe"
            coverage = min(100, 60 + (chl_a - 40) * 0.5)
        elif chl_a > 20:
            severity = "High"
            coverage = min(60, 30 + (chl_a - 20) * 1.5)
        elif chl_a > 10:
            severity = "Medium"
            coverage = min(30, 10 + (chl_a - 10))
        else:
            # Use NDVI and FAI as backup
            if ndvi > 0.5 or fai > 0.3:
                severity = "Medium"
                coverage = 20 + (ndvi * 30)
            else:
                severity = "Low"
                coverage = 10 + (ndvi * 20)
        
        return {
            'severity': severity,
            'coverage': coverage
        }
    
    def calculate_water_extent(self, imagery_data):
        """Calculate water extent using NDWI"""
        
        bands = imagery_data['bands']
        satellite = imagery_data['metadata']['satellite']
        
        if satellite == "Sentinel-2":
            green = bands.get('B3', 0)
            nir = bands.get('B8', 0)
        elif satellite in ["Landsat 8/9"]:
            green = bands.get('SR_B3', 0)
            nir = bands.get('SR_B5', 0)
        else:  # MODIS
            green = bands.get('sur_refl_b04', 0)
            nir = bands.get('sur_refl_b02', 0)
        
        # Calculate NDWI
        if (green + nir) != 0:
            ndwi = (green - nir) / (green + nir)
        else:
            ndwi = 0
        
        # Water extent based on NDWI threshold
        water_pixels = 1 if ndwi > 0 else 0
        total_pixels = 1
        
        return {
            'water_extent_percent': (water_pixels / total_pixels) * 100,
            'ndwi': ndwi
        }
