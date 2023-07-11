import pandas as pd
import os

def validate_data(df, col_name, valid_values):
    if not df[col_name].isin(valid_values).all():
        invalid_values = df[~df[col_name].isin(valid_values)][col_name].unique()
        raise ValueError(f"Invalid {col_name}(s): {', '.join(map(str, invalid_values))}")

def read_and_validate_data(file_path):
        if not os.path.exists(file_path):
            raise ValueError(f"File {file_path} does not exist")
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path, sep=',', comment='#')
        elif file_path.endswith('.tsv') or file_path.endswith('.txt'):
            df = pd.read_csv(file_path, sep=r'\s+', comment='#')
        elif file_path.endswith('.xlsx'):
            df = pd.read_excel(file_path, comment='#')
        else:
            raise ValueError('File format not supported')

        print(df.head())
        
         # Make column names case insensitive, ignore leading/trailing whitespaces and replace whitespaces with underscore
        df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
         
        # Check for required columns
        required_cols = {'rsid', 'position'}
        if not required_cols.issubset(df.columns):
           missing_cols = required_cols - set(df.columns)
           raise ValueError(f"Required columns are missing: {', '.join(missing_cols)}")
        
        # Remove 'rs' prefix from 'rsid' and convert to int
        df['rsid'] = df['rsid'].str.replace('rs', '').astype(int)    
 
        return df