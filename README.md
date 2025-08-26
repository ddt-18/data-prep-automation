# 🪄 Excel Data Automation with Python  

Tired of manually summarizing and cleaning datasets in Excel?  
This Python automation takes any dataset from a folder and instantly produces:  

✅ A **Summary Excel file** (4 sheets):  
- **Preview**: first 10 rows of the dataset  
- **Dataset Info**: rows, columns, total missing values  
- **Statistics**: descriptive stats (mean, std, quartiles, freq, unique, etc.)  
- **Missing Values**: count of missing values per column  

✅ A **Cleaned Dataset**:  
- Duplicate rows removed  
- Missing values handled (numeric → mean, categorical → mode)  
- Column names standardized  
- Datetime columns correctly set  

---

## ⚡ Features  
- **Dataset Selection Toggle** → pick one or multiple datasets from a folder  
- **Automated Cleaning** → consistent formatting & missing value handling  
- **Summary File Export** → quick overview for analysis  
- **Future Roadmap**: automatic visualizations (charts with Seaborn/Matplotlib)  

---

## 📂 Example Datasets Tested On  
- Sales Data Sample (Kaggle)  
- Global Superstore (Kaggle)  
- Adult Income Dataset (Kaggle)  
- Wine Quality Dataset (Kaggle)  

*(more datasets can be plugged in directly via the folder toggle)*  

---

## 🚀 Getting Started  

1. **Clone this repo**  
   ```bash
   git clone https://github.com/ddt-18/your-repo-name.git

2. **Install dependencies** 
    ```bash
    pip install pandas matplotlib seaborn openpyxl

3. **Place your datasets (.csv or .xlsx) in the Datasets/ folder**

4. **Run the script**
    ```bash
    python automation.py

## 📸 Demo (placeholder)

## 📜 License

This project is licensed under the MIT License – use it, tweak it, share it.
