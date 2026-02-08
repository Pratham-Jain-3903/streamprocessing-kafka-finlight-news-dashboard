"""
__summary__: 
    "spark code for:
            1.  Ingesting news data from Finlight API and storing it in parquet format
            2.  sentiment analysis using pre-trained models
            3.  storing the processed data in iceberg tables
            4.  pull stock market data from yfinance API
            5.  storing stock data in iceberg tables
            6. scheduling the job using airflow DAGs "
"""
