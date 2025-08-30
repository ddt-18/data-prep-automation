# 📊 Data Cleaning & Profiling Automation

A beginner-friendly Python project to **clean, profile, and visualize datasets** automatically.  
This tool saves you time by generating:  
- ✅ Cleaned Excel datasets  
- 📊 Bar & Pie chart visualizations  
- 🌐 Interactive [ydata-profiling](https://github.com/ydataai/ydata-profiling) HTML report  

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
├── output/                # Auto-generated reports and cleaned data
├── your_datasets_folder/  # Place your CSV/Excel datasets here
└── script.ipynb           # Notebook version with usage guide
```
---

## 🚀 How to Use

1. Clone or download this repo

2. Place your datasets inside your chosen folder (update the DATA_FOLDER path in the script)

3. Run the script:
```
jupyter notebook script.ipynb
```
4. Follow the prompts to:
   - Select dataset(s)
   - Choose cleaning options
   - Decide visualization columns (or let it auto-select)

5. Check the output/ folder for:
   - 📑 Cleaned Excel file
   - 🖼 PNG plots
   - 🌐 HTML profiling report

---

## 📝 Example Workflow

Input: sales_data.csv

Automation generates:

- sales_data_cleaned_20250827.xlsx
- sales_data_plots/ (bar/pie charts)
- sales_data_report_20250827.html

---

## 🙋 Honesty Note

This project was built with AI assistance (ChatGPT + Grok).
I’m still a beginner learning Python, and while I understand what each part does, I didn’t build everything from scratch.
Instead, I iterated with AI tools to create a working version — and learned a lot along the way.

💡 Goal: Share this openly to help other beginners and to showcase my learning journey.

---

## 📌 Future Improvements

- Add optional summary Excel reports
- Support additional file formats
- Automate integration with BI tools

---

## 📸 Demo (placeholder)

## 📜 License

This project is licensed under the [MIT License](LICENSE) – use it, tweak it, share it.  
