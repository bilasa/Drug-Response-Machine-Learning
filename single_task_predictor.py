import numpy as np
import pandas as pd

from sklearn.preprocessing import StandardScaler
from sklearn_pandas import DataFrameMapper
from sklearn.linear_model import ElasticNetCV
from sklearn.datasets import make_regression
from scipy import stats

################# SINGLE TASK DRUG RESPONSE PREDICTOR ################# 

# Takes two numpy arrays as input: y_actual, y_predicted
# Returns two sample groups:
#   The first contains a list of predicted drug response values for which the patient's actual response was 0
#   The second contains a list of predicted drug response values for which the patient's actual response was 1
def get_t_test_groups(y_actual, y_predicted):
    
    # Ensure the sizes are the same
    try:
        assert len(y_actual) == len(y_predicted)
    except AssertionError:
        print("AssertionError: size of y_actual and y_predicted must be the same")
        print("y_actual size: " + str(len(y_actual)))
        print("y_predicted size: " + str(len(y_predicted)))

    # Construct the two sample groups
    drug_responses_0 = []
    drug_responses_1 = []
    for i in range(len(y_actual)):
        if y_actual[i] == 0:
            drug_responses_0.append(y_predicted[i])
        elif y_actual[i] == 1:
            drug_responses_1.append(y_predicted[i])

    return drug_responses_0, drug_responses_1

# Takes in y_test and converts the four categories to 0 and 1
# "Complete response" and "Partial response" are mapped to 1
# "Stable disease" and "Clinical progressive disease" are mapped to 0
def category_to_binary(y_test):
    y_test_binary = y_test
    for drug_name in list(y_test_binary.columns.values):
        y_test_binary = y_test_binary.replace("Complete Response", 1)
        y_test_binary = y_test_binary.replace("Partial Response", 1)
        y_test_binary = y_test_binary.replace("Stable Disease", 0)
        y_test_binary = y_test_binary.replace("Clinical Progressive Disease", 0)
    return y_test_binary

# Path to datasets
data_path = '../Data/'

# Load training and test set
x_train = pd.read_csv(data_path + 'gdsc_expr_postCB.csv', index_col=0, header=None).T.set_index('cell line id')#.iloc[0:200, 0:200]
y_train = pd.read_csv(data_path + 'gdsc_dr_lnIC50.csv', index_col=0, header=None).T.set_index('cell line id')#.iloc[0:200, ]
x_test = pd.read_csv(data_path + 'tcga_expr_postCB.csv', index_col=0, header=None).T.set_index('patient id')#.iloc[0:200, 0:200]
y_test = pd.read_csv(data_path + 'tcga_dr.csv', index_col=0, header=None).T.set_index('patient id')#.iloc[0:200, ]
y_test_binary = category_to_binary(y_test)

# Normalize data for mean 0 and standard deviation of 1
ss = StandardScaler()
x_train = pd.DataFrame(ss.fit_transform(x_train), index = x_train.index, columns = x_train.columns)
y_train = pd.DataFrame(ss.fit_transform(y_train), index = y_train.index, columns = y_train.columns)
x_test = pd.DataFrame(ss.fit_transform(x_test), index = x_test.index, columns = x_test.columns)

# Verify axes match
#compare_column_headers(x_train, x_test)
#compare_column_headers(y_train, y_test)
#compare_row_headers(x_train, y_train)
#compare_row_headers(x_test, y_test)

# Matrix to store y_test predictions
y_test_prediction = pd.DataFrame(index=y_test.index, columns=y_test.columns)

# Matrix to store drug statistics, including t-statistic and p-value for each drug
results = y_test.describe().T.join(pd.DataFrame(index=y_test.columns, columns=['T-statistic', 'P-value']))

# Predict the response for each drug individually
for drug in y_train:

    # Keep only one drug column
    y_train_single = y_train[[drug]]

    # Drop cell line ids in y_train where drug response is NaN
    y_train_single = y_train_single.dropna()
    non_null_ids = y_train_single.index
    
    # Drop cell line ids in x_train where drug response is NaN
    x_train_single = x_train[x_train.index.isin(non_null_ids)]

    # Create elastic net model with five-fold cross validation 
    print("Fitting ElasticNetCV for drug: " + drug)
    regr = ElasticNetCV(cv=5, random_state=0)
    regr.fit(x_train_single.values, np.ravel(y_train_single.values))

    # Produce prediction vector for y_test drug response
    print("Predicting y test...")
    y_test_prediction_single = regr.predict(x_test) # RANDOM NUMBERS FOR TESTING: y_test_prediction_single = np.random.rand(len(y_train[[drug]].values))

    # Insert prediction vector into matrix of predictions
    y_test_prediction[drug] = y_test_prediction_single

    # Get the actual y_test binary values
    y_test_actual_single = y_test_binary[[drug]]

    # Get sample groups for category 0 and category 1
    drug_responses_0, drug_responses_1 = get_t_test_groups(y_test_actual_single.values, y_test_prediction_single)
    
    # Perform T-test
    print("Performing t-test...")
    t, p = stats.ttest_ind(drug_responses_0, drug_responses_1)
    results.loc[drug, 'T-statistic'] = t
    results.loc[drug, 'P-value'] = p

# Store predictions and results in csv file
y_test_prediction.to_csv(data_path + 'tcga_dr_prediction(normalized).csv')
results.to_csv(data_path + 'results.csv')

# Cross validation: used to select hyperparameters
#   Do it with diff values of alpha
#   Choose a loss function to choose the alpha that minimizes loss
#       Ex: euclidean norm, cosine similarity....
#   Find alpha with "path" --> elasticnet CV, lasso CV
#   Scikit has modules for cross validation and hyperparam selection
#   If multiple hyperparams, can have a LOT of possibilites --> scikit learn help save time
# Lasso
#   Lasso minimize 1/2 || y - x ||
#   L1: minimize absolute values of some of weights --> imposes sparsity
# Elastic
#   Has extra L2 norm of w

# Normalization of original data
#   Figure data distribution
#   
# Improve code
#   Pandas, generalizability of data loading
#   Hyperparameter tuning
#   Normalization
#   T-test: scipy
#   Can report: cross validation accuracy (check for overfitting/underfitting)
#   Can try nonlinear models: e.g. Support vector regression

# Sensitive: complete response, partial response
# Resistant: stable disease, progressive disease

# Spend time learning multi-task methods

# Profile compute canada: find what is accessible to us, etc...
#       Takes time when requesting resources: in case need for next semester
#       Access GPUs: good for neural networks

# Right things down for report immediately: so that he can give us feedback