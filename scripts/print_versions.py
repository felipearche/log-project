import sys
import numpy
import sklearn
import matplotlib
import psutil

print("python==" + sys.version.split()[0])
print("numpy==" + numpy.__version__)
print("scikit-learn==" + sklearn.__version__)
print("matplotlib==" + matplotlib.__version__)
print("psutil==" + psutil.__version__)
try:
    import scipy

    print("scipy==" + scipy.__version__)
except Exception as e:
    print("scipy import error:", e)
