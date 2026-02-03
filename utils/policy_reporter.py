import os
import re

import pandas as pd
import matplotlib.pyplot as plt


def generate_trend_chart(csv_file="policy_summary/policy_reports.csv"):
    if not os.path.exists(csv_file):
        print(f"File {csv_file} does not exist!")
        return

    df = pd.read_csv(csv_file)

    # 1. DEBUG: Look raw data before cleaning
    print("Raw data from CSV:")
    print(df['Total Policy Premium'].head())

    # 2. EXTREME CLEANING: Saving only numeric values and decimal points in 'Total Policy Premium'
    # Using re.sub inside lambda function because is safer than str.replace for multiple unwanted characters
    def clean_currency(value):
        if pd.isna(value): return 0.0
        # Cleaning everything except digits and decimal point
        clean_val = re.sub(r'[^\d.]', '', str(value))
        return float(clean_val) if clean_val else 0.0

    df['Total Policy Premium'] = df['Total Policy Premium'].apply(clean_currency)

    # 3. Control: is there any row with zero or negative premium after cleaning?
    df = df[df['Total Policy Premium'] > 0]

    if df.empty:
        print("ERROR: DataFrame isd empty after cleaning. Check format in CSV!")
        return

    print(f"Successfully cleaned {len(df)} rows.")

    # 4. DRAWING THE CHART
    plt.figure(figsize=(10, 6))

    # Using bar chart because it's better for small number of tests
    # df.plot(kind='bar', x='Policy Coverage Option', y='Total Policy Premium', color='skyblue', legend=False)

    # Grouping by 'Policy Coverage Option' and 'Vehicle Use' to get average premiums
    df_grouped = df.groupby(['Policy Coverage Option', 'Vehicle Use'])['Total Policy Premium'].mean().unstack()
    df_grouped.plot(kind='bar', figsize=(12, 6), color=['skyblue', 'salmon', 'lightgreen', 'orange'])

    plt.title('Mean Total Policy Premium by Coverage Option and Vehicle Use', fontsize=14)
    plt.ylabel('Premium ($)')
    plt.xlabel('Policy Coverage Option')
    plt.xticks(rotation=45)
    plt.legend(title='Vehicle Use')
    plt.tight_layout() # Adjust layout to prevent clipping of labels
    # plt.show()
    plt.savefig("policy_summary/policy_report.png")
    plt.close() # Close the plot to free memory

def generate_status_pie_chart(csv_file="policy_summary/policy_reports.csv"):
    df = pd.read_csv(csv_file)

    # Counting the occurrences of each status
    status_counts = df['Status'].value_counts()

    plt.figure(figsize=(8, 8))
    status_counts.plot(kind='pie', autopct='%1.1f%%', startangle=140, colors=['#66b3ff', '#99ff99', '#ff9999'])
    plt.title('Policy Status Distribution ', fontsize=14)
    plt.ylabel('')  # Clearing the y-label for better aesthetics

    plt.savefig("policy_summary/status_distribution.png")

if __name__ == "__main__":
    # Calling functions for direct testing purposes with default path
    generate_trend_chart("policy_summary/policy_reports.csv")
    generate_status_pie_chart("policy_summary/policy_reports.csv")