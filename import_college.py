## Import College Scorecard Data
## Using API: https://github.com/18F/open-data-maker/blob/api-docs/API.md

## Load Libraries
import pandas as pd
import requests
import json
import csv

# Take arguments from the command line
if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description = 'Import College Scorecard Data')
    parser.add_argument('--year', default = 2011, help = 'Example: 2011')
    args = parser.parse_args()
    year = int(args.year)
else:
    year = 2011

## Get data.gov API key https://api.data.gov/signup/
with open('data_gov_api_key') as k:
    data_gov_api_key = k.read()

## Earnings columns from year
earnings_cols = ['admissions.act_scores.midpoint.cumulative', 
'admissions.sat_scores.average.overall', 
'cost.tuition.in_state', 'cost.tuition.out_of_state', 
'completion.completion_rate_4yr_150nt', 
'admissions.admission_rate.overall', 'earnings.10_yrs_after_entry.median', 
'earnings.10_yrs_after_entry.female_students',
'earnings.10_yrs_after_entry.male_students', 'cost.avg_net_price.public',
'cost.avg_net_price.private', 'cost.net_price.public.by_income_level.0-48000',
'cost.net_price.private.by_income_level.0-48000']

## Student cohort columns from year
student_cols = ['student.demographics.share_black.home_ZIP', 
'student.demographics.share_hispanic.home_ZIP',
'student.demographics.over_23_at_entry', 'student.demographics.female_share', 
'student.students_with_pell_grant',
'student.demographics.first_generation', 'student.demographics.avg_family_income_log',
'student.demographics.median_family_income',
'student.demographics.median_hh_income', 
'student.demographics.share_born_US.home_ZIP',
'student.demographics.share_bachelors_degree_age25.home_ZIP',
'student.size', 'student.demographics.median_hh_income_log']

## School columns from cohort year (10 years earlier)
school_cols = ['admissions.act_scores.midpoint.cumulative', 
'admissions.sat_scores.average.overall', 
'cost.tuition.in_state', 'cost.tuition.out_of_state', 
'completion.completion_rate_4yr_150nt', 
'admissions.admission_rate.overall', 'cost.avg_net_price.public',
'cost.avg_net_price.private',
'admissions.sat_scores.midpoint.critical_reading',
'admissions.sat_scores.midpoint.math',
'admissions.act_scores.25th_percentile.cumulative',
'admissions.act_scores.75th_percentile.cumulative']

## Query parameters
# Keep schools predominantly granting bachelor degrees 
# because they are the ones with ACT/SAT scores needed for model
# Remove for-profit schools beause we don't have enough data on them
school_params = 'school.degrees_awarded.predominant=3&school.operating=1&school.ownership=1,2'

## Query College Scorecard data
def query_college(page_num, year, school_params, school_cols, student_cols, 
    earnings_cols, data_gov_api_key):
    url_start = ('https://api.data.gov/ed/collegescorecard/v1/schools.json?'+school_params+
        '&api_key='+data_gov_api_key+'&_per_page=100&_page='+str(page_num)+
        '&_fields=id,school.name,school.city,school.state,school.minority_serving.predominantly_black'+
        ',school.minority_serving.historically_black,school.women_only'+
        ',school.degrees_awarded.predominant,school.ownership,school.operating,school.region_id'+
        ',school.locale,school.degree_urbanization,school.carnegie_basic')
    # Turn the list of columns into a string
    school_str = ''.join([','+str(year - 10)+'.'+colname for colname in school_cols])
    student_str = ''.join([','+str(year - 10)+'.'+colname for colname in student_cols])
    earnings_str = ''.join([','+str(year)+'.'+colname for colname in earnings_cols])
    # Run the query 
    url = (url_start+school_str+student_str+earnings_str)
    r = requests.get(url = url)
    d = json.loads(r.text)
    # Need to find the last page so that we can automatically pull all pages in
    last_page = int(d['metadata']['total'] / d['metadata']['per_page']) + 1
    df = pd.DataFrame(d['results'])
    total_num = d['metadata']['total']
    return(df, last_page, total_num)

def run_full_query(results, last_page, total_num):
    # Stack all of the pages into a single data frame
    for i in range(1, last_page):
        results = results.append(query_college(i, year, school_params, 
            school_cols, student_cols, earnings_cols, data_gov_api_key)[0])
    assert total_num == results.shape[0], 'Rows (%s) should equal query total count (%d)' % (results.shape[0], total_num) 
    assert len(results.id) == len(results.id.unique()), 'Duplicate school id numbers'
    return(results)

# Run the first page to get the initial results and the last page number
page_one_result, last_page, total_num = query_college(0, year, school_params, 
    school_cols, student_cols, earnings_cols, data_gov_api_key)
# Run the rest of the pages 
run_full_query(page_one_result, last_page, total_num).to_csv('college_raw.csv', index = False)
