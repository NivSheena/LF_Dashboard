import streamlit as st
import pandas as pd
import psycopg2
import plotly.express as px

# 1. הגדרות דף
st.set_page_config(page_title="LF Finance - Starry Ocean Edition", layout="wide", initial_sidebar_state="expanded")

# 2. CSS - אוקיינוס לילי, כוכבים וכרטיסים בולטים
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@200;600;800&display=swap');
    .stApp {
        background: url('https://images.unsplash.com/photo-1504333638930-c8787321eee0?auto=format&fit=crop&w=2850&q=80');
        background-size: cover; background-attachment: fixed; direction: rtl;
    }
    .glass-box {
        background: rgba(255, 255, 255, 0.94); /* אטימות גבוהה לקריאות מושלמת */
        backdrop-filter: blur(10px);
        border-radius: 30px;
        box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5);
        text-align: center; color: #1d1d1f;
        padding: 40px; margin-bottom: 25px;
    }
    .hero-value { font-size: 7.5rem !important; font-weight: 800; color: #0071e3; line-height: 1.1; }
    .small-label { font-size: 1.8rem; font-weight: 700; margin-bottom: 8px; color: #333; }
    .small-value { font-size: 3.2rem; font-weight: 800; color: #1d1d1f; }
    .detail-text { font-size: 1.1rem; font-weight: 600; opacity: 0.9; text-align: right; color: #444; }
    h3 { font-family: 'Assistant', sans-serif; font-weight: 800; color: #1d1d1f; }
    
    /* עיצוב סיידבר לילי */
    [data-testid="stSidebar"] {
        background-color: rgba(0, 5, 15, 0.9);
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

# 3. מנוע חישוב חכם (פריסת חודשים) - משיכה מה-Secrets לאבטחה
# השורה הזו שונתה כדי שלא יראו את הסיסמה שלך ב-GitHub
DB_URI = st.secrets["DB_URI"]

def calculate_detailed_net(profit, months_count=1):
    if profit <= 0: return {k: 0 for k in ['net', 'tax', 'bl', 'pension', 'training', 'total_social']}
    pension = profit * 0.165 
    training = min(profit * 0.045, 1100 * months_count)
    bl_low_bracket = 7522 * months_count
    bl = (bl_low_bracket * 0.0597) + (max(0, profit - bl_low_bracket) * 0.1783) if profit > bl_low_bracket else profit * 0.0597
    taxable = profit - pension - training - (bl * 0.52)
    tax_bracket_1 = 7000 * months_count
    raw_tax = (tax_bracket_1 * 0.10) + ((taxable - tax_bracket_1) * 0.14) if taxable > tax_bracket_1 else taxable * 0.10
    credit_points_total = (4.25 * 245) * months_count
    income_tax = max(0, raw_tax - credit_points_total) 
    net = profit - bl - income_tax - pension - training
    return {'net': net, 'tax': income_tax, 'bl': bl, 'pension': pension, 'training': training, 'total_social': pension + training}

try:
    conn = psycopg2.connect(DB_URI)
    income_df = pd.read_sql("SELECT *, split_part(project_description, ' - ', 1) as clean_client FROM income WHERE payment_status = 'paid'", conn)
    expenses_df = pd.read_sql("SELECT * FROM expenses", conn)
    conn.close()

    income_df['date'] = pd.to_datetime(income_df['date'])
    income_df['month_year'] = income_df['date'].dt.strftime('%m/%Y')
    all_months = income_df['month_year'].unique().tolist()
    total_months_in_data = len(all_months)

    # --- Sidebar ---
    st.sidebar.title("🛠️ הגדרות Vision")
    target_net = st.sidebar.number_input("יעד נטו חודשי (₪):", value=20000, step=1000)
    months_list = ["הכל (שנתי)"] + sorted(all_months, reverse=True)
    selected_vision = st.sidebar.selectbox("בחר תקופה:", months_list)

    if selected_vision == "הכל (שנתי)":
        display_inc = income_df
        display_exp = expenses_df
        m_count = total_months_in_data
    else:
        display_inc = income_df[income_df['month_year'] == selected_vision]
        expenses_df['date'] = pd.to_datetime(expenses_df['date'])
        expenses_df['month_year'] = expenses_df['date'].dt.strftime('%m/%Y')
        display_exp = expenses_df[expenses_df['month_year'] == selected_vision]
        m_count = 1

    biz_profit = display_inc['amount_pre_vat'].sum() - display_exp['amount_pre_vat'].sum()
    res = calculate_detailed_net(biz_profit, m_count)

    # --- תצוגה ראשית ---
    st.markdown(f"""<div class="glass-box">
        <div class="small-label" style="font-size:1.4rem;">🏠 נטו סופי לבית - {selected_vision}</div>
        <div class="hero-value">₪{int(round(res['net'])):,}</div>
        <div style="margin-top:15px;"><p style="font-weight:700;">התקדמות ליעד: {min(100, int(res['net']/(target_net * m_count)*100))}%</p></div>
    </div>""", unsafe_allow_html=True)
    st.progress(min(1.0, res['net']/(target_net * m_count)))

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"""<div class="glass-box"><div class="small-label">📈 רווח עסקי</div><div class="small-value">₪{int(round(biz_profit)):,}</div></div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="glass-box"><div class="small-label">🏛️ מיסים</div><div class="small-value">₪{int(res['tax']+res['bl']):,}</div><p class="detail-text">מס הכנסה: ₪{int(res['tax']):,}</p><p class="detail-text">ביטוח לאומי: ₪{int(res['bl']):,}</p></div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class="glass-box"><div class="small-label">💰 חיסכון</div><div class="small-value">₪{int(res['total_social']):,}</div><p class="detail-text">פנסיה: ₪{int(res['pension']):,}</p><p class="detail-text">השתלמות: ₪{int(res['training']):,}</p></div>""", unsafe_allow_html=True)

    # פילוח לקוחות
    st.markdown("<div class='glass-box'><h3>👥 הכנסה לפי לקוח</h3>", unsafe_allow_html=True)
    client_data = display_inc.groupby('clean_client')['amount_pre_vat'].sum().sort_values(ascending=False).reset_index()
    fig_clients = px.bar(client_data, x='amount_pre_vat', y='clean_client', orientation='h', 
                         color_discrete_sequence=['#0071e3'], labels={'amount_pre_vat':'סכום', 'clean_client':'לקוח'})
    fig_clients.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="#1d1d1f", height=380,
                              xaxis_title="", yaxis_title="")
    st.plotly_chart(fig_clients, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

except Exception as e:
    st.error(f"Error: {e}")