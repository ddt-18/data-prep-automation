# 🐍 Excel Data Prep Automation  

A Python script that automates dataset cleanup and profiling into two ready-to-use outputs:  

1. **Cleaned Dataset (Excel)**  
   - Duplicate rows removed  
   - Column names standardized (spaces → underscores)  
   - Saved with timestamp  

2. **Summary File (Excel, 4 sheets)**  
   - **Preview:** first 10 rows of the dataset  
   - **Dataset_Info:** rows, columns, total missing values  
   - **Statistics:** descriptive stats for all columns (numeric + categorical)  
   - **Missing_Values:** missing value count per column  

---

## ✨ Features
- **Dataset selection toggle:** choose one or more files from a folder interactively  
- **Multiple formats supported:** CSV, XLS, XLSX  
- **Consistent summaries across datasets**  
- **Outputs saved with timestamped filenames**  

---

## 🚀 Usage

1. Clone this repo
   ```bash
   git clone https://github.com/ddt-18/data-prep-automation.git
   cd data-prep-automation
