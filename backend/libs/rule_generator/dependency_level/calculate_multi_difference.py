import pandas as pd
import numpy as np

def calculate_multi_difference(columnList):
    """Compute statistics for Euclidean distances between consecutive rows of multi-column data.

    Args:
        columnList: List of pandas.Series instances representing aligned features.

    Returns:
        dict: Statistical summary of the computed distances.
    """

    if not columnList or len(columnList) == 0:
        raise ValueError("Input list cannot be empty")

    first_len = len(columnList[0])
    if not all(len(col) == first_len for col in columnList):
        raise ValueError("All columns must have the same length")

    df = pd.concat(columnList, axis=1)
    is_numeric = df.apply(lambda x: pd.to_numeric(x, errors='coerce')).notna().all(axis=1)
    df_numeric = df[is_numeric].astype(float)
    
    if len(df_numeric) <= 1:
        return {
            "min": None,
            "max": None,
            "median": None,
            "std": None,
            "P1": None,
            "P5": None,
            "P10": None,
            "P90": None,
            "P95": None,
            "P99": None
        }
    
    differences = []
    for i in range(1, len(df_numeric)):
        diff_vector = df_numeric.iloc[i] - df_numeric.iloc[i-1]
        euclidean_dist = np.sqrt(np.sum(diff_vector ** 2))
        differences.append(euclidean_dist)
    
    differences = pd.Series(differences)
    
    # return empty stats when no valid distances were produced
    if len(differences) == 0:
        return {
            "min": None,
            "max": None,
            "median": None,
            "std": None,
            "P1": None,
            "P5": None,
            "P10": None,
            "P90": None,
            "P95": None,
            "P99": None
        }
    
    return {
        "min": float(differences.min()),
        "max": float(differences.max()),
        "median": float(differences.median()),
        "std": float(differences.std()),
        "P1": float(differences.quantile(0.01)),
        "P5": float(differences.quantile(0.05)),
        "P10": float(differences.quantile(0.1)),
        "P90": float(differences.quantile(0.9)),
        "P95": float(differences.quantile(0.95)),
        "P99": float(differences.quantile(0.99))
    }