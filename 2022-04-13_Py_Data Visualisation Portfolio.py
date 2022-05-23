import pandas as pd
import numpy as np
import datetime as dt
import requests
from bs4 import BeautifulSoup
import re
import plotly.io as pio
import plotly.graph_objects as go
from plotly.subplots import make_subplots

pio.renderers.default = "browser"

# Read GDP data

gdp = pd.read_excel('GDP.xls')

gdp = gdp.iloc[7:,]
gdp.columns = ['Quarter', 'GDP_Growth']

# Get and tidy recession history from Wikipedia

wikiurl="https://en.wikipedia.org/wiki/List_of_recessions_in_the_United_Kingdom"
table_class="wikitable sortable jquery-tablesorter"
response=requests.get(wikiurl)

soup = BeautifulSoup(response.text, 'html.parser')
recessiontable=soup.find('table',{'class':"wikitable"})

recessions = pd.read_html(str(recessiontable))
df_recessions = pd.DataFrame(recessions[0])

def get_dates(x):
    split_x = re.split(r'(\d+ Q\d)', x)
    y = [d for d in split_x if d != '']
    return y

df_recessions['Dates'] = [get_dates(x) for x in df_recessions['Dates']]

df_res_expanded = df_recessions[['Name', 'Dates']]
Dates = df_res_expanded['Dates'].apply(pd.Series).reset_index().melt(id_vars='index').dropna()[['index',
                                                                                         'value']].set_index('index')
df_res_expanded = pd.DataFrame({'Name':df_res_expanded.Name.loc[Dates.index],
                                'Dates':Dates.value})

# Merge GDP and recession data

gdp = gdp.merge(df_res_expanded,
                left_on = 'Quarter',
                right_on = 'Dates',
                how = 'left')

gdp['Quarter'] = gdp['Quarter'].str.replace(' ', '-')
gdp['Quarter'] = pd.PeriodIndex(gdp['Quarter'], freq='Q').to_timestamp()

# Create dataframe containing recession causes

recession_plot = gdp[~gdp.Name.isna()].merge(df_recessions[['Name', 'Causes']])

recession_plot = recession_plot.groupby('Causes').agg(Quarter = ('Quarter', np.mean),
                                                      GDP_Growth = ('GDP_Growth', 'max')).reset_index()

# Clean text and keep first line of causes

recession_plot.Causes = recession_plot.Causes.str.replace('\[\d+\]', '')
recession_plot['Causes'] = [x.split(',')[0] for x in recession_plot['Causes']]

recession_plot.Causes = recession_plot.Causes.str.replace(' including spending cuts', '')
recession_plot.Causes = recession_plot.Causes.str.replace(' in America and high bank rate.', '')

recession_plot = recession_plot.sort_values('Quarter')

recession_plot = pd.concat([recession_plot,
                            pd.DataFrame({'Causes': ['Covid 19 First Lockdown'],
                                          'Quarter': [dt.datetime(2020, 4, 1, 0, 0, 0)],
                                          'GDP_Growth': [-19.4]})])

gdp.loc[gdp.Quarter == dt.datetime(2020, 4, 1, 0, 0, 0), 'Name'] = 'Covid-19 Lockdown'

### Plot 1

fig = go.Figure(data = go.Scatter(x=gdp.Quarter,
                                  y=gdp.GDP_Growth,
                                  mode='lines',
                                  name = '% Quarterly GDP Change',
                                  line=dict(color="#005AB5")))

fig.add_trace(go.Scatter(x = gdp.Quarter[~gdp.Name.isna()],
                         y = gdp.GDP_Growth[~gdp.Name.isna()],
                         mode='markers',
                         name = 'UK Recessions',
                         marker = dict(color="#DC3220")
                         ))

fig.update_layout(margin=dict(t=100, b = 100),
                  title = go.layout.Title(
                      text="<b>Covid-19: An economic shock like no other</b><br><br><sup>"
                           "UK post-war recessions as shown by periods of negative GDP growth compared to the "
                           "period during the Covid-19 pandemic</sup>",
                      xref="paper",
                      x=0
                  ),
                  xaxis_title="Year",
                  yaxis_title="% GDP Change",
                  plot_bgcolor = 'rgba(0, 0, 0, 0)'
                  )

# Add annotations

