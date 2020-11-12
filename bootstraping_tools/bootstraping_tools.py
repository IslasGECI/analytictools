#!/usr/bin/env python

import numpy as np
import pandas as pd

from scipy.optimize import curve_fit
from tqdm import tqdm


def power_law(T, Lambda, No):
    return No * np.power(Lambda, T)


def lambda_calculator(
    temporadas, maximo_nidos, max_iter=10000, lower_bounds=0, lambda_upper_bound=50
):
    temporadas = np.array(temporadas)
    numero_agno = temporadas - temporadas[0]
    maximo_nidos = np.array(maximo_nidos)
    popt, pcov = curve_fit(
        power_law,
        numero_agno,
        maximo_nidos,
        maxfev=max_iter,
        bounds=((lower_bounds, lower_bounds), (lambda_upper_bound, np.inf)),
    )
    return popt


def remove_distribution_outliers(data, multiplier=2.5):
    data = np.array(data)
    mean = np.mean(data)
    std = np.std(data)
    mask = abs(data - mean) < std * multiplier
    return data[mask]


def tukey_fences(data, multiplier=1.5):
    data = np.array(data)
    first_quantile = np.quantile(data, 0.25)
    third_quantile = np.quantile(data, 0.75)
    interquartile_range = third_quantile - first_quantile
    lower_limit = first_quantile - (interquartile_range * multiplier)
    upper_limit = third_quantile + (interquartile_range * multiplier)
    mask = (data > lower_limit) & (data < upper_limit)
    return data[mask]


def seasons_from_date(data):
    seasons = data["Fecha"].str.split("/", n=2, expand=True)
    return np.array(seasons[2])


def boostrapping_feature(data, N=2000):
    dataframe = pd.DataFrame(data)
    bootstrap_data = []
    for i in range(N):
        resampled_data = dataframe.sample(n=1, random_state=i)
        bootstrap_data.append(resampled_data.iloc[0][0])
    return bootstrap_data


def lambdas_from_bootstrap_table(dataframe, remove_outliers=True, outlier_method="tukey", **kwargs):
    lambdas_bootstraps = []
    seasons = np.array(dataframe.columns.values, dtype=int)
    N = len(dataframe)
    print("Calculating bootstrap growth rates distribution:")
    for i in tqdm(range(N)):
        fitting_result = lambda_calculator(seasons, dataframe.T[i].values)
        lambdas_bootstraps.append(fitting_result[0])
    if remove_outliers == True:
        if outlier_method == "tukey":
            lambdas_bootstraps = tukey_fences(lambdas_bootstraps, **kwargs)
        elif outlier_method == "std":
            lambdas_bootstraps = remove_distribution_outliers(lambdas_bootstraps, **kwargs)
        else:
            raise Exception("No se reconoce el método de filtrado")
    return lambdas_bootstraps


def lambdas_bootstrap_from_dataframe(
    dataframe,
    column_name,
    N=2000,
    return_distribution=False,
    remove_outliers=True,
    outlier_method="tukey",
    **kwargs
):
    bootstraped_data = pd.DataFrame()
    lambdas_bootstraps = []
    seasons = dataframe.sort_values(by="Temporada").Temporada.unique()
    print("Calculating samples per season:")
    for season in tqdm(seasons):
        data_per_season = dataframe[dataframe.Temporada == season]
        bootstraped_data[season] = boostrapping_feature(data_per_season[column_name], N)
    lambdas_bootstraps = lambdas_from_bootstrap_table(bootstraped_data)
    if remove_outliers == True:
        if outlier_method == "tukey":
            lambdas_bootstraps = tukey_fences(lambdas_bootstraps, **kwargs)
        elif outlier_method == "std":
            lambdas_bootstraps = remove_distribution_outliers(lambdas_bootstraps, **kwargs)
        else:
            raise Exception("No se reconoce el método de filtrado")
    if return_distribution == True:
        return lambdas_bootstraps, np.percentile(lambdas_bootstraps, [2.5, 50, 97.5])
    else:
        return np.percentile(lambdas_bootstraps, [2.5, 50, 97.5])


def get_bootstrap_interval(bootrap_interval):
    inferior_limit = np.around(bootrap_interval[1] - bootrap_interval[0], decimals=2)
    superior_limit = np.around(bootrap_interval[2] - bootrap_interval[1], decimals=2)
    bootrap_interval = np.around(bootrap_interval, decimals=2)
    return [inferior_limit, bootrap_interval[1], superior_limit]


def bootstrap_from_time_series(
    dataframe,
    column_name,
    N=2000,
    return_distribution=False,
    remove_outliers=True,
    outlier_method="tukey",
    **kwargs
):
    lambdas_bootstraps = []
    cont = 0
    rand = 0
    print("Calculating bootstrap growth rates distribution:")
    while cont < N:
        resampled_data = dataframe.sample(
            n=len(dataframe), replace=True, random_state=rand
        ).sort_index()
        try:
            fitting_result = lambda_calculator(
                resampled_data["Temporada"], resampled_data[column_name]
            )
        except RuntimeError:
            rand += 1
            continue
        lambdas_bootstraps.append(fitting_result[0])
        cont += 1
        rand += 1
    if remove_outliers == True:
        if outlier_method == "tukey":
            lambdas_bootstraps = tukey_fences(lambdas_bootstraps, **kwargs)
        elif outlier_method == "std":
            lambdas_bootstraps = remove_distribution_outliers(lambdas_bootstraps, **kwargs)
        else:
            raise Exception("No se reconoce el método de filtrado")
    if return_distribution == True:
        return lambdas_bootstraps, np.percentile(lambdas_bootstraps, [2.5, 50, 97.5])
    else:
        return np.percentile(lambdas_bootstraps, [2.5, 50, 97.5])


def calculate_p_values(distribution):
    distribution = np.array(distribution)
    mask = distribution < 1
    mask2 = distribution > 1
    return mask.sum() / len(distribution), mask2.sum() / len(distribution)
