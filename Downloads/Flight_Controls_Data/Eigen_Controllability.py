import numpy as np, joblib

d = joblib.load('Outputs/drone_dynamics_best_model.pkl')
A = np.asarray(d['A']); B = np.asarray(d['B'])
STATE_VARS = d['state_vars']; INPUT_VARS = d['input_vars']
print('A shape', A.shape, 'B shape', B.shape)
# eigenvalues (stability)
eigvals = np.linalg.eigvals(A)
print('A eigenvalues:', eigvals)
# controllability rank
n = A.shape[0]
ctrb = np.hstack([np.linalg.matrix_power(A, i) @ B for i in range(n)])
rank = np.linalg.matrix_rank(ctrb)
print('Controllability rank:', rank, '/', n)
# Input ranges in saved bundle
print('u_min, u_max:', d.get('u_min'), d.get('u_max'))