import os

for name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'KMP_NUM_THREADS'):
    os.environ.setdefault(name, '1')