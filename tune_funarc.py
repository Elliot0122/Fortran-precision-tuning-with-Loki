from loki import Visitor, flatten, Sourcefile, FindNodes, VariableDeclaration, Literal, fgen
from pathlib import Path
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


def walk_ir(ir, types=None, across_scopes=False):
    """Depth-first search of the control flow tree."""

    class WalkVisitor(Visitor):

        def visit_Sourcefile(self, o, **kwargs):
            if not across_scopes:
                return [o]
            children = flatten(self.visit(ch, **kwargs) for ch in o.ir)
            return [o] + children

        visit_ProgramUnit = visit_Sourcefile

        def visit_Node(self, o, **kwargs):
            children = flatten(self.visit(ch, **kwargs) for ch in o.children)
            return [o] + children
        
    for node in flatten(WalkVisitor().visit(ir)):
        if node and (types is None or isinstance(node, types)):
            yield node


def apply_precision_assignment(precision_assignment):

    # create directory that will eventually contain the transformed funarc code and the outlog.txt
    # from the run that the eval script will use as input to measure correctness & performance
    subprocess.run(
        f"mkdir variants/{COUNTER:0>4}",
        cwd="funarc",
        shell=True,
        executable="/bin/bash",
    )

    with open(f"funarc/variants/{COUNTER:0>4}/precision_assignment.txt", "w") as f:
        pprint(precision_assignment['config'], stream=f)

################################################################################################################################################################
    # this block calls the loki transformation which reads in "target_module.f90" and generates the variant
    # which reflects the "config" entry in the precision_assignment dict; saved as "target_module.f90" in variants/{COUNTER:0>4}.
    # At the start of compile_run_eval(), the transformed file will be copied to the necessary location
    # At the end of compile_run_eval(), the original file will be restored

    # prune the precision assignment to only include the scopedVarName
    candidates = {}
    for i in precision_assignment['config']:
        key = i.split('::')[-1]
        candidates[key] = precision_assignment['config'][i]

    # source file to modify
    source = Sourcefile.from_file("funarc/target_module.f90", preprocess=True)

    # find all real variables in the source file
    variables = []
    for node in walk_ir(source.ir, across_scopes=True):
        variables.extend(FindNodes(match=VariableDeclaration, mode='type', greedy=False).visit_TypeDef(node))

    # apply the precision assignment
    for v in variables:
        for s in v.symbols:
            if s in candidates:
                typeS = s.type
                typeS.kind = Literal(candidates[s])
                s.type = typeS

    # write the modified source file to disk
    Sourcefile.to_file(fgen(source.ir), Path(f"funarc/variants/{COUNTER:0>4}/target_module.f90"))
################################################################################################################################################################

# return the cost if successfully compiled, run, and passed correctness checks; else, returns inf
def compile_run_eval():

    # save the original file, move the transformed file, and compile
    print("** compiling")
    try:
        subprocess.run(
            f"mv target_module.f90 target_module.f90.orig && cp variants/{COUNTER:0>4}/target_module.f90 . && make",
            cwd="funarc",
            shell=True,
            executable="/bin/bash",
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
    except subprocess.CalledProcessError as e:
        print("\t COMPILE ERROR")
        compile_log = e.output.decode("utf-8").splitlines()
        with open(f"funarc/variants/{COUNTER:0>4}/compile_error.txt", "w") as f:
            for line in compile_log:
                f.write(line+"\n")
        return float("inf")


    # execute and save stdout and stderr to be read by the eval program
    print("** running")
    try:
        with open(f"funarc/variants/{COUNTER:0>4}/outlog.txt", "w") as outlog:
            subprocess.run(
                "./main",
                cwd="funarc",
                shell=True,
                executable="/bin/bash",
                check=True,
                stdout=outlog,
                stderr=outlog,
            )
    except subprocess.CalledProcessError as e:
        print("\t RUNTIME ERROR")
        subprocess.run(
            f"mv funarc/variants/{COUNTER:0>4}/outlog.txt funarc/variants/{COUNTER:0>4}/runtime_error.txt"
        )
        return float("inf")

    print("** evaluating")
    try:
        output = subprocess.run(
            f"python3 eval.py variants/{COUNTER:0>4} variants/0000",
            stdout=subprocess.PIPE,
            text=True,
            cwd="funarc",
            shell=True,
            executable="/bin/bash",
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print("\t EVAL PROGRAM ERROR")
        assert(False) # the eval program should not fail

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