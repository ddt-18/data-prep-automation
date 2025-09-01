# 📊 Data Cleaning & Profiling Automation

A beginner-friendly Python project to **automate data cleaning, visualization, and profiling for datasets of any size**. This tool streamlines exploratory data analysis, generating clean datasets, insightful charts, and interactive reports with minimal user input.  

---

## 🎯 Features

- Data Cleaning: Handles missing values (drop or fill with mean/mode) and removes duplicates.

- Visualizations: Generates bar charts (e.g., top categories) and pie charts (e.g., distributions) with automatic or manual column selection.
  
- Performance Optimization: Uses sampling (50,000 rows for datasets >150,000) for fast visualization of large datasets like ncr_ride_bookings.csv (150,000 rows).
  
- Profiling: Creates interactive HTML reports with ydata-profiling for quick insights.

- Flexible Input: Supports CSV, Excel, JSON, and Parquet files with robust encoding handling.

- Output: Saves cleaned datasets (CSV/Excel) and PNG plots in an organized output/ folder.


---

## ⚙️ Requirements

- Python 3.9+  
- Install dependencies:  

```
pip install pandas matplotlib seaborn ydata-profiling openpyxl
```
---

## 📂 Project Structure
```
project/
│
├── output/                         # Auto-generated reports, cleaned data and plots
├── datasets/                       # Place your CSV/Excel/JSON/Parquet datasets here
└── data_cleaning_automation.ipynb    # Jupyter Notebook with usage guide
```
---

## 🚀 How to Use

1. Clone or download this repo

2. Place your datasets inside your chosen folder (update the DATA_FOLDER path in the script)

3. Run the script:
```
jupyter notebook data_cleaning_automation.ipynb
```
4. Follow prompts:
   - Select dataset(s) from your folder.
   - Choose cleaning options (e.g., fill missing values, drop duplicates).
   - Pick columns for bar/pie charts or let the script auto-select suitable ones.
   - Specify sample size for large datasets (default: 50,000 rows for >150,000).

5. Check Outputs in output/:
   - Cleaned dataset: <filename>_cleaned_<timestamp>.csv/xlsx
   - Plots: <filename>_plots/bar_<column>.png, pie_<column>.png
   - HTML report: <filename>_report_<date>.html

---

## 📝 Example Workflow

Input: ncr_ride_bookings.csv (150,000 rows, ride-sharing data)

Steps:

Select dataset and choose to fill missing values and drop duplicates.
Pick Vehicle_Type, Pickup_Location for bar charts; Booking_Status, Payment_Method for pie charts.
Use default sample size (50,000 rows) for fast visualization.

Outputs:

- output/ncr_ride_bookings_cleaned_20250902_XXXXXX.csv/xlsx
- output/ncr_ride_bookings_plots/:
   - bar_Vehicle_Type.png (top 10 vehicle types)
   - bar_Pickup_Location.png (top 10 pickup locations)
   - pie_Booking_Status.png (e.g., 70% Completed, 20% Cancelled)
   - pie_Payment_Method.png (payment method distribution)
- output/ncr_ride_bookings_report_20250902.html (interactive profiling report)

---

## 🙋 Honesty Note

This project was built with AI assistance (ChatGPT + Grok).
As a beginner, I used AI to iterate on the script, learning Python, pandas, and visualization techniques along the way. I understand each component and tailored it to create a practical tool for data analysis.

💡 Goal: Share a clean, functional project to inspire other beginners and showcase my growth as a data analyst.

---

## 📌 Future Improvements

- Add summary statistics to Excel outputs (e.g., key metrics per column).
- Integrate with SQL databases for querying cleaned data.
- Automate data export to Power BI for dashboard creation.
- Add support for more visualization types (e.g., line charts for trends).

---

## 📜 License

This project is licensed under the [MIT License](LICENSE) – use it, tweak it, share it.  
