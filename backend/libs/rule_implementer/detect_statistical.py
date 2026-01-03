import pandas as pd
import numpy as np
from scipy import stats
from sklearn.cluster import DBSCAN

def detect_outlier(column, outlierMethod, **parameters):
    """
    Detect outliers in a data column using the specified method

    Parameters:
        column (pandas.Series): Data column to be checked
        outlierMethod (str): Outlier detection method ('zscore', 'modified_zscore', 'dbscan', 'iqr')
        parameters: Parameters required for each method
            zscore: threshold (default 3)
            modified_zscore: threshold (default 3.5)
            dbscan: eps (default 0.5), min_samples (default 2)
            iqr: factor (default 1.5)

    Returns:
        list: Index list of outliers
    """

    # Get indices and values of non-null values
    valid_indices = column[~pd.isna(column)].index
    valid_values_zscore = column[valid_indices]
    valid_values = column[valid_indices].values.reshape(-1, 1)
    
    if len(valid_values) == 0:
        return []
        
    outlier_indices = []
    
    if outlierMethod == 'zscore':
        threshold = parameters.get('threshold', 3)
        z_scores = np.abs(stats.zscore(valid_values_zscore))
        outlier_mask = z_scores > threshold
        outlier_indices = valid_indices[outlier_mask]
        
    elif outlierMethod == 'modified_zscore':
        threshold = parameters.get('threshold', 3.5)
        median = np.median(valid_values)
        mad = stats.median_abs_deviation(valid_values)
        modified_z_scores = 0.6745 * np.abs(valid_values - median) / mad
        outlier_mask = modified_z_scores > threshold
        outlier_indices = valid_indices[outlier_mask.flatten()]
        
    elif outlierMethod == 'dbscan':
        eps = parameters.get('eps', 0.5)
        min_samples = parameters.get('min_samples', 2)
        
        # Normalize data
        scaler = valid_values.std()
        if scaler == 0:  # Handle case where all values are the same
            return []
        normalized_values = valid_values / scaler
        
        dbscan = DBSCAN(eps=eps, min_samples=min_samples)
        clusters = dbscan.fit_predict(normalized_values)
        outlier_mask = clusters == -1
        outlier_indices = valid_indices[outlier_mask]
        
    elif outlierMethod == 'iqr':
        factor = parameters.get('factor', 1.5)
        Q1 = np.percentile(valid_values, 25)
        Q3 = np.percentile(valid_values, 75)
        IQR = Q3 - Q1
        lower_bound = Q1 - factor * IQR
        upper_bound = Q3 + factor * IQR
        outlier_mask = (valid_values < lower_bound) | (valid_values > upper_bound)
        outlier_indices = valid_indices[outlier_mask.flatten()]
        
    else:
        raise ValueError(f"Unsupported outlier detection method: {outlierMethod}")
        
    return sorted(list(outlier_indices))