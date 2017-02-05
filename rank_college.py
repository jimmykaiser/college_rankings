## Produce College Rankings
## Based on Earnings Outcomes

## Load Libraries
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import statsmodels.formula.api as sm
from scipy import stats 
from sklearn.model_selection import KFold
from sklearn.metrics import mean_squared_error
from statsmodels.stats.outliers_influence import variance_inflation_factor

## Function to standardize a given column
def std_score(x):
    return((x - x.mean()) / x.std())

## Initialize random number generator
# So that kfold produces the same cuts
np.random.seed(2001)

## Import clean data set from transform_college.py
df = pd.read_csv('college_cleaned.csv')

info_cols = ['score_sat_act', 'pell_grant_pct', 'born_in_usa_pct',
    'female_pct', 'region_high_inc', 'urban_area', 'enrollment',
    'black_or_hispanic_pct', 'overage23', 'median_hh_income', 
    'avg_sat_2011', 'median_act_2011', 'avg_net_price_2011', 
    'avg_net_price_lowinc_2011', 'admission_rate_2011', 
    'completion_rate_6yr_2011']

## OLS Linear Model
id_vars = ['id', 'school_name', 'school_city', 'school_state',
'region', 'public']
y_var = 'log_earnings_10yr'
discrete_vars = ['region_high_inc', 'urban_area']
cont_vars = ['score_sat_act', 'female_pct', 'born_in_usa_pct', 
'pell_grant_pct', 'enrollment']

## Columns needed for model
dfmod = df[id_vars + [y_var] + cont_vars + discrete_vars].copy()
print(dfmod.shape)

## Standardize continuous columns 
for var in cont_vars:
    dfmod[var] = std_score(dfmod[var])

## Features and dependent variable
y = dfmod[y_var]
X = dfmod.drop(id_vars + [y_var], 1)
## Check for multicollinearity 
vif = [variance_inflation_factor(X.values, i) for i in range(X.shape[1])]
n = 0
print('variance inflation factors')
for x in X.columns:
    print(x, vif[n].round(3))
    n += 1

## Cross validation
# Create a fold object to organize cross validation
X['intercept'] = 1
kf = KFold(n_splits = 5, shuffle = True)
kf.get_n_splits(X)
all_scores = []

# Get indices of corresponding train & test
for train, test in kf.split(X):
    x_train = X.iloc[train]
    y_train = y.iloc[train]
    x_test = X.iloc[test]
    y_test = y.iloc[test]
    pvals = []
    sig_cols = []
    
    model = sm.OLS(y_train, x_train)
    est = model.fit()
    pvals = est.pvalues.sort_values()
    
    y_train_pred = est.predict(x_train)
    y_test_pred = est.predict(x_test)

    r_2 = est.rsquared
    all_scores.append(r_2)
    # Summary of R2 and pvalues for each of the five folds
    # Folds should be similar to each other
    print('R2 =', round(r_2, 3))
    print(est.pvalues.sort_values())
    
# Summary of the last model (out of N folds)
print(est.summary())
f = open('summary.txt', 'a')
print(est.summary(), file = f)

## Calculate means of predicted Ys
mean_y_test = np.mean(y_test)
mean_y_train = np.mean(y_train)

## Find R2 for train and test; should be close
train_r2 = (1 - (mean_squared_error(y_train, 
    y_train_pred)/mean_squared_error([mean_y_train]*len(y_train), 
    y_train)))
test_r2 = (1 - (mean_squared_error(y_test, 
    y_test_pred)/mean_squared_error([mean_y_test]*len(y_test), 
    y_test)))
print('Train R2 =', round(train_r2, 3))
print('Test R2 =', round(test_r2, 3))

## Plot of model residuals 
est.resid.plot(style = 'o').get_figure().savefig('./plots/resid.png')

## Get predicted values
dfmod['pred_ols'] = est.predict(X)

## Get residuals and predictions in dollar terms
dfmod = pd.merge(dfmod, df[['id', 'earnings_10yr']], on = 'id')
# OLS
dfmod['diff_ols'] = dfmod['log_earnings_10yr'] - dfmod['pred_ols']
print(dfmod['diff_ols'].describe().round(2))
dfmod['pred_earnings_10yr_ols'] = np.exp(dfmod['pred_ols'])

## Plot of predicted versus real 10 year income
def make_scatter(df, var1, var2, labx, laby):
    x = df[var1]
    y = df[var2]
    plt.subplots(figsize = (8, 6))
    plt.xlabel(labx)
    plt.ylabel(laby)
    plt.scatter(x, y)
    return(plt)
make_scatter(dfmod, 'pred_earnings_10yr_ols', 'earnings_10yr', 
    'Predicted Earnings', 'Real Earnings').savefig('./plots/preds.png')

make_scatter(dfmod, 'born_in_usa_pct', 'log_earnings_10yr', 
    'Percent Born in USA', 'Log Earnings').savefig('./plots/born_usa.png')

## Standardized score based on how well schools performed relative to predicted earnings
dfmod['score'] = std_score(dfmod['diff_ols']).round(2)
plt.subplots(figsize = (8, 6))
plt.xlabel('Score')
plt.ylabel('Number of Schools')
plt.hist(dfmod['score'], 50)
plt.savefig('./plots/scores.png')

## Set ratings based on standard deviation cutoffs 
# Most schools get middle rating: performed as expected
dfmod.loc[dfmod['score'] >= 0.5, 'rating'] = 4
dfmod.loc[dfmod['score'] >= 1.5, 'rating'] = 5
dfmod.loc[dfmod['score'] < 0.5, 'rating'] = 3
dfmod.loc[dfmod['score'] <= -0.5, 'rating'] = 2
dfmod.loc[dfmod['score'] <= -1.5, 'rating'] = 1

## Rank order
dfmod = dfmod.sort_values('score', ascending = False).reset_index(drop = True)
dfmod['rank'] = dfmod.index + 1

## Round predictions
dfmod['pred_earnings_10yr_ols'] = dfmod['pred_earnings_10yr_ols'].round()

## Number of schools by rating
print(dfmod[['id', 'rating']].groupby('rating').count())

## Drop standardized columns
dfmod = dfmod.drop(cont_vars + discrete_vars, 1)

## Add columns to dataframe
dfmod = pd.merge(dfmod, df[['id'] + info_cols], on = 'id')

## Net price by score
make_scatter(dfmod, 'avg_net_price_lowinc_2011', 'score', 
    'Average Net Price for 0-48k Income in 2011', 'Score').savefig('./plots/price.png')

## Ratings by region
print(pd.crosstab(dfmod['rating'], dfmod['region']))

## Ratings public vs. private
print(pd.crosstab(dfmod['rating'], dfmod['public']))

## Percent public overall
print('Percent public =', round(dfmod['public'].mean(), 3))

## Format and export rankings to file
csv_cols = ['rank', 'school_name', 'school_city', 'school_state', 'rating', 'score', 
    'earnings_10yr', 'pred_earnings_10yr_ols', 'public'] + info_cols
dfmod = dfmod[csv_cols]
for var in info_cols:
	dfmod[var] = dfmod[var].round(2)
dfmod.to_csv('college_rankings.csv', index = False)

## Means by rating
means_by_rating = dfmod.groupby('rating').mean().round(2).reset_index()
means_by_rating.to_csv('college_means.csv')
print(means_by_rating)

