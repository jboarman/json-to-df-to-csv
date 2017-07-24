import json
from pandas.io.json import json_normalize
from pandas import pandas as pd


def fixRecordKeys(rows, keyName, default=''):
    """
    Adds record keys to rows that are missing the expect key
        and resets to default value if value is None
    """

    # add missing keys to malformed rows
    for row in rows:
        if keyName not in row:
            row[keyName] = default
        elif row[keyName] is None:
            row[keyName] = default


def extractAddress(address, parsed):

    # ensure min length for subsequent parsing logic
    address = address.ljust(65, ' ')

    # extract first chars as street
    parsed['street'] = address[0:50].strip()

    # extract remaining chars as city/state/zip (c,s,z)
    csz = address[50:]
    c, sz = (csz + ',').split(',')[:2]
    s, z = (sz.strip() + ' ').split(' ')[:2]
    parsed['city'] = c.strip()
    parsed['state'] = s.strip()
    parsed['zip'] = z.strip()


def trimAllColumns(df):
    trimStrings = lambda x: x.strip() if type(x) is str else x
    return df.applymap(trimStrings)


def removePeriodsFromAllColumns(df):
    trimStrings = lambda x: x.replace('.', '') if type(x) is str else x
    return df.applymap(trimStrings)


def combineRows(series):
    return ','.join(map(str, series.tolist()))


#########################################################

# load JSON string data into python list
with open('./tax_payers.json') as data_file:
    jdata = json.load(data_file)

# make sure each comany row has the target officers list key
fixRecordKeys(jdata, 'offiersList', default=[])

# remove unwanted rows
jdata[:] = [
    r for r in jdata
    if r['agentName'] != 'Not on file' and r['status'] == 'ACTIVE'
]

# transform company and officer records
parsed = {}
for row in jdata:

    # rename / remove company fields
    row['officersList'] = row.pop('offiersList')
    row['companyName'] = row.pop('businessEntityName', '')
    row.pop('dbaName', None)
    row.pop('ltrCode', None)
    row.pop('regionIncLabel', None)
    row.pop('regionIncName', None)
    row.pop('status', None)

    # fixup company address
    address = row.pop('businessEntityAdd', '')
    extractAddress(address, parsed)
    row['companyAddress.street'] = parsed['street']
    row['companyAddress.city'] = parsed['city']
    row['companyAddress.state'] = parsed['state']
    row['companyAddress.zip'] = parsed['zip']

    # fixup registered agent address
    address = row.pop('agentAddress', '')
    extractAddress(address, parsed)
    row['agentAddress.street'] = parsed['street']
    row['agentAddress.city'] = parsed['city']
    row['agentAddress.state'] = parsed['state']
    row['agentAddress.zip'] = parsed['zip']

    # transform officer records
    for officer in row['officersList']:

        # remove unwanted columns
        officer.pop('agentRsgnDate', None)
        officer.pop('agentPositionEndDate', None)
        officer.pop('agentTypeCode', None)
        officer.pop('formatedAddress', None)

        # move and transform address within officer node
        address = officer.pop('address', None)
        if address is not None:
            officer['agentAddress.street'] = address['street']
            officer['agentAddress.city'] = address['city']
            officer['agentAddress.state'] = address['state']
            officer['agentAddress.zip'] = address['zipCode']

# export officer records from in-memory python objects to dataframes
df_officers = json_normalize(
    jdata,
    'officersList', [
        'companyAddress.city',
        'companyAddress.state',
        'companyAddress.street',
        'companyAddress.zip',
        'companyName',
        'fileNumber',
        'reportYear',
        'sosRegDate',
        'taxpayerId',
    ],
    sep='.',
    errors='ignore')

# clean and transform agent records
for row in jdata:

    row['agentActiveYr'] = row['reportYear']
    row['agentTitle'] = 'REGISTERED AGENT'

    # remove unwanted officers
    row.pop('officersList', None)

# export agent records from in-memory python objects to dataframes
df_agents = json_normalize(jdata, None, errors='ignore')

# combine agents and offices into a single dataframe set
df = pd.concat([df_agents, df_officers])

# trim all fields on all rows
df = trimAllColumns(df)
df = removePeriodsFromAllColumns(df)

# remove duplicates
groupby_list = list(set(df.columns) - set(['agentTitle']))
df = df.groupby(groupby_list).agg({
    'agentTitle': combineRows,
})

# remove multi-level index prior to JSON export
df = df.reset_index()
df = df.sort_index(axis=1)
df = df.sort_values(['taxpayerId'])

# dump dataframes to JSON
with open('./tax_payer_output.json', 'w') as output_file:
    df.to_json(output_file, orient='records')

# dump dataframes to CSV
with open('./tax_payer_output.csv', 'w') as output_file:
    df.to_csv(output_file)

print(df.shape)
