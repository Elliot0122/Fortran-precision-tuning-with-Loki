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


def dummy_apply_precision_assignment(precision_assignment):
    print("\n** dummy transformation NOT actually applying the following precision assignment to funarc:")
    pprint(precision_assignment)
    return


# return the cost if successfully compiled, run, and passed correctness checks; else, returns inf
def compile_run_eval():

    print("\n** compiling")
    subprocess.run(
        "make",
        cwd="funarc",
        shell=True,
        executable="/bin/bash",
    )

    print("\n** running")
    subprocess.run(
        f"mkdir variants/{COUNTER:0>4} && ./main | tee variants/{COUNTER:0>4}/outlog.txt 2>&1",
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

        dummy_apply_precision_assignment(precision_assignment)
        precision_assignment['cost'] = compile_run_eval()
        my_search_algorithm.feedback(precision_assignment)
        precision_assignment = my_search_algorithm.get_next()

    print("\n\n** Done; best variant:")
    pprint(my_search_algorithm.current_best_configuration)