import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, Input, Output, State
import plotly.graph_objects as go
import json

#Prepare datasets
organizations = pd.read_csv("organizations.csv")              
skills = pd.read_csv("volunteer_skills_breakdown.csv")       
fund = pd.read_csv("budget_vs_actual.csv")
volunteer = pd.read_csv("volunteer_count.csv")
hours = pd.read_csv("service_hours.csv")
programs = pd.read_csv("programs_by_year.csv")
location = pd.read_csv("project_locations.csv")
evaluation = pd.read_csv("project_evaluation.csv")

#Dropdown for choosing organization 1: 
merged_skills = pd.merge(
    organizations[['org_id', 'name']],
    skills,
    how='right',
    on='org_id'
)

org_options = sorted(merged_skills['name'].dropna().astype(str).unique().tolist())
default_orgs = org_options[0] if org_options else None

#information:
cols = {c.lower(): c for c in organizations.columns}
name_col = cols.get("name", list(organizations.columns)[0])
loc_col = cols.get("location", None)
found_col = cols.get("founded", None)
field_col = cols.get("field_primary", None)
mission_col = cols.get("mission", None)
aud_col = cols.get("main_audience", None)

names = sorted(organizations[name_col].dropna().astype(str).unique())

# budget_vs_actual：
fund["year"] = pd.to_numeric(fund["year"], errors="coerce")
for c in ["annual_budget", "actual_expenditure"]:
    fund[c] = pd.to_numeric(fund[c], errors="coerce").fillna(0)
fund = fund.dropna(subset=["year"])
fund["year"] = fund["year"].astype(int)

names = sorted(fund["name"].dropna().unique().tolist())
fund_years = sorted(fund["year"].unique().tolist())

#volunteer_count:
years_volunteer = sorted(fund["year"].unique().tolist())

# volunteer_skills:
CAT_ORDER = ['Education', 'Health', 'Environment', 'Others', 'Law']
if not set(CAT_ORDER).issubset(set(merged_skills['skill'].dropna().unique().tolist())):
    CAT_ORDER = sorted(merged_skills['skill'].dropna().astype(str).unique().tolist())

#service_hours:
org_ids = sorted(hours["name"].astype(str).unique().tolist())
genders = sorted(hours["gender"].astype(str).dropna().unique().tolist())
ages = sorted(hours["age_group"].astype(str).dropna().unique().tolist())

#programs_by_year:
programs["year"] = pd.to_numeric(programs["year"], errors="coerce")
programs = programs.dropna(subset=["name", "category", "programs", "year"])

names = sorted(programs["name"].astype(str).unique().tolist())
ymin, ymax = int(programs["year"].min()), int(programs["year"].max())

#project_location:
def normalize(df):
    df = df.copy()
    df["project_count"] = pd.to_numeric(df.get("project_count"), errors="coerce").fillna(0)
    df["latitude"]  = pd.to_numeric(df.get("latitude", df.get("lat")), errors="coerce")
    df["longitude"] = pd.to_numeric(df.get("longitude", df.get("lon")), errors="coerce")
    return df.dropna(subset=["latitude","longitude"])

location = normalize(location)
orgs_unique = organizations.drop_duplicates("org_id").sort_values("name")

#project_evaluation:
evaluation["score"] = pd.to_numeric(evaluation["score"], errors="coerce").fillna(0)

app = Dash(__name__)

PAGE = {
    "fontFamily": "Arial, sans-serif",
    "background": "#f7f9f7",
    "padding": "16px 18px",
    "minHeight": "100vh"
}

CARD = {
    "background": "#ffffff",
    "border": "1px solid #dfe7da",
    "borderRadius": "10px",
    "padding": "8px 8px"
}

ROW2 = {
    "display": "grid",
    "gridTemplateColumns": "1fr 2fr",
    "gap": "14px",
    "alignItems": "stretch",
    "marginTop": "14px",
    
}

ROW3 = {
    "background": "#ffffff",
    "display": "grid",
    "gridTemplateColumns": "repeat(3, 1fr)", 
    "gap": "14px",                            
    "padding": "10px",
    "alignItems": "stretch",
    "borderRadius": "10px",
    "marginTop": "14px"
}

