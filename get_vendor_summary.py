import sqlite3
import pandas as pd
import logging
import os
from ingestion_db import ingest_db

# logging.basicConfig(
#    filename="logs/get_vendor_summary.log",
#    level=logging.DEBUG,
#    format="%(asctime)s - %(levelname)s - %(message)s",
#    filemode="a"
#)

# create logs folder if not exists
os.makedirs("logs", exist_ok=True)

logger = logging.getLogger("get_vendor_summary")
logger.setLevel(logging.DEBUG)

file_handler = logging.FileHandler("logs/get_vendor_summary.log")
file_handler.setLevel(logging.DEBUG)

formatter = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(message)s"
)
file_handler.setFormatter(formatter)

# Avoid duplicate handlers
if not logger.handlers:
    logger.addHandler(file_handler)


def create_vendor_sales_summart(conn):
    '''This function will merge the different tables to get the overall vendor summary and adding new columns in the resultant data'''
    vendor_sales_summart = pd.read_sql_query("""WITH FreightSummary AS (
        SELECT
            VendorNumber,
            SUM(Freight) AS FreightCost
        FROM vendor_invoice
        GROUP BY VendorNumber
    ),

    PurchaseSummary AS (
        SELECT
            p.VendorNumber,
            p.VendorName,
            p.Brand,
            p.Description,
            p.purchasePrice,
            pp.Price AS ActualPrice,
            pp.Volume,
            SUM(p.Quantity) AS TotalPurchaseQuantity,
            SUM(p.Dollars) AS TotalPurchaseDollars
        FROM purchases p
        JOIN purchase_prices pp
         ON p.Brand = pp.Brand
        WHERE p.PurchasePrice >0
        GROUP BY p.VendorNumber, p.VendorName, p.Brand, p.Description, p.purchasePrice, pp.Price,pp.Volume
    ),
    
    SalesSummary AS (
        SELECT
            VendorNo,
            Brand,
            SUM(SalesQuantity) AS TotalSalesQuantity,
            SUM(SalesPrice) AS TotalSalesPrice,
            SUM(SalesDollars) AS TotalSalesDollars,
            SUM(ExciseTax) AS TotalExciseTax
        FROM sales
        GROUP BY VendorNo, Brand
    )
    
    SELECT
        ps.VendorNumber,
        ps.VendorName,
        ps.Brand,
        ps.Description,
        ps.PurchasePrice,
        ps.ActualPrice,
        ps.Volume,
        ps.TotalPurchaseQuantity,
        ps.TotalPurchaseDollars,
        ss.TotalSalesQuantity,
        ss.TotalSalesDollars,
        ss.TotalSalesPrice,
        ss.TotalExciseTax,
        fs.FreightCost
    FROM PurchaseSummary ps
    LEFT JOIN SalesSummary ss
        ON ps.VendorNumber = ss.VendorNo
        AND ps.Brand = ss.Brand
    LEFT JOIN FreightSummary fs
        ON ps.VendorNumber = fs.VendorNumber
    ORDER BY ps.TotalPurchaseDollars DESC""",conn)

    return vendor_sales_summart


def clean_data(df):
    '''this function will clean the data'''
    # changing datatype to float
    df['Volume'] = df['Volume'].astype('float')

    # filling missing values with 0
    df.fillna(0, inplace = True)

    # removing spaces from categorical columns
    df['VendorName'] = df['VendorName'].str.strip()
    df['Description'] = df['Description'].str.strip()

    # creating new columns for better analysis
    vendor_sales_summart['GrossProfit'] = vendor_sales_summart['TotalSalesDollars'] - vendor_sales_summart['TotalPurchaseDollars']
    vendor_sales_summart['ProfitMargin'] = (vendor_sales_summart['GrossProfit'] / vendor_sales_summart['TotalSalesDollars'])*100
    vendor_sales_summart['StockTurnover'] = vendor_sales_summart['TotalSalesQuantity'] / vendor_sales_summart['TotalPurchaseQuantity']
    vendor_sales_summart['SalesToPurchaseRatio'] = vendor_sales_summart['TotalSalesDollars'] / vendor_sales_summart['TotalPurchaseDollars']

    return df

if __name__ == '__main__':
    # creating database connection
    conn.commit()
    conn.close()
    conn = sqlite3.connect('inventory.db')

    logger.info('Creating Vendor Summary Table.... ')
    summary_df = create_vendor_sales_summart(conn)
    logger.info(summary_df.head())

    logger.info('Cleaning Data.... ')
    clean_df = clean_data(summary_df)
    logger.info(clean_df.head())

    logger.info('Ingesting Data... ')
    ingest_db(clean_df, 'vendor_sales_summart',conn)
    logger.info('Completed')