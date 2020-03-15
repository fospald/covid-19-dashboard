
import csv
import sys
import datetime
import time
import copy
import json
from functools import cmp_to_key


ref_time = datetime.datetime(1970,1,1)

data = {}
global_case = {'id': 'World/', 'province': '', 'country': 'World', 'lat': 0.0, 'lng': 0.0, 'is_group': True}

for k in ["Confirmed", "Recovered", "Deaths"]:
    ts_key = 'timeseries_' + k.lower()

    fn = "COVID-19/csse_covid_19_data/csse_covid_19_time_series/time_series_19-covid-" + k + ".csv"
    with open(fn) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        line_count = 0
        for row in csv_reader:

            if line_count == 0:
                header = row

                current_day = datetime.datetime.strptime(row[-1], '%m/%d/%y')
                current_day_data_fn = "COVID-19/csse_covid_19_data/csse_covid_19_daily_reports/%s.csv" % current_day.strftime('%m-%d-%Y')
                with open(current_day_data_fn) as cd_csv_file:
                    cd_csv = csv.reader(cd_csv_file, delimiter=',')
                    cd_line_count = 0
                    cd_data = {}
                    for cd_row in cd_csv:
                        if cd_line_count == 0:
                            cd_line_count += 1
                            continue
                        # fix UK bug
                        if cd_row[0] == cd_row[1]:
                            cd_row[0] = ""
                        cd_key = cd_row[1] + '/' + cd_row[0]
                        # Province/State,Country/Region,Last Update,Confirmed,Deaths,Recovered,Latitude,Longitude
                        cd_data[cd_key] = {'last_update': cd_row[2], 'confirmed': int(cd_row[3]), 'deaths': int(cd_row[4]), 'recovered': int(cd_row[5])}
                        cd_line_count += 1


                for i in range(4,len(row)):
                    header[i] = int((datetime.datetime.strptime(row[i], '%m/%d/%y') - ref_time).total_seconds())

                line_count += 1
                continue
                
            line_count += 1

            # fix UK bug
            if row[0] == row[1]:
                row[0] = ""

            key = row[1] + '/' + row[0]
            if key in data:
                rec = data[key]
            else:
                rec = {'id': key, 'province': row[0], 'country': row[1], 'lat': float(row[2]), 'lng': float(row[3])}

            timeseries = {}
            for i in range(4,len(row)):
                if row[i] == "":
                    if i+1 == len(row) and key in cd_data:
                        timeseries[header[i]] = cd_data[key][k.lower()]
                        continue
                    break
                timeseries[header[i]] = int(row[i])

            rec[ts_key] = timeseries
            data[key] = rec

    # group by country
    keys = list(data.keys())
    for key in keys:
        if data[key]['province'].strip() != "":
            group_key = data[key]['country'] + '/'
            if group_key in data:
                new_group_data = data[group_key]
                add_timeseries = copy.deepcopy(data[key][ts_key])
                if ts_key in new_group_data:
                    for k,v in add_timeseries.items():
                        if k in new_group_data[ts_key]:
                            new_group_data[ts_key][k] += v
                        else:
                            new_group_data[ts_key][k] = v
                else:
                    new_group_data[ts_key] = add_timeseries
            else:
                new_group_data = copy.deepcopy(data[key])
                new_group_data['id'] = group_key
                new_group_data['province'] = ''
                new_group_data['is_group'] = True
            data[group_key] = new_group_data


    # global group
    keys = list(data.keys())
    for key in keys:
        if not "is_group" in data[key]:
                add_timeseries = copy.deepcopy(data[key][ts_key])
                if ts_key in global_case:
                    for k,v in add_timeseries.items():
                        if k in global_case[ts_key]:
                            global_case[ts_key][k] += v
                        else:
                            global_case[ts_key][k] = v
                else:
                    global_case[ts_key] = add_timeseries

data[global_case["id"]] = global_case

# add german province data
for k in ["Confirmed"]:
    ts_key = 'timeseries_' + k.lower()
    fn = "COVID-19-Germany/germany_with_source.csv"
    with open(fn) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        line_count = 0
        for row in csv_reader:

            if line_count == 0:
                header = row
                line_count += 1
                continue
                
            line_count += 1

            date = int((datetime.datetime.strptime(row[1], '%m/%d/%Y') - ref_time).total_seconds())
            country = "Germany"

            
            key = country + '/' + row[2] + '/' + row[3] # with district

            if key in data:
                rec = data[key]
            else:
                try:
                    ts = {}
                    rec = {'id': key, 'province': row[3] + ", " + row[2], 'state': row[2], 'district': row[3], 'country': country, 'lat': float(row[4]), 'lng': float(row[5]), ts_key: ts}
                except:
                    continue

            if date in rec[ts_key]:
                rec[ts_key][date] += 1
            elif "last_date" in rec:
                rec[ts_key][date] = rec[ts_key][rec["last_date"]] + 1
            else:
                rec[ts_key][date] = 1

            rec["last_date"] = date
            data[key] = rec


            # add province grouped items

            key = country + '/' + row[2] + '/'

            if key in data:
                rec = data[key]
            else:
                try:
                    rec = {'id': key, 'province': row[2], 'country': country, 'lat': float(row[4]), 'lng': float(row[5]), ts_key: {}, 'is_group': True}
                except:
                    continue

            if date in rec[ts_key]:
                rec[ts_key][date] += 1
            elif "last_date" in rec:
                rec[ts_key][date] = rec[ts_key][rec["last_date"]] + 1
            else:
                rec[ts_key][date] = 1

            rec["last_date"] = date
            data[key] = rec


    data['Germany/']['is_group_confirmed'] = True


