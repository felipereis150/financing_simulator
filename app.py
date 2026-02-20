import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# --- PAGE CONFIG ---
st.set_page_config(page_title="Financing Simulator", layout="wide")
st.title("Financing & Amortization Simulator")

# --- SIDEBAR INPUTS ---
st.sidebar.header("Financing Details")
principal = st.sidebar.number_input("Hired Value (Principal)", min_value=0.0, value=50000.0, step=1000.0)
rate_pct = st.sidebar.number_input("Monthly Interest Rate (%)", min_value=0.0, value=1.5, step=0.1)
installments = st.sidebar.number_input("Total Installments", min_value=1, value=48, step=1)

r = rate_pct / 100

if r > 0:
    pmt = principal * (r * (1 + r)**installments) / ((1 + r)**installments - 1)
else:
    pmt = principal / installments

st.sidebar.markdown("---")
st.sidebar.metric("Standard Monthly Installment", f"${pmt:,.2f}")

# --- CALCULATION ENGINE ---
def calculate_schedule(p, rate, fixed_pmt, n, extra_payments_dict=None):
    schedule = []
    balance = p
    cum_interest = 0
    
    if extra_payments_dict is None:
        extra_payments_dict = {}

    for month in range(1, int(n) + 1):
        if balance <= 0.01:
            break
            
        interest = balance * rate
        extra = extra_payments_dict.get(month, 0.0)
        
        regular_principal = fixed_pmt - interest
        
        if regular_principal > balance:
            regular_principal = balance
            fixed_pmt = regular_principal + interest
            
        total_principal_paid = regular_principal + extra
        
        if total_principal_paid > balance:
            extra = balance - regular_principal
            total_principal_paid = balance
            
        total_payment = fixed_pmt + extra
        balance -= total_principal_paid
        cum_interest += interest
        
        schedule.append({
            "Month": month,
            "Installment": fixed_pmt,
            "Interest Paid": interest,
            "Principal Paid": regular_principal,
            "Extra Amortization": extra,
            "Total Paid This Month": total_payment,
            "Remaining Balance": max(0, balance),
            "Cumulative Interest": cum_interest
        })
        
    return pd.DataFrame(schedule)

# Generate pure baseline (no extra payments)
baseline_schedule = calculate_schedule(principal, r, pmt, installments)

# --- USER INPUT FOR AMORTIZATION ---
st.subheader("Add Extra Amortizations")
# Create an editable dataframe for user input
input_df = pd.DataFrame({"Month": range(1, int(installments) + 1), "Extra Amortization": 0.0})

# Updated parameter here:
edited_df = st.data_editor(
    input_df, 
    hide_index=True, 
    width='stretch',
    column_config={
        "Month": st.column_config.NumberColumn(disabled=True),
        "Extra Amortization": st.column_config.NumberColumn(format="$%.2f", min_value=0.0)
    },
    height=200
)

# Generate actual schedule based on user inputs
extra_dict = dict(zip(edited_df["Month"], edited_df["Extra Amortization"]))
final_schedule = calculate_schedule(principal, r, pmt, installments, extra_dict)

# --- METRICS ---
st.markdown("---")
st.subheader("Financing Summary")

baseline_total_paid = baseline_schedule["Total Paid This Month"].sum()
baseline_total_interest = baseline_schedule["Interest Paid"].sum()

actual_total_paid = final_schedule["Total Paid This Month"].sum()
actual_total_interest = final_schedule["Interest Paid"].sum()
actual_installments = final_schedule["Month"].max()

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Paid (Overall)", f"${actual_total_paid:,.2f}", 
              delta=f"-${(baseline_total_paid - actual_total_paid):,.2f} saved", delta_color="inverse")
with col2:
    st.metric("Total Interest Paid", f"${actual_total_interest:,.2f}", 
              delta=f"-${(baseline_total_interest - actual_total_interest):,.2f} saved", delta_color="inverse")
with col3:
    st.metric("Time to Pay Off", f"{actual_installments} months", 
              delta=f"-{int(installments) - actual_installments} months early", delta_color="inverse")

# --- CHARTS ---
st.markdown("---")
st.subheader("Visual Comparisons")

# Merge data for easy plotting
compare_df = pd.merge(
    baseline_schedule[["Month", "Remaining Balance", "Cumulative Interest", "Total Paid This Month"]],
    final_schedule[["Month", "Remaining Balance", "Cumulative Interest", "Total Paid This Month", "Installment", "Extra Amortization"]],
    on="Month",
    how="left",
    suffixes=('_Base', '_Amortized')
).fillna(0)

col_chart1, col_chart2 = st.columns(2)

with col_chart1:
    # 1. Cumulative Interest Comparison
    fig_interest = go.Figure()
    fig_interest.add_trace(go.Scatter(x=compare_df["Month"], y=compare_df["Cumulative Interest_Base"], 
                                      mode='lines', name='Baseline Interest', line=dict(dash='dash', color='red')))
    fig_interest.add_trace(go.Scatter(x=compare_df["Month"], y=compare_df["Cumulative Interest_Amortized"], 
                                      mode='lines', name='Actual Interest', line=dict(color='green', width=3)))
    fig_interest.update_layout(title="Cumulative Interest Paid (Fees)", xaxis_title="Month", yaxis_title="Amount ($)")
    st.plotly_chart(fig_interest, width='stretch') # Updated parameter

with col_chart2:
    # 2. Remaining Balance Comparison
    fig_balance = go.Figure()
    fig_balance.add_trace(go.Scatter(x=compare_df["Month"], y=compare_df["Remaining Balance_Base"], 
                                     mode='lines', name='Baseline Balance', line=dict(dash='dash', color='gray')))
    fig_balance.add_trace(go.Scatter(x=compare_df["Month"], y=compare_df["Remaining Balance_Amortized"], 
                                     mode='lines', name='Actual Balance', line=dict(color='blue', width=3), fill='tozeroy'))
    fig_balance.update_layout(title="Remaining Principal Balance", xaxis_title="Month", yaxis_title="Balance ($)")
    st.plotly_chart(fig_balance, width='stretch') # Updated parameter

# 3. Monthly Payments Breakdown
st.markdown("#### Monthly Cash Flow Breakdown")
fig_payments = go.Figure()

fig_payments.add_trace(go.Bar(x=final_schedule["Month"], y=final_schedule["Installment"], 
                              name='Standard Installment', marker_color='lightblue'))
fig_payments.add_trace(go.Bar(x=final_schedule["Month"], y=final_schedule["Extra Amortization"], 
                              name='Extra Amortization', marker_color='orange'))

fig_payments.add_trace(go.Scatter(x=compare_df["Month"], y=compare_df["Total Paid This Month_Base"], 
                                  mode='lines', name='Baseline Monthly Total', line=dict(color='red', dash='dot')))

fig_payments.update_layout(barmode='stack', title="Actual Payments vs. Baseline Payments", 
                           xaxis_title="Month", yaxis_title="Payment Amount ($)")
st.plotly_chart(fig_payments, width='stretch') # Updated parameter

# --- FINAL TABLE VIEW ---
with st.expander("View Full Amortization Table"):
    # Updated parameter here:
    st.dataframe(
        final_schedule.style.format({
            "Installment": "${:,.2f}",
            "Interest Paid": "${:,.2f}",
            "Principal Paid": "${:,.2f}",
            "Extra Amortization": "${:,.2f}",
            "Total Paid This Month": "${:,.2f}",
            "Remaining Balance": "${:,.2f}",
            "Cumulative Interest": "${:,.2f}"
        }),
        width='stretch',
        hide_index=True
    )