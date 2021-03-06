import errno
import os
import bnpy
import tempfile
import shutil
import shlex
import sys

from subprocess import Popen, PIPE
from threading import Timer


def mkdir_p(path):
    """
    https://stackoverflow.com/questions/600268/mkdir-p-functionality-in-python

    :param path:
    :return:
    """
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


# Disable
def blockPrint():
    sys.stdout = open(os.devnull, 'w')


# Restore
def enablePrint():
    sys.stdout = sys.__stdout__


def fit_model(name, dataset):
    """

    :param name:
    :param dataset: bnpy.data.XData object
    :return:
    """
    gamma = 1.0              # Prior on dirichlet dispersion parameter
    sF = 1.0                 # Prior covariance matrix is Identity * sF
    K = 5                    # Numver of initial clusters


    workdir = tempfile.mkdtemp(prefix=name)
    outputdir = 'trymoves-K={K}-gamma={G}-ECovMat={Cov}-moves=birth,merge,shuffle/'.format(K=K,
                                                                                           G=gamma,
                                                                                           Cov=sF)
    output_path = os.path.join(workdir, outputdir)

    blockPrint()
    trained_model, info_dict = bnpy.run(dataset,
                                        'DPMixtureModel',
                                        'Gauss',
                                        'memoVB',
                                        output_path=output_path,
                                        nLap=100,
                                        nTask=1,
                                        nBatch=1,
                                        gamma0=gamma,
                                        sF=sF,
                                        ECovMat='eye',
                                        K=K,
                                        moves='birth,merge,shuffle')
    enablePrint()

    shutil.rmtree(workdir)
    return trained_model


def run(cmd, timeout_sec):
    """
    https://stackoverflow.com/questions/1191374/using-module-subprocess-with-timeout
    :param cmd:
    :param timeout_sec:
    :return:
    """
    proc = Popen(shlex.split(cmd), stdout=PIPE, stderr=PIPE)
    timer = Timer(timeout_sec, proc.kill)

    try:
        timer.start()
        stdout, stderr = proc.communicate()

    finally:
        timer.cancel()

    return stdout, stderr


def parallel_fit(name, dataset, save_output=False, timeout_sec=900):
    """

    :param name:
    :param dataset: bnpy.data.XData object
    :return:
    """
    gamma = 1.0
    sF = 1.0
    K = 5

    workdir = tempfile.mkdtemp(prefix=name)
    output_dir = 'trymoves-K={K}-gamma={G}-ECovMat={Cov}-moves=birth,merge,shuffle/'.format(K=K,
                                                                                             G=gamma,
                                                                                             Cov=sF)
    output_path = os.path.join(workdir, output_dir)

    csv_file_path = os.path.join(workdir, "%s.csv" % name)
    dataset.to_csv(csv_file_path)

    cmd = """
          python -m bnpy.Run {data} 
                    DPMixtureModel 
                    Gauss 
                    memoVB 
                    --K {K}
                    --nLap 100
                    --nTask 1
                    --nBatch 1
                    --gamma0 {G}
                    --sF {sF}
                    --ECovMat eye
                    --moves birth,merge,shuffle
                    --output_path {output}
          """.format(data=csv_file_path,
                     K=K,
                     G=gamma,
                     sF=sF,
                     output=output_path)

    stdout, stderr = run(cmd, timeout_sec=timeout_sec)

    hmodel = bnpy.ioutil.ModelReader.load_model_at_prefix(os.path.join(output_path, '1'),
                                                          prefix='Best')

    if not save_output:
        shutil.rmtree(workdir)

    else:
        print("Output:\n%s" % workdir)

    return hmodel
