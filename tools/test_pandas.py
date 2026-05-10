import pandas as pd
p = r'C:\Users\helpdesk\Downloads\tempD\rec-amazon-ratings.edges'
print('trying read_csv header=0')
try:
    df = pd.read_csv(p, nrows=5)
    print('shape', df.shape)
    print(df.head())
except Exception as e:
    print('err0', e)
print('\ntrying read_csv header=None, sep=, engine=python')
try:
    df = pd.read_csv(p, header=None, sep=',', engine='python', nrows=5)
    print('shape', df.shape)
    print(df.head())
except Exception as e:
    print('err1', e)
print('\ntrying read_csv header=None, sep=, engine=c')
try:
    df = pd.read_csv(p, header=None, sep=',', engine='c', nrows=5)
    print('shape', df.shape)
    print(df.head())
except Exception as e:
    print('err2', e)
