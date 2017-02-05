## Prepare College Scorecard Raw Data for Analysis

## Load Libraries
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import statsmodels.formula.api as smf
from scipy import stats 

# Take arguments from the command line
if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description = 'Transform College Scorecard Data')
    parser.add_argument('--year', default = 2011, help = 'Example: 2011')
    args = parser.parse_args()
    year = int(args.year)
else:
    year = 2011

## Run data from import_college.py
df = pd.read_csv('college_raw.csv')
year = str(year)
year_cohort = str(int(year) - 10)

## Function to standardize a given column
def std_score(x):
    return((x - x.mean()) / x.std())

## Test Scores
# No exam N counts, so we can't do a weighted average
# Use standardized SAT score
df['sat_score'] = std_score(df[year_cohort+'.admissions.sat_scores.average.overall'])
# If missing use standardized ACT score
df['act_score'] = std_score(df[year_cohort+'.admissions.act_scores.midpoint.cumulative'])
df['score_sat_act'] = np.where(df['sat_score'].isnull(), df['act_score'], df['sat_score'])

## Average Net Price
# Use public net price if school is public
# Using average net price calculated in college scorecard data
df.loc[df['school.ownership'] == 1, 'avg_net_price_2011'] = df[year+'.cost.avg_net_price.public']
df.loc[df['school.ownership'] == 2, 'avg_net_price_2011'] = df[year+'.cost.avg_net_price.private']
# Avg net price for low income students
df.loc[df['school.ownership'] == 1, 'avg_net_price_lowinc_2011'] = df[year+'.cost.net_price.public.by_income_level.0-48000']
df.loc[df['school.ownership'] == 2, 'avg_net_price_lowinc_2011'] = df[year+'.cost.net_price.private.by_income_level.0-48000']

## Completion Rate
# Need to standardize completion rate as well 
df['completion_rate_std_2011'] = std_score(df[year+'.completion.completion_rate_4yr_150nt'])

## Take log of median earnings
df['log_earnings_10yr'] = np.log(df[year+'.earnings.10_yrs_after_entry.median'])
# df['log_fam_income'] = np.log(df[year_cohort+'.student.demographics.median_family_income'])

## Percent female from earnings cohort
df['total_cohort_n'] = df[[year+'.earnings.10_yrs_after_entry.female_students', year+'.earnings.10_yrs_after_entry.male_students']].sum(axis=1)
df['female_pct2'] = df[year+'.earnings.10_yrs_after_entry.female_students'] / df['total_cohort_n']

## Region
# Northeast, Mid-atlantic, and 'Far West' have much higher median incomes
df[['id', 'school.region_id', year+'.earnings.10_yrs_after_entry.median']].groupby('school.region_id').mean()
# ANOVA test for significance 
regiondf = df[['school.region_id', year+'.earnings.10_yrs_after_entry.median']].dropna()
regiondf = regiondf.groupby('school.region_id')
d = {}
for i in range(0, 10):
        d['region{0}'.format(i)] = regiondf.get_group(i)[year+'.earnings.10_yrs_after_entry.median']
stats.f_oneway(d['region0'], d['region1'], d['region2'], d['region3'], d['region4'], 
                            d['region5'], d['region6'], d['region7'], d['region8'], d['region9'])
# So we will give them a flag in the model
df['region_high_inc'] = 0
df.loc[df['school.region_id'].isin([0, 1, 2, 8]), 'region_high_inc'] = 1

## City, suburban, rural: more urban areas tend to have higher incomes
print(df[['school.locale', year+'.earnings.10_yrs_after_entry.median']].groupby('school.locale').mean())
df['urban_area'] = 0
df.loc[df['school.locale'].isin([11, 12, 13, 21, 22, 23, 31]), 'urban_area'] = 1

## Race/ethnicity based on 2001 student cohort 
df['pct_black'] = df[year_cohort+'.student.demographics.share_black.home_ZIP'] / 100
df['pct_hispanic'] = df[year_cohort+'.student.demographics.share_hispanic.home_ZIP'] / 100
df['black_or_hispanic_pct'] = df[['pct_black', 'pct_hispanic']].sum(axis=1)
df.loc[df['black_or_hispanic_pct'] > 1, 'black_or_hispanic_pct'] = 1

