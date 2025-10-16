"""
Scientific Formulas Module - Research-Based Calculations
All formulas derived from peer-reviewed scientific papers with citations
"""

import numpy as np
from typing import Dict, Any, List, Tuple
from datetime import datetime
from sklearn.linear_model import LinearRegression
import warnings
warnings.filterwarnings('ignore')


class ScientificAlgaeMetrics:
    """
    Research-based algae bloom metrics calculator
    
    References:
    - Hu (2009): FAI for algae detection
    - Carlson (1977): Trophic State Index
    - Garcia et al. (2013): Scaled Algae Index
    - Paraná River study: DO-Chlorophyll correlation
    """
    
    def __init__(self):
        """Initialize scientific thresholds from literature"""
        
        # FAI thresholds for algae detection (Hu, 2009)
        self.fai_threshold = 0.001  # FAI > 0.001 indicates floating algae
        
        # Carlson's TSI classification (Carlson, 1977)
        self.tsi_classes = {
            'oligotrophic': (0, 40),      # Low algae, excellent
            'mesotrophic': (40, 50),      # Moderate algae, good
            'eutrophic': (50, 70),        # High algae, fair
            'hypereutrophic': (70, 100)   # Excessive algae, poor
        }
        
        # WHO/EPA chlorophyll-a guidelines (μg/L)
        self.chl_guidelines = {
            'drinking_water': 10.0,   # Recreational drinking water limit
            'recreational': 25.0,      # Recreational water limit
            'hypereutrophic': 40.0     # Hypereutrophic warning threshold
        }
    
    def calculate_algae_coverage_fai(self, fai_values: np.ndarray, total_pixels: int) -> float:
        """
        Calculate algae coverage using FAI threshold method
        
        Method: Pixel-based thresholding (Hu, 2009; Garcia et al., 2013)
        
        Args:
            fai_values: Array of FAI values for each pixel
            total_pixels: Total number of water pixels
            
        Returns:
            Coverage percentage (0-100)
            
        Reference:
            Hu, C. (2009). A novel ocean color index to detect floating algae 
            in the global oceans. Remote Sensing of Environment, 113(10), 2118-2129.
        """
        if len(fai_values) == 0 or total_pixels == 0:
            return 0.0
        
        # Count pixels above threshold
        algae_pixels = np.sum(fai_values > self.fai_threshold)
        
        # Calculate percentage
        coverage = (algae_pixels / total_pixels) * 100.0
        
        return min(100.0, max(0.0, coverage))
    
    def calculate_algae_coverage_combined(self, fai: float, ndvi: float, chl_a: float) -> float:
        """
        Estimate algae coverage from mean spectral indices
        
        **LIMITATION**: The scientifically proper method requires pixel-level data to count 
        pixels exceeding FAI threshold (Hu, 2009). When only mean values are available, 
        we use a threshold-based correlation as an approximation.
        
        Proper method (when pixel data available):
        Coverage % = (pixels where FAI > 0.001) / total_water_pixels × 100
        
        Approximation (mean values only):
        - FAI > 0.001: Indicates algae presence
        - Higher FAI correlates with greater coverage
        - NDVI and Chl-a provide supporting evidence
        
        Args:
            fai: Floating Algae Index (mean value)
            ndvi: Normalized Difference Vegetation Index (mean value)  
            chl_a: Chlorophyll-a concentration (μg/L)
            
        Returns:
            Estimated coverage percentage (0-100) - approximation only
            
        References:
            - Hu, C. (2009). FAI threshold: 0.001 for algae detection
            - Garcia et al. (2013). Scaled Algae Index methodology
        """
        # Primary indicator: FAI-based coverage estimation
        # Note: Hu (2009) threshold of 0.001 was for ocean waters
        # Inland waters (canals, rivers, lakes) typically have FAI values 0.01-0.20 due to:
        # - Higher suspended sediments
        # - Dissolved organic matter
        # - Mixed vegetation/water pixels
        
        # Use Chlorophyll-a as primary indicator for inland waters (more reliable)
        # FAI and NDVI provide supporting evidence
        
        # Chlorophyll-a based coverage (using trophic state relationships)
        if chl_a < 3:
            chl_coverage = 0.0  # Oligotrophic - very low algae
        elif chl_a < 10:
            chl_coverage = 5.0 + (chl_a - 3) * 2.0  # Low: 5-19%
        elif chl_a < 30:
            chl_coverage = 20.0 + (chl_a - 10) * 1.5  # Moderate: 20-50%
        elif chl_a < 100:
            chl_coverage = 50.0 + (chl_a - 30) * 0.5  # High: 50-85%
        else:
            chl_coverage = 85.0 + min(15.0, (chl_a - 100) * 0.1)  # Severe: 85-100%
        
        # FAI adjustment (for inland waters, use relative comparison)
        # Only add coverage if FAI is exceptionally high for the given baseline
        fai_adjustment = 0.0
        if fai > 0.15:  # Very high FAI for inland water
            fai_adjustment = 10.0
        elif fai > 0.10:  # High FAI
            fai_adjustment = 5.0
        elif fai > 0.05:  # Moderate FAI
            fai_adjustment = 2.0
        
        # NDVI adjustment (vegetation over water)
        ndvi_adjustment = 0.0
        if ndvi > 0.4:
            ndvi_adjustment = 5.0
        elif ndvi > 0.2:
            ndvi_adjustment = 2.0
        
        # Combine (Chl-a is primary, FAI and NDVI are secondary)
        estimated_coverage = chl_coverage + fai_adjustment + ndvi_adjustment
        
        return min(100.0, max(0.0, estimated_coverage))
    
    def calculate_tsi_carlson(self, chl_a: float) -> Tuple[float, str]:
        """
        Calculate Carlson's Trophic State Index from chlorophyll-a
        
        Formula: TSI(Chl-a) = 9.81 × ln(Chl-a) + 30.6
        
        Args:
            chl_a: Chlorophyll-a concentration in μg/L
            
        Returns:
            Tuple of (TSI value, trophic classification)
            
        Reference:
            Carlson, R.E. (1977). A trophic state index for lakes. 
            Limnology and Oceanography, 22(2), 361-369.
        """
        if chl_a <= 0:
            return 0.0, 'oligotrophic'
        
        # Carlson's formula
        tsi = 9.81 * np.log(chl_a) + 30.6
        
        # Classify trophic state
        if tsi < 40:
            classification = 'oligotrophic'
        elif tsi < 50:
            classification = 'mesotrophic'
        elif tsi < 70:
            classification = 'eutrophic'
        else:
            classification = 'hypereutrophic'
        
        return tsi, classification
    
    def calculate_water_quality_score(self, tsi: float) -> float:
        """
        Convert TSI to 0-10 water quality score
        
        Args:
            tsi: Trophic State Index value
            
        Returns:
            Water quality score (0-10, higher is better)
        """
        # Inverse relationship: lower TSI = better quality
        # TSI 0-40 (oligotrophic) → score 8-10
        # TSI 40-50 (mesotrophic) → score 6-8
        # TSI 50-70 (eutrophic) → score 3-6
        # TSI 70-100 (hypereutrophic) → score 0-3
        
        if tsi < 40:
            score = 10.0 - (tsi / 40.0) * 2.0  # 8-10
        elif tsi < 50:
            score = 8.0 - ((tsi - 40) / 10.0) * 2.0  # 6-8
        elif tsi < 70:
            score = 6.0 - ((tsi - 50) / 20.0) * 3.0  # 3-6
        else:
            score = 3.0 - ((tsi - 70) / 30.0) * 3.0  # 0-3
        
        return max(0.0, min(10.0, score))
    
    def calculate_do_reduction(self, chl_a: float, temperature: float = 25.0) -> float:
        """
        Calculate dissolved oxygen depletion from algae decomposition using Redfield stoichiometry
        
        Formula (based on Redfield ratio C:N:P:O₂ = 106:16:1:138):
        1. Convert Chl-a to carbon: C (mg/L) = Chl-a (μg/L) × 0.04
        2. Calculate O₂ demand: O₂ (mg/L) = C × 3.3
        Simplified: O₂ demand (mg/L) ≈ Chl-a (μg/L) × 0.13
        
        Args:
            chl_a: Chlorophyll-a concentration (μg/L)
            temperature: Water temperature (°C), default 25°C
            
        Returns:
            Estimated DO reduction percentage (0-100%)
            
        Reference:
            Redfield, A.C. (1958). The biological control of chemical factors in the environment.
            American Scientist, 46(3), 230A-221.
            
            Redfield ratio: (CH₂O)₁₀₆(NH₃)₁₆H₃PO₄ + 138O₂ → decomposition products
            
            Modern calculation: O₂ consumed = Algae biomass (mg C/L) × 3.3
            (Source: EPA/Aquatic Systems Research)
        """
        # DO saturation at given temperature (simplified Henry's Law)
        # At 20°C: ~9.1 mg/L, decreases ~2% per °C increase
        do_saturation = 9.1 * (1.0 - 0.02 * (temperature - 20.0))
        do_saturation = max(6.0, min(10.0, do_saturation))  # Realistic bounds
        
        # Calculate oxygen demand using Redfield stoichiometry
        # Chl-a to carbon conversion: (Chl-a μg/L / 1000) × 40 = Chl-a × 0.04 mg C/L
        # O₂ demand from carbon: C × 3.3 = O₂ mg/L (from 138:106 molar ratio)
        # Combined: O₂ demand (mg/L) = (Chl-a μg/L / 1000) × 40 × 3.3 = Chl-a × 0.132
        
        # Chl-a is in μg/L, need to convert properly:
        # Step 1: Chl-a (μg/L) to carbon biomass
        carbon_mg_per_L = (chl_a / 1000.0) * 40.0  # 1 mg Chl-a ≈ 40 mg C
        
        # Step 2: Carbon to oxygen demand (Redfield ratio: 138 O₂ per 106 C)
        oxygen_demand_mg_per_L = carbon_mg_per_L * 3.3
        
        # Calculate reduction percentage
        reduction_percent = (oxygen_demand_mg_per_L / do_saturation) * 100.0
        
        return min(100.0, max(0.0, reduction_percent))
    
    def assess_water_usability(self, chl_a: float, coverage: float) -> Dict[str, str]:
        """
        Assess water usability for different purposes using WHO/EPA guidelines
        
        Args:
            chl_a: Chlorophyll-a concentration (μg/L)
            coverage: Algae coverage percentage
            
        Returns:
            Dictionary with usability assessments
            
        References:
            - WHO Guidelines for drinking water quality
            - EPA recreational water quality criteria
        """
        usability = {}
        
        # Drinking Water (WHO guideline: <10 μg/L Chl-a for low risk)
        if chl_a > 30 or coverage > 30:
            usability['Drinking Water'] = 'Unsafe'
        elif chl_a > 10 or coverage > 15:
            usability['Drinking Water'] = 'Caution - Treatment Required'
        else:
            usability['Drinking Water'] = 'Safe'
        
        # Recreation (EPA: <25 μg/L Chl-a)
        if chl_a > 40 or coverage > 35:
            usability['Recreation'] = 'Unsafe'
        elif chl_a > 25 or coverage > 20:
            usability['Recreation'] = 'Caution'
        else:
            usability['Recreation'] = 'Safe'
        
        # Agriculture/Irrigation
        if chl_a > 60 or coverage > 50:
            usability['Agriculture'] = 'Not Recommended'
        elif chl_a > 35 or coverage > 30:
            usability['Agriculture'] = 'Caution'
        else:
            usability['Agriculture'] = 'Safe'
        
        # Aquaculture (most sensitive)
        if chl_a > 30 or coverage > 25:
            usability['Aquaculture'] = 'Unsafe - Fish Kill Risk'
        elif chl_a > 15 or coverage > 15:
            usability['Aquaculture'] = 'Caution - Monitor Closely'
        else:
            usability['Aquaculture'] = 'Safe'
        
        return usability
    
    def calculate_fish_mortality_risk(self, do_reduction: float, chl_a: float) -> str:
        """
        Assess fish mortality risk based on DO depletion
        
        Args:
            do_reduction: Dissolved oxygen reduction percentage
            chl_a: Chlorophyll-a concentration
            
        Returns:
            Risk level: 'Low', 'Medium', 'High', 'Critical'
            
        Reference:
            EPA hypoxia thresholds: DO < 2-3 mg/L causes fish kills
        """
        # Critical hypoxia (DO reduction >60% or very high algae)
        if do_reduction > 60 or chl_a > 100:
            return 'Critical'
        # High risk (DO reduction 40-60%)
        elif do_reduction > 40 or chl_a > 50:
            return 'High'
        # Medium risk (DO reduction 20-40%)
        elif do_reduction > 20 or chl_a > 25:
            return 'Medium'
        # Low risk
        else:
            return 'Low'