app.layout = html.Div([
    html.Div([
        html.H1("NGO Information Integration and Disclosure Dashboard", 
            style={"margin": 0, "color": "#2f4f2f"}),
        dcc.Dropdown(
            id='organization_1',
            options=org_options,     
            value=default_orgs,     
            clearable=False,
            placeholder="Select organization"
        )
    ], style = CARD),

    html.Div([
    #information:
        html.Div([
            html.H3("Basic Information Overview", style={"margin":"4px 0 8px 0"}),
            html.Div(id="info-box", style={
            "backgroundColor": "#E6EFE4",
            "border": "2px dashed #7da472",
            "borderRadius": "10px",
            "padding": "20px",
            "maxWidth": "420px",
            "fontFamily": "Arial",
            "lineHeight": "1.6"
            })
        ], style = CARD ),
    #budget_vs_actual：
        html.Div([
            html.H3("Annual Budget vs Actual Expenditure", style={"margin":"4px 0 8px 0"}),
            dcc.Graph(id="budget_bar", style={"height": "320px"}),
            dcc.RangeSlider(
                id="year_slider_fund",
                min=fund_years[0], 
                max=fund_years[-1],
                value=[fund_years[0], fund_years[-1]],
                marks={y: str(y) for y in fund_years},
                step=None,
                tooltip={"placement": "bottom", "always_visible": False}
            )        
        ], style = CARD )
    ], style=ROW2),

    html.Div([
        html.Div([
            html.H3('Selecting Specific Gender and Age Group', style={"margin":"4px 0 8px 0"}),
            dcc.RadioItems(
                id='gender',
                options=["All", "Female", "Male"],
                value='All',
                style={"display":"inline-block","marginRight":"12px"}
            ),
            dcc.Dropdown(
                id='age_group',
                options=['All', '18-25', '26-45', '46-60', 'Above 60'],
                value='All',
                clearable=False,
                style={"display":"inline-block","width":"220px"}
            )], style=ROW3),
    
        html.Div([
        #volunteer_count:        
            html.Div([
                html.H3("Total Number of Volunteers", style={"margin":"4px 0 8px 0"}),

                dcc.Dropdown(
                    id="organization_2_line", 
                    options=[{"label": o, "value": o} for o in org_ids],
                    value=org_ids[1] if len(org_ids) > 1 else (org_ids[0] if org_ids else None),
                    clearable=False, 
                    placeholder="Organization 2",
                    style={"width":"260px","display":"inline-block","marginRight":"10px"}
                ),

                dcc.Graph(id='volunteer_count', style={"height": "320px"}),
                            html.Label("Year Range"),
                dcc.RangeSlider(
                    id="year_slider_volunteer",
                    tooltip={"placement": "bottom", "always_visible": True},
                    min=years_volunteer[0], 
                    max=years_volunteer[-1],
                    value=[years_volunteer[0], years_volunteer[-1]],
                    marks={y: str(y) for y in years_volunteer},
                    step=None          
                    )
            ], style = CARD),
        #volunteer_skills：
            html.Div([
                html.H3("Distribution of Skill/Interests of Volunteers", style={"margin":"4px 0 8px 0"}),
                dcc.Graph(id='radar_map', style={"height": "320px"})
            ], style = CARD),
        #service_hours:
            html.Div([
                html.H3("Service Hours in Different Fields", style={"margin":"4px 0 8px 0"}),
                dcc.Dropdown(
                    id="organization_2_bar", 
                    options=[{"label": o, "value": o} for o in org_ids],
                    value=org_ids[1] if len(org_ids) > 1 else (org_ids[0] if org_ids else None),
                    clearable=False, 
                    placeholder="Organization 2",
                    style={"width":"260px","display":"inline-block","marginRight":"10px"}
                ),
                dcc.Graph(id="service_hours", style={"height": "320px"}),
            ], style = CARD)
        ], style=ROW3)
    ]),

    html.Div([
    #programs_by_year:
        html.Div([
            html.H3("The Number of Projects", style={"margin":"4px 0 8px 0"}),
                dcc.Graph(id="programs_by_year", style={"height": "320px"}),
                dcc.RangeSlider(
                    id="years_slider_program", 
                    min=ymin, 
                    max=ymax, 
                    step=1,
                    value=[ymin, ymax],
                    marks={y: str(y) for y in range(ymin, ymax+1, max(1,(ymax-ymin)//10 or 1))}
                )          
            ], style = CARD),
    #project_evaluation:
        html.Div([
            html.H3("Organization Evaluation", style={"margin":"4px 0 8px 0"}),      
            dcc.Graph(id="eval-bar", style={"height": "320px"})
            ], style = CARD)           
    ], style=ROW2 | {"gridTemplateColumns": "repeat(2, 1fr)"}),
#project_location:
    html.Div([
        dcc.Store(
            id="store-projects",
            data=location.to_json(orient="records")),
        dcc.Store(
            id="store-orgs",     
            data=orgs_unique.to_json(orient="records")),

        html.H3("Available Project Locations & Fields"),
        dcc.Graph(
            id="project-map" 
            #style={"marginTop":"10px"}
            ),
        html.Div(
            id="project-detail",
            style={
                "marginTop":"10px",
                "padding":"10px",
                "background":"#fff",
                "border":"1px solid #e0e6e0",
                "borderRadius":"8px",
                "minHeight":"64px",
                "whiteSpace":"pre-wrap"})
    ], style=CARD#{"fontFamily":"Arial","padding":"16px"}
    )
], style=PAGE)

#information:
@app.callback(
    Output("info-box", "children"), 
    Input("organization_1", "value")
    )
def show_info(selected):
    if not selected:
        return "Please select an organization."

    row = organizations[organizations['name'] == selected].iloc[0].to_dict()

    info_items = [
        f"📍 Location: {row.get(loc_col, 'N/A')}",
        f"🕓 Founding time: {row.get(found_col, 'N/A')}",
        f"🏷️ Primary Field: {row.get(field_col, 'N/A')}",
        f"👥 Main audience: {row.get(aud_col, 'N/A')}",
        f"🎯 Mission and Vision: {row.get(mission_col, 'N/A')}"        
    ]
    return [html.Div(i) for i in info_items]

#budget_vs_actual:
@app.callback(
    Output("budget_bar", "figure"),
    Input("organization_1", "value"),
    Input("year_slider_fund", "value")
)
def update_chart(selected_name, year_range):
    if not selected_name:
        return px.bar(title="Please select a name.")
    y_min, y_max = year_range
    d = fund[(fund["name"] == selected_name) &
             (fund["year"].between(y_min, y_max))]

    if d.empty:
        return px.bar(title=f"No data for {selected_name}")

    g = d.groupby("year", as_index=False)[["annual_budget", "actual_expenditure"]].sum()
    long_df = g.melt(id_vars="year", var_name="Category", value_name="Amount")
    long_df["Category"] = long_df["Category"].replace({
        "annual_budget": "Annual Budget",
        "actual_expenditure": "Actual Expenditure"
    })

    fig = px.bar(
        long_df,
        x="year", y="Amount", 
        color="Category", 
        barmode="group",
        labels={"year": "Year", "Amount": "Amount (Thousands AUD)", "Category": ""},
        color_discrete_map={
            "Annual Budget": "rgba(180,198,169,1)",  
            "Actual Expenditure": "rgba(59,91,59,1)"}
    )

    fig.update_layout(template="plotly_white",)

    return fig

#volunteer_count:
@app.callback(
    Output("volunteer_count", "figure"),
    Input("organization_1", "value"),
    Input("organization_2_line", "value"),
    Input("gender", "value"),
    Input("age_group", "value"),
    Input("year_slider_volunteer", "value")
)
def update_chart(org_a, org_b, selected_genders, selected_ages, selected_years):
    dff = volunteer.copy()

    if selected_genders != "All":
        dff = dff[dff["gender"]==selected_genders]
    if selected_ages != "All":
        dff = dff[dff["age_group"]==selected_ages]

    chosen = [x for x in [org_a, org_b] if x is not None]
    dff = dff[dff["name"].astype(str).isin([str(x) for x in chosen])]

    # aggregate hours by field × org_id
    dff = dff[(dff["year"] >= selected_years[0]) & (dff["year"] <= selected_years[1])]
    dff_grouped = dff.groupby(["year", "name"], as_index=False)["volunteers"].sum()

    # color mapping: Org A = light green, Org B = dark green
    color_map = {}
    if org_a is not None: color_map[str(org_a)] = "rgba(180,198,169,1)"  # light
    if org_b is not None: color_map[str(org_b)] = "rgba(59,91,59,1)"     # dark

  #  dff_grouped = dff.groupby(["year", "name"], as_index=False)["volunteers"].sum()

    fig = px.line(
        dff_grouped,
        x="year",
        y="volunteers",
        color="name",
        markers=True,
        color_discrete_map=color_map,
        labels={"year": "Year", "volunteers": "Count", "org_id": "Organization"}
    )
    fig.update_layout(template="plotly_white", xaxis=dict(dtick=1),
                     legend=dict(orientation="h", y=1.15, x=0.5, xanchor="center"), legend_title_text="",
                     margin=dict(l=60, r=40, t=60, b=50), hovermode="x unified")
    return fig

#volunteer_skills：
@app.callback(
    Output('radar_map', 'figure'),
    Input('organization_1', 'value'),
    Input('gender', 'value'),
    Input('age_group', 'value')
)
def update_radar(org, gender_name, age_name):
    if not org:
        return {}

    df = merged_skills[merged_skills['name'] == org].copy()
    if gender_name != "All":
        df = df[df['gender'] == gender_name]
    if age_name != "All":
        df = df[df['age_group'] == age_name]
    if df.empty:
        return {}

    sub = df.groupby('skill', as_index=True)['sub_percentage'].sum()

    vals = [float(sub.get(cat, 0.0)) for cat in CAT_ORDER]

    # 闭合多边形
    r_vals = vals + [vals[0]]
    theta_vals = CAT_ORDER + [CAT_ORDER[0]]

    # 极轴上限（向上取整到 5 的倍数，至少 5）
    r_max = max(vals) if vals else 0.0
    radial_upper = max(5, ((int(r_max) + 4) // 5) * 5)

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=r_vals,
        theta=theta_vals,
        fill='toself',
        name='Percentage of Focused Field',
        line=dict(color='rgba(59,91,59,1)', width=2),   
        fillcolor='rgba(0,128,0,0.22)'               
    ))

    # 主题（接近你截图的风格）
    fig.update_layout(
        title=f"{org}",
        showlegend=False,
        legend=dict(orientation='h', x=0.02, y=1.1),
        polar=dict(
            bgcolor="#f4f7f2",
            radialaxis=dict(visible=True, range=[0, radial_upper],
                            gridcolor="rgba(0,0,0,0.25)", gridwidth=1, dtick=5),
            angularaxis=dict(gridcolor="rgba(0,0,0,0.25)", gridwidth=1, direction='clockwise')
        ),
        margin=dict(l=20, r=20, t=60, b=20)
    )
    return fig

#service_hours:
@app.callback(
    Output("service_hours", "figure"),
    Input("organization_1", "value"),
    Input("organization_2_bar", "value"),
    Input("gender", "value"),
    Input("age_group", "value")
)
def update_chart(org_a, org_b, sel_gender, sel_age):
    d = hours.copy()

    if sel_gender and sel_gender != "All":
        d = d[d["gender"] == sel_gender]
    if sel_age and sel_age != "All":
        d = d[d["age_group"] == sel_age]

    chosen = [x for x in [org_a, org_b] if x is not None]
    d = d[d["name"].astype(str).isin([str(x) for x in chosen])]

    agg = d.groupby(["field", "name"], as_index=False)["hours"].sum().sort_values(["field", "name"])

    color_map = {}
    if org_a is not None: color_map[str(org_a)] = "rgba(180,198,169,1)"  # light
    if org_b is not None: color_map[str(org_b)] = "rgba(59,91,59,1)"     # dark

    fig = px.bar(
        agg, 
        x="field", y="hours", 
        color="name", 
        barmode="group",
        color_discrete_map=color_map,
        custom_data=["name", "field", "hours"],
        labels={"field": "Fields", "hours": "Hours", "name": "Organization"},
    )
    fig.update_layout(
        template="plotly_white",
        legend=dict(orientation="h", y=1.15, x=0.5, xanchor="center"), legend_title_text="",
        margin=dict(l=60, r=40, t=60, b=50),
    )
    fig.update_traces(hovertemplate="<b>%{customdata[1]}</b><br>%{customdata[0]}: %{y:.0f} hours<extra></extra>")

    return fig

#programs_by_year:
@app.callback(
    Output("programs_by_year","figure"),
    Input("organization_1","value"), 
    Input("years_slider_program","value")
)
def update(orgs_sel, yr):
    if not orgs_sel: 
        return {}

    y0 = int(yr[0])
    d = programs[(programs["name"]==orgs_sel)]
    d = d[d["year"].between(int(yr[0]), int(yr[1]))]
    if d.empty: 
        return {}

    color_palette = ["#3D91B5", "#D87070", "#6CA162", "#D8A54F", "#8A68A6", "#8C8C8C"]

    fig = px.line(
        d, 
        x="year", y="programs",
        color="category", 
        facet_col="name", 
        facet_col_wrap=2,
        markers=True, 
        color_discrete_sequence=color_palette,
        labels={"programs":"Count","year":"Year"}
    )
    fig.update_layout(template="plotly_white", hovermode="x unified", xaxis=dict(dtick=1))
    return fig

#project_location:
@app.callback(
    Output("project-map","figure"),
    Output("project-detail","children"),
    Input("organization_1","value"),
    Input("project-map","clickData"),
    State("store-projects","data"),
    State("store-orgs","data")
)
def update_map(selected_org, clickData, projects_json, orgs_json):
    import json, pandas as pd, plotly.express as px

    projects_df = pd.DataFrame(json.loads(projects_json))
    orgs_df     = pd.DataFrame(json.loads(orgs_json))

    by_id   = orgs_df[orgs_df["org_id"].astype(str).str.lower() == str(selected_org).lower()]
    by_name = orgs_df[orgs_df["name"].astype(str) == str(selected_org)]
    row_df  = by_id if not by_id.empty else by_name

    if row_df.empty:
        empty_fig = px.scatter_mapbox(lat=[], lon=[], title="No data")
        return empty_fig, "No organization matched. Please select another."

    row = row_df.iloc[0]
    org_id  = str(row["org_id"])
    org_name= str(row["name"])

    d = projects_df[projects_df["org_id"].astype(str).str.lower() == org_id.lower()].copy()

    color_map = {
        "Education": "#5FB6D4", "Health": "#EC8F8F", "Law": "#92C47E",
        "Community": "#E6B85C", "Environment": "#A680C5", "Others": "#B0B0B0"}

    fig = px.scatter_mapbox(
        d, lat="latitude", lon="longitude",
        hover_name="city",
        hover_data={"state": True, "field": True, "project_count": True},
        color="field", 
        color_discrete_map=color_map,
        size="project_count", size_max=40, zoom=3.5, height=600,
        title=f"Project Location & Types — {org_name}",
        custom_data=["city","state","field","project_count","latitude","longitude"]
    )
    fig.update_layout(
        mapbox_style="carto-positron",
        mapbox_center={"lat": -25.2744, "lon": 133.7751},
        margin=dict(l=0, r=0, t=60, b=0),
        legend_title_text="Field",
    )
    if not d.empty:
        fig.update_traces(marker=dict(
            sizemode="area",
            sizeref=2.0 * max(d["project_count"]) / (40**2),
            sizemin=6
        ))

    if clickData and clickData.get("points"):
        city, state, field, count, lat, lon = clickData["points"][0]["customdata"]
        sub = d[(d["city"]==city) & (d["state"]==state) & (d["field"]==field)]
        total = int(sub["project_count"].sum()) if not sub.empty else int(count)
        detail = f"Organization: {org_name} ({org_id})\nCity/State: {city}, {state}\nField: {field}\nProjects: {total}\nLat/Lon: {lat:.4f}, {lon:.4f}"
    else:
        detail = "Click on the bubble on the map to view the details of that point"

    return fig, detail

#project_evaluation:
@app.callback(
    Output("eval-bar", "figure"), 
    Input("organization_1", "value")
    )
def update_chart(selected_org):
    d =  evaluation[evaluation["name"].astype(str) == str(selected_org)]
    d = d.sort_values("score")

    fig = px.bar(
        d,
        x="score",
        y="metric",
        orientation="h",
        labels={"score": "", "metric": ""},
        color_discrete_sequence=["rgba(59,91,59,1)"],
    )

    fig.update_layout(
        template="plotly_white",
        showlegend=False,
        margin=dict(l=80, r=40, t=60, b=40),
        xaxis=dict(range=[0, max(100, float(d["score"].max() if len(d) else 100))]),
    )
    fig.update_traces(hovertemplate="<b>%{y}</b><br>Score: %{x:.0f}<extra></extra>")
    return fig


if __name__ == '__main__':
    app.run(debug=True)
