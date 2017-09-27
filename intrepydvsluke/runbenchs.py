import multiprocessing as mp
import subprocess as sp
import time
import argparse as ap
from os import listdir
from os.path import isfile, join
import sys
import importlib
import psutil
from intrepyd.engine import EngineResult
from intrepyd.lustre2py import translator
from intrepyd import config

TIMEOUT = 300

def worker_intrepyd_br(result, mtime):
    """
    Executes a translated benchmark
    """
    enc = importlib.import_module('encoding')
    start = time.time()
    try:
        ctx, prop = enc.lustre2py_main_ctxless()
        breach = ctx.mk_backward_reach()
        breach.add_target(ctx.mk_not(prop))
        eng_result = breach.reach_targets()
        if eng_result == EngineResult.REACHABLE:
            result.value = 'Invalid'
        elif eng_result == EngineResult.UNREACHABLE:
            result.value = 'Valid'
        else:
            result.value = 'Unknown'
    except:
        result.value = 'Exception'
    mtime.value = time.time() - start

def worker_intrepyd_bmc(result, mtime):
    """
    Executes a translated benchmark
    """
    enc = importlib.import_module('encoding')
    start = time.time()
    result.value = 'Unknown'
    try:
        ctx, prop = enc.lustre2py_main_ctxless()
        bmc = ctx.mk_bmc()
        bmc.add_target(ctx.mk_not(prop))
        for depth in range(100000):
            bmc.set_current_depth(depth)
            eng_result = bmc.reach_targets()
            if eng_result == EngineResult.REACHABLE:
                result.value = 'Invalid'
                break
    except:
        result.value = 'Exception'
    mtime.value = time.time() - start

def worker_luke(fname, result, mtime):
    """
    Executes luke
    """
    start = time.time()
    try:
        result.value = 'Unknown'
        cmdline = ['luke.exe', '--int', '32', '--node', 'top', '--verify'] + [fname]
        out = sp.check_output(cmdline)
        if 'Falsified' in out:
            result.value = 'Invalid'
        elif 'Valid' in out:
            result.value = 'Valid'
    except:
        result.value = 'Exception'
    mtime.value = time.time() - start

def killer(proc_name):
    """
    Kills the process whose name is proc_name
    """
    for proc in psutil.process_iter():
        if proc.name() == proc_name:
            proc.kill()
            break

def run_with_timeout(fname, timeout, tool):
    """
    Runs a benchmark with a time limit
    """
    if not tool in set(['intrepyd_br', 'intrepyd_bmc', 'intrepyd_parallel', 'luke']):
        raise RuntimeError('Could not find specified tool')
    result = mp.Array('c', 15)
    mtime = mp.Value('d', 0.0)
    if tool == 'luke':
        proc = mp.Process(target=worker_luke, args=(fname, result, mtime))
    elif tool == 'intrepyd_br':
        proc = mp.Process(target=worker_intrepyd_br, args=(result, mtime))
    elif tool == 'intrepyd_bmc':
        proc = mp.Process(target=worker_intrepyd_bmc, args=(result, mtime))
    else:
        assert tool == 'intrepyd_parallel'
        result_bmc = mp.Array('c', 15)
        result_br = mp.Array('c', 15)
        mtime_bmc = mp.Value('d', 0.0)
        mtime_br = mp.Value('d', 0.0)
        proc_bmc = mp.Process(target=worker_intrepyd_bmc, args=(result_bmc, mtime_bmc))
        proc_br = mp.Process(target=worker_intrepyd_br, args=(result_br, mtime_br))
        proc_bmc.start()
        proc_br.start()
        bmc_timeout = True
        br_timeout = True
        start = time.time()
        while True:
            if not proc_bmc.is_alive():
                proc_br.terminate()
                bmc_timeout = False
            elif not proc_br.is_alive():
                proc_bmc.terminate()
                br_timeout = False
            elif time.time() - start > timeout:
                proc_bmc.terminate()
                proc_br.terminate()
            else:
                time.sleep(.1)
                continue
            break
        proc_bmc.join()
        proc_br.join()
        if bmc_timeout and br_timeout:
            return 'Timeout', timeout
        if not bmc_timeout:
            return result_bmc.value, mtime_bmc.value
        else:
            assert not br_timeout
            return result_br.value, mtime_br.value
        assert False
    proc.start()
    proc.join(timeout=timeout)
    if proc.is_alive():
        proc.terminate()
        if tool == 'luke':
            killer('luke.exe')
        return 'Timeout', timeout
    return result.value, mtime.value

def doit():
    """
    Main
    """
    argument_parser = ap.ArgumentParser(description='Runs a set of benchmars')
    argument_parser.add_argument('filelist', type=str,
                                 help='a text file that specifies the list of files to process')
    argument_parser.add_argument('tool', type=str,
                                 help='specifies the tool to be run (intrepyd_br, intrepyd_bmc, intrepyd_parallel, luke)')
    argument_parser.add_argument('-t', '--timeout', type=int, default=TIMEOUT,
                                 help='specifies the timeout in seconds for each benchmark')
    argument_parser.add_argument('-c', '--config', default='config.json',
                                 help='Specifies a config file')
    argument_parser.add_argument('-b', '--benchmarks', type=str, default='../../kind2-benchmarks',
                                 help='Specifies the path to kin2-benchmarks suite')
    parsed_args = argument_parser.parse_args()
    filelist = open(parsed_args.filelist).readlines()
    filtered_filelist = [line.strip() for line in filelist if len(line) > 0 and line[0] != '#']
    len_filelist = len(filtered_filelist)
    cfg = config.Config.get_instance(parsed_args.config)
    i = 0
    for fname in filtered_filelist:
        i += 1
        fullname = parsed_args.benchmarks + '/' + fname
        if parsed_args.tool != 'luke':
            translator.translate(fullname, 'top', 'encoding.py', cfg['type.real'])
            time.sleep(1) # Give some extra time to write encoding.py to a file
        result, mtime = run_with_timeout(fullname, parsed_args.timeout, parsed_args.tool)
        # print '%4.1f %% %s %s %.2f' % (100.0 * i / len_filelist, fname, result, mtime)
        print '%s %s %.2f' % (fname, result, mtime)
        sys.stdout.flush()

if __name__ == "__main__":
    doit()
