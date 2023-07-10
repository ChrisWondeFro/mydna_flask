import pandas as pd
import os

# Helper function to validate data
def validate_data(df, col_name, valid_values):
    if not df[col_name].isin(valid_values).all():
        invalid_values = df[~df[col_name].isin(valid_values)][col_name].unique()
        raise ValueError(f"Invalid {col_name}(s): {', '.join(map(str, invalid_values))}")

def read_and_validate_data(file_path):
        if not os.path.exists(file_path):
            raise ValueError(f"File {file_path} does not exist")
         # Check the file extension and preprocess the file if needed
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
         # Fill missing values with 'N'
        df.fillna('N', inplace=True)

        if 'genotype' in df.columns:
        # Ensure genotype is exactly two characters long
            invalid_genotypes = df[df['genotype'].str.len() != 2]['genotype'].unique()
            if invalid_genotypes.size > 0:
                raise ValueError(f"Invalid genotype(s): {', '.join(invalid_genotypes)}")

            df[['allele1', 'allele2']] = df['genotype'].apply(lambda x: pd.Series(list(x)))
            df.drop(columns=['genotype'], inplace=True)

        # Check for required columns
        required_cols = {'rsid', 'chromosome', 'position', 'allele1', 'allele2'}
        if not required_cols.issubset(df.columns):
           missing_cols = required_cols - set(df.columns)
           raise ValueError(f"Required columns are missing: {', '.join(missing_cols)}")
        
        # Replace '0' with 'N'
        df.replace('0', 'N', inplace=True)

         # Validate the alleles
        valid_alleles = {'A', 'T', 'C', 'G', 'I', 'D', 'N'}
        validate_data(df, 'allele1', valid_alleles)
        validate_data(df, 'allele2', valid_alleles)

        # Validate chromosome values
        valid_chromosomes = set(range(1, 27)).union({'X', 'Y', 'MT'})
        validate_data(df, 'chromosome', valid_chromosomes)

        # Validate position values - must be positive integers
        if not (df['position'].astype(float).apply(float.is_integer) & (df['position'] > 0)).all():
          raise ValueError("Some positions are not valid (should be positive integers)")     
        # Remove 'rs' prefix from 'rsid' and convert to int
        df['rsid'] = df['rsid'].str.replace('rs', '').astype(int)    
 
        return df