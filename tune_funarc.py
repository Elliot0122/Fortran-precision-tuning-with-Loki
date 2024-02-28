from Precimonious import PrecimoniousSearch
from pprint import pprint
import subprocess
import random

random.seed(1)

# global
COUNTER = -1

# dummy version that returns manually-constructed search space
def dummy_generate_search_space():
    
    # contains pairs of the form scopedVarName : possibleKinds
    search_space = {
                        "::target_module::funarc::h"    : [4,8],
                        "::target_module::funarc::t1"   : [4,8],
                        "::target_module::funarc::t2"   : [4,8],
                        "::target_module::funarc::dppi" : [4,8],
                        "::target_module::funarc::s1"   : [4,8],
                        "::target_module::fun::x"       : [4,8],
                        "::target_module::fun::t1"      : [4,8],
                        "::target_module::fun::d1"      : [4,8],
                    }
    return search_space


def apply_precision_assignment(precision_assignment):

    # create directory that will eventually contain the transformed funarc code and the outlog.txt
    # from the run that the eval script will use as input to measure correctness & performance
    subprocess.run(
        f"mkdir variants/{COUNTER:0>4}",
        cwd="funarc",
        shell=True,
        executable="/bin/bash",
    )

################################################################################################################################################################
    # TODO: change this block to call your loki transformation which will read in "target_module.f90" and generate the variant
    # which reflects the "config" entry in the precision_assignment dict; save it as "target_module.f90" in variants/{COUNTER:0>4}.
    # At the start of compile_run_eval(), the transformed file will be copied to the necessary location
    # At the end of compile_run_eval(), the original file will be restored
    subprocess.run(
        f"echo '** dummy transformation NOT actually applying the following precision assignment to funarc' && cp target_module.f90 variants/{COUNTER:0>4}",
        cwd="funarc",
        shell=True,
        executable="/bin/bash",
    )
    print("\n")
    pprint(precision_assignment)
################################################################################################################################################################

# return the cost if successfully compiled, run, and passed correctness checks; else, returns inf
def compile_run_eval():

    # save the original file, move the transformed file, and compile
    print("\n** compiling")
    subprocess.run(
        f"mv target_module.f90 target_module.f90.orig && cp variants/{COUNTER:0>4}/target_module.f90 . && make",
        cwd="funarc",
        shell=True,
        executable="/bin/bash",
    )

    # execute and save stdout and stderr to be read by the eval program
    print("\n** running")
    subprocess.run(
        f"./main | tee variants/{COUNTER:0>4}/outlog.txt 2>&1",
        cwd="funarc",
        shell=True,
        executable="/bin/bash",
    )

    print("\n** evaluating")
    output = subprocess.run(
        f"python3 eval.py variants/{COUNTER:0>4} variants/0000",
        stdout=subprocess.PIPE,
        text=True,
        cwd="funarc",
        shell=True,
        executable="/bin/bash",
    )
    cost = float(output.stdout)
    print(f"\tcost: {abs(cost)}")
    if cost < 0:
        print(f"\tcorrectness check: FAILED")
        cost = float("inf")
    else:
        print(f"\tcorrectness check: PASSED")

    # reset for next call to apply_precision_assignment()
    subprocess.run(
        f"mv target_module.f90.orig target_module.f90",
        cwd="funarc",
        shell=True,
        executable="/bin/bash",
    )

    return cost


if __name__ == "__main__":

    # setup
    subprocess.run(
        "make reset && mkdir variants",
        cwd="funarc",
        shell=True,
        executable="/bin/bash",
    )

    search_space = dummy_generate_search_space()

    my_search_algorithm = PrecimoniousSearch(search_space)

    precision_assignment = my_search_algorithm.get_next()

    while (precision_assignment):
        COUNTER += 1
        print(f"\n============ {COUNTER:0>4} ============")

        apply_precision_assignment(precision_assignment)
        precision_assignment['cost'] = compile_run_eval()
        my_search_algorithm.feedback(precision_assignment)
        precision_assignment = my_search_algorithm.get_next()

    print("\n\n** Done; best variant:")
    pprint(my_search_algorithm.current_best_configuration)