for i in range(len(recession_plot)):

    if i % 2 == 0:
        yshift_a = -8
        yshift_b = -1
        yshift_c = -7
    else:
        yshift_a = 8
        yshift_b = 1
        yshift_c = 7

    fig.add_shape(type='line',
                    x0=recession_plot.Quarter.iloc[i],
                    y0=recession_plot.GDP_Growth.iloc[i] + yshift_b,
                    x1=recession_plot.Quarter.iloc[i],
                    y1=recession_plot.GDP_Growth.iloc[i] + yshift_c,
                    line=dict(color='black', dash='dot')
    )

    fig.add_annotation(dict(font=dict(color="black",size=10),
                                x=recession_plot.Quarter.iloc[i],
                                y=recession_plot.GDP_Growth.iloc[i] + yshift_a,
                                showarrow=False,
                                text=recession_plot.Causes.iloc[i],
                                textangle=0
                               ))



fig.show()

### Plot 2
# Description of phenomenon from ONS here:
# https://blog.ons.gov.uk/2021/07/15/far-from-average-how-covid-19-has-impacted-the-average-weekly-earnings-data/

# Get unemployment and average weekly earnings data

unemployment = pd.read_excel('unemployment.xls')

unemployment = unemployment.iloc[262:,]
unemployment.columns = ['Month', 'Unemployment_Rate']
unemployment['Month'] = pd.PeriodIndex(unemployment['Month'], freq='M').to_timestamp()

awe = pd.read_excel('average earnings.xls')
awe = awe.iloc[7:,]
awe.columns = ['Month', 'AWE']

awe['Month'] = pd.PeriodIndex(awe['Month'], freq='M').to_timestamp()

df_labour = unemployment.merge(awe)
df_labour = df_labour[df_labour.Month >= dt.datetime.now() - dt.timedelta(days = 365*4)]
df_labour.Month = pd.to_datetime(df_labour.Month).dt.date

max_point = df_labour.sort_values('AWE').tail(1)

# Compile plot

fig = make_subplots(rows=2, cols=1)

fig.add_trace(
    go.Scatter(x=df_labour.Month,
               y=df_labour.Unemployment_Rate,
               mode='lines',
               name = '% Unemployment',
               line=dict(color="#005AB5")),
    row= 1, col = 1)

fig.add_trace(
    go.Scatter(x=df_labour.Month,
               y=df_labour.AWE,
               mode='lines',
               name = '% Change in average earnings',
               line=dict(color="#DC3220")),
    row = 2, col = 1)

fig.add_trace(
    go.Scatter(x=max_point.Month,
               y=max_point.AWE,
               mode='markers',
               showlegend= False,
               line=dict(color="black")),
    row = 2, col = 1)

fig.add_vline(x = dt.date(2020,3,23),
              line_dash="dash",
              line_color="black",
              row = 1,
              col = 1)

fig.add_vline(x = dt.date(2020,3,23),
              line_dash="dash",
              line_color="black",
              row = 2,
              col = 1)

fig.add_annotation(x=0.5,
                   y=1.02,
                   xref="paper",
                   yref='paper',
                   text="First UK Lockdown",
                   showarrow=False)

fig.add_annotation(x=max_point.Month.iloc[0],
                   y=max_point.AWE.iloc[0] + 0.5,
                   text="False rebound*",
                   showarrow=True,
                   row = 2,
                   col = 1)

fig.update_layout(margin=dict(r = 350, t = 200),
                  title = go.layout.Title(
                      text="<b>Covid-19: Unemployment increased but, paradoxically, so did earnings</b><br><br>"
                           "<sup>UK unemployment and change in average earnings</sup>",
                      xref="paper",
                      x=0
                  ),
                  plot_bgcolor = 'rgba(0, 0, 0, 0)'
                  )

# Add annotation

fig.add_annotation(dict(font=dict(color="black",size=11),
                        x=1.24,
                        y=0.2,
                        showarrow=False,
                        text='* It appears average earnings increased,<br>'
                             'but this is in comparison to the year before<br>'
                             'when many workers were furloughed. Also,<br>'
                             'predominantly lower income earners lost their<br>'
                             'employment during the pandemic, meaning<br>'
                             'a higher average overall.',
                        align="left",
                        yref="paper",
                        xref="paper",
                        bordercolor = "#c7c7c7",
                        borderwidth = 2,
                        borderpad = 4))

fig.update_yaxes(title_text="%", row=1, col=1)
fig.update_yaxes(title_text="% Change", row=2, col=1)

fig.show()