## Public ownership flag
df['public'] = 0
df.loc[df['school.ownership'] == 1, 'public'] = 1

## Born in USA: negative correlation with income
df['born_in_usa_pct'] = df[year_cohort+'.student.demographics.share_born_US.home_ZIP'] / 100

## Rename columns
df = df.rename(columns = {
    'school.name': 'school_name',
    'school.ownership': 'school_ownership',
    'school.state': 'school_state',
    'school.city': 'school_city',
    'school.region_id': 'region',
    year+'.earnings.10_yrs_after_entry.median': 'earnings_10yr',
    year_cohort+'.student.demographics.over_23_at_entry': 'overage23',
    year_cohort+'.student.students_with_pell_grant': 'pell_grant_pct',
    year_cohort+'.student.demographics.female_share': 'female',
    'school.minority_serving.historically_black': 'hb_univ',
    'school.women_only': 'women_only',
    year_cohort+'.student.demographics.share_bachelors_degree_age25.home_ZIP': 'pct_college_degree',
    year_cohort+'.student.demographics.median_family_income': 'median_family_income',
    year+'.admissions.sat_scores.average.overall': 'avg_sat_2011',
    year+'.admissions.act_scores.midpoint.cumulative': 'median_act_2011',
    year+'.completion.completion_rate_4yr_150nt': 'completion_rate_6yr_2011',
    year+'.admissions.admission_rate.overall': 'admission_rate_2011',
    year_cohort+'.student.demographics.first_generation': 'first_gen',
    year_cohort+'.student.demographics.median_hh_income': 'median_hh_income',
    year_cohort+'.student.demographics.median_hh_income_log': 'log_median_hh_income',
    'school.locale': 'locale',
    'school.degree_urbanization': 'locale2',
    year_cohort+'.student.size': 'enrollment',
    'school.carnegie_basic': 'carnegie_basic'
    })

## Remove Penn State campuses with indentical earnings
df = df.loc[df['school_name'].str.contains('Pennsylvania State University-Penn State') == False, ]

## Remove bible and nursing schools
print(df['carnegie_basic'].value_counts())
# print(df.loc[df['carnegie_basic'].isin([-2, 30, 24, 26, 29, 32, 27]), ['school_name', 'carnegie_basic']].sort_values('carnegie_basic'))
df = df.loc[df['carnegie_basic'].isin([15, 16, 17, 18, 19, 20, 21, 22, 27, 29, 32]), ]

## Remove specialized maritime academies 
df = df.loc[df['school_name'].str.contains('Maritime') == False, ]

## Remove U. Colorado Medical Campus
df = df.loc[df['school_name'].str.contains('Anschutz') == False, ]

## Remove schools in Puerto Rico
df = df.loc[df['school_state'] != 'PR', ]

## Remove schools without earnings cohort
df = df.loc[df['earnings_10yr'].notnull(), ]

## Remove schools with missing test scores
df = df.loc[df['score_sat_act'].notnull(), ]

## Use female_pct2 if female is missing
df['female_pct'] = np.where(df['female'].isnull(), df['female_pct2'], df['female'])

## Impute with average for remaining missing values 
# print(df.loc[(df['female_pct'].isnull()) | (df['pell_grant_pct'].isnull()), ['school_name', 'school_state', 'region', 'female_pct', 'pell_grant_pct']])
df.loc[df['female_pct'].isnull(), 'female_pct'] = df['female_pct'].mean()
df.loc[df['pell_grant_pct'].isnull(), 'pell_grant_pct'] = df['pell_grant_pct'].mean()

## Clean file ready for analysis
df.to_csv('college_cleaned.csv', index = False)

## Correlation table
print(df[['log_earnings_10yr', 'born_in_usa_pct', 'pct_college_degree',
    'score_sat_act', 'female_pct', 'region_high_inc', 'median_hh_income',
    'pell_grant_pct', 'locale', 'enrollment', 'urban_area']].corr().round(2))