def comp_active(cs):
    # compute active cases
        timeseries_active = {}
        if not "timeseries_confirmed" in cs:
            return None
        if not "timeseries_deaths" in cs:
            return None
        if not "timeseries_recovered" in cs:
            return None
        for date, confirmed in cs["timeseries_confirmed"].items():
            if not date in cs["timeseries_deaths"]:
                continue
            if not date in cs["timeseries_recovered"]:
                continue
            timeseries_active[date] = cs["timeseries_confirmed"][date] - cs["timeseries_deaths"][date] - cs["timeseries_recovered"][date]
        return timeseries_active


keys = list(data.keys())
for key in keys:
    timeseries_active = comp_active(data[key])
    if timeseries_active:
        data[key]["timeseries_active"] = timeseries_active

# calculate distance to earest neighbour

min_date = 10000000000000
max_date = 0
for k1 in data.keys():
    radius = 10000
    for k2 in data.keys():
        if k2 == k1:
            continue

        dx = data[k1]['lat'] - data[k2]['lat'];
        dy = data[k1]['lng'] - data[k2]['lng'];
        r = (dx*dx + dy*dy)**0.5
        if r < radius:
            radius = r
    data[k1]['approx_radius'] = radius;

    min_date = min(min_date, min(data[k1]['timeseries_confirmed'].keys()))
    max_date = max(max_date, max(data[k1]['timeseries_confirmed'].keys()))


# complete missing dates
for k in data.keys():
    for ts in ["Confirmed", "Recovered", "Deaths", "Active"]:
        ts_key = 'timeseries_' + ts.lower()
        last_val = None
        if not ts_key in data[k]:
            continue
        for date in range(min_date, max_date + 24*60*60, 24*60*60):
            if date in data[k][ts_key]:
                last_val = data[k][ts_key][date]
            elif not last_val is None:
                data[k][ts_key][date] = last_val


def cmp_by_name(x, y):
    if x["country"] == global_case["country"]:
        return -1
    if y["country"] == global_case["country"]:
        return 1
    if x["country"] == y["country"]:
        return 1 if x["province"] > y["province"] else -1
    return 1 if x["country"] > y["country"] else -1
data_by_name = data.values()
data_by_name.sort(key=cmp_to_key(cmp_by_name))
keys_by_name = [c['id'] for c in data_by_name]

def cmp_by_confirmed(x, y):
    if not "timeseries_confirmed" in x or not "timeseries_confirmed" in y:
        return -1
    return y["timeseries_confirmed"][max_date] - x["timeseries_confirmed"][max_date]
data_by_confirmed = data.values()
data_by_confirmed.sort(key=cmp_to_key(cmp_by_confirmed))
keys_by_confirmed = [c['id'] for c in data_by_confirmed]

def cmp_by_deaths(x, y):
    if not "timeseries_deaths" in x or not "timeseries_deaths" in y:
        return -1
    return y["timeseries_deaths"][max_date] - x["timeseries_deaths"][max_date]
data_by_deaths = data.values()
data_by_deaths.sort(key=cmp_to_key(cmp_by_deaths))
keys_by_deaths = [c['id'] for c in data_by_deaths]

def cmp_by_recovered(x, y):
    if not "timeseries_recovered" in x or not "timeseries_recovered" in y:
        return -1
    return y["timeseries_recovered"][max_date] - x["timeseries_recovered"][max_date]
data_by_recovered = data.values()
data_by_recovered.sort(key=cmp_to_key(cmp_by_recovered))
keys_by_recovered = [c['id'] for c in data_by_recovered]

def cmp_by_active(x, y):
    if not "timeseries_active" in x or not "timeseries_active" in y:
        return -1
    return y["timeseries_active"][max_date] - x["timeseries_active"][max_date]
data_by_active = data.values()
data_by_active.sort(key=cmp_to_key(cmp_by_active))
keys_by_active = [c['id'] for c in data_by_active]

export_data = {
        'cases': data,
        'keys_by_name': keys_by_name,
        'keys_by_confirmed': keys_by_confirmed,
        'keys_by_recovered': keys_by_recovered,
        'keys_by_active': keys_by_active,
        'keys_by_deaths': keys_by_deaths,
        'min_date': min_date,
        'max_date': max_date
}

fn = "../public_html/data.json"
with open(fn, 'w') as outfile:
    json.dump(export_data , outfile) 

print("data written to %s" % fn)